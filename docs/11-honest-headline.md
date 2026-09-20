# 11 — The honest headline

**LANE C (TRUTH). Measured live against `api.typesafe.ai/v1/systemone` (`jev-1.13.0`) on 2026-09-20.**
Reproduce with `python scripts/engine_decontaminated_v2.py` (set `DECON_REPEATS=5`).
Raw numbers: `data/decontaminated-results.json` · extracted standard: `data/standard-extracted.json`
· the full judge states, printed for a hostile reader: `data/decontaminated-judge-states.json`.

---

## 0. The one-paragraph version

We extracted eight more typed slots out of Maya's captions instead of writing rules, as §2 of
`09-GO.md` required. **The fidelity bug is fixed: Priya now gets Red Reset, in 5 runs out of 5,
with nothing forced.** And **the divergence claim died completely.** With both judges asked the
same fourteen questions, Maya and the dermatologist return the **identical basket for all eight
shoppers**: 0/8 divergence, 0.00 products' difference, £0 difference. The 3/8 in the six-slot run
was not a small finding — it was under-specification, and it disappears the moment you ask both
sides enough questions. What survives is better founded and, we think, more interesting: the
questions still disagree, and the routing we pulled out of her public captions matches the private
routing sheet she keeps in her head — a sheet the extractor never saw.

---

## 1. Before / after

| | Authored (what we nearly claimed) | Decontaminated v1, 6 slots | **Expanded v2, 14 slots** |
|---|---|---|---|
| Script | `engine_basket.py` | `engine_decontaminated.py` | **`engine_decontaminated_v2.py`** |
| Basket divergence | 5/6 shoppers | 3/8 shoppers | **0/8 shoppers** |
| Fewer products | 0.7 | 0.2 | **0.00** |
| Less money | £14 | £7 | **£0** |
| Priya gets Red Reset | — | **NO** (`SPF 50` alone) | **YES — 5/5 runs, nothing forced** |
| Slot disagreement | n/a (rules, not slots) | 3 of 6 | **4 of 14** |
| Her private routing sheet recovered from public posts | not tested | not tested | **3 of 3** |
| Basket stability over 5 repeats | not measured | not measured | **1.00** |
| Extraction time | — | 0.72 s | **0.65 s** |

Every v2 number is the **modal** result over **5 full repeats** of the whole shopper sweep, not a
single run. Per-run divergence was `[0, 0, 0, 0, 0]`.

### The fourteen questions, both sides, verbatim

| Slot | Maya, from her public posts | A dermatologist, from clinical guidance | |
|---|---|---|---|
| routine_size | **The fewest possible products** | A small routine | ✗ |
| price_refusal | **Price is central to their judgement** | Mentions price occasionally | ✗ |
| skippable_category | makeup *(unstable — see §5)* | serum | ✗ |
| route_reacting | **Red Reset** | Soft Clean | ✗ |
| budget_behaviour | leaves money unspent | leaves money unspent | = |
| subtraction | YES | YES | = |
| hype | sceptical | sceptical | = |
| defended_category | spf | spf | = |
| interchangeable_category | cleanser | cleanser | = |
| starting_from_zero | three products | three products | = |
| subtraction_scope | only to a crowded routine | only to a crowded routine | = |
| route_redness | Red Reset | Red Reset | = |
| route_dry | Cloud Cream | Cloud Cream | = |
| route_oily | Daily Gel | Daily Gel | = |

**Ten agree, four disagree.** The four disagreements are real but they do **not** change a single
basket.

### The held-out check — the strongest thing we found today

