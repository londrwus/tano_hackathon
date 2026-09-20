"""FastAPI app. Routes only, thin.

Nothing on stage may render a 500. Every route falls back to the frozen cache
and sets "live": false.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from fastapi import FastAPI, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from . import cache, cards, engine as E, og
from .jev import JEV, JevUnavailable

app = FastAPI(title="Maya's judgement, running without her", version="2.0")

# CORS FIRST THING.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173",
                   "http://localhost:4173", "http://localhost:3000"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------- plumbing
def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)


def ok(payload: dict, t0: float, cached: bool, live: bool) -> JSONResponse:
    body = {"cached": bool(cached), "ms": _ms(t0), "live": bool(live)}
    body.update(payload)
    body["cached"] = bool(cached)
    body["ms"] = _ms(t0)
    body["live"] = bool(live)
    return JSONResponse(body)


def fallback(name: str, t0: float, err: Exception, extra: dict | None = None) -> JSONResponse:
    """Serve the frozen cache. Never a 500, never an empty screen."""
    body = cache.get(name) or {}
    body = dict(body) if isinstance(body, dict) else {"data": body}
    body.update(extra or {})
    body["error"] = "Live inference is unavailable, so this is the frozen run from the cache."
    body["error_detail"] = str(err)[:200]
    body["fallback"] = True
    body["cached"] = True
    body["live"] = False
    body["ms"] = _ms(t0)
    return JSONResponse(body)


async def current_standard(live: bool) -> dict:
    """The standard, from cache unless asked to run live. Always returns something."""
    if not live:
        c = cache.get("standard")
        if c:
            c = dict(c)
            c["live"] = False           # it came off disk, whatever produced it
            return c
    file_slots = E.load_standard_file()
    if live:
        try:
            maya, derm, secs = await E.extract_standard_live()
            st = E.build_standard(maya, derm, secs, True, file_slots)
            cache.put("standard", st)
            return st
        except JevUnavailable as e:
            c = cache.get("standard")
            st = dict(c) if c else E.build_standard({}, {}, 0.0, False, file_slots)
            st["live"] = False
            st["fallback"] = True
            st["error"] = "Live inference is unavailable, so this is the frozen extraction."
            st["error_detail"] = str(e)[:200]
            return st
    st = E.build_standard({}, {}, 0.0, False, file_slots)
    return st


def pol_for(standard: dict, overrides: dict | None = None) -> dict:
    return E.policy_from(standard, overrides)


# ---------------------------------------------------------------- 1. the case
@app.get("/api/case")
async def api_case():
    t0 = time.perf_counter()
    c = E.CASE
    payload = {
        "case": c["case"],
        "creator": {"name": c["creator"]["name"], "handle": "@mayarao",
                    "city": c["creator"]["city"],
                    "niche": c["creator"]["niche"],
                    "followers_total": c["creator"]["followers"]["total"],
                    "followers": c["creator"]["followers"],
                    "dms_per_month": c["creator"]["load"]["dms_per_month"],
                    "reply_hours_per_month": c["creator"]["load"]["reply_hours_per_month"],
                    "creed": c["voice"]["creed"],
                    "style_rules": c["voice"]["style_rules"]},
        "shelf": [E.shelf_row(p) for p in E.SHELF],
        "personas": c["personas"],
        "inbox": c["inbox"],
        "routing": E.ROUTING,
        "intake_questions": E.INTAKE,
        "affiliate_rule": E.AFFILIATE_RULE,
        "frozen_card_ids": list(cards.FROZEN.keys()),
    }
    return ok(payload, t0, cached=True, live=False)


@app.get("/api/health")
async def api_health():
    t0 = time.perf_counter()
    return ok({"key_configured": JEV.configured,
               "cache": {n: cache.exists(n) for n in ("standard", "queue", "queue-judgments")},
               "cards_cached": cards.all_ids(),
               "calls": JEV.calls, "judgments": JEV.judgments},
              t0, cached=True, live=False)


# ---------------------------------------------------------------- 2. the standard
@app.get("/api/standard")
async def api_standard(live: int = Query(0)):
    t0 = time.perf_counter()
    try:
        st = await current_standard(bool(live))
        return ok(st, t0, cached=not bool(st.get("live")), live=bool(st.get("live")))
    except Exception as e:                                    # pragma: no cover
        return fallback("standard", t0, e)


class Overrides(BaseModel):
    overrides: dict = Field(default_factory=dict)


@app.post("/api/standard/override")
async def api_standard_override(body: Overrides):
    """Flip a switch -> the whole queue re-ranks. ZERO inference: this re-reads
    judgments we already paid for."""
    t0 = time.perf_counter()
    try:
        ov = {k: v for k, v in (body.overrides or {}).items()}
        st = await current_standard(False)
        pol = pol_for(st, ov)
        ck = "override-" + cache.key("queue", ov)
        hit = cache.get(ck)
        if hit:
            hit = dict(hit)
            hit["overrides"] = ov
            return ok(hit, t0, cached=True, live=False)
        raw = cache.get("queue-judgments")
        if not raw:
            return fallback("queue", t0, RuntimeError("no warm queue in cache"),
                            {"overrides": ov})
        out = E.assemble_queue(raw, pol)
        out["overrides"] = ov
        out["policy"] = {k: v for k, v in pol.items() if k != "routing"}
        cache.put(ck, out)
        return ok(out, t0, cached=True, live=False)
    except Exception as e:
        return fallback("queue", t0, e)


# ---------------------------------------------------------------- 3. the queue
@app.get("/api/queue")
async def api_queue(live: int = Query(0)):
    t0 = time.perf_counter()
    try:
        st = await current_standard(bool(live))
        pol = pol_for(st)
        if not live:
            hit = cache.get("queue")
            if hit:
                return ok(hit, t0, cached=True, live=False)
            raw = cache.get("queue-judgments")
            if raw:
                return ok(E.assemble_queue(raw, pol), t0, cached=True, live=False)
        raw = await E.build_queue_raw(st, pol)
        cache.put("queue-judgments", raw)
        out = E.assemble_queue(raw, pol)
        cache.put("queue", out)
        return ok(out, t0, cached=False, live=True)
    except Exception as e:
        return fallback("queue", t0, e)


class QueueAction(BaseModel):
    action: str
    text: str | None = None


@app.post("/api/queue/{qid}/action")
async def api_queue_action(qid: str, body: QueueAction):
    """It never actually sends anything. It records."""
    t0 = time.perf_counter()
    log = cache.get("corrections") or {"events": []}
    moved = None
    if body.action == "edit":
        moved = "price_refusal +0.1"
    elif body.action == "hold":
        moved = "confidence_gate +0.05"
    log["events"].append({"id": qid, "action": body.action, "text": body.text,
                          "at": E.now_iso(), "standard_moved": moved})
    cache.put("corrections", log)
    return ok({"ok": True, "id": qid, "action": body.action,
               "correction_written": body.action in ("edit", "hold"),
               "standard_moved": moved,
               "sent": False,
               "note": "Nothing was sent. This is a record of what she approved."},
              t0, cached=False, live=False)


# ---------------------------------------------------------------- 4. /ask
class Ask(BaseModel):
    skin: list = Field(default_factory=list)
    budget: int = 60
    how_many: int = 2
    owns: list = Field(default_factory=list)
    text: str | None = None
    name: str | None = None


@app.post("/api/ask")
async def api_ask(body: Ask):
    t0 = time.perf_counter()
    try:
        st = await current_standard(False)
        pol = pol_for(st)
        spec: dict[str, Any] = {
            "card_id": cards.mint(),
            "name": body.name or "you",
            "said": body.text or "",
            "skin": [str(s).lower() for s in (body.skin or [])],
            "budget": int(body.budget or 60),
            "how_many": int(body.how_many or 2),
            "owns": [o for o in (body.owns or []) if o in E.BY],
            "parent_card_id": None,
        }
        if body.text:
            # the free-text fallback routes through the DM router: ONE fan-out
            try:
                a = (await E.run_triage([body.text], st))[0]
                sh = E.shopper_from_triage(a)
                if not spec["skin"]:
                    spec["skin"] = sh["skin"]
                if not spec["owns"]:
                    spec["owns"] = sh["owns"]
                named = E.choice(a, "named_product", "none")
                if named in E.BY:
                    spec["named_product"] = named
            except JevUnavailable:
                pass
        card = await E.build_card(spec, st, pol)
        cards.save(card)
        _seed_memo(card)
        try:
            og.render_to_cache(card)
        except Exception:
            pass
        return ok({"card_id": card["card_id"], "share_url": card["share_url"],
                   "og_image": card["og_image"]}, t0, cached=False, live=True)
    except Exception as e:
        return fallback("cards/c-jessica", t0, e,
                        {"card_id": "c-jessica", "share_url": "/c/c-jessica",
                         "og_image": "/api/card/c-jessica/og.png"})


# ---------------------------------------------------------------- 5. the card
# RE-DECIDE ON OPEN, WITHOUT PAYING FOR IT FORTY TIMES.
#
# The demo beat is real: a forwarded card recomputes for whoever opens it, against
# whatever her standard says at that moment. It was also, measured, the single most
# expensive thing in the product, because it ran a full two-stage basket on EVERY
# page view - every screenshot, every reload, every contract run, every agent poke.
# One open of c-sister is 3 requests and ~16.7k input tokens.
#
# So: a short-TTL memo, in this process only, keyed by the card id AND the receiver
# constraints it was decided under. Ten minutes, chosen because it is longer than any
# single run-through of the demo or burst of screenshots, and far shorter than the gap
# between one rehearsal and the next - so a stale memo is never what the stage sees.
#
# The memo lives in memory and NOT on disk, and that is the load-bearing detail:
# `python -m backend.warm` is a different process, so warming the cache can never
# seed it. The first open after the server starts is always cold and always genuinely
# re-decides. Restarting the backend is the reset. `?live=1` forces a re-decide at any
# time, and a memo hit says so on the wire (`cached: true`, `live: false`, `memo`).
CARD_MEMO_TTL_SECONDS = 600
_CARD_MEMO: dict[str, tuple[float, dict]] = {}

#: the receiver constraints a card is decided under. Change any of these and it is a
#: different decision, so it is a different memo entry.
_MEMO_FIELDS = ("skin", "budget", "owns", "how_many", "said", "named_product",
                "parent_card_id", "name")


def _memo_key(card_id: str, spec: dict) -> str:
    return card_id + "|" + cache.key("card", {k: spec.get(k) for k in _MEMO_FIELDS})


def _memo_get(key: str) -> dict | None:
    hit = _CARD_MEMO.get(key)
    if not hit:
        return None
    age = time.time() - hit[0]
    if age > CARD_MEMO_TTL_SECONDS:
        _CARD_MEMO.pop(key, None)
        return None
    body = dict(hit[1])
    body["cached"] = True
    body["live"] = False
    body["memo"] = {
        "hit": True,
        "age_seconds": int(age),
        "ttl_seconds": CARD_MEMO_TTL_SECONDS,
        "decided_at": body.get("re_decided_at"),
        "note": ("This is the decision this card already re-computed, inside a "
                 + str(CARD_MEMO_TTL_SECONDS // 60) + "-minute window. It re-decides "
                 "when the window lapses, when the backend restarts, or on ?live=1."),
    }
    return body


def _seed_memo(card: dict) -> None:
    """A card we have JUST decided is, by definition, its own freshest re-decide.

    /api/ask and /redecide both build a card and hand back an id the client opens a
    heartbeat later. Without this, that open paid for the identical decision twice.
    The key is read back through `cards.spec_for`, which is the same function the GET
    route uses, so the two can never disagree about what the constraints were.
    """
    try:
        cid = card.get("card_id")
        spec = cards.spec_for(cid) if cid else None
        if cid and spec is not None:
            _memo_put(_memo_key(cid, spec), card)
    except Exception:                                  # never break a route over a memo
        pass


def _memo_put(key: str, card: dict) -> None:
    _CARD_MEMO[key] = (time.time(), card)
    if len(_CARD_MEMO) > 256:                      # bounded; oldest out first
        for k, _v in sorted(_CARD_MEMO.items(), key=lambda kv: kv[1][0])[:64]:
            _CARD_MEMO.pop(k, None)


def _frozen_from_disk(card_id: str, t0: float) -> JSONResponse | None:
    """The four demo cards, exactly as `python -m backend.warm` last computed them.

    THE FOUR FROZEN IDS ARE READ-ONLY. They are not a "card open" in the product
    sense, they are the demo: c-jessica IS beat 1 and its headline is quoted in the
    script. The basket is a live two-stage judgement and it is not deterministic -
    c-jessica has been observed coming back "Not that. The SPF and the cleanser. £48"
    where the cold open says "No. Just the SPF. £26." So every contract run, every
    screenshot and every reload was a fresh roll of the dice on the opening line of
    the demo, and was paying ~16k input tokens for the privilege.

    They now come off disk. Re-deciding them is an explicit act - `?live=1`, or
    `python -m backend.warm` - and both of those write the new decision back, so what
    is on stage is always something a human chose to compute. Nothing is invented
    here: the payload served is a real run, it says `cached: true, live: false`, and
    `frozen` says why.
    """
    saved = cards.load(card_id)
    if not saved:
        return None
    body = dict(saved)
    body["cached"] = True
    body["live"] = False
    body["ms"] = _ms(t0)
    body["frozen"] = {
        "read_only": True,
        "decided_at": body.get("re_decided_at"),
        "why": ("One of the four frozen demo cards. It is served from the warmed cache "
                "so the demo says the same words twice. Pass ?live=1, or run "
                "python -m backend.warm, to re-decide it."),
    }
    return JSONResponse(body)


async def _card(card_id: str, t0: float, live_flag: bool):
    if card_id in cards.FROZEN and not live_flag:
        frozen = _frozen_from_disk(card_id, t0)
        if frozen is not None:
            return frozen
    spec = cards.spec_for(card_id)
    if spec is None:
        saved = cards.load(card_id)
        if saved:
            saved = dict(saved)
            saved["live"] = False
            return ok(saved, t0, cached=True, live=False)
        return fallback("cards/c-jessica", t0, KeyError("unknown card " + card_id),
                        {"error": "That card id is not one we hold. This is the demo card."})
    mk = _memo_key(card_id, spec)
    if not live_flag:
        memo = _memo_get(mk)
        if memo is not None:
            memo["ms"] = _ms(t0)
            return JSONResponse(memo)
    st = await current_standard(False)
    pol = pol_for(st)
    try:
        card = await E.build_card(spec, st, pol)
        cards.save(card)
        _memo_put(mk, card)
        try:
            og.render_to_cache(card)
        except Exception:
            pass
        return ok(card, t0, cached=False, live=True)
    except JevUnavailable as e:
        saved = cards.load(card_id)
        if saved:
            saved = dict(saved)
            saved["re_decided_at"] = E.now_iso()
            saved["live"] = False
            saved["cached"] = True
            saved["fallback"] = True
            saved["error"] = "Live inference is unavailable, so this is the frozen decision."
            saved["error_detail"] = str(e)[:200]
            saved["ms"] = _ms(t0)
            return JSONResponse(saved)
        return fallback("cards/c-jessica", t0, e)


@app.get("/api/card/{card_id}")
async def api_card(card_id: str, live: int = Query(0)):
    t0 = time.perf_counter()
    if not cards.valid(card_id):
        return fallback("cards/c-jessica", t0, ValueError("bad card id"))
    try:
        return await _card(card_id, t0, bool(live))
    except Exception as e:
        return fallback("cards/" + card_id, t0, e)


class Redecide(BaseModel):
    skin: list = Field(default_factory=list)
    budget: int = 60
    owns: list = Field(default_factory=list)
    how_many: int | None = None
    name: str | None = None


@app.post("/api/card/{card_id}/redecide")
async def api_redecide(card_id: str, body: Redecide):
    """'Do it for me instead' - a child card carrying parent_card_id."""
    t0 = time.perf_counter()
    try:
        parent = cards.spec_for(card_id) or {}
        st = await current_standard(False)
        pol = pol_for(st)
        spec = {
            "card_id": cards.mint(),
            "parent_card_id": card_id,
            "name": body.name or "someone this was forwarded to",
            "said": parent.get("said") or "",
            "skin": [str(s).lower() for s in (body.skin or [])],
            "budget": int(body.budget or 60),
            "owns": [o for o in (body.owns or []) if o in E.BY],
            "how_many": int(body.how_many or parent.get("how_many") or 3),
        }
        card = await E.build_card(spec, st, pol)
        cards.save(card)
        _seed_memo(card)
        try:
            og.render_to_cache(card)
        except Exception:
            pass
        return ok(card, t0, cached=False, live=True)
    except Exception as e:
        return fallback("cards/c-sister", t0, e)


@app.get("/api/card/{card_id}/og.png")
async def api_og(card_id: str):
    headers = {"Cache-Control": "public, max-age=31536000"}
    data = cache.get_bytes("og/" + card_id + ".png")
    if data is None:
        payload = cards.load(card_id)
        if payload is None and card_id in cards.FROZEN:
            payload = None
        if payload is None:
            payload = cache.get("cards/c-jessica") or {
                "card_id": card_id, "asker": {"name": "@someone", "said": ""},
                "verdict": {"headline": "Warming up.", "in_her_voice": "", "is_refusal": False},
                "basket": [], "total": "£0", "unspent": {"line": ""}, "left_out": [],
                "ceiling": {"band": ""}}
        try:
            data = og.render_to_cache(payload)
        except Exception:
            data = b""
    return Response(content=data, media_type="image/png", headers=headers)


# ---------------------------------------------------------------- 6. onboard
@app.get("/api/onboard")
async def api_onboard(handle: str = Query("@mayarao"), live: int = Query(0)):
    t0 = time.perf_counter()
    try:
        st = await current_standard(bool(live))
        heard = []
        for s in st.get("slots", []):
            m = s.get("maya") or {}
            heard.append({"trait": s.get("statement") or m.get("level"),
                          "level": m.get("level"),
                          "caption": s["source_caption"],
                          "evidence_ref": s["evidence_ref"],
                          "confidence": m.get("confidence"),
                          "value": m.get("value"),
                          "slot_key": s["key"],
                          "toggleable": s["toggleable"],
                          "agrees_with_derm": s["agrees"]})
        return ok({"handle": handle, "heard": heard,
                   "accuracy": "89% correct against her documented self",
                   "accuracy_source": "scripts/engine_onboarding.py, 8 of 9 slots recovered",
                   "extraction_seconds": st.get("extraction_seconds"),
                   "slot_count": st.get("slot_count"),
                   "first_verdict_card_id": "c-jessica"},
                  t0, cached=not bool(st.get("live")), live=bool(st.get("live")))
    except Exception as e:
        return fallback("onboard", t0, e)


# ---------------------------------------------------------------- 7. the extraction replay
# The data behind the hero visual on /onboard: watch Jev read her channel.
#
# THE HONESTY RULE, enforced here and not negotiable: Jev returns all fourteen answers
# for a judge in ONE response. There is no genuine per-slot arrival time, so no event
# below ever carries a per-slot `ms`. Timings are per REQUEST and were measured on the
# wire. Every slot of a request resolves at the same instant and is emitted with that
# request's `at_ms`. The reveal in the browser is a replay and must say so.
async def _extract_payload(live: bool) -> tuple:
    """-> (payload, cached, live). Never raises."""
    if not live:
        hit = cache.get("extract")
        if hit:
            hit = dict(hit)
            hit["measured"] = bool(hit.get("measured"))
            return hit, True, False
        return E.build_extract_frozen(), True, False
    try:
        p = await E.extract_live()
        cache.put("extract", p)
        return p, False, True
    except Exception as e:
        hit = cache.get("extract") or E.build_extract_frozen()
        hit = dict(hit)
        hit["fallback"] = True
        hit["error"] = "Live inference is unavailable, so this is the frozen extraction."
        hit["error_detail"] = str(e)[:200]
        return hit, True, False


# --- the same fourteen questions, a different person -------------------------
# The corpus fetch is PREFETCHED (scripts/fetch_corpus.py, by hand, committed). It is
# slow and network-fragile and it must never run on stage. The EXTRACTION is what runs
# live, because that is the fast, reliable part - and it is the number we put on screen,
# so the timing is genuinely real.
async def _subject_payload(subject: str, live: bool) -> tuple:
    """-> (payload, cached, live) for any non-Maya subject. Never raises."""
    name = E.extract_cache_name(subject)
    if not live:
        hit = cache.get(name)
        if hit:
            hit = dict(hit)
            hit["measured"] = bool(hit.get("measured"))
            return hit, True, False
        p = E.build_extract_frozen(subject)
        p["error"] = ("No cached extraction for this subject yet. Run "
                      "`python -m backend.warm extract` or ask for ?live=1.")
        return p, True, False
    try:
        p = await E.extract_live(subject)
        cache.put(name, p)
        return p, False, True
    except Exception as e:
        hit = cache.get(name) or E.build_extract_frozen(subject)
        hit = dict(hit)
        hit["fallback"] = True
        hit["measured"] = bool(hit.get("measured"))
        hit["error"] = "Live inference is unavailable, so this is the frozen extraction."
        hit["error_detail"] = str(e)[:200]
        return hit, True, False


async def extract_for(subject: str, live: bool) -> tuple:
    """One door for every subject. Maya's path is the original one, untouched."""
    subject = (subject or "").strip().lower() or E.MAYA_SLUG
    if subject == E.MAYA_SLUG:
        return await _extract_payload(live)
    return await _subject_payload(subject, live)


