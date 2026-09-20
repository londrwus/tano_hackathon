# Constraints & stack status

Written 2026-09-20, the day before build. Everything here is **verified**, not assumed.
Read this first next session.

---

## 1. The event

**Tano x Corgi Creator Heist Hack** — Corgi Cafe, 74 Great Eastern St, London EC2A 3JL.
~54 builders registered. Approval required.

| Time | Beat |
|---|---|
| 09:00 | Doors |
| 10:30 | Heist starts, registration closes |
| **16:00** | **Sealed intelligence drop — the case changes** |
| 17:00 | The creator walks in (Case 001) |
| 18:00 | Judging + Q&A |
| 19:00 | Top six pitch |
| 19:45 | Demos |
| 20:30 | Prizes |

Prizes: **1st £500** + interviews at Tano · 2nd Sony over-ears · 3rd noise-cancelling headphones.

Framing: *"Find something stealing a creator's time, attention or commercial potential.
Then steal it back."*

---

## 2. Hard constraints (non-negotiable)

These come from the briefs and from the team. Violating any of them loses the hackathon.

### From the case files
1. **Demo in under 60–90 seconds. Product first. NO DECK.**
2. **"You do not need to use an LLM. You do not get extra points for complexity."**
3. **"Not require expensive AI inference to be impressive."**
4. **"A simple product that works beats a complicated demo."**
5. **"If you cannot name the person and the decision, you do not have a product yet."**
6. **Do not make the audience "feel handed to a machine."** Maya's stated pet peeve is
   *generic automation*. An obvious chatbot loses on "Would I trust this with my audience?"
7. **"Don't just tell what you've built — show how it makes their life easier."**

### From us
8. **ONE PAGE. Two absolute maximum. Prefer everything on a single screen.**
   We are not building a platform. We are building one screen that wins a 90-second demo.
