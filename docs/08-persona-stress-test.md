# Persona stress-test — what's actually wrong, and what to build

Five adversarial personas reviewed THE FENCE independently: **Maya** herself, **Priya** (the named
audience member), a **Tano operator**, a **tired hackathon judge at 19:50**, and an
**onboarding/adoption critic**. Then one agent consolidated. Full transcripts in `docs/personas/`.

Alongside them I ran four new experiments against the live API. **Two of them contradict claims we
were about to make on stage.** Those come first, because they change the product.

---

## 1. The verdict, in one paragraph

> THE FENCE has the only real idea in the room — pricing a human being's endorsement as a curve —
> and the mechanism is verified, not asserted. **But it is currently a proof of the mechanism
> wearing a product's clothes**, and four of five personas reached that conclusion independently
> from different seats. Will it WOW? **Yes — at second 38**, when Glass Drop reads £62 sticker /
> £40 line / *"Good. Not £62 good."* Not at second 0, with a grid a tired judge reads as a
> screensaver and Priya read as a crypto site.

Maya's own line: **"You built the proof and forgot the product."**

The judge's scores: use of evidence **9/10**, voice fidelity **8/10** — but
**value to a real audience member 5/10**, would-my-audience-use-it **4/10**,
**would I share it 3/10**.

---

## 2. Two experiments that changed my mind

### 2a. ❌ The Wall is largely generic — Maya is ~decoration on it

The adoption critic predicted our CeraVe/Cetaphil result was "almost exactly the r/SkincareAddiction
consensus" and proposed a test. I ran it: the same 50 real products judged twice — once as Maya,
once as *"a generic good-taste dermatologist"*.

```
TOP-10 OVERLAP: 8/10 = 80%
TOP-20 OVERLAP: 17/20 = 85%
CORRELATION:    +0.859
```

**On taste ranking, Maya adds almost nothing.** If Sagar Shah — a judge who makes content himself —
asks *"how do I know this isn't ChatGPT with a skincare prompt?"*, the honest answer today is
"mostly, it is."

I then tested whether the **price** axis is more uniquely hers. Partly, but not cleanly:
ceiling correlation **+0.79**, with Maya systematically ~£12 more generous. That gap is largely an
artifact of giving Maya a price universe and the dermatologist none.

> **Conclusion: the differentiator is NOT the ranking and NOT the wall. It is the specific
> refusals on her own shelf, where we hold her actual sentences** — Glass Drop and Oil Balm, the
> only two products whose line falls below sticker, and the asymmetry between them.

Reproduce: `scripts/eval_ab_vs_generic.py`.

### 2b. ⚠️ The held-out proof is much weaker than we claimed

Maya's own challenge: *"Deleting the Glass Drop note might just mean the model has a generic
'expensive dewy serum is suss' prior. Test me on an **asymmetry**."*

So I ran leave-one-note-out across five products:

| Product | Line WITH her note | Line with note DELETED | Shift |
|---|---|---|---|
| SPF 50 *"Non-negotiable."* | £54.0 | £52.0 | −2.0 |
| Soft Clean *"Boring in the best way."* | £33.4 | £33.5 | +0.1 |
| Glass Drop *"Good. Not £62 good."* | £36.0 | £31.8 | −4.2 |

**Her sentence moves the line by £0–4, not by £22.** The model gets the ordering from rating, type
and shelf context — *not* from her note. **Do not say "we deleted her sentence and it found her
standard."** A technical judge will take that apart.

**What IS defensible, and it survived the test:**

```
Her SPF 50  costs £26 and she defends it to £54
Her Soft Clean costs £22 and she defends it to £33
-> Two cheap products, £21 apart. Not a generic price prior.
Would she buy a £34 cleanser?  P = 0.48  -> NO   (exactly as Maya predicted)
```

Run-to-run variance is small (SD ≤ £1.3) but the line moves ~£5 between prompt formulations.
**Maya was right on both counts: round it, and show a band.** `£50–55`, never `£54.0`.

Reproduce: `scripts/eval_asymmetry.py`, `scripts/eval_line_variance.py`.

### 2c. ✅ Two things that *did* work

- **The price-data blocker is solved.** The judge proved Open Beauty Facts has **no price field**
  (verified: 11 fields, none of them price), so "is it worth £X?" can't run on 349 of 359 products.
  **Fix: invert the question.** Don't ask "is it worth £X" — ask **"what would Maya pay for this?"**
  No price input needed; the shopper is already looking at the price. Measured on 10 real products:
  stable ceilings (SD 0.0–1.2), e.g. pipette Mineral SPF 50 → £34, a lip balm → £17.
  Reproduce: `scripts/eval_price_ceiling.py`.
- **Ingredients unlock Priya's actual problem.** 198 of the catalogue have full ingredient lists.
  Adding them doubled information-sufficiency (0.14 → 0.30) and produced a correct safety axis:
  Acnemix 0.92 / L'Oréal Revitalift **Laser** 0.85 / transparent sun **spray** 0.85 irritation risk,
  versus **Cetaphil 0.25** and **mineral** SPF 0.37. That is the textbook sensitive-skin answer.
  Reproduce: `scripts/eval_ingredients_safety.py`.

---

## 3. The six blockers (all five personas converged)