@app.get("/api/creators")
async def api_creators():
    """Every subject the engine can be pointed at, and which of them are real."""
    t0 = time.perf_counter()
    try:
        subjects = E.list_subjects()
        for s in subjects:
            s["cached_extraction"] = cache.exists(E.extract_cache_name(s["slug"]))
            s["extract_url"] = "/api/extract?subject=" + str(s["slug"])
        real = [s for s in subjects if s.get("real")]
        return ok({"creators": subjects,
                   "count": len(subjects),
                   "real_count": len(real),
                   "control": E.subject_meta(E.DERM_SLUG),
                   "slot_count": len(E.SLOTS_V14),
                   "note": ("Every subject is asked the SAME fourteen questions, against the "
                            "same control. `real: true` means the corpus is that person's own "
                            "public writing, fetched verbatim; `real: false` means the words "
                            "are ours. The fetch is prefetched and committed - only the "
                            "extraction runs live.")},
                  t0, cached=True, live=False)
    except Exception as e:                                    # pragma: no cover
        return fallback("creators", t0, e)


@app.get("/api/extract")
async def api_extract(live: int = Query(0), subject: str = Query("")):
    t0 = time.perf_counter()
    try:
        want = (subject or "").strip().lower() or E.MAYA_SLUG
        if not E.subject_exists(want):
            return ok({"error": "unknown subject " + repr(want),
                       "known_subjects": [s["slug"] for s in E.list_subjects()],
                       "corpus": [], "questions": [], "requests": [], "slots": [],
                       "totals": {"questions": 0, "requests": 0, "seconds": 0.0,
                                  "input_tokens": None, "agree": 0, "disagree": 0,
                                  "slot_count": 0}},
                      t0, cached=True, live=False)
        payload, cached, is_live = await extract_for(want, bool(live))
        return ok(payload, t0, cached=cached, live=is_live)
    except Exception as e:                                    # pragma: no cover
        return fallback(E.extract_cache_name(subject or E.MAYA_SLUG), t0, e)


