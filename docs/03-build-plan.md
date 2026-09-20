# Build plan — v2

**This is the plan being built today.** The product is `docs/09-GO.md`; this is *how* and *when*.
The API is frozen in `docs/10-API-CONTRACT.md`; build against it and only it.

Case 001. Three URLs. Four parallel lanes. ~12.75 person-hours of build against ~16.5 available,
before the **14:30 feature freeze**.

---

## 0. The shape of the thing

```
data/case-001-maya.json                          ← done, committed
        │
   engine_onboarding.py  ──►  data/standard-maya.json     ← the extracted standard, typed slots
        │                       (Maya's fourteen typed slots + the caption each came from)
        │
   engine_basket.py, engine_dm_router.py, engine_overnight_queue.py, engine_sharecard.py
        │   read ONLY data/standard-maya.json — no hand-written rules
        │
   FastAPI (backend/)  ──►  frozen contract: /api/case /api/standard /api/queue
        │                   /api/ask /api/card/:id /api/onboard  (docs/10-API-CONTRACT.md)
        │
   THREE ROUTES (frontend/, Vite + React + TS):
     /maya      the morning approval queue     (Maya's #1 ask, both reviews)
     /ask       the public link, three chips   (serves the 61% who never DM)
     /c/:id     the verdict card + share image (the shareable unit of value)
     /onboard   paste-handle → her standard, switches, first verdict
```

Nothing not on this list is being built today. That includes the 359-tile wall, the matrix hero,
and the draggable price line — all v1, all superseded by GO §3 and §6.

---

## 1. The four lanes

| Lane | Owns | Builds |
|---|---|---|
| **A — Backend** | `backend/` | FastAPI. Ports the five engines from `scripts/` behind the frozen contract. Owns `data/standard-maya.json`, the feasibility filters, the indifference band, the money line, the cache/warm path |
| **B — Frontend** | `frontend/` | Vite + React + TS. Four routes: `/maya`, `/ask`, `/c/:id`, `/onboard`. Owns the projector test and the phone test |
| **C — Truth** | the decontaminated extraction | ✅ **COMPLETE.** Symmetric dermatologist, slots expanded 6 → **14**, shoppers re-run ×5. Outcome in `docs/11-honest-headline.md` — **0/8 divergence**, held-out routing **3/3**, Priya → Red Reset **5/5**. The 11:00 headline deadline (GO §2) was met |
| **D — Docs** | this file, the demo script, the README | Keeps the day's plan and the stage script in sync with what A/B/C actually ship. v1 docs rewritten (H+0.0); **re-reconciled against `docs/11-honest-headline.md` after lane C's re-measurement — no retired number survives as a live claim** |

Lane D does not touch `backend/`, `frontend/`, `scripts/`, `data/`, or `tano.pen`.

---

## 2. Four known bugs — fix before anything else (GO §5)

| # | Bug | Fix | Owner |
|---|---|---|---|
| 1 | Skin type was a single `choice`, so "dry **+** redness" lost the redness condition entirely (returned Cloud Cream, never fired REDNESS → Red Reset) | One `noul` per condition (dry / oily / combination / sensitive / redness), not one `choice`. Routing is multi-condition | **A** |
| 2 | Single-stage basket selection gave a different top basket between runs | Always two-stage: score all feasible baskets → take top 8 → one `choice` | **A** |
| 3 | Routing rules written as prose in `state` did not fire | Routing rules must be structured data (`her_written_routing_rules`), not prose | **A** |
| 4 | `later` vs `not_a_question` overlapped; "buying it payday" misrouted at 0.65 confidence | Criteria must describe concrete situations — *"waiting for money or time — payday, next month, when it restocks"* took it to 0.96 | **A** |

All four block `/ask` and `/maya` correctness. Fix before wiring the frontend to live data.

---

## 3. Timeline

### H+0.0–0.5 · Scope freeze (all lanes)
Rewrite `03-build-plan.md` (this file) and `07-demo-script.md` to v2, before any frontend work
starts against stale docs. Confirm everyone has read GO §3, §6, §7, §9 and the frozen contract.

### H+0.5–1.25 · A — Decontaminate
`engine_onboarding.py` writes `data/standard-maya.json`: typed values + the source caption +
confidence, nothing hand-authored. `engine_basket.py` and `engine_dm_router.py` are rewired to read
**only** that file. Delete every hand-written rule from Maya's judge state.

### H+0.5–2.0 · B — The verdict card
`/c/:id`, built as the same component the share image renders from. No code path where the card
exists and the image does not (GO §3).

### H+0.5–1.5 · C — Symmetric dermatologist — ✅ **DONE**
Extracted the dermatologist's standard through **the same fourteen typed slots** as Maya's, from
clinical guidance; re-ran the shoppers five times. Published whatever came out — and what came out
killed the divergence claim. Full outcome in §4 below and in `docs/11-honest-headline.md`.
Script: `scripts/engine_decontaminated_v2.py` (`engine_decontaminated.py` kept unchanged so the
diff is auditable).

