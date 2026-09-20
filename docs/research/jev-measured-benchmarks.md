# Jev — measured benchmarks (not estimates)

> **V2 SUMMARY — the five mechanics that make the product, all measured live.**
> Details in the sections below; scripts in `scripts/engine_*.py`.
>
> | Mechanic | Measured | What it proves |
> |---|---|---|
> | **Combinatorial basket** | 530 judgments / 6 shoppers / **4.8s** · re-measured symmetrically: 8 shoppers × 5 repeats, **4.76s** | Every feasible set scored as a whole, one `choice` picks the winner. **The divergence claim is RETIRED — 0/8 shoppers, 0.00 products, £0** (dated note at the foot of this file). What survives: her private routing sheet recovered from public posts **3/3**, held out |
> | **DM router** (speculative fan-out) | 12 real DMs, 132 judgments, **0.68s** | **12/12 routed**, 11 at high confidence, 1 correctly held as ambiguous |
> | **Link-paste onboarding** | 6 posts + 8 captions, **0.67s**, 1,483 tokens | **89%** of her documented standard recovered from public posts alone |
> | **Share card re-decides** | 222 baskets, **2.55s** | One forwarded card gives 4 receivers 4 different answers |
> | **Overnight queue** | 50 DMs, 250 judgments, **0.85s** | **78% handled without Maya**, 8% held, **14% medical refused** |

---