@app.get("/api/compare")
async def api_compare(a: str = Query("maya"), b: str = Query(""), live: int = Query(0)):
    """Two subjects, the same fourteen questions, aligned slot by slot."""
    t0 = time.perf_counter()
    try:
        sa = (a or E.MAYA_SLUG).strip().lower()
        sb = (b or "").strip().lower()
        if not sb:
            others = [s["slug"] for s in E.list_subjects() if s["slug"] != sa]
            sb = others[0] if others else E.MAYA_SLUG
        for s in (sa, sb):
            if not E.subject_exists(s):
                return ok({"error": "unknown subject " + repr(s),
                           "known_subjects": [x["slug"] for x in E.list_subjects()],
                           "subjects": [], "slots": [], "agree_count": 0,
                           "disagree_count": 0, "totals": {}},
                          t0, cached=True, live=False)
        (pa, ca, la), (pb, cb, lb) = await asyncio.gather(
            extract_for(sa, bool(live)), extract_for(sb, bool(live)))
        pa, pb = dict(pa), dict(pb)
        pa["cached"], pa["live"] = ca, la
        pb["cached"], pb["live"] = cb, lb
        out = E.align_subjects(pa, pb)
        errs = [p.get("error") for p in (pa, pb) if p.get("error")]
        if errs:
            out["error"] = errs[0]
            out["fallback"] = True
        return ok(out, t0, cached=bool(ca or cb), live=bool(la and lb))
    except Exception as e:                                    # pragma: no cover
        return fallback("compare", t0, e)