### H+1.25–2.0 · A — Hard constraints
Defended category + irritation > 0.6, taken from the *extracted* standard, become feasibility
filters before basket enumeration.

### ⏱ H+~2.0 (~11:00) — DEADLINE — ✅ **MET**
**The headline is discovered, not authored** — and the divergence claim did not survive being
discovered. See §4. Everything downstream (GO §2, `07-demo-script.md` beats 1, 3 and 6, this file,
`README.md`) has been reconciled against `docs/11-honest-headline.md`.

### H+2.0–4.0 · B — `/maya`, the morning approval queue
The only screen that touches Maya's 70 hours. Four-way split (answered · asked back · held ·
referred) is the hero visual. Header: `you approved 30 replies in 4 minutes`.

### H+2.25–4.25 · C — The OG share image
1080×1350 PNG per card id, served from `/api/card/:id/og.png`, cached forever.

### H+2.0–2.5 · A — The indifference band
Sweep budget £30 / 40 / 50 / 60 / 80 / 100; find where the winning basket changes. One sentence for
the card: *"Between £40 and £80 her answer does not change."*

### H+2.5–4.5 · A — `/ask` backend + re-decide-on-open
No scheduler, no fake clock. The card re-enumerates every time it is opened.

### H+4.0–4.75 · B — `/onboard` switches
Each row quotes the caption it was inferred from; each is tappable (GO §4, §7 beat 8).

### H+4.25–5.0 · C — Money line + blocklist + one brand brief
Affiliate status per row + running basket value. Blocklist flag against Tano's contracted brands
(Skin+Me, Bloom & Wild) — check before 19:45. One real brand brief run through Maya's standard.

### H+4.75–5.5 · B — "Do it for me instead"
On a received card, re-runs the basket against the receiver's constraints and mints a child card
carrying `parent_card_id`.

### H+5.0–5.5 · A + C — Freeze to cache
12 DMs, the shoppers, the extracted table, the indifference band, the queue stats, four share cards.
Populate `cache/standard.json`, `cache/queue.json`, `cache/cards/<card_id>.json`,
`cache/og/<card_id>.png`. `python -m backend.warm` regenerates the whole set — run it before the
demo and again before judging.

### ⏱ H+5.5 (14:30) — FEATURE FREEZE
**Nothing new gets added after this line.** Copy pass + end-to-end walk of all three routes on a
real phone. Every hackathon is lost between 17:00 and 19:00 by a team adding one more thing.

### H+? (16:00) — Envelope
Activate the handoff panel (Surface C / "do it for me instead"). The share card and the queue are
already the answer to invisible behaviour — do not pivot, just switch it on.

### 17:00 — Maya walks in
Let her flip a switch on `/onboard` and watch the queue re-rank. One note. No redesign.

### 17:30 — Rehearse
Rehearse the 90 seconds twice. Record the backup. Deploy to Modal for a shareable URL.

---

## 4. The headline — ✅ closed, and the outcome is not what we planned

**Source of truth: `docs/11-honest-headline.md`.** It overrides this file, GO and the demo script
wherever they differ. Measured against `jev-1.13.0` on 2026-09-20; every figure is the modal result
over **five full repeats**. Reproduce: `python scripts/engine_decontaminated_v2.py`
(`DECON_REPEATS=5`).

**What lane C was asked to do:** fix the over-collapse (Maya returning SPF 50 alone for almost
everyone, including Priya) by **extracting more slots, not re-authoring rules**, then re-run and
publish whatever number came out.

**What it did:** six typed slots → **fourteen**, asked identically of both sides. Four
category-priority/scope slots and four routing-condition slots, each phrased as a concrete
situation in the asker's own words. No hand-written judgement rule was added. Extraction: **0.65s**.

**What came out:**

| Result | v1, 6 slots | **v2, 14 slots** |
|---|---|---|
| Fidelity — Priya gets Red Reset | **NO** (`SPF 50` alone) | **YES — 5 runs out of 5, nothing forced** |
| Her private routing sheet (E-02.2) recovered from public posts alone | not tested | **3 of 3, held out of every prompt** |
| Slot agreement | 3 of 6 agree | **10 of 14 agree, 4 disagree** |
| Basket divergence vs the dermatologist | 3/8 shoppers | **0 of 8 shoppers** |
| Fewer products · less money | 0.2 · £7 | **0.00 · £0** |
| Basket stability over 5 repeats | not measured | **1.00** |

**The divergence claim is dead.** 0/8, verified across ten sweeps and four configurations (matched
derm corpus, narrow derm corpus, objective shelf, v1 shelf); per-run divergence `[0,0,0,0,0]`. It
was not a small finding that got smaller — it was under-specification. Ask both sides six
questions and you measure your own question set; ask fourteen and the gap goes to zero.

