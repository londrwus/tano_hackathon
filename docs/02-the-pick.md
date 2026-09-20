# The pick

**Case 001 — OPERATION SHADE (Maya Rao).**
**Build: THE FENCE — *what Maya's word is actually worth*.**

Decided from a 9-agent panel: 4 recon agents (Jev docs, Tano/judges, stack, market) + 3 concept
architects (one per case) + 2 independent judging lenses. **Both judges ranked The Fence #1**, from
opposite seats — one scoring as the creator-in-the-room, one as a TypeSafe engineer and demo critic.

Then the core mechanism was **empirically verified against the live API** before this doc was written.
See §5. It failed the first way we built it, and we know the fix.

---

## 1. Why Case 001

### It is the only case that needs zero fabricated data
This is the argument that decided it, and both judges landed on it independently.

| Case | What the inventory actually gives you | What you'd have to invent |
|---|---|---|
| **001 Maya** | **10 complete rows** — ref, product, price, type, skin, finish, a **numeric Maya rating**, and a **verbatim note** | **Nothing** |
| 002 Sofia | 8 of 36 items, notes but **no numeric ratings** | 25–200 garments **plus photography**, in the one vertical where the eye decides |
| 003 Aditi | 8 rows, 5 fields; the useful fields it names (Room, Decision, Cost, rating, "would I do it again?") are **printed but unpopulated** | ~53 authored ledger rows |

"Use of the evidence" and "Work with the evidence provided" are printed judging criteria. In a room
of ~54 builders where half the demos will contain invented inventory, being the team whose
showpiece is **100% real file** is an advantage nobody can copy in the last hour.

### Maya physically walks into the room at 17:00
Case 001's sheet 02 lists it: *"16:00 intelligence drop. 17:00 Maya walks in. 20:00 you pitch."*
No other case has the creator arriving before judging. That turns *"does it work"* from an assertion
into a live event — and Maya can verifiably confirm or correct *"would you tell someone this £62
serum is worth £62?"* Aditi cannot confirm a verdict about a stranger's career; Case 002's judging
sheet doesn't name Sofia among the judges at all.

### It has the only usable price contradiction
E-04.6: **Glass Drop, £62, Maya rating 8.1/10, her note: *"Good. Not £62 good."*** — plus E-08.3
explicitly flagging it as a discounted lead. A creator who rates a product highly and still refuses
to endorse its price is a **calibration target**, not a string. That single sentence is the whole
product.

### The honest case against
Case 001 is the crowded one — the market brief expects 40–50% of teams to build a Maya DM-bot and
30–40% a skincare quiz. **Crowding is a differentiation problem, and we solve it with the
mechanism, not by fleeing to a weaker case.** Nobody else will build a price-elasticity curve of a
human being's integrity.

---

## 2. What we are building

> **A creator's taste is not a list of links. It is a standard — and a standard can be applied to
> things she has never seen.**

Two layers, one engine.

### Layer 1 — THE STANDARD (her own shelf)
Sweep a price ladder per product; one `noul` per rung: *"If this cost £X, would Maya tell her
audience to buy it at that price?"* The 0.5 crossing is **THE MAYA LINE** — the price above which
her endorsement stops. **Headroom** = her line − its sticker.

### Layer 2 — THE WALL (products she has never seen) ← *the WOW*
Jev takes text, not pixels, so: **photo → `gpt-4o-mini` vision → structured attributes → Jev.**
Verified end to end. We point Maya's standard at **359 real products** — real brands, real names,
real photography, from the open Open Beauty Facts database. **Nothing fabricated.**

```
VISION : 60 real product images in 3.6s   (~16 images/sec)   ~$0.029
JEV    : 120 judgments over 60 products in 3.9s              ~$0.0011
→ all 359 products ≈ 22s of vision + ~4s of Jev, under $0.30
```

And it sounds exactly like her:

| Score | Product | Jev's reservation |
|---|---|---|
| **2.85** | CeraVe Facial Moisturizing Lotion | — |
| 2.75 | Cetaphil Moisturising Lotion | — |
| 0.98 | St. Ives **Renewing** Moisturizer | `unproven` |
| **0.70** | M. Asam Vinolift Skin **Tightening** Cream | `unproven` |

**It champions boring-but-good and rejects hype.** Her own note on Soft Clean is *"Boring in the
best way."* Nobody encoded that rule.