def _sse(event: str, data: dict) -> bytes:
    return ("event: " + event + "\ndata: " + json.dumps(data, ensure_ascii=False)
            + "\n\n").encode("utf-8")


def _slot_rows(payload: dict) -> dict:
    return {s["key"]: s for s in payload.get("slots", [])}


@app.get("/api/extract/stream")
async def api_extract_stream(live: int = Query(0)):
    # Defaults to 0, not 1. This is reachable on a public URL and a live run costs real
    # Jev tokens, so an anonymous GET must replay the cache. Pass ?live=1 to mean it.
    """SSE. Runs the extraction for real and emits events as they genuinely occur.

    corpus   -> the strings that go into the prompt, plus the 28 questions, immediately
    dispatch -> a request was actually fired  { request_id, judge, question_ids, at_ms }
    resolved -> that request genuinely came back { request_id, judge, slot_keys, ms, input_tokens }
    slot     -> one per slot; all slots of a request share that request's at_ms, because
                that is the truth - they arrived together in one response
    done     -> the totals
    """
    # Build the HTTP client before the clock starts - see Jev.prepare(). Nothing is sent.
    JEV.prepare()
    t0 = time.perf_counter()

    def el() -> int:
        return int((time.perf_counter() - t0) * 1000)

    async def gen():
        frozen = cache.get("extract") or E.build_extract_frozen()
        yield _sse("corpus", {"corpus": frozen.get("corpus", []),
                              "corpus_note": frozen.get("corpus_note"),
                              "derm_corpus": frozen.get("derm_corpus", []),
                              "derm_corpus_note": frozen.get("derm_corpus_note"),
                              "questions": frozen.get("questions", []),
                              "replay_note": frozen.get("replay_note"),
                              "at_ms": el()})

        plan = E.extract_plan()
        frozen_slots = _slot_rows(frozen)
        done_reqs: set = set()
        results: list = []
        err = None

        if bool(live) and JEV.configured:
            tasks = []
            for r in plan:
                tasks.append(asyncio.create_task(E.run_extract_request(r, t0)))
                yield _sse("dispatch", {"request_id": r["id"], "judge": r["judge"],
                                        "question_ids": r["question_ids"],
                                        "question_count": r["question_count"],
                                        "at_ms": el()})
            for fut in asyncio.as_completed(tasks):
                try:
                    res = await fut
                except Exception as e:                         # JevUnavailable, mostly
                    err = e
                    continue
                results.append(res)
                done_reqs.add(res["id"])
                at = res["at_ms"] + res["ms"]
                yield _sse("resolved", {"request_id": res["id"], "judge": res["judge"],
                                        "slot_keys": res["slot_keys"], "ms": res["ms"],
                                        "input_tokens": res["input_tokens"],
                                        "dispatched_at_ms": res["at_ms"], "at_ms": at,
                                        "cached": False})
                for k in res["slot_keys"]:
                    row = frozen_slots.get(k, {})
                    side = (res["packed"] or {}).get(k)
                    yield _sse("slot", {"request_id": res["id"], "judge": res["judge"],
                                        "slot_key": k,
                                        "label": row.get("label") or k,
                                        "type": row.get("type"),
                                        "level": (side or {}).get("level"),
                                        "value": (side or {}).get("value"),
                                        "confidence": (side or {}).get("confidence"),
                                        "source_caption": row.get("source_caption"),
                                        "evidence_ref": row.get("evidence_ref"),
                                        "question_id": E.question_id(res["judge"], k),
                                        "at_ms": at, "cached": False})
        else:
            err = None if not bool(live) else RuntimeError("JEV_API_KEY is not set")

        # Anything we did not get live, replay from the frozen extraction. Marked cached,
        # with null timings, because we did not measure THIS one.
        if len(done_reqs) < len(plan):
            for r in plan:
                if r["id"] in done_reqs:
                    continue
                yield _sse("resolved", {"request_id": r["id"], "judge": r["judge"],
                                        "slot_keys": r["slot_keys"], "ms": None,
                                        "input_tokens": None, "dispatched_at_ms": None,
                                        "at_ms": None, "cached": True})
                for k in r["slot_keys"]:
                    row = frozen_slots.get(k, {})
                    side = row.get(r["judge"]) or {}
                    yield _sse("slot", {"request_id": r["id"], "judge": r["judge"],
                                        "slot_key": k,
                                        "label": row.get("label") or k,
                                        "type": row.get("type"),
                                        "level": side.get("level"),
                                        "value": side.get("value"),
                                        "confidence": side.get("confidence"),
                                        "source_caption": row.get("source_caption"),
                                        "evidence_ref": row.get("evidence_ref"),
                                        "question_id": E.question_id(r["judge"], k),
                                        "at_ms": None, "cached": True})

        if results and len(results) == len(plan):
            payload = E.build_extract(results, round(time.perf_counter() - t0, 2), True,
                                      E.load_standard_file())
            cache.put("extract", payload)
            cached = False
        else:
            payload = frozen
            cached = True
        body = {"totals": payload.get("totals", {}), "cached": cached, "live": not cached,
                "ms": el(), "replay_note": payload.get("replay_note"),
                "measured": bool(payload.get("measured"))}
        if err is not None:
            body["error"] = "Live inference is unavailable, so this is the frozen extraction."
            body["error_detail"] = str(err)[:200]
            body["fallback"] = True
        yield _sse("done", body)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache, no-transform",
                                      "Connection": "keep-alive",
                                      "X-Accel-Buffering": "no"})