`case-001-maya.json → decision_rules.routing` (**E-02.2**, "the routing she already does in her
head") was **never put in any prompt**. It is loaded at the end purely to score what we discovered
from her public captions plus the shelf:

| Condition | Her private sheet | What we extracted from public posts alone | |
|---|---|---|---|
| DRY | Cloud Cream / Barrier Oil | **Cloud Cream** | ✓ |
| OILY | Daily Gel | **Daily Gel** | ✓ |
| REDNESS | Red Reset | **Red Reset** | ✓ |

**3 / 3.** This is a genuine held-out test, it is in the code, and a judge can grep for
`HELD_OUT_PRIVATE_ROUTING` to confirm it only ever touches the scorer.

---

## 2. The sentence we are allowed to say on stage

> **"We asked her public posts and a dermatologist's clinical guidance the same fourteen questions
> and had both answers back in under a second. They agree on ten and disagree on four. Then we
> checked the routing we'd pulled out of her captions against the routing sheet Maya keeps in her
> head — which this machine has never seen — and it matched three times out of three."**

If anyone asks whether that changes what gets bought, the honest follow-up, which we should
volunteer rather than wait to be caught on:

> **"On the actual baskets, they land in the same place eight times out of eight. Once you ask both
> sides enough questions, the dermatologist and the creator buy the same things. The difference is
> who it's for and how it's explained — not a cheaper bill."**

And the fidelity beat, which is now true and was not this morning:

> **"Priya says her face freaks out at everything. She gets Red Reset. Nobody wrote a rule that
> says redness means Red Reset — that came out of a caption, and it agrees with the routing sheet
> in Maya's head."**

---

## 3. Claims we must retire — now, everywhere

1. **"0.7 fewer products, £14 less."** Dead since the v1 decontamination. Never say it.
2. **"5/6 shoppers diverge."** Dead. Artefact of hand-written rules in Maya's state only.
3. **"3/8 shoppers diverge, 0.2 fewer products, £7 less."** ← **NEW.** The v1 decontaminated
   baseline in `09-GO.md` §2 **also does not survive.** It was produced by asking only six
   questions. Ask fourteen and it goes to 0/8. Do not use 3/8 anywhere.
4. **Any "Maya vs a dermatologist saves you money" framing at all.** Our own symmetric test says
   the saving is **£0**.
5. **`09-GO.md` §2 table "they agree on three and disagree on three".** Superseded: **ten agree,
   four disagree, out of fourteen.**
6. **⚠ `09-GO.md` §7 step 1 and `docs/07-demo-script.md` — the cold open.** *"A dermatologist says
   three products and seventy-two. That's forty-six pounds this machine just talked her out of
   spending."* **This is not reproducible under the symmetric test.** For @jessica (owns the Night
   Serum, £80) both judges return `SPF 50 + Soft Clean`, £48. **The opening beat of the demo rests
   on a number we just disproved.** LANE C does not own `docs/07`; whoever does must change it
   before rehearsal. The refusal itself is still real and still evidence-backed — the £62 Glass
   Drop, *"Good. Not £62 good."* (E-04.6) is verbatim from the case pack. Open on **that** refusal,
   not on a dermatologist comparison.
7. **`skippable_category`** must not go on a slide. It flipped between `makeup` and `serum` across
   five identical extractions (stability 0.60).

---

## 4. What actually changed in the engine

`scripts/engine_decontaminated.py` is **kept unchanged** so the diff is auditable.
`scripts/engine_decontaminated_v2.py` is the new run. No hand-written judgement rule was added.

* **+4 category-priority / scope slots** — `interchangeable_category`, `skippable_category`,
  `starting_from_zero`, `subtraction_scope`. The last one exists because her caption says *"stop
  adding things, take things away"* and we needed to know **who she says it to**; extracted answer,
  both sides: only to someone already using a lot of products. That is what stopped the
  over-collapse — not a rule.
* **+4 routing-condition slots** — each phrased as a **concrete situation in the asker's own
  words** (*"every time I try something new my face freaks out"*), per the `09-GO.md` §5 bug #4
  finding, not as a bare label.
* **Routing lands in `state` as structured data** under `her_written_routing_rules`
  (`by_situation` / `by_category`), per bug #3. Identical key, identical shape, on both sides.
* **Shopper skin is multi-label**, per bug #1: one `noul` per condition (dry / oily / combination /
  sensitive / redness), extracted from what the shopper wrote. Priya comes back `sensitive 0.98`.
* **The shelf in both judge states is now objective** — no `creator_rating`, no `creator_note`. v1
  put Maya's own words (*"Non-negotiable."*, 9.6) inside the **dermatologist's** state. That was
  symmetric but it let her voice leak into the control. Set `DECON_OBJECTIVE_SHELF=0` to reproduce
  the v1 configuration; baskets stay 0/8 either way.
* **Two modes are run and both reported.** Mode A leaves the routing in `state` and forces nothing.
  Mode B additionally turns each judge's **own** extracted routing into a feasibility filter when a
  condition fires above 0.6, as `09-GO.md` §6 sanctions. **Priya gets Red Reset in Mode A** — the
  unforced one — so the fidelity result does not depend on the filter at all.

---

## 5. Adversarial self-review — our handwriting, listed