### The consumer gesture that ties them together
**Screenshot anything. Get Maya's verdict.** Priya sees a £62 serum on TikTok, drops the image in,
and in ~4 seconds gets Maya's actual answer — what it competes with on Maya's shelf, who it's for,
what Maya's line is for *it*, and whether she'd endorse it at that price.

The Wall is the proof that the gesture scales. The gesture is the proof that the Wall serves a person.

| For | It answers |
|---|---|
| **Priya** (31, sensitive skin) | *"Should I buy this thing I just saw?"* — including the refusal |
| **Emily** (22, *"I'm not spending £100 on serum"*) | what is actually worth her money |
| **Maya** | a rate card for her credibility, and a brand-brief screen |

### Name the person and the decision
Per the brief (*"If you cannot name the person and the decision, you do not have a product yet"*):

- **Person:** **Priya, 31** — E-01 persona, *"Every time I try something new my face freaks out."*
  Or **Emily, 22**, £60 in hand.
- **Decision:** *"Do I spend £62 on the Glass Drop everyone is posting about?"*
- **Today:** she asks Maya, waits, and either buys wrong or never buys. Per the 16:00 drop, 61% of
  buyers never DM at all — so mostly she just decides alone, badly.
- **With us:** she gets Maya's actual verdict, *including Maya's actual refusal*, in seconds,
  without Maya being in the loop.

---

## 3. The hero screen — THE WALL

One page. Near-black. Three beats on the same screen, no navigation.

**Beat 1 — the wall.** A full-bleed grid of **real product photographs**, 300+ of them, all lit.
Brands you recognise. This alone says "this is not a mockup."

**Beat 2 — the scan.** A vertical line sweeps left → right. Behind it, products **dim to near-black
and take a stamp** — `UNPROVEN` · `GENERIC` · `NOT HER LANE` · `FRAGRANCE RISK`. A handful stay lit.
A counter runs in tabular mono:

```
359 PRODUCTS · 718 JUDGMENTS · 3.9 SECONDS · $0.009
```

Because `score` returns a probability-weighted float, the dimming is a **gradient**, not a binary —
the wall has texture. (Measured spread 0.70 → 2.85; we verified it is not mush.)

**Beat 3 — the survivor.** One lit cell expands into the verdict card: the product, Maya's voice,
what it competes with on her shelf, **and its price curve** — her line vs its sticker. This is where
Layer 1 pays off: THE STANDARD is no longer a separate chart, it's the *evidence panel* behind a
single verdict.

**The consumer gesture, same screen:** a drop target. Drop any product photo → ~4 seconds → a new
cell joins the wall with its own verdict. That is the audience-facing product, live.

### Why this ordering (a correction to my earlier draft)
I previously made the ten-curve chart the hero. That was wrong on the **first** judging criterion:
a price-elasticity chart of Maya's shelf is a *creator-and-brand dashboard*, not value to a named
audience member. **The verdict leads; the curve proves it.** Same engine, same sweeps, same numbers —
inverted hierarchy.

*(Form, colour and motion specs: `04-visual-language.md`. Diverging blue↔red, neutral gray midpoint,
palette validated against our surface. Canvas 2D for the wall — 300+ animated cells is past the
DOM/React ceiling.)*

---

## 4. Why this wins on the stated axes

| Axis | The argument |
|---|---|
| **Value to a real audience member** | Priya is told not to spend £62. That is money in her pocket, from Maya's own judgement |
| **Fidelity to her voice** | 100% recall on her documented decision tree, 0 violations. SPF 50 tops every shopper because she wrote *"Non-negotiable"* — nobody coded that |
| **Use of the evidence** | Every pixel traces to a printed line of the dossier. Nothing invented |
| **Does it work** | Verified. 561 judgments, 0.97s, $0.003. §5 |
| **Would I trust it?** | **It refuses to sell.** A machine that turns down a sale is the strongest trust proof available |
| **Commercial potential** | §6 |
| **Elegance** | One question, asked 50 times per product. The entire product is one primitive |
| **Inventiveness** | Nobody has priced a human being's endorsement as a curve |
| **Jev showcase** | Pure `noul` fan-out, calibration rendered as consumer-visible honesty — the exact whitespace §7 identifies |

---

## 5. VERIFIED — and the trap we already fell into

**Read this section before writing a single question tomorrow. It will save hours.**