# ------------------------------------------------- 8. the voice notes (static audio)
# Her audience sends voice notes. These four are SYNTHETIC - OpenAI tts-1 speaking a
# script we wrote, transcribed by OpenAI whisper-1, both done ahead of time by
# scripts/transcribe_voice.py. This route is a file read: no inference, no OpenAI, no
# Jev. The disclosure travels with the bytes, in the filename, in the mp3's own ID3
# tag and in the X-Synthetic-Audio header, so nobody can mistake it for a real DM.
VOICE_DIR = E.DATA / "voice"
_AUDIO_TYPES = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4",
                ".ogg": "audio/ogg", ".opus": "audio/ogg", ".flac": "audio/flac"}


@app.get("/api/voice")
async def api_voice_index():
    """The manifest: what was said, what was heard, who spoke it, who transcribed it."""
    t0 = time.perf_counter()
    man = E.voice_manifest()
    notes = man.get("notes") or []
    return ok({"synthetic": True,
               "disclosure": man.get("_comment", "Synthetic demo audio."),
               "who_did_what": man.get("who_did_what"),
               "tts_model": man.get("tts_model"), "stt_model": man.get("stt_model"),
               "built_at": man.get("built_at"), "count": len(notes), "notes": notes},
              t0, cached=True, live=False)