We printed both final `state` dicts (`data/decontaminated-judge-states.json`) and grepped them.
Structural symmetry holds: identical top-level keys, identical `extracted_standard` keys, identical
`her_written_routing_rules` keys, byte-identical `shelf`, byte-identical `instruction`. The only
differences are `name` and the extracted values. No v1 rule string survives anywhere — grep for
`Fewer steps`, `does NOT spend`, `whole budget`, `retinol`, `Non-negotiable`: **zero hits in either
state.** The only occurrence of the string `Maya` in either state is the literal `"name": "Maya Rao"`.

**That is the good news. Here is everything a hostile judge can still legitimately call ours.**

1. **The caption corpus is a reconstruction, and it is our biggest exposure.** The six post
   *titles* (E-03.1–E-03.6), the £62 note (E-04.6) and the creed (E-06.1) are verbatim from the
   case pack. The caption **bodies** the extractor reads were written by us in the voice of those
   titles. We chose the words the machine reads. We cannot remove this without a real scrape, which
   §6 of `09-GO.md` explicitly discarded as login-walled. **Say "reconstructed from her posts", not
   "scraped".**
2. **The dermatologist's corpus is 100% written by us** — twelve statements. v1 had six; we added
   six (irritation, erythema, dryness, oiliness, cost, cleansing) so the control was not starved of
   routing content that Maya's captions have. **We ablated this**: revert to the original six and
   slot disagreement goes 4/14 → 6/14, but the baskets stay **0/8**. So our expansion did not
   manufacture the convergence — but it is still our writing, and it is the reason the *slot* count
   moved. `ablation_narrow_derm_corpus` in the results file.
3. **We chose the fourteen questions.** They are symmetric, but their wording, their criteria
   ladders and their very existence are ours, and they demonstrably move answers. Adding
   `starting_from_zero` took Maya from "the fewest possible products" in practice to a three-item
   basket. **Our question changed her answer.** Anyone claiming the standard is "just extracted"
   should be corrected: the *values* are extracted, the *questions* are designed.
4. **The mechanism is ours**, applied identically to both sides: the two-stage basket (score all,
   take top 8, one `choice`), the `defended_category` hard feasibility filter, the 0.6 condition
   threshold in Mode B, the `max_items` caps, and the eight shoppers with their budgets — those
   shoppers are ours, not from the evidence, apart from Priya, Emily and @gracelee.
5. **There is one sentence of our prose inside both `state` dicts**, and it is load-bearing:
   *"Where a rule in `her_written_routing_rules.by_situation` matches this shopper's conditions, it
   is what this person actually does."* It is byte-identical on both sides and it contains no
   judgement — but it is an instruction to obey the routing, and without it the routing is less
   likely to fire. We are not hiding it. It is line 1 of `judge_from_slots()`.
6. **The key is called `her_written_routing_rules` on the dermatologist too.** Ugly, and it is
   there because `09-GO.md` §5 names that key and LANE A reads it. Structural symmetry beat
   pretty naming. Worth knowing before someone screenshots the derm's state.
7. **`route_reacting` for Maya is low-confidence: 0.34** (though it returned `Red Reset` in 5/5
   extractions). That low number is the model being genuinely torn between `Red Reset` and *"tell
   her to buy nothing"* — which is exactly the tension in her caption. It is honest, it is stable,
   and it is the slot the whole Priya result rests on. Do not present it as certainty.
8. **`skippable_category` is unstable** (0.60 over five extractions). Reported above; keep it off
   the slide.
9. **We did not fix the divergence story; we killed it.** We were asked to publish whatever number
   came out. It came out zero, across four separate configurations (matched corpus, narrow corpus,
   objective shelf, v1 shelf) and across ten full sweeps. We are not going to round that toward the
   story.

---

## 6. Recommendation

Drop "she diverges from a dermatologist" from the narrative entirely. It is the one claim the
personas attacked, we have now tested it four ways, and it does not hold. Lead instead with the two
things that did hold and that nobody has questioned:

1. **The standard is recovered, not authored** — fourteen typed slots out of her public posts in
   **0.65 seconds**, each shown next to the caption it came from, each one tappable; and the
   routing matched her private sheet **3/3** on a held-out test.
2. **It routes like her** — Priya says her face freaks out, `sensitive 0.98` fires, and Red Reset
   lands in the basket **5 runs out of 5**, from a caption, with no rule written by us.

That is a smaller claim than "she saves you £14". It has the advantage of being true.