### Attempt 1 failed
Naive framing — product row + generic price question — produced a **Maya line of £20–28 for almost
every product, regardless of sticker.** Jev applied a generic "£25 is a lot for skincare" prior. The
frontier would have rendered nearly vertical: grey mush, no hero image, no product. This is exactly
the failure mode the technical judge predicted.

### The fix: give Jev *her* price universe, not the world's
Put **the other nine shelf rows into `state`** as `her_shelf_for_price_context`, with an explicit
note that this is the range she actually defends (£20–£62), and ask the question **counterfactually**
(*"If it cost £X, would she still say buy it?"*).

### Attempt 2 — the result

```
561 judgments (11 products x 51 rungs) in 0.97s, 71,630 input tokens, ~$0.003
```

| Product | Her note | Sticker | **Maya line** | Headroom |
|---|---|---|---|---|
| SPF 50 | *"Non-negotiable."* | £26 | £60.4 | **+£34.4** |
| Red Reset | *"For angry skin days."* | £32 | £53.7 | +£21.7 |
| Daily Gel | *"Easy. No drama."* | £24 | £42.6 | +£18.6 |
| Tint Veil | *"Best on camera."* | £34 | £49.0 | +£15.0 |
| Cloud Cream | *"My winter skin saviour."* | £38 | £49.6 | +£11.6 |
| Night Serum | *"Best for texture."* | £42 | £43.8 | +£1.8 |
| **Oil Balm** | *"Beautiful, but too much for me."* | £29 | £24.8 | **−£4.2** |
| **Glass Drop** | *"Good. Not £62 good."* | **£62** | **£40.0** | **−£22.0** |

**The only two products that fall below their sticker are exactly the two whose notes contain a
reservation.** Nobody wrote that rule. The headroom ordering also tracks her ratings.

### The held-out test lands
Re-run Glass Drop with **`maya_note` deleted** — the model sees only `Glass Drop, Serum, All, Dewy,
rating 8.1`, and calibrates from the other nine products:

| | Maya line | P(worth it) at £62 |
|---|---|---|
| With her note | £40.0 | **0.08** |
| **Note held out** | **£41.7** | 0.14 |

**It still puts her line £20 below the sticker without ever being told.** And her sentence *sharpens*
the refusal (0.14 → 0.08). This is a falsifiable, reproducible-on-stage calibration proof — the
answer to *"how do you know it sounds like her?"* that does not rely on vibes.

**Reproduce:** `scripts/price_curve_sweep.py` (working) · `scripts/price_curve_sweep_v1_FAILED.py`
(kept deliberately, so nobody re-invents the broken framing).

---

## 6. The commercial argument

Tano's own numbers, from the intel brief: **they sell to brands, not creators** — ~**$35–45 per
creator** plus management fees; customers Bloom & Wild, Skin+Me, Wild; **70% MoM** growth; their
agent "Charlie" matches creators to briefs. Their stated religion:
*"AI handles intelligence, humans handle relationships."* Will Caplan's thesis:
*"Influencers have become walking billboards… when consumers see that, they stop trusting."*

**The Fence is that thesis, made measurable.**

- **To a brand:** before you pay a creator, you can see whether her endorsement of *your* £62 product
  is credible **to her own audience** — priced, not guessed. That is a pre-campaign screen Tano could
  sell tomorrow, and it directly de-risks the ROAS they sell to FMCG clients.
- **To a creator:** a rate card for her credibility. She can decline the brief that would cost her
  more trust than it pays — which is the thing Caplan says the whole industry is burning.
- **To Tano specifically:** say the line out loud — ***"this is Charlie, pointed the other way."***
  Their tagline just migrated from "AI-native influencer agency" to "the AI creator-led growth
  partner". A hackathon whose three case files are all creator-side is a company **shopping for its
  creator-facing product.** Winners get interviews.

---

## 7. Why this isn't a Jev cliché

**Critical intel: persona simulation is already saturated.** madewithjev.com has ~187 builds in five
days, including *"A/B test against 4,000 personas"*, *Crowdcheck* (10,000 persistent synthetic
personas), *"100,000 viral posts in 20.4 seconds"*, and TypeSafe's **own official cookbooks** on
comparing messages with synthetic personas.

> **If our build is "we made 30 fake Mayas react to a post", a TypeSafe person in the room has seen
> five of those this week and the wow is gone.**

That is why **STAKEOUT — the 200-ghost synthetic audience — is cut**, despite being the first idea
everyone (including me) reaches for. The simulation stays as *substrate*, never as the pitch.