9. **Backend: Python + FastAPI.** No Docker, no heavy local container tooling — this is
   Windows 11 and local Docker is a waste of hackathon hours.
   *(Note: Modal is still Docker-free locally — it builds images remotely from a Python spec.
   So Modal remains an option; it just isn't needed for throughput. See §4.)*
10. **Visualisation over text.** The WOW is visual. Text output is the losing move.
11. Judged additionally on: **best commercial potential**, **most elegant**, **most inventive**.

### Judging rubric, verbatim
- Value to a real audience member
- Fidelity to the creator's voice / focus to her judgement
- Use of the evidence
- Does it work
- **Would I use it? · Would I trust it? · Would my audience use it? · Would I share it?**

---

## 3. The 16:00 twist — plan for it NOW

All three case files contain the *same* sealed reversal, so we can pre-empt it with certainty:

> **The valuable audience behaviour is invisible to the obvious metrics.**

| Signal | Case 001 (Maya) | Case 002 (Sofia) | Case 003 (Aditi) |
|---|---|---|---|
| Acted without clicking / DMing | 61% sent no DM | 62% no affiliate click | 71% never clicked |
| Saver conversion multiple | 2.4× | 2.2× | 3.1× (3+ saves) |
| Action following a private share | 41% | 41% | 44% |
| Median lag, save → action | 4.6 d | 3.4 d | 9.2 d |

**Consequence:** the brief is *not* "answer DMs faster". Any DM-bot / inbox-triage product is
explicitly listed as a discounted lead (Case 001, E-08.1: *"The obvious answer: build a DM bot.
Too literal. It handles volume, not judgement."*).

The real question, quoted from Case 001 E-09:
> *"How do we help someone make a confident decision **before they ever need to ask** Maya?"*

**Strategy: build for the post-drop brief from hour one.** At 16:00, while every other team
panics and pivots, we show a product that already assumed the twist. Ideally we hold back one
view that *activates* at 16:00 — so the drop makes our demo stronger, not weaker.

---

## 4. Stack status — VERIFIED TODAY

| Component | Status | Detail |
|---|---|---|
| **Jev / TypeSafe** | ✅ **WORKING** | Key valid. `jev-latest` → `jev-1.13.0`. Benchmarked: 1,149 judgments/sec. See `docs/research/jev-measured-benchmarks.md` |
| **Modal** | ✅ **WORKING** | `modal token set` verified, profile `bernararno17`. CLI v1.5.2. Limits: 10 GPU / 100 containers, ~$100 credit |
| **Python** | ✅ | 3.12.0 · `httpx` 0.27.2 · `aiohttp` present |
| **Node** | ✅ | v22.20.0 |
| **FastAPI** | ⚠️ **not installed** | `pip install fastapi uvicorn` next session |
| **Google / Gemini** | ❌ **DEAD KEY** | `API_KEY_INVALID` on both `models.list` and `generateContent`. **Do not plan around it.** Replaced by OpenAI + DeepSeek below |
| **OpenAI** | ✅ **WORKING** | `text-embedding-3-small` → 1536 dims, and `gpt-4o-mini` chat/vision both return 200. Use for **embeddings and image understanding** |
| **DeepSeek** | ✅ **WORKING** | `deepseek-chat` → served by `deepseek-flash`. **Balance $5.68 — small.** Use for the little text generation we need, sparingly |
| **Pen (pencil MCP)** | ⚠️ **needs a file open** | Both `get_app_state` and `read_skill` return *"A file needs to be open in the editor"*. **ACTION: open or create a `.pen` file in the Pen app before the design step.** |
| **TypeSafe skill** | ✅ installed | `typesafe:typesafe-ai` v0.5.7, loadable via the Skill tool |

### Credentials (keep server-side — never ship to the browser)
```
JEV_API_KEY=apikey_...            # real value in .env (gitignored)
OPENAI_API_KEY=sk-proj-...        # real value in .env (gitignored)
DEEPSEEK_API_KEY=sk-...           # real value in .env (gitignored), $5.68 balance            # $5.68 balance, spend carefully
MODAL: already written to ~/.modal.toml (profile bernararno17)    # already written to ~/.modal.toml
GOOGLE_API_KEY=<dead>             # INVALID - do not use          # INVALID — dead
```

**Put these in `backend/.env` and add `.env` to `.gitignore` before the first commit.**
The TypeSafe docs explicitly warn: *"Keep API credentials server-side in web apps."*
FastAPI proxies every Jev call. The frontend never holds a key.

### Voice: Wispr Flow vs OpenAI
Tano gives out **Wispr Flow**, and voice is already in the evidence (Maya's voice note E-06.1;
Case 003's *"9 hrs of unfiled walk-home voice notes — where the real thinking is"*).

- **Wispr Flow does have a developer API** — REST + WebSocket streaming, 100+ languages, with
  auto-edit that strips filler words while keeping the speaker's style
  ([docs](https://api-docs.wisprflow.ai/introduction), [developers page](https://wisprflow.ai/developers)).
  We do **not** have a key. If Tano hands out credentials on the day, take them — using a sponsor's
  tech in the demo is free goodwill.
- **OpenAI is our verified fallback and the default.** Round trip confirmed on our key:
  `gpt-4o-mini-tts` → 185KB mp3, `gpt-4o-mini-transcribe` → text back with `£60` and "62 quid"
  intact. See `docs/research/jev-measured-benchmarks.md`.

**Keep transcription behind a one-function interface** (`transcribe(audio_bytes) -> str`). Both
providers are "audio in, text out", so swapping to Wispr on the day is a ~10-line change. Do not
put Wispr on the critical path before we hold a working key.

### Division of labour between the models — keep this straight
| Job | Use | Why |
|---|---|---|
| **Every judgement, score, ranking, verdict, routing decision** | **Jev** | It is the hero, it is calibrated, it is 1,000×/sec, and it is what the room came to see |
| Embeddings / semantic similarity | OpenAI `text-embedding-3-small` | 1536 dims, cheap |
| Understanding an uploaded image | OpenAI `gpt-4o-mini` | Vision-capable |
| The handful of sentences of real prose | DeepSeek `deepseek-chat` | Cheap; but only $5.68 left |

**Anti-pattern to avoid:** using a chat model to make a decision Jev should make. If a judge asks
"why not just one LLM call?", the answer must be a measured one — 3,000 calibrated judgments in
1.18s, with probabilities we can draw. Do not undercut that by routing decisions through DeepSeek.

---

## 5. Do we actually need Modal?

**Measured answer: not for throughput.** A single Python process did 1,149 judgments/sec against
Jev with zero errors, because the workload is *network-bound*, not compute-bound. Jev's own servers
are the parallelism. Spinning up Modal containers to make HTTPS calls adds cold-start latency and
spends credit to solve a problem we do not have.

**Where Modal still earns its place:**
- A **public HTTPS URL** for the demo, so the judges can open it on their own phones
  (`would I share it?` is an explicit judging question — a localhost demo cannot be shared).
- Insurance if the venue wifi is hostile: compute runs in the cloud, the laptop only renders.
- Precomputing the dense judgment matrix once and serving it from a Volume/Dict.

**Recommendation:** build against local FastAPI for speed of iteration, keep the app a single
ASGI object so it can be wrapped in `modal.asgi_app()` in ~10 lines, and deploy to Modal late in
the day purely to get a shareable URL. Decide at ~16:00, not at 10:30.

---

## 6. Evidence files in this repo

```
docs/evidence/case-001-operation-shade.txt      Maya Rao    beauty    50K   4.8K DMs/mo
docs/evidence/case-002-operation-lookbook.txt   Sofia Bennett fashion 50K   3.1K DMs/mo
docs/evidence/case-003-operation-front-row.txt  Aditi Mishra tech media 320K 2.6K DMs+email/mo
docs/evidence/case-00{1,2,3}.pdf                originals as issued
```

**Important:** all three cases share one skeleton — subject file, audience personas, a categorised
inbox (E-01), a broadcast log where reach and intent diverge (E-03), an inventory mixing objective
fields with the creator's subjective notes (E-04), a recovered notebook with her decision rules
(E-02/E-05), tracked individuals (E-07), and the 16:00 drop (E-09/E-10).

**This is a strategic gift.** If we build a case-agnostic engine driven by a JSON "case pack",
we can load a different creator in minutes — which both de-risks being handed a different case on
the day, and gives us a genuinely strong closing beat: *"this isn't Maya's app, it's the machine
that compiles any creator's judgement — here's Sofia, loaded in thirty seconds."*