@app.get("/api/voice/{name}")
async def api_voice_file(name: str):
    """Serve data/voice/<name>. Static, cached, no inference."""
    t0 = time.perf_counter()
    p = (VOICE_DIR / name).resolve()
    try:
        inside = p.is_relative_to(VOICE_DIR.resolve())
    except AttributeError:                                       # pragma: no cover
        inside = str(p).startswith(str(VOICE_DIR.resolve()))
    ctype = _AUDIO_TYPES.get(p.suffix.lower())
    if ("/" in name or "\\" in name or not inside or ctype is None or not p.is_file()):
        # Not a 500 and not a stack trace. A named miss.
        return JSONResponse({"error": "No such voice note.", "name": name,
                             "available": sorted(f.name for f in VOICE_DIR.glob("*.mp3"))
                             if VOICE_DIR.is_dir() else [],
                             "cached": True, "live": False, "ms": _ms(t0)}, status_code=404)
    try:
        data = p.read_bytes()
    except Exception as e:                                       # noqa: BLE001
        return JSONResponse({"error": "That voice note could not be read.",
                             "error_detail": str(e)[:200], "fallback": True,
                             "cached": True, "live": False, "ms": _ms(t0)}, status_code=200)
    return Response(content=data, media_type=ctype, headers={
        "Cache-Control": "public, max-age=31536000, immutable",
        "Content-Disposition": 'inline; filename="' + p.name + '"',
        "X-Synthetic-Audio": "true",
        "X-Audio-Source": "OpenAI tts-1 (synthetic demo recording, not a real person)",
        "X-Transcribed-By": "OpenAI whisper-1",
    })


@app.get("/")
async def root():
    return {"ok": True,
            "routes": ["/api/case", "/api/standard", "/api/standard/override", "/api/queue",
                       "/api/queue/{id}/action", "/api/ask", "/api/card/{id}",
                       "/api/card/{id}/redecide", "/api/card/{id}/og.png", "/api/onboard",
                       "/api/creators", "/api/extract", "/api/extract/stream",
                       "/api/compare", "/api/health", "/api/voice", "/api/voice/{name}"]}


@app.exception_handler(Exception)
async def nothing_renders_a_500(request: Request, exc: Exception):   # pragma: no cover
    return JSONResponse({"error": "Something went wrong, so this is the frozen run.",
                         "error_detail": str(exc)[:200], "fallback": True,
                         "cached": True, "live": False, "ms": 0}, status_code=200)