The identified whitespace, which The Fence occupies:
- **Jev pointed at one individual's decision**, not at a corpus — calibrated *personalisation*, not
  calibrated *classification*. Every existing demo is many-items/one-judge.
- **Transferring a specific human's taste with their contradictions preserved.**
- **Probability and confidence rendered as UI a non-technical person reads as honesty** — every
  existing demo renders confidence as a dev-facing debug number. Nobody has made calibration *feel
  like trust to a consumer.* That is simultaneously the most elegant and most inventive move
  available, and it is literally what the case file asks for: *"People do not need more products.
  They need confidence."*
- **Vision → Jev.** Jev is text-only, so every build on madewithjev judges *text*. Putting a vision
  model in front of it so Jev can judge **photographs** — and running that over a real product
  catalogue — is a shape nobody there has shown. It is also the honest answer to "what else could
  this model do?", which is the question TypeSafe people came to have answered.

---

## 8. The biggest risk, and the beat that converts it

**Maya rejects the premise at 17:00.** We are putting a number on a creator's integrity and then
showing it to her in person, two hours before judging. If she says *"that's not how I think about
it — it's case by case, not a curve"*, we are not merely marked down on fidelity; it reads as
presumptuous about the exact thing her brand is built on.

**Mitigation — and this is also the best moment in the demo:**

1. **Make the Maya Line a draggable handle from the first commit.**
2. **Label it honestly on screen:** `ESTIMATED FROM MAYA'S OWN NOTES — SHE SETS THE LINE.`
3. **Show confidence bands, not hairlines.** We have the distributions; use them.
4. **End the demo by handing her the control.** *"Is £44 right? Move it."* She drags; every
   downstream verdict re-ranks instantly with zero inference.

That single interaction answers *Would I use it? Would I trust it? Would my audience use it?* in
one gesture, and it obeys sheet 16's instruction — **"DO NOT ASK 'do you like our app?' Ask about
the behaviour you observed instead."**

---

## 9. Explicitly NOT building

From the judges' combined cut list:

- **A DM bot / inbox assistant** — pre-killed by the file itself (E-08.1: *"Too literal. It handles
  volume, not judgement"*), and post-16:00 it is *actively wrong*.
- **A skincare quiz → 3 products** — Octane AI, 5,000 merchants, ten years old.
- **"Maya's Shelf" filterable storefront** — it's ShopMy with worse design, and it delivers a
  *catalogue*, the exact thing the briefs forbid.
- **Any chat interface, typing indicator, or "Hi, I'm Maya's AI"** — her pet peeve is printed on
  sheet 03: *generic automation*. A verdict card is not a conversation.
- **A video avatar clone** — maximum surface wow, maximum trust risk, and Maya is in the room.
- **The 200-ghost synthetic audience** — §7.
- **Any fabricated catalogue.** ✅ **Solved** — `data/real-catalogue-openbeautyfacts.json` holds 359
  real products with real brands and real photography from an open database. When a judge asks
  *"where did this catalogue come from?"* the answer is a URL, not a shrug. **If we ever find
  ourselves inventing a product to make the wall look better, stop.**
- **Any threshold tuned to produce a headline.** If we tighten criteria until the refusal rate makes
  a nice number, we are fitting the demo, and a TypeSafe judge will smell it. Report the
  distribution we actually got.
- **Any retrodiction claim against E-03.** There is one labelled outcome (317 conversions on E-03.5)
  plus one stated negative. That is n=2. Do not build a validation story on it.
- **The retinol line as a hard guardrail.** *"DO NOT RECOMMEND RETINOL TO EVERYONE"* sits on E-02.4,
  an **unrelated to-do list**, between "call Sarah" and "buy more brown lip liner". Do not present
  it as policy — a judge who reads the sheet will catch it.

### One disagreement between the judges, resolved
The creator-lens judge wanted **zero inference on stage** (a static cached file that cannot fail).
The technical judge called that *"architecturally correct and strategically wrong — TypeSafe judges
watching a JSON lookup never see Jev run."*

**Resolution: run exactly one live sweep on stage.** The full 561-judgment sweep takes **0.97s** and
costs a third of a cent. Fire it live, with the counter visible, then everything downstream is
arithmetic on the cached array. If the venue wifi is dead, one keypress falls back to the committed
cache and the demo is unchanged. Both judges get what they actually wanted.

---

## 10. The final line

> **"Maya no longer needs to be in the room for her audience to know what she'd actually say —
> because her judgement now has a price."**
