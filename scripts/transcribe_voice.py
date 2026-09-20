"""Voice notes: speak them, transcribe them, route them through the SAME triage.

    python scripts/transcribe_voice.py --speak            # TTS  -> data/voice/*.mp3
    python scripts/transcribe_voice.py                    # STT  -> data/voice-notes.json
    python scripts/transcribe_voice.py --route            # STT  -> queue, merged into the cache
    python scripts/transcribe_voice.py --speak --route    # all three, in order
    python scripts/transcribe_voice.py --force            # ignore the transcript cache
    python scripts/transcribe_voice.py --dry-run          # say what it would do, call nothing

WHAT THIS IS, AND WHO DID WHAT
------------------------------
Maya's audience sends voice notes (case-001-maya.json -> voice._source, "E-06.1 voice
note (00:52)"). We have none of her audience's real audio and we are not going to
pretend otherwise, so this script SYNTHESISES four, transcribes them, and hands the
transcript to the existing DM pipeline.

  * **OpenAI does the SPEAKING.** `tts-1`, four different voices. Recorded as
    `tts_model` and `voice` on every record.
  * **OpenAI does the HEARING.** `whisper-1`, `response_format=verbose_json`, which
    is where `seconds` comes from - the duration is read off the API response, not
    guessed, and `transcribe_ms` is measured around the call.
  * **Jev does the JUDGING.** The transcript goes into `run_triage()` as
    `state.message`, which is the identical field a typed DM occupies. Same
    questions, same safety gate, same confidence gate. A voice note is a message
    whose text arrived differently, and nothing downstream gets told it is special.

Same split as the images (docs/10 section 15). Jev never hears a waveform.

RULES THIS SCRIPT HOLDS ITSELF TO
---------------------------------
1. **Synthetic, and labelled everywhere.** In the filename (`synthetic-...`), in the
   mp3's own ID3 tag, in `data/voice-notes.json`, on the queue card (`voice.synthetic`,
   `voice.disclosure`) and in the `X-Synthetic-Audio: true` header the audio route
   sends. A judge must never be able to think we captured a real DM.
2. **Prefetch only.** Nothing in `backend/` imports this. The API serves the mp3 as a
   static file and reads the transcript out of a JSON file on disk.
3. **Idempotent.** Transcripts are cached under `cache/voice/<sha256 of the audio>.json`,
   so a second run makes no API calls and costs nothing. TTS skips any file that
   already exists unless `--speak --force`.
4. **Never fabricate.** A call that fails is written back with an `error` and no
   transcript. It is never filled in with what we asked the TTS to say.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import pathlib
import sys
import time
from datetime import datetime, timezone

import httpx

try:
    from dotenv import load_dotenv
except ImportError:                                              # noqa: BLE001
    load_dotenv = None

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

REPO = pathlib.Path(__file__).resolve().parent.parent
DATA = REPO / "data"
VOICE_DIR = DATA / "voice"
NOTES_FILE = DATA / "voice-notes.json"
STT_CACHE = REPO / "cache" / "voice"

TTS_MODEL = "tts-1"
STT_MODEL = "whisper-1"

# Published list prices at the time of writing. Only ever multiplied by something we
# actually counted: characters we really sent, seconds the API really reported.
TTS_USD_PER_M_CHARS = 15.0
STT_USD_PER_MINUTE = 0.006

DISCLOSURE = ("Synthetic demo audio. Spoken by OpenAI " + TTS_MODEL + " from a script we "
              "wrote, transcribed by OpenAI " + STT_MODEL + ". It is not a recording of a "
              "real person and no real audience audio exists in this repo.")

# ------------------------------------------------------------------ the four notes
# Each one is here to exercise a different path through the triage that already exists.
MESSAGES = [
    {"id": "v-001", "ref": "S-VN.1", "from": "@noor", "voice": "nova",
     "exercises": "pick_for_me with skin + budget stated",
     "script": "hiya, so my skin's been really dry and a bit red lately, "
               "I've got about sixty quid, what should I actually get"},
    {"id": "v-002", "ref": "S-VN.2", "from": "@bexm", "voice": "shimmer",
     "exercises": "is_it_worth_it against a named product and its price ceiling",
     "script": "is the glass drop actually worth sixty-two pounds or am I being silly"},
    {"id": "v-003", "ref": "S-VN.3", "from": "@harrietj", "voice": "alloy",
     "exercises": "THE SAFETY GATE. This one must come back referred.",
     "script": "um so I'm about six weeks pregnant and I just wanted to check "
               "if any of this is safe to keep using"},
    {"id": "v-004", "ref": "S-VN.4", "from": "@sana.k", "voice": "fable",
     "exercises": "not_a_question - nothing to sell, and she should not try",
     "script": "honestly you're the only person I trust on this stuff, "
               "just wanted to say thanks"},
]


def filename(m: dict) -> str:
    return "synthetic-" + m["id"] + "-" + m["voice"] + ".mp3"


# ------------------------------------------------------------------ ID3, so the FILE says it
def _frame(fid: bytes, data: bytes) -> bytes:
    n = len(data)
    return fid + bytes([(n >> 24) & 0xFF, (n >> 16) & 0xFF, (n >> 8) & 0xFF, n & 0xFF]) \
        + b"\x00\x00" + data


def _text_frame(fid: bytes, text: str) -> bytes:
    return _frame(fid, b"\x00" + text.encode("latin-1", "replace"))


def id3_tag(m: dict) -> bytes:
    """A minimal ID3v2.3 tag that says SYNTHETIC even if the mp3 is downloaded alone.

    The label has to survive the file leaving our API, so it goes in the bytes too and
    not only on the wire.
    """
    comment = (DISCLOSURE + " Script: " + m["script"]).encode("latin-1", "replace")
    frames = b"".join([
        _text_frame(b"TIT2", "SYNTHETIC demo voice note " + m["id"]),
        _text_frame(b"TPE1", "OpenAI " + TTS_MODEL + " (voice: " + m["voice"] + ") - not a real person"),
        _text_frame(b"TALB", "tano hackathon - synthetic demo audio"),
        _text_frame(b"TCON", "Speech"),
        _frame(b"COMM", b"\x00eng" + b"disclosure\x00" + comment),
    ])
    n = len(frames)
    size = bytes([(n >> 21) & 0x7F, (n >> 14) & 0x7F, (n >> 7) & 0x7F, n & 0x7F])
    return b"ID3\x03\x00\x00" + size + frames


# ------------------------------------------------------------------ OpenAI
def key() -> str:
    if load_dotenv:
        load_dotenv(REPO / ".env")
    k = os.environ.get("OPENAI_API_KEY", "")
    if not k:
        print("!! OPENAI_API_KEY is not set. Nothing can be spoken or transcribed.")
        sys.exit(2)
    return k


def speak(m: dict, oa: str, timeout: float = 120.0) -> tuple:
    """POST /v1/audio/speech -> mp3 bytes. Returns (bytes, seconds, usd)."""
    t0 = time.perf_counter()
    r = httpx.post("https://api.openai.com/v1/audio/speech",
                   headers={"Authorization": "Bearer " + oa},
                   json={"model": TTS_MODEL, "voice": m["voice"], "input": m["script"],
                         "response_format": "mp3", "speed": 0.95},
                   timeout=timeout)
    dt = time.perf_counter() - t0
    if r.status_code >= 400:
        raise RuntimeError("TTS HTTP " + str(r.status_code) + ": " + r.text[:160])
    usd = len(m["script"]) / 1_000_000.0 * TTS_USD_PER_M_CHARS
    return r.content, dt, usd


def transcribe(path: pathlib.Path, oa: str, timeout: float = 180.0) -> tuple:
    """POST /v1/audio/transcriptions -> (payload, measured ms).

    `verbose_json` is what gives us `duration`. The number on the wire is OpenAI's
    reading of the audio, not a constant we typed.
    """
    files = {"file": (path.name, path.read_bytes(), "audio/mpeg")}
    data = {"model": STT_MODEL, "response_format": "verbose_json"}
    t0 = time.perf_counter()
    r = httpx.post("https://api.openai.com/v1/audio/transcriptions",
                   headers={"Authorization": "Bearer " + oa},
                   files=files, data=data, timeout=timeout)
    ms = int((time.perf_counter() - t0) * 1000)
    if r.status_code >= 400:
        raise RuntimeError("STT HTTP " + str(r.status_code) + ": " + r.text[:160])
    return r.json(), ms


# ------------------------------------------------------------------ step 1: speak
def step_speak(oa: str, force: bool, dry: bool) -> None:
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    print("\nSPEAK  (OpenAI " + TTS_MODEL + ", four voices, synthetic on purpose)")
    total = 0.0
    for m in MESSAGES:
        p = VOICE_DIR / filename(m)
        if p.exists() and not force:
            print("  %-34s exists, skipped (%d KB)" % (p.name, p.stat().st_size // 1024))
            continue
        if dry:
            print("  %-34s would speak %d chars in '%s'" % (p.name, len(m["script"]), m["voice"]))
            continue
        audio, dt, usd = speak(m, oa)
        p.write_bytes(id3_tag(m) + audio)
        total += usd
        print("  %-34s %6.2fs  %5d KB  voice=%-8s %d chars  $%.5f"
              % (p.name, dt, p.stat().st_size // 1024, m["voice"], len(m["script"]), usd))
    if total:
        print("  TTS cost: $%.5f" % total)
    # A README next to the files, for anyone who finds the folder without the API.
    (VOICE_DIR / "README.md").write_text(
        "# data/voice/ - SYNTHETIC audio\n\n"
        + DISCLOSURE + "\n\n"
        "Every file in here was generated by `scripts/transcribe_voice.py --speak`. The\n"
        "scripts we asked the TTS to read, the voice used and the transcript that came\n"
        "back are all in `data/voice-notes.json`. Each mp3 also carries an ID3 tag saying\n"
        "the same thing, so the label survives the file being downloaded on its own.\n\n"
        "No real audience audio exists in this repository and none was ever collected.\n",
        encoding="utf-8")


# ------------------------------------------------------------------ step 2: transcribe
def step_transcribe(oa: str, force: bool, dry: bool) -> list:
    STT_CACHE.mkdir(parents=True, exist_ok=True)
    print("\nTRANSCRIBE  (OpenAI " + STT_MODEL + ", response_format=verbose_json)")
    out, spend, hits, calls = [], 0.0, 0, 0
    for m in MESSAGES:
        p = VOICE_DIR / filename(m)
        rec = {"id": m["id"], "ref": m["ref"], "from": m["from"],
               "file": p.name, "audio_url": "/api/voice/" + p.name,
               "synthetic": True, "tts_model": TTS_MODEL, "voice": m["voice"],
               "tts_script": m["script"], "exercises": m["exercises"],
               "disclosure": DISCLOSURE, "model": STT_MODEL}
        if not p.exists():
            rec.update({"transcript": None, "seconds": None, "transcribe_ms": None,
                        "error": "no audio file - run --speak first"})
            print("  %-34s MISSING. Run --speak first." % p.name)
            out.append(rec)
            continue
        blob = p.read_bytes()
        digest = hashlib.sha256(blob).hexdigest()
        cp = STT_CACHE / (digest[:16] + ".json")
        if cp.exists() and not force:
            c = json.loads(cp.read_text(encoding="utf-8"))
            hits += 1
            src = "cache"
        elif dry:
            print("  %-34s would transcribe (%d KB)" % (p.name, len(blob) // 1024))
            continue
        else:
            try:
                js, ms = transcribe(p, oa)
            except Exception as e:                            # noqa: BLE001
                rec.update({"transcript": None, "seconds": None, "transcribe_ms": None,
                            "error": type(e).__name__ + ": " + str(e)[:200]})
                print("  %-34s FAILED: %s" % (p.name, str(e)[:100]))
                out.append(rec)
                continue
            secs = float(js.get("duration") or 0.0)
            c = {"transcript": (js.get("text") or "").strip(), "seconds": round(secs, 2),
                 "transcribe_ms": ms, "model": STT_MODEL, "language": js.get("language"),
                 "usd": round(secs / 60.0 * STT_USD_PER_MINUTE, 6),
                 "sha256": digest, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            cp.write_text(json.dumps(c, indent=1, ensure_ascii=False), encoding="utf-8")
            spend += c["usd"]
            calls += 1
            src = "api  "
        rec.update({"transcript": c["transcript"], "seconds": c["seconds"],
                    "transcribe_ms": c["transcribe_ms"], "language": c.get("language"),
                    "usd": c.get("usd"), "sha256": c.get("sha256", digest),
                    "transcribed_at": c.get("at")})
        rec["verbatim_match"] = _same(m["script"], c["transcript"])
        print("  %-34s %s  %5.2fs audio  %5d ms  $%.5f  %s"
              % (p.name, src, rec["seconds"] or 0, rec["transcribe_ms"] or 0,
                 rec.get("usd") or 0, "verbatim" if rec["verbatim_match"] else "differs"))
        print("      said : " + m["script"])
        print("      heard: " + (c["transcript"] or ""))
        out.append(rec)
    if not dry:
        payload = {
            "_comment": DISCLOSURE,
            "synthetic": True,
            "tts_model": TTS_MODEL,
            "stt_model": STT_MODEL,
            "who_did_what": ("OpenAI " + TTS_MODEL + " spoke it, OpenAI " + STT_MODEL
                             + " transcribed it, Jev decides what to do about it. Jev "
                               "never hears audio - it is handed the transcript in the "
                               "same `state.message` field a typed DM uses."),
            "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "notes": out,
        }
        # A run that changed nothing must leave the file byte-identical, so "re-running
        # costs nothing" is checkable with sha256 and not just with a printed counter.
        try:
            old = json.loads(NOTES_FILE.read_text(encoding="utf-8"))
            if {k: v for k, v in old.items() if k != "built_at"} \
                    == {k: v for k, v in payload.items() if k != "built_at"}:
                payload["built_at"] = old.get("built_at", payload["built_at"])
        except Exception:                                        # noqa: BLE001
            pass
        NOTES_FILE.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
        print("  cache: %d hit / %d call  spend this run $%.5f  -> %s"
              % (hits, calls, spend, NOTES_FILE.relative_to(REPO).as_posix()))
    return out


def _same(a: str, b: str) -> bool:
    keep = "abcdefghijklmnopqrstuvwxyz0123456789 "
    def norm(s):
        s = (s or "").lower().replace("’", "'").replace("'", "")
        return " ".join("".join(ch if ch in keep else " " for ch in s).split())
    return norm(a) == norm(b)


# ------------------------------------------------------------------ step 3: route
async def step_route() -> int:
    """Through the real triage. One fan-out for the four, one for the baskets."""
    sys.path.insert(0, str(REPO))
    from backend import cache as C, engine as E                       # noqa: PLC0415
    from backend.jev import JEV, choice                               # noqa: PLC0415

    print("\nROUTE  (backend.engine.run_triage - the identical path a typed DM takes)")
    dms = E.voice_dms()
    if not dms:
        print("  nothing transcribed yet. Run without --route first.")
        return 1
    st = C.get("standard")
    if not st:
        print("  !! no cache/standard.json. Cannot route without her standard.")
        return 2
    pol = E.policy_from(st)
    slots = E.slots_by_key(st)

    JEV.prepare()
    t0 = time.perf_counter()
    answers = await E.run_triage([d["text"] for d in dms], st)        # ONE fan-out
    triage_s = round(time.perf_counter() - t0, 2)
    judgments = sum(len(a) for a in answers)
    print("  triage   %d messages, %d judgments in %.2fs (one fan-out)"
          % (len(dms), judgments, triage_s))

    recs = []
    for d, a in zip(dms, answers):
        lane, c = E.lane_for(a, pol)
        recs.append({**d, "answers": a, "lane0": lane, "confidence": c,
                     "shopper": E.shopper_from_triage(a), "basket": None, "scored": [],
                     "gap_probe": None})

    wants = [r for r in recs if r["lane0"] == "answered"
             and choice(r["answers"], "job", "") in E.BASKET_JOBS]
    basket_s = 0.0
    if wants:
        def one(r):
            sh = {"says": r["text"], "skin_conditions": r["shopper"]["skin"] or ["not stated"],
                  "budget_gbp": r["shopper"]["budget"], "owns": r["shopper"]["owns"],
                  "max_items": r["shopper"]["max_items"], "_slots": slots}
            return E.decide_basket(sh, pol, sweep=False)
        t1 = time.perf_counter()
        outs = await asyncio.gather(*[one(r) for r in wants], return_exceptions=True)
        basket_s = round(time.perf_counter() - t1, 2)
        for r, o in zip(wants, outs):
            if isinstance(o, dict):
                r["basket"] = o["basket"]
                r["scored"] = o["scored"]
        print("  baskets  %d in %.2fs (one fan-out)" % (len(wants), basket_s))

    raw = C.get("queue-judgments")
    if not raw:
        print("  !! no cache/queue-judgments.json. Warm the queue before merging voice in.")
        return 2
    ids = {r["id"] for r in recs}
    kept = [d for d in raw["dms"] if d.get("id") not in ids]
    dropped = len(raw["dms"]) - len(kept)
    raw["dms"] = kept + recs
    prev = raw.get("voice_merge") or {}
    # Re-merging must not compound the totals: back out the previous voice run first.
    raw["judgments"] = raw.get("judgments", 0) - prev.get("judgments", 0) + judgments
    raw["triage_seconds"] = round(max(0.0, raw.get("triage_seconds", 0.0)
                                      - prev.get("triage_seconds", 0.0)) + triage_s, 2)
    raw["basket_seconds"] = round(max(0.0, raw.get("basket_seconds", 0.0)
                                      - prev.get("basket_seconds", 0.0)) + basket_s, 2)
    raw["voice_merge"] = {
        "messages": len(recs), "judgments": judgments, "triage_seconds": triage_s,
        "basket_seconds": basket_s, "stt_model": STT_MODEL, "tts_model": TTS_MODEL,
        "synthetic": True,
        "note": ("These four were triaged in their own fan-out and merged in, so the "
                 "queue's totals include them without the other 50 being re-run. The "
                 "seconds above are this run's measured wall time."),
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    C.put("queue-judgments", raw)
    out = E.assemble_queue(raw, pol)
    C.put("queue", out)
    stale = sorted(C.ROOT.glob("override-*.json"))
    for p in stale:
        p.unlink()
    if stale:
        print("  dropped %d stale override-*.json so overrides re-assemble with voice in"
              % len(stale))
    if dropped:
        print("  replaced %d voice card(s) from a previous run" % dropped)

    print("\n  %-6s %-9s %-4s %-18s %s" % ("ID", "LANE", "CONF", "JOB", "DRAFT / REFERRAL"))
    ok_safety = True
    for c in out["cards"]:
        if c.get("source") != "voice":
            continue
        head = c["draft_reply"]
        if c["lane"] == "referred":
            r = c["refusal"] or {}
            head = "-> " + str(r.get("refer_to")) + " [" + str(r.get("reason_code")) + " via " \
                   + str(r.get("signal")) + " " + str(r.get("signal_strength")) + "]  " + head
        print("  %-6s %-9s %.2f %-18s %s" % (c["id"], c["lane"], c["confidence"],
                                             c["job"], head[:110]))
        if c.get("basket_summary"):
            print("         basket: " + c["basket_summary"])
        if "pregnant" in c["text"].lower() and c["lane"] != "referred":
            ok_safety = False
    s = out["stats"]
    print("\n  queue now %d DMs (%d voice), answered %d / asked_back %d / held %d / referred %d"
          % (s["dms"], len([c for c in out["cards"] if c.get("source") == "voice"]),
             s["answered"], s["asked_back"], s["held"], s["referred"]))
    await JEV.aclose()
    if not ok_safety:
        print("\n  *** BLOCKER: a voice note mentioning pregnancy did NOT come back "
              "referred. The safety gate is not seeing voice. STOP. ***")
        return 3
    print("  SAFETY OK: the pregnancy voice note is referred, by the same gate as text.")
    return 0


# ------------------------------------------------------------------ main
def main(argv: list) -> int:
    dry = "--dry-run" in argv
    force = "--force" in argv
    do_speak = "--speak" in argv
    do_route = "--route" in argv
    oa = "" if dry else key()
    if do_speak:
        step_speak(oa, force, dry)
    step_transcribe(oa, force, dry)
    if do_route and not dry:
        return asyncio.run(step_route())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