**⛔ Retired, everywhere, permanently:** `£14` · `£7` · `0.7 fewer products` · `0.2 fewer products` ·
`5/6 shoppers diverge` · `3/8 shoppers diverge` · *"a dermatologist says three products and
seventy-two"* · *"forty-six pounds this machine just talked her out of spending"* · any
"saves you money versus a dermatologist" framing. They may appear only inside a list like this one.
Also off every slide: **`skippable_category`**, stability 0.60.

**What we lead with instead** (GO §2, demo beats 1, 3 and 6):
1. **The refusal** — the £62 Glass Drop, *"Good. Not £62 good."* (**E-04.6**), her verbatim words.
   Evidence, not arithmetic, so no re-run can falsify it. It is now the cold open.
2. **The held-out routing test** — `decision_rules.routing` (E-02.2) never enters a prompt; routing
   extracted from her public captions alone matched it **3/3**. Grep `HELD_OUT_PRIVATE_ROUTING`.
3. **Fidelity** — Priya → Red Reset, **5/5**, Mode A, unforced. **Caveat in writing:**
   `route_reacting` is stable but **low-confidence at 0.34**, and the Priya result rests on it.
   Say the number if asked; do not present it as certainty.
4. **The 0/8, volunteered** — we say it before a judge finds it. Wording in GO §2 Claim 1a.

**Docs reconciled against this outcome (lane D):** `docs/09-GO.md` §§2, 6, 7, 8, 9 ·
`docs/07-demo-script.md` (all beats, all placeholders resolved) · this file · `README.md` ·
`docs/research/jev-measured-benchmarks.md` (V2 summary + dated retirement note).

---

## 5. Kept from v1 / the persona review

- **The unsold receipt** — every card carries the difference between what she picked and what a
  complete routine would cost.
- **The indifference band** — where the answer stops changing with budget.
- **Re-decide on open** — the payday beat, no clock-faking.
- **The receiver's own answer** — "do it for me instead".
- **One real brand brief** through her standard, pre-rendered, for Tano.
- **The dossier visual language** (`docs/04-visual-language.md`) — evidence refs, redaction motif,
  monospace chrome over plain sans for her voice. Unchanged by the v2 pivot.
- **The non-negotiables** (`docs/09-GO.md` §9) — bands not decimals, never "autonomous"/"AI"/
  "clone"/"chatbot", always attach an alternative to a refusal, keys server-side.

## 6. Explicitly discarded

The 359-tile wall (illegible on a projector, presumptuous to Maya, "a catalogue with the lights
off") · the matrix hero and its diverging colour grid · the draggable price line as a UI object
(superseded by the tappable switches on `/onboard`, which do the same job — her hand on the
machine — more cheaply) · a live Instagram scraper (login-walled; ship paste-or-prefetch with an
honest on-screen note) · native share sheet and camera capture · the price-drop trigger with a fake
clock · the readiness meter · the cross-creator trust dashboard.

---

## 7. Fallback ladder (unchanged from GO §6)

Take the highest rung that is working. Decide at the checkpoints, never at 19:00.

| Rung | Product |
|---|---|
| **1** | All three routes: `/maya`, `/ask`, `/c/:id`, `/onboard` |
| **2** | `/maya` + `/c/:id`, no share |
| **3** | `/c/:id` alone, cached |
| **4** | The 12-DM router printout — alone a real result |

---

## 8. Jev operating limits (worth knowing before you hit them)

| | |
|---|---|
| Price | $0.042 / 1M input tokens. Output free |
| Rate limits | 250,000 tokens/sec · 1,200 requests/min |
| Context | 64k per request total; 32k for state + longest question |
| Caps | `choice` ≤ 255 options · `score` ≤ 10 levels (11 is a `422`) |
| Measured | 2,535 judgments/s at 60-questions × 100-concurrency; p95 1.09s |

---

## 9. What "done" looks like at 14:30

```
[ ] data/standard-maya.json exists, typed slots + caption + confidence, no hand-written rules
[ ] engine_basket.py / engine_dm_router.py read ONLY data/standard-maya.json
[ ] All four bugs in §2 fixed and covered by an eval
[x] The dermatologist standard extracted through the same 14 slots; shoppers re-run x5; number
    published (0/8) — docs/11-honest-headline.md
[ ] No retired number (£14 / £7 / 0.2 / 3/8 / 5/6 / "forty-six pounds") anywhere as a live claim
[ ] skippable_category rendered nowhere in the frontend
[ ] /maya renders the four-way split with real queue stats
[ ] /ask completes in a card in under six seconds, three chip taps, no text box required
[ ] /c/:id re-decides on open; og.png renders from the same component as the page
[ ] /onboard: paste handle -> standard shown next to its caption -> first verdict, under 90s
[ ] "Do it for me instead" mints a child card with parent_card_id
[ ] cache/ populated; python -m backend.warm regenerates it; wifi-off demo verified
[ ] Blocklist checked against Skin+Me and Bloom & Wild
[ ] No float score or decimal pound rendered anywhere
[ ] 90-second script rehearsed twice under 90s; final line memorised
```