| # | Blocker | Who raised it |
|---|---|---|
| 1 | **No shareable, persistent verdict object.** The unit of value is a card; we built a screen. E-09.4: 41% of high-value buyers arrive via a private share. A link to a black grid is a dead share | **All five** |
| 2 | **The wall is the wrong hero** — illegible on a projector, presumptuous to Maya, and *"a catalogue with the lights off"*, which our own kill-list forbids | Maya, Priya, judge, Tano |
| 3 | **No price on the wall** → the mechanic we're named after applies to 10 of 359 products | Judge (proved from our files) |
| 4 | **The onboarding that works is sitting in a drawer.** Voice → shelf is verified; the plan instead implies 20–40 min of typing. `03-build-plan.md` contains the word "onboarding" zero times | Maya, Tano, judge, critic |
| 5 | **Zero personalisation.** Priya gets the identical verdict Emily gets — and Priya's constraint is her *face*, not her money | Priya, Maya, Tano, critic |
| 6 | **No provenance layer.** Unlabelled verdicts on products Maya never touched, float scores, decimal pounds, no disclosure | Maya, Priya, critic, Tano |

Plus two serious ones worth naming:

- **Legal exposure.** Public negative stamps on named third-party brands, under Maya's name.
  *"Brand deals are a third of my income. I have a legal email and no deal."* Tano's own clients
  include **Skin+Me and Bloom & Wild** — a red stamp on a client's product on stage is the worst
  possible outcome of a winning demo. **Check the wall against their client list.**
- **It answers ~2 of the 12 documented DMs.** Three personas counted independently and all got 2.
  The canonical DM — *"dry skin + redness and £60, tell me what to buy"* — needs a **budget
  tradeoff** (Cloud Cream £38 + Red Reset £32 = £70, she has £60) and we stop one step short.

---

## 4. Revised build list

Ranked by (impact on winning + real usefulness) / cost. Full detail in `docs/personas/synthesis.json`.

### Build tomorrow — hero
| Feature | Time | Why |
|---|---|---|
| **The verdict card as THE product** — phone-first, permalink, share image, provenance badge | 3h | Highest convergence item. All five personas |
| **Price ladder on the wall survivors** — put an actual fence in The Fence, via the *ceiling* inversion | 1h | Closes blocker 3; already verified |
| **Leave-one-note-out across all ten** | 45m | Turns our weakest claim into a real one. Already built: `eval_asymmetry.py` |
| **Voice onboarding, placed in the product** | 2h | Pipeline verified; this is placement + UI |

### Build tomorrow — strong
| Feature | Time | Why |
|---|---|---|
| **The budget basket** — "£60, dry + redness" → a *set*, with the tradeoff | 2h | Maya's #1 audience ask; answers the canonical DM |
| **One-tap skin type + hard refusal gate** | 1.5h | Priya's actual problem; ingredients work is done |
| **Shrink the wall to ~24 recognisable products** + honest split counter | 1h | Fixes blocker 2 and the counter honesty bug in one move |
| **Persist the line** — drag writes back, survives refresh | 1h | Maya's explicit quit condition: *"if it doesn't persist, it's a screensaver"* |

### Build tomorrow — supporting
Legal/disclosure pass (40m) · copy-as-reply button (20m) · camera capture instead of file drop (20m)
· ~~rotate and env-ify the API keys~~ ✅ **done — 8 files cleaned, `.env` gitignored**

### After the hackathon
- **The price-drop trigger** — *"She said not at £62. It's £39 today. That's now a yes."* An
  autonomous commercial event from an opinion recorded once. Highest commercial potential of
  anything proposed; needs a price feed we don't have.
- **The morning approval queue** — Maya's own spec, and the only thing that touches her 70 hours.
- **Storefront/caption importer** — cold start when there is no case file.

---

## 5. Cut list

- **The 359-tile wall as hero** → ~24 recognisable products, with "359" as a line of *text*.
- **The cost-per-judgement counter in the consumer view.** Priya: *"$0.009 reads as her judgement
  being printed by the yard"* — the visual signature of her printed pet peeve. Keep it for the
  brand view.
- **Float scores and decimal pounds shown to anyone.** `2.85`, `£60.4`. Round; show a band.
- **"Nothing fabricated" as currently phrased.** True of photos and names, false of prices.
  Say *"real products, real photography"*.
- **"This is Charlie, pointed the other way."** The Tano operator says it dies on the first
  follow-up — Charlie runs an operational chain we don't touch.
- **The word "autonomous".** Four personas, same conclusion: it removes zero DMs today. Use
  **leverage** — E-06.3 hands us the word.
- **First-person Maya voice on any product she hasn't touched.** That's a fabricated quote and an
  ASA problem. Third person, always.
- **The 30-second scan animation** → 1.2 seconds, then get to the card.

---

## 6. On "fully autonomous" — the honest answer

**It isn't, and it shouldn't be.** Maya said: *"I genuinely do not want to stop talking to my
audience. That is the best part."* (E-06.1). Her pet peeve is generic automation. Replacing her is
the losing move, and all five personas said so.

What she actually asked for is **leverage**. The honest framing is **additive**, not substitutive:

> Today 1,847 of 6,219 "what should I buy?" questions get a personal answer (E-05.3/E-05.4).
> **The other 4,372 get silence.** We don't replace the 1,847 — we give the 4,372 an answer
> that is hers.

The path to real autonomy, in her own words, is the **morning approval queue**: overnight it drafts
answers for everything inside her standard, holds everything outside it, and at 9am she swipes
thirty cards — each edit moving the line. That's a post-hackathon build, but it is the right
north star and it's worth one sentence in the pitch.

---

## 7. The biggest unresolved risk

> **Nobody has ever observed Maya declining at £X.** Every number in the system is internally
> consistent and externally unvalidated — and the one person who can falsify it walks into the room
> at **17:00**, three hours before judging.

The mitigation is unchanged and it is also the best beat in the demo: **the line is a draggable
handle, labelled honestly, shown as a band, and we end by handing her the control.**
After §2b, that mitigation is no longer optional — it is the product's honesty.