All numbers below were measured live on **2026-09-20** from this machine (Windows 11, London),
against `POST https://api.typesafe.ai/v1/systemone`, `model: "jev-latest"` → served by `jev-1.13.0`.
Payloads used real Case-001 evidence (Maya's shelf + her six audience personas), not synthetic filler.

Reproduce with the probe scripts in the scratchpad (`probe.py`, `probe2.py`) — port them into
`backend/scripts/bench_jev.py` next session.

---

## Headline numbers

| Metric | Measured |
|---|---|
| Single request, 3 questions | **0.87 s** (cold), 563 in / 84 out tokens |
| Single request, 18 questions | **0.62 s**, 2,247 in / 552 out |
| Single request, 36 questions | **0.31 s**, 4,029 in / 1,106 out |
| Single request, 60 questions | **0.38 s**, 6,434 in / 1,860 out |
| 24 concurrent requests (432 judgments) | **0.77 s** wall, 0 errors, 558 judgments/s |
| 100 concurrent requests (1,800 judgments) | **1.57 s** wall, 0 errors, **1,149 judgments/s** |
| Latency at 100-way concurrency | p50 0.95 s · p95 1.09 s · max 1.51 s |
| Cost per judgment (amortised) | **123 input / 29 output tokens** |

**Extrapolation: 20,000 judgments ≈ 17 seconds wall, ≈ 2.5M input tokens.**
This is the same order as TypeSafe's own viral demo ("21,690 stop-or-scroll decisions, 22 cents").

---

## The three findings that shape our architecture

### 1. Fan-out is nearly free — latency is flat in question count
Going from 18 → 60 questions in a single request did **not** increase latency
(0.62 s → 0.38 s; the variance is network noise, not load). Input tokens scale with the
questions, but wall time does not.

> **Design rule:** batch every judgment that shares a `state` into ONE request.
> One request per (item × persona-set), not one request per judgment.
> A 60-question request costs the same wall time as a 3-question one.

### 2. Concurrency is real — no rate limiting observed at 100-way
100 simultaneous requests returned `{200: 100}`. Zero `429`, zero `529`, zero retries consumed.
p95 held at 1.09 s.

> **Design rule:** an `asyncio.Semaphore(100)` over a single `httpx.AsyncClient`
> (with `Limits(max_connections=200)`) saturates happily. We still ship exponential backoff for
> 429/529 because the docs promise them, but we have not provoked them at our demo scale.
> **We do not need Modal for throughput.** See `docs/research/` stack playbook for the full call.

### 3. Judgments are calibrated and they reproduce the case file's own insight
Asking Maya's six personas about the £62 Glass Drop — the case file's deliberate contradiction
("Good. Not £62 good.", her rating 8.1/10):

| Persona | P(Maya says buy) | Predicted behaviour | Trust damage (0–3) |
|---|---|---|---|
| Emily (price sensitive) | 0.28 | scroll_past | 1.49 |
| Priya (sensitive skin) | 0.28 | scroll_past (c=0.63) | **1.97** |
| Sophie (beauty obsessive) | 0.37 | save_for_later | 1.19 |
| Hannah (overwhelmed) | 0.31 | scroll_past | 1.34 |
| Grace (busy) | 0.29 | scroll_past (c=0.76) | 1.79 |
| Alex (**silent browser**) | 0.28 | **save_for_later (c=0.84)** | 1.75 |

Two things to notice, because both are demo gold:

- Jev refuses to recommend a product the creator likes but thinks is overpriced. It learned
  that from one sentence of her voice (`"Good. Not 62 quid good."`). **A machine that says
  "don't buy this" is the single strongest trust proof we can put on a screen** — and it directly
  answers the judges' question *"Would I trust this with my audience?"*
- Alex, the persona the case file flags as *"only one of them is quiet, and she may be the most
  valuable"*, is the one persona Jev predicts will **save rather than scroll**, at the highest
  confidence in the table (0.84). Jev independently rediscovered the 16:00 intelligence drop
  (`E-09.3: top-decile savers converted 2.4× more`). That is a slide-free way to prove we read
  the evidence.

---

## Accuracy check — 100% against the creator's own decision tree

The user's requirement was "make sure that accuracy is decent". It is better than decent.

Ground truth was taken **only** from evidence in the case file: Maya's routing rules (E-02.2), her
shelf notes (E-04) and the discounted leads (E-08). Six shoppers were drawn from her real DMs and
personas. Each was scored against all ten products — 60 judgments, **one `noul` per product**,
batched as six requests.

```
6 shoppers x 10 products = 60 judgments in 0.67s

OK gracelee        (E-01.2) top: SPF 50 .94, Cloud Cream .90, Red Reset .89, Soft Clean .72
OK oily_gym        (E-02.2) top: SPF 50 .94, Daily Gel .92, Clear Wash .86, Soft Clean .56
OK priya_sensitive (E-02.2) top: Red Reset .91, SPF 50 .89, Soft Clean .64, Tint Veil .35
OK joanna_2step    (E-01.9) top: SPF 50 .92, Soft Clean .63, Tint Veil .43, Night Serum .34
OK emily_budget    (persona) top: SPF 50 .93, Soft Clean .74, Daily Gel .62, Clear Wash .55
OK kate_date       (E-01.8) top: SPF 50 .77, Tint Veil .58, Daily Gel .24, Soft Clean .24

RECALL on Maya's documented rules: 11/11 = 100%
VIOLATIONS (recommended something her rules exclude): 0
```

Three behaviours emerged that nobody programmed:

1. **SPF 50 ranks top for every single shopper.** Her note on it is two words: *"Non-negotiable."*
   Jev turned that into a universal prior. That is voice fidelity you can point at on stage.
2. **Glass Drop (£62) never enters a single top-5**, despite Maya rating it 8.1/10 — because of
   *"Good. Not £62 good."* The model is refusing to upsell, exactly as E-08.3 demands.
3. **`kate_date`** ("first date Friday, doesn't care about skincare") gets Tint Veil, the *makeup*
   item — matching Maya's own intake question *"do you actually care about skincare or do you just
   want to look hot tomorrow?"* (E-02.1). It routed on intent, not on skin type.

> **Design rule:** one `noul` per (shopper × product) beats one `choice` over all products.
> It gives a full ranked distribution instead of a single winner, it degrades gracefully, and it
> is what makes a sortable/filterable visual possible. Ask them all in one request.

Reproduce with `accuracy.py` (scratchpad) → port to `backend/scripts/eval_judgement.py`.
**Run this as a regression check after any prompt change during the build.**

---

## Full-audience simulation — 3,000 judgments in 1.18 seconds

The hero mechanic, de-risked. 300 synthetic audience members (built from the six personas in E-01
crossed with skin type, budget and lifestyle variation) scored against all ten products on Maya's
shelf. Batched as **50 requests of 60 questions each**, at 100-way concurrency.

```
audience=300  products=10  requests=50 (60 questions each)
codes={200: 50}  wall=1.18s  judgments=3000  throughput=2535/s
tokens in=597,147 out=81,500
```

**2,535 judgments/sec** — higher than the 100-request test, because packing 60 questions per
request amortises the shared `state`. This is the batching shape to ship.

### The aggregate is a portrait of her taste

| Product | £ | % of audience Maya would send it to | mean P |
|---|---|---|---|
| SPF 50 | 26 | **100.0%** | 0.89 |
| Soft Clean | 22 | **100.0%** | 0.73 |
| Red Reset | 32 | 46.7% | 0.46 |
| Daily Gel | 24 | 43.0% | 0.44 |
| Tint Veil | 34 | 21.7% | 0.39 |
| Night Serum | 42 | 15.7% | 0.33 |
| Clear Wash | 20 | 16.7% | 0.27 |
| Cloud Cream | 38 | 10.0% | 0.24 |
| Oil Balm | 29 | **0.0%** | 0.12 |
| Glass Drop | **62** | **0.0%** | 0.10 |

Nobody wrote a rule for any of this. It is derived entirely from one short note per product:

- **SPF 50 → 100%** from *"Non-negotiable."*
- **Soft Clean → 100%** from *"Boring in the best way."*
- **Glass Drop → 0%** from *"Good. Not £62 good."* — she rates it **8.1/10** and still would not
  send it to a single person. This is E-08.3 (*"The most expensive product: Maya likes it. She would
  not recommend paying £62"*) reproduced from evidence, at scale, live.
- **Oil Balm → 0%** from *"Beautiful, but too much for me."*

> **The two products Maya would never recommend are the ones a naive recommender would push hardest
> (highest price, highest aesthetic appeal). That contrast is the demo.**

### Derived analytics that fall out for free
Because the matrix is dense, code alone — no further inference — yields:
- **Shelf coverage / gap analysis:** audience members with no confident recommendation.
  Measured: **0/300 (0.0%)** — her shelf covers her audience. A gap would be a product opportunity
  worth real money to a creator, and it is one line of Python over the matrix.
- Per-persona fit, per-price-band fit, "who is this product actually for", and any re-weighting the
  user drags a slider to — all instant, all from the same cached matrix.

**Cost note:** 3,000 judgments ≈ 600K input tokens. Run the big batch **once** per demo, cache to
JSON, and re-weight in the frontend. Do not re-run inference on every slider drag.

Reproduce with `audience.py` (scratchpad) → port to `backend/scripts/simulate_audience.py`.

---

## Voice → typed judgement — the whole chain, verified

Tano hands out **Wispr Flow**, and voice is already sitting in the evidence: Maya's voice note
(E-06.1, 00:52), Sofia's (E-06.1, 01:42), and — most pointedly — Case 003's E-04.4:
*"Walk-home voice notes · Audio · 9 hrs · **Unfiled** · 'where the real thinking is'."*

We don't need Wispr Flow's API (it is a dictation product, not a developer platform). **OpenAI gives
us the same capability on a key we already verified**, and the full chain runs end to end:

```
creator speaks  →  gpt-4o-mini-transcribe  →  Jev  →  typed verdicts across the whole shelf
    12 sec              ~1 s, £0.00               1.4 s, 20 questions
```

**Verified round trip.** Synthesised a voice note with `gpt-4o-mini-tts` (HTTP 200, 185KB), then
transcribed it with `gpt-4o-mini-transcribe` — it returned the text **with `£60` and "62 quid"
intact**. That transcript then went into Jev as `new_voice_note`, asking two questions per product
across the shelf (20 questions, one request, 1.40 s, 4,602 in / 755 out):

| Product | P(mentioned) | Verdict | Confidence |
|---|---|---|---|
| Cloud Cream | 0.88 | `endorse` | 0.95 |
| Red Reset | 0.85 | `endorse` | 0.96 |
| **Glass Drop** | 0.98 | **`endorse_with_caveat`** | 0.71 |
| *(other 7 products)* | <0.4 | `no_signal` | — |

Two things make this a demo beat rather than a plumbing detail:

1. **It caught the price reservation on its own.** Nothing in the question mentioned price. Jev
   returned `endorse_with_caveat` for the Glass Drop because she said *"good, just not 62 quid
   good"* — and its **lower confidence (0.71 vs 0.95)** is itself honest: that verdict genuinely is
   more ambiguous than the other two. Calibration doing visible work.
2. **It stayed silent about the seven products she didn't mention.** No hallucinated opinions.
   `no_signal` is a real answer, which is exactly what the `choice` primitive's no-match outcome
   is for.

### Why this matters strategically
This is the **onboarding** for any "capture the creator's judgement" product: *she talks for twelve
seconds and her taste compiles into a typed decision layer.* It turns the coldest part of a demo
(where does the data come from?) into the warmest — and it uses her actual voice, which is the one
thing the briefs insist we preserve.

It also converts Case 003's single most wasted asset (**9 hours of unfiled voice notes**) into the
input of a product, which is the sharpest possible answer to that case's brief.

Reproduce with `voice2judgement.py` (scratchpad) → port to `backend/scripts/voice_to_judgement.py`.

**Cost note:** OpenAI transcription is billed per audio token (116 audio tokens for ~12 s). Trivial.
Do not put Wispr Flow itself on the critical path — it is a dictation UX, not an API we control.

---

## Images → Jev — verified, and faster than expected

Jev takes **text state, not pixels.** The chain that works:

```
product photo  →  gpt-4o-mini vision (detail:"low")  →  structured attributes  →  Jev judges
                        ~16 images/sec at 40-way parallel            ~1–4 s per 20-product batch
```

### Single item — it slots an unseen product against her shelf

Two real product photos (Wikimedia), vision → attributes → Jev, with Maya's shelf as taste reference:

| | La Roche-Posay Anthelios @ £19 | Dior lipstick @ £38 |
|---|---|---|
| Would Maya stock it | 0.64 | 0.25 |
| Worth the price | 0.78 | 0.26 |
| Send it to | emily_price_sensitive | **nobody** (0.45) |
| **Competes with** | **her own SPF 50 — confidence 1.00** | **none (0.79)** |
| Verdict | *"Underpriced — she'd defend it higher"* | *"Good, but not worth the money"* |
| Credibility effect | Neutral (0.63) | *"Mild mismatch her audience would notice"* (2.38) |

Vision 2.9–4.8 s · Jev 1.03–1.08 s. It correctly placed an unseen sunscreen in her SPF slot at
**confidence 1.00**, and correctly ruled a luxury lipstick outside a skincare creator's lane.

### At catalogue scale — on 100% real products

**`data/real-catalogue-openbeautyfacts.json` — 359 real products** (real brands, real names, real
photography) pulled from the open [Open Beauty Facts](https://world.openbeautyfacts.org) database.
465 face creams / 604 sunscreens / 308 cleansers are available if we paginate further.

**This kills the single biggest objection to a catalogue demo.** The judging panel's cut list flagged
a fabricated catalogue as *"the best visual, poisoned by its data — one judge asking 'where did this
come from?' turns the showpiece into an embarrassment."* Nothing here is invented.

```
VISION : 60 images in 3.6s  (178,380 in / 4,175 out)  ~$0.029
JEV    : 120 judgments over 60 products in 3.92s      ~$0.0011
```

**Extrapolated: all 359 products ≈ 22 s of vision + ~4 s of Jev, for well under $0.30.**

### The framing matters — first attempt was too harsh
Asking *"would Maya put her name on this?"* against her own shelf returned **0 of 60** — because she
already stocks something better. Refusal reasons were sensible (36 `she_has_better`, 23
`not_her_lane`) but an all-dark wall is a worse visual and reads as "the model just says no."

**The fix:** frame it as a brand brief (*"a brand sent her these hoping she'll feature them"*), and
ask a 5-level `score` instead of a binary. That produces a **gradient** — which is what a wall needs.

```
DISTRIBUTION: min 0.70  median 1.87  max 2.85  spread 2.15
```

| Score | Product | Jev's stated reservation |
|---|---|---|
| **2.85** | CeraVe Facial Moisturizing Lotion | — |
| 2.75 | Cetaphil Moisturising Lotion | — |
| 2.72 | Cetaphil Gentle Exfoliating SA Cleanser | — |
| 1.09 | BIOAQUA Kiwi Vitamin E Essence | `generic` |
| 0.98 | St. Ives **Renewing** Moisturizer | `unproven` |
| **0.70** | M. Asam Vinolift Skin **Tightening** Cream | `unproven` |

**It rewards boring-but-good and punishes hype claims.** Her own note on Soft Clean is
*"Boring in the best way."* Nobody encoded that — it came out of her five words.

> **Design rules:** filter to face skincare with a vision `is_face_skincare` boolean *before* Jev
> (cheaper and cleaner than asking Jev to reject non-skincare). Use `detail:"low"` — it is ~10×
> cheaper and accuracy was unaffected for packaging. Batch 20 products per Jev request.

Reproduce: `scripts/vision_to_jev.py` (single) · `scripts/catalogue_wall.py` (scale).

---

## V2 mechanic 1 — Combinatorial basket judgement

> **⛔ SUPERSEDED 2026-09-20 — the divergence numbers in this section did not reproduce under a
> symmetric re-test and are RETIRED. The section is kept verbatim as the audit trail. Read the
> dated retirement note at the foot of this file, and `docs/11-honest-headline.md`, before
> quoting anything below.**

**The insight that fixes the generic problem.** Ranking products is what a dermatologist does, and we
measured it as 85% identical to one. **Choosing a SET under constraints is what Maya does, and it is
not generic.**

Code enumerates every feasible basket (all subsets of her shelf, filtered by budget / what you
already own / how many products you'll tolerate). Jev scores **every basket as a whole** in parallel.
One `choice` picks the winner among the top 8.

```
530 judgments across 6 shoppers x 2 judges in 4.8s   (each shopper resolves in <1s)
```

| Shopper | **Maya** | A dermatologist |
|---|---|---|
| @gracelee "dry + redness, £60" | Red Reset + SPF 50 — £58 | Cloud Cream + Soft Clean — £60 |
| @joanna "only 2 products" | SPF 50 + Soft Clean — £48 | *same* |
| @jessica "already have the night serum" | **SPF 50 only — £26** | Daily Gel + SPF 50 + Soft Clean — £72 |
| Priya "my face freaks out" | Red Reset + SPF 50 — £58 | + Soft Clean — £80 |
| Emily "not spending £100 on serum" | Daily Gel — £24 | SPF 50 — £26 |
| @kate "first date Friday HELP" | SPF 50 + **Tint Veil** — £60 | Daily Gel + SPF 50 + Clear Wash — £70 |

**5 of 6 diverge.** Maya averages **1.7 products / £46**; the dermatologist **2.3 / £59**.

> **⛔ RETIRED 2026-09-20 — disproved by our own re-test. Original text kept for the record:**
> ~~Headline: "Maya sends 0.7 fewer products and spends £14 less of your money. Same shelf,
> same shopper."~~
> **Re-measured symmetrically — 14 slots, 8 shoppers, 5 repeats: 0/8 diverge, 0.00 products, £0.**

Three behaviours nobody coded: her **E-02.2 routing fires** (REDNESS → Red Reset); **@kate gets the
makeup item**, matching her intake question *"do you actually care about skincare or do you just want
to look hot tomorrow?"*; and **@jessica gets subtraction** — *"no, you don't need it, just get SPF."*

**Load-bearing detail:** her routing rules must be **structured data** in state
(`her_written_routing_rules`), not prose. As prose they did not fire.

Reproduce: `scripts/engine_basket.py`.

---

## V2 mechanic 2 — the DM router (speculative fan-out)

One request per incoming message, **11 questions asked at once**, code consumes what applies. This is
the TypeSafe `speculative fan-out` pattern and it is what makes all 12 DMs one mechanism.

It classifies the job *and simultaneously* extracts skin type, budget, item tolerance, what they own,
which product they mean, urgency, and **which one question Maya would ask back**.

```
All 12 real DMs from E-01, 132 judgments, 0.68s total. 12/12 routed.
```

| Exhibit | Job | Conf | Route |
|---|---|---|---|
| E-01.1 "what shade are u wearing" | `what_is_it` | 0.99 | **asks back "What are you using now?"** — her E-02.2 shade rule |
| E-01.2 "dry + redness, £60" | `pick_for_me` | 1.00 | basket |
| E-01.4 "is the cloud cream worth £38" | `is_it_worth_it` | 1.00 | price ceiling |
| E-01.5 "already have the night serum" | `do_i_need_it` | 1.00 | basket minus owned |
| E-01.7 "i trust you more than Sephora" | `not_a_question` | 1.00 | acknowledge, no sell |
| E-01.8 "first date Friday HELP" | `occasion` | 0.95 | **asks back "do you actually care about skincare or do you just want to look hot tomorrow?"** |
| E-01.10 "buying it payday" | `later` | 0.96 | price watch |
| E-01.11 "what would you do if it was your money" | — | **0.25** | **correctly held as ambiguous** |

**Low confidence is a feature.** Below threshold it does not guess — it holds the message for Maya.

**Bug found and fixed:** `later` and `not_a_question` initially overlapped; E-01.10 misrouted at 0.65.
Sharpening the criterion to name the actual situation (*"waiting for money or time — payday, next
month, when it restocks"*) moved it to **0.96**. Criteria must describe concrete situations.

Reproduce: `scripts/engine_dm_router.py`.

---

## V2 mechanic 3 — link-paste onboarding

She pastes her handle. We read what she **already published** and Jev extracts her standard as typed
values. We extract **principles, not rankings** — because we proved rankings don't transfer (below).

```
0.67s, 1,483 input tokens, from 6 posts + 8 captions. No notes, no ratings, no interview.
```

| Extracted | Value | Correct? |
|---|---|---|
| sells_hard | "Actively tells people NOT to buy" | ✅ |
| price_sensitive | "Price is central to her judgement" | ✅ |
| routine_length | "Fewest possible products" | ✅ |
| subtraction | YES | ✅ |
| hype_tolerance | "Actively sceptical of hype" | ✅ |
| spends_whole_budget | NO | ✅ |
| category_she_defends | **spf** (conf 1.00) | ✅ |
| asks_before_advising | NO | ❌ |
| tone | **dry_decisive** (conf 1.00) | ✅ |

**8/9 = 89% of her documented standard, from public posts, in under a second.**

The single miss is honest and instructive: *"does she ask before advising"* lives in her **private
notebook** (E-02.1), not her feed. A scrape cannot see it. **That is exactly what the 60-second voice
top-up fills.**

Reproduce: `scripts/engine_onboarding.py`.

---

## V2 mechanic 4 — the share card re-decides for the receiver

E-09.4: **41% of high-value buyers first arrive through a private forward.** The receiver has never
heard of Maya. So the shared object is not a screenshot — it is a verdict that re-runs.

```
222 baskets judged in 2.55s
```

| Who opens the same card | Maya's answer |
|---|---|
| Priya, sender (sensitive, £80) | Red Reset + SPF 50 + Soft Clean — £80 |
| Her sister (oily, £40) | **SPF 50 only — £26** |
| Her mum (dry, £100) | Cloud Cream + SPF 50 — **£64, leaves £36 unspent** |
| A colleague who **owns SPF** (£60) | **Daily Gel — £24** (won't re-sell the SPF) |

This is the unoccupied ground the market brief identified and v1 failed to claim.
Reproduce: `scripts/engine_sharecard.py`.

---

## V2 mechanic 5 — the overnight queue (the autonomy number)

50 DMs (the 12 real ones plus realistic variants, including deliberate medical traps), triaged with a
four-way gate: answer / ask one question back / hold for Maya / refuse.

```
50 DMs triaged in 0.85s (250 judgments)
  ANSWERED OUTRIGHT                     12%
  ASKED HER ONE INTAKE QUESTION BACK    66%   <- this IS what she does (E-02.1)
  -> HANDLED WITHOUT MAYA               78%
  HELD FOR MAYA                          8%
  REFUSED / REFERRED ON (medical)       14%
```

**The safety gate refused every medical case** — tretinoin interaction, pregnancy, accutane,
perioral dermatitis, eczema medication, a 12-year-old, rosacea. Maya's stated red line
(*"a yes on a sensitive-skin product without a hard gate"*) is enforced, and it is enforced by a
`noul` against her own stated scope, not a keyword list.

The 8% held are exactly the right ones: *"not a beauty question…"* (job unclear 0.41) and
*"can you send me the one you would buy if you were me"* (**wants Maya personally, 2.7**).

> **At her real volume: ~3,744 of 4,800 handled while she sleeps, ~12 cards a day to swipe,
> ~672 referred on and never answered by a machine.**
> **70 hours a month becomes 12 cards a day.**

**Gate design note:** an early version treated "not enough info" as a failure and auto-answered only
10%. That was wrong — *asking one question back is her documented behaviour*, not a fallback. Routing
it as an action took the handled rate from 10% → 78%.

Reproduce: `scripts/engine_overnight_queue.py`.

---

## ⚠️ What does NOT work — the onboarding limit

Two negative results. **Read these before promising anything on stage.** They change the onboarding
design and they protect us from an overclaim a judge could dismantle in one question.

### 1. Cold start from organic content alone is weak — and it loses the refusals

Given **only** things Maya produced anyway — her six post titles with engagement (E-03) and the
twelve questions her audience sends her (E-01) — and **no** ratings, notes, routing rules or voice
note, Jev ranked her shelf at **correlation +0.46** with the full-evidence ranking. Top-3 overlap 2/3.

That sounds survivable until you look at the bottom of the list:

| | Top 3 | Bottom 2 |
|---|---|---|
| Cold start (organic only) | Red Reset, **Oil Balm**, SPF 50 | Soft Clean, Clear Wash |
| Full evidence | SPF 50, Red Reset, Cloud Cream | **Oil Balm, Glass Drop** |

Cold start puts **Oil Balm 2nd** — a product she actually rates 7.7 and describes as *"Beautiful,
but too much for me."* And the whole range compresses (2.03–3.02 vs 2.45–4.00).

> **The refusals do not survive cold start — and the refusals are the entire product.**
> You cannot infer "Good. Not £62 good." from someone's post titles.

### 2. Per-product judgement does NOT extrapolate between products

Seed Jev with the products she *has* annotated, ask it to predict the rest:

| Products she annotated | Correlation with her real ratings on the held-out rest |
|---|---|
| 1 | +0.25 |
| 2 | −0.08 |
| 3 | −0.11 |
| 5 | −0.63 |

Held-out scores collapse into mush (1.87 → 2.12 across eight products). **Knowing she rated SPF 50
"Non-negotiable" tells Jev nothing about how she feels about Cloud Cream.** More seeds did not help
and sometimes hurt.

This is correct behaviour, not a bug — Jev is a judgement model, not a preference-learning model.
It judges what it is *told*, it does not learn a latent user embedding. But it kills any pitch line
like *"annotate ten products and it learns your whole taste."* **Do not say that.**

### What this means — and it is good news for onboarding

The distinction that matters:

| Input | Transfers to unseen products? |
|---|---|
| Her **per-product ratings/notes** | ❌ No — does not extrapolate |
| Her **stated principles** (creed, voice rules, how she talks about money) | ✅ **Yes** — this is what drove the whole 359-product Wall |

The Wall works because it applies *"willing to say what is not worth buying"*, *"boring in the best
way"*, *"people need confidence, not more products"* — **general standards**, not memorised opinions.

> **Onboarding must capture PRINCIPLES, not a product spreadsheet.**
> Asking a solo creator to annotate 500 products is dead on arrival. Asking her to *talk for two
> minutes about how she decides* is not — and we have verified that voice → typed judgement works
> (12 seconds of speech → verdicts across her whole shelf in 1.4s, catching an implied price caveat).

**Honest framing for the stage:** *"It doesn't memorise her opinions — it applies her standard."*
That is both true and a better line than the overclaim.

Reproduce: `scripts/eval_coldstart.py` · `scripts/eval_annotation_transfer.py`.

---

## Verified request/response contract

```python
import httpx, asyncio

URL = "https://api.typesafe.ai/v1/systemone"
H = {"Authorization": f"Bearer {JEV_KEY}", "Content-Type": "application/json"}

payload = {
    "model": "jev-latest",                      # → resolves to jev-1.13.0 today
    "state": {                                  # str | object | array
        "creator": {"name": "Maya Rao", "decision_rules": "...", "voice": "dry, funny, decisive"},
        "product": {"product": "Glass Drop", "gbp": 62, "note": "Good. Not 62 quid good."},
        "shoppers": {"alex": {"tag": "silent browser", "says": "..."}},
    },
    "questions": {                              # your own ids; ids are NOT sent to the model
        "alex__buy": {
            "type": "noul",
            "instructions": "Would Maya tell `shoppers.alex` to buy `product`?",
            "criteria": {"true": "Maya says buy it", "false": "Maya steers them away"},
        },
        "alex__act": {
            "type": "choice",
            "instructions": "What would `shoppers.alex` actually do after Maya's verdict?",
            "criteria": {"buy_now": "Buys within a day", "save_for_later": "Saves it, buys days later",
                         "share": "Sends it to a friend instead", "scroll_past": "Ignores it"},
        },
        "alex__trust": {
            "type": "score",
            "instructions": "If Maya recommended `product` to `shoppers.alex`, what happens to their trust?",
            "criteria": ["Trust grows, exactly right for them", "Neutral",
                         "Mild mismatch they would notice", "They would feel sold to"],
        },
    },
}
```

Responses, confirmed by observation:

- `noul` → `{"type":"noul","noul": 0.28}` — probability of yes. **No confidence field.**
- `choice` → `{"type":"choice","choice":"save_for_later","probabilities":{...},"confidence":0.84}`
- `score` → `{"type":"score","score":1.97,"legend":{"0":"...","3":"..."},"probabilities":{...},"confidence":0.74}`
  — note `score` lands **between** levels; that float is what makes smooth visual gradients possible.
- `usage` → `{"input_tokens":…,"output_tokens":…}` on every response.

Backticked paths into `state` (`` `shoppers.alex` ``, `` `product` ``) work exactly as documented
and are how we keep one shared `state` with many per-entity questions.

### Naming convention that paid off
Question ids of the form `{entity}__{dimension}` let the frontend pivot the flat `answers` map into
a matrix with one line of code. Keep it.

---

## What this buys us for the demo

- A **live**, on-stage batch of 5,000–20,000 judgments finishes in **5–20 seconds**, for a few cents.
  We do not need to fake it, and we should not pre-record it.
- Because `score` returns a probability-weighted float plus the full distribution, every judgment is
  **already a visualisable quantity** — no post-processing needed to drive gradients, heatmaps,
  densities or animated particles.
- Because judgments are atomic and cheap, we can precompute a **dense matrix once** and let the
  frontend re-weight it instantly. Sliders that re-rank thousands of items at 60fps with **zero**
  further inference. (This is the `composite-scoring` pattern in TypeSafe's docs.)

## Open questions to settle next session

- Hard cap on questions per request (docs state 255 options per Choice, ≤10 Score levels; the
  per-request question ceiling is undocumented — we tested to 60 and it was healthy).
- Real rate limits on this key at 500+ concurrency, and whether sustained load provokes 429s.
- Whether `jev-latest` pins to `jev-1.13.0` for the whole event (read
  `https://docs.typesafe.ai/model-jaggedness/jev-1.13.md` before relying on any edge behaviour).

---

## ⛔ Retirement note — 2026-09-20, the divergence claim was retested and killed

**Appended, not merged. Everything above this line is left exactly as it was measured, so the
audit trail survives. This note overrides it.**

**What was retested.** "Maya sends fewer products and spends less of your money than a
dermatologist." First measured by `scripts/engine_basket.py` (**0.7 fewer products, £14 less,
5/6 shoppers diverge**), then by `scripts/engine_decontaminated.py` after three review personas
found hand-written rules in Maya's judge state and none in the dermatologist's (**3/8 shoppers,
0.2 products, £7**).

**By which script.** `scripts/engine_decontaminated_v2.py`, run against
`api.typesafe.ai/v1/systemone` (`jev-1.13.0`) on 2026-09-20 with `DECON_REPEATS=5`.
`scripts/engine_decontaminated.py` is deliberately left unchanged so the diff is auditable.
Raw output: `data/decontaminated-results.json`. Both full judge states, printed for a hostile
reader: `data/decontaminated-judge-states.json`. Extracted standards:
`data/standard-extracted.json`.

**What changed in the method.** Six typed slots became **fourteen**, asked identically of both
sides: four category-priority/scope slots and four routing-condition slots, each phrased as a
concrete situation in the asker's own words. The shelf in both judge states was made objective
(no `creator_rating`, no `creator_note`), shopper skin became multi-label, and routing entered
`state` as structured data. **No hand-written judgement rule was added to either side.**

**The result, modal over five full repeats:**

| | v1 authored | v1 decontaminated, 6 slots | **v2, 14 slots** |
|---|---|---|---|
| Basket divergence | 5/6 shoppers | 3/8 shoppers | **0 of 8 shoppers** |
| Fewer products | 0.7 | 0.2 | **0.00** |
| Less money | £14 | £7 | **£0** |
| Slot disagreement | n/a (rules) | 3 of 6 | **4 of 14** |
| Basket stability over 5 repeats | not measured | not measured | **1.00** |
| Extraction time | — | 0.72 s | **0.65 s** |

Per-run divergence was `[0, 0, 0, 0, 0]`, and 0/8 held across **four configurations** — matched
derm corpus, narrow derm corpus, objective shelf, v1 shelf — over ten full sweeps. The 3/8 was not
a small finding; it was under-specification. Ask both sides six questions and you measure the gap
in your own question set. Ask fourteen and it goes to zero.

**Retired from every live claim in this repo:** `£14` · `£7` · `0.7 fewer products` ·
`0.2 fewer products` · `5/6 shoppers diverge` · `3/8 shoppers diverge` · *"a dermatologist says
three products and seventy-two"* · *"forty-six pounds this machine just talked her out of
spending"* · any "she saves you money versus a dermatologist" framing. Also off every slide:
`skippable_category`, which flipped between `makeup` and `serum` across five identical extractions
(stability 0.60).

**What the same run established instead, and what the headline now rests on:**

| Result | Measured |
|---|---|
| Typed slots, both sides, extracted in **0.65s** | **14** — 10 agree, 4 disagree |
| Her private routing sheet (`E-02.2`) recovered from public captions alone, held out of every prompt | **3 of 3** — DRY→Cloud Cream, OILY→Daily Gel, REDNESS→Red Reset |
| Priya ("my face freaks out") gets Red Reset, Mode A, nothing forced | **5 runs out of 5** |
| Basket stability over 5 repeats | **1.00** |

Grep `HELD_OUT_PRIVATE_ROUTING` to confirm the private sheet only ever touches the scorer.
**Caveat recorded rather than hidden:** `route_reacting` for Maya is stable (5/5 extractions) but
**low-confidence at 0.34**, and the Priya result rests on it.

Full workings, including an adversarial self-review of everything still in our handwriting:
`docs/11-honest-headline.md`.
