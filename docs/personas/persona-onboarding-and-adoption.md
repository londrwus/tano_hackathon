# ADOPTION / ONBOARDING ADJUDICATION — THE FENCE

**Verdict up front:** the mechanism is real and the demo will land. The *product* has a cold-start problem the hackathon is hiding from you, and a weekly-use problem the hackathon cannot show you at all. Two specific things are missing that I would build before anything else: **a draft-shelf importer** and **a provenance badge**. Everything below is ranked and costed.

---

## 1. COLD START — where does "the standard" come from when there is no case file?

In the hackathon, E-04 hands you ten rows with price, a numeric rating *and* a verbatim note. That is a gift you will never receive again. No real creator has that artefact. Enumerated sources, ranked by cost **to the creator** (cheapest first):

| # | Source | Creator cost | What it gives | What it fatally lacks |
|---|---|---|---|---|
| 1 | **Affiliate storefront export** (ShopMy / LTK / Amazon Associates) | ~0 min — she already has it | product identity, sticker price, implied endorsement, conversion data | **every row is a "yes."** Zero refusals |
| 2 | **Her own captions + video transcripts** | ~0 min (paste a handle/URL) | judgement *in her voice*, price-conditioned | needs extraction; platform API access is a real blocker (see below) |
| 3 | **Comment replies** (public, 38,421 beauty comments — E-05.1) | ~0 min | her judgement conditioned on a real person's constraint | noisy, mostly logistics |
| 4 | **DM replies** — 1,847 she answered personally (E-05.4) | ~0 min to produce, high to export | highest-fidelity corpus that exists | privacy/consent, platform export |
| 5 | **Voice** — verified, 12s → 1.4s | 15–60 sec per session | refusals, caveats, vocabulary | she has to produce it; blank-mic paralysis |
| 6 | **Hand-annotating a product list** | 20–40 min | everything | **dead on arrival.** Never make this step 1 |

**The trap you are walking into: source #1 is the obvious one and it is poison.** An affiliate export contains only things she promoted. Train The Fence on it and you build a yes-machine — precisely the "walking billboard" Caplan says destroys trust, and precisely the opposite of what makes her valuable (sheet 03: *"willing to say what is not worth buying"*). Your entire measured signal comes from the two products that fall *below* sticker — Glass Drop (E-04.6) and Oil Balm (E-04.8). Affiliate data cannot contain those.

**The good source is #2, and the evidence says so explicitly.** Her broadcast log is already price-conditioned judgement content:
- E-03.1 *"3 things I would repurchase with £50"* — that is a price ladder she already published
- E-03.4 *"Luxury vs drugstore: where should your money go?"* — that is the Maya Line as a video
- E-03.6 *"The product I would NOT rebuy"* — 3.1K saves — **this is where the refusals live**

Twenty captions/transcripts → Jev extracts `(product, verdict, price_caveat, quoted_sentence)` tuples → draft shelf. That is the onboarding. She types nothing.

**Engineering risk you must price honestly:** TikTok caption access is not casually available and IG Graph API needs a Business account plus app review. Do not promise "connect your account" if you cannot ship it. Shippable fallback, in order: (a) her public affiliate storefront URL for the *what*, (b) three pasted captions or one 60-second voice note for the *judgement*. Get the products for free, buy the judgement with one minute of her time.

### How many products before it is trustworthy?

**You already have the instrument and have not noticed.** Your held-out test — delete the Glass Drop note, still land £41.7 vs £40.0 — is leave-one-out cross-validation with n=9 context. Generalise it: run LOO at n=3, 5, 7, 9 tonight and find where the error explodes. That gives you a real, defensible number for "how many products do I need," and it gives you the missing onboarding instrument:

> **MISSING FEATURE #1 — a readiness meter.** Right now nothing tells the creator when the model is good enough to publish. She has no way to know, so she will either publish too early (trust bomb) or never publish (churn). A LOO-driven "±£6 average error across your shelf — ready" gauge is the single cheapest confidence artefact you can build, and it doubles as a demo beat: *"you gave me seven products; watch me predict the eighth before you tell me."*

My prior, to be replaced by your LOO curve: **7–10 products, of which at least 2 must be negative or caveated.** The count of refusals matters more than the count of products.

---

## 2. IS VOICE THE ONBOARDING? Yes — but not as a blank microphone.

You verified the right capability and are about to use it the wrong way. "Tell me about your taste" into an open mic is the blank-page problem with extra social anxiety. The correct shape is **the machine speaks first and she reacts** — reacting is roughly 10× cheaper than authoring, and it is how you convert her into a labeller without her noticing.

### First-run flow, with a clock

**Screen 0 — 0:00 to 0:20. No signup.** One field: paste your storefront link or handle. That is it. No account, no email, no skin-type quiz. Account creation happens *after* the wow, not before it.

**Screen 1 — 0:20 to 1:20. "Here is what I think I heard."** A draft shelf appears: products it extracted, each with a guessed price line, **and next to each one the sentence of hers it came from, quoted.** She is correcting, not authoring. The quote is load-bearing: it is the anti-generic guardrail and the reason she believes the thing.

**THE WOW MUST LAND HERE, BY 1:30 — and it must be a verdict on a product she never entered.** Take one real product from the catalogue she has no relationship with, show its verdict in her voice with its price curve. If your first-value moment is after she has finished configuring, you have already lost most creators.

**Screen 2 — 1:30 to 3:00. The disagreement test.** Eight real catalogue products, already judged, one tap each: *right / wrong / not my lane*. Every tap is a labelled datapoint; the readiness meter moves visibly as she taps. This is where the personality actually forms.

**Screen 3 — 3:00 to 3:20. One question, not an open mic:**
> *"Name something you genuinely like that you would not tell people to buy at that price."*

That is the E-04.6 shape stated as a prompt. It is the single highest-information sentence a beauty creator can produce, it is the one signal no import can ever recover, and your voice pipeline already proved it catches exactly this (it returned `endorse_with_caveat` on the Glass Drop unprompted).

**Screen 4 — 3:20. Her wall lights up with her name on it, and a link.**

**Time-to-first-value: ~90 seconds. Time-to-publishable: ~4 minutes.** If the importer does not exist, TTFV is 20–40 minutes of typing and the product is dead — that gap is the whole difference between a tool and a demo.

---

## 3. THE GENERIC CLIFF — and it is closer than you think

Your own measured output is the warning. **CeraVe 2.85, Cetaphil 2.75, St. Ives "Renewing" 0.98, tightening cream 0.70.** That is an excellent result and it is also, almost exactly, the r/SkincareAddiction consensus ranking. A judge — especially Sagar Shah, who makes content himself — can look at that and think *"this is a dermatologist, not Maya."* Ranking is table stakes. The differentiator is the **sentence**, not the order.

What only Maya does, all citable:
- refuses on price while rating highly (E-04.6)
- *rewards* unremarkable — *"Boring in the best way"* (E-04.7)
- fragrance-avoidance for sensitive skin (E-02.2)
- answers a shade question with a question — *"what foundation do you wear now?"* (E-02.2)
- diagnoses by complaint — *"what do you hate about it?"* (E-02.1)
- calls it *"the good one"* and her audience copied her (E-02.5)

> **BUILD THIS, IT IS ~30 MINUTES — the A/B diff.** Run the same 359-product wall twice: once with Maya's standard, once with a generic "good-taste dermatologist" persona. Diff the top 20. If overlap is >70%, Maya is decoration and you need to fix the questions before you pitch. If overlap is low, you have just built the best answer in the room to *"how do I know this isn't ChatGPT?"* — and a demo beat nobody else will have.

**Minimum viable Maya:** ~7–10 products, **≥2 of them refusals or caveats**, 3 routing rules from E-02.2, and 1 vocabulary quirk. Below two refusals it reads as a machine that sells, which is the worst possible reading.

---

## 4. MAINTENANCE — where most of these tools actually die

Budget: **under 5 minutes a week, mostly zero-touch.** Four drift vectors:

**(a) Price — and this is a missed feature, not just a risk.** Your product is a function of price. A stale sticker is a publicly wrong verdict. Prices must be *fetched*, never remembered. Flip it into the feature:

> **MISSING FEATURE #2 — the price-drop trigger.** Maya's line on the Glass Drop is £40 and its sticker is £62. When it hits £39, her endorsement turns *on*, automatically, with a true sentence: *"She said not at £62. It's £39 today. That's now a yes."* This is an autonomous commercial event generated by an opinion she recorded once and never revisits. Your architecture already supports it for free — `05-backend-architecture.md` commits to zero-inference re-ranking on cached judgments, so a price change is arithmetic, not an API call. This is the highest commercial-potential feature in the build and it is currently not in the build.

**(b) Discontinuation / reformulation.** Dead links and wrong chemistry. Needs a staleness timer per item and an automatic demotion to "unverified" past N days.

**(c) Taste drift.** She is already generating the correction signal — every post she makes is a maintenance event. Default to zero-touch ingestion plus one 20-second weekly confirm: *"You posted 3 videos. I heard 4 new judgements. Tap to confirm."*

**(d) The maintenance channel you are ignoring, which is also the retention engine:**

> **MISSING FEATURE #3 — the "what I couldn't answer" digest.** Every low-confidence or `no_signal` query is a ranked list of what she should rule on next. Weekly: *"312 people asked about products you have never ruled on. Top 3: X, Y, Z. Fifteen seconds of voice covers all three."* This converts maintenance from a chore into **content ideas**, which is the one thing a solo creator always wants — and E-02.3 is her literally asking for it: *"Need to turn all this into something people can use without me answering 200 questions a day."*

---

## 5. AUTONOMY — an honest accounting

**Can be autonomous, today:**
- matching unseen products to her standard
- the price-conditioned verdict
- re-ranking on price change
- and the number that matters: **6,219 people asked "what should I buy?" (E-05.3); she personally answered 1,847 (E-05.4).** ~4,372 got nothing.

**Reframe your claim.** The honest autonomy story is not *"she stops replying."* It is: **the 4,372 who got silence now get an answer, and the 61% of repeat buyers who never DM at all (E-09.2) get one without ever having to ask.** That is additive, not substitutive — which is exactly what E-06.1 asks for (*"I genuinely do not want to stop talking to my audience"*) and it completely dodges the "handed to a machine" failure. Claiming "fully autonomous" against a woman who said the conversation is the best part is the fastest way to lose the room at 17:00.

**Cannot / must not be autonomous:**
- **The first endorsement of a product she has never touched.** *"She'd champion CeraVe (2.85)"* is a claim about a product with no evidence she has ever used it. Rendered in her voice, that is a fabricated endorsement — a trust bomb and, in the UK, an ASA problem. Two visually distinct states, non-negotiable: **SHE USES THIS** vs **THIS FITS HER STANDARD**.
- **Relationship and diagnosis.** E-01.8 *"I have a first date Friday HELP"* and E-01.6 *"I don't even know what my skin type is lol"* are not judgement queries. Routing them to her is a *feature*.
- **Anything where a brand deal is in play.** Her business is affiliate + brand deals + UGC (sheet 03). An automated "Maya recommends" pointing at a paid link on a product she has not used is the walking billboard, verbatim. Flag paid/affiliate items visually and mark their line as derived.
- **Medical-adjacent.** Pregnancy, accutane, actives interactions need a hard escalation layer regardless of whether she wrote the rule. (You are right that the retinol line sits on an unrelated to-do list, E-02.4 — do not cite it as policy, but do build the layer.)

**The division of labour you are missing:** The Fence removes her inbox without giving her a *better* inbox. She said she likes talking to people. Give her three names a day — picked by the silent-high-intent signal from the 16:00 drop (E-09.3, top-decile savers convert 2.4×; E-10.5 Tara: 0 DMs, 11 saves, £122 order). That is a new capability, comes straight from the sealed evidence, and makes her hour *more valuable* instead of merely shorter.

---

## 6. TRUST DECAY — design the failure before it happens

It will get one wrong in public. Design for the screenshot.

1. **Abstention must be a designed, first-class state — not a low score.** Your spread is 0.70–2.85 with no "no opinion" zone. Define one. And note it is *on brand*: her reputation (sheet 03) is built on being willing to say something is not worth it, so *"She hasn't ruled on this one"* reads as characteristic, not broken.
2. **Provenance badge on every single verdict** — `SHE SAID "…"` / `DERIVED (calibrated against her Night Serum)` / `NO SIGNAL`. This is the day-one guardrail. When it is wrong, the receipt turns *"Maya's AI lied to me"* into *"it reasoned from her shelf, got it wrong, she fixed it."* Different story entirely.
3. **Correction latency is the real trust metric.** She sees a bad verdict at 9pm on her phone. How long to fix? Target: **under 30 seconds, from her phone, no laptop.** If fixing it requires re-running a sweep, it is too slow. Your zero-inference architecture makes this achievable — the draggable Maya Line is the right primitive, it just needs to exist on a phone.
4. **Label it.** Unambiguously hers-and-automated, everywhere. Caplan's thesis cuts both ways: one unlabelled screenshot costs more than the feature earns.

---

## 7. TWO GAPS THAT ARE NOT ABOUT MAYA'S ONBOARDING

**(a) The audience has a cold start too, and it is currently empty.** Every consumer sees the same wall. But E-02.2 routes on skin type, and **two of six personas lead with a budget**: Emily — *"I trust you, but I am not spending £100 on serum"*; @gracelee (E-01.2) — *"dry skin + redness and £60."* The entire product is price-conditioned, and you never ask the one number that makes the price conditioning personal. **Add a budget field and one skin-type tap to the consumer gesture** — not a six-question quiz (Hannah: *"just tell me"*; Grace: *"I have 5 mins"*), two controls. Zero-inference re-rank makes it free. This is the difference between a wall and a recommendation.

**(b) Distribution.** 41% of high-value buyers first met Maya through **a private share from a friend** (E-09.4), and the shares column in E-10 is where the money is (Megan 6, Zoe 5, Tara 2 — all buyers). So the verdict card must be a **shareable image with her handle on it**, sized for a DM thread. If the only surface is a website she must drive traffic to, you have built for the channel the evidence says is *not* how her buyers arrive.

---

## 8. THE THREE HIGHEST-LEVERAGE ONBOARDING BUILDS, RANKED

1. **Caption/storefront → draft shelf importer.** One paste, zero typing. Cuts TTFV from ~30 min to ~90 s. Her E-03 posts are *already* price-judgement content. This is the onboarding; everything else is polish.
2. **React-don't-author calibration + the readiness meter.** Eight pre-judged products, one tap each, LOO error visible and falling. Turns authoring into tapping and gives her a reason to believe the number.
3. **The 15-second refusal prompt.** One specific question, not a blank mic: *"Name something you like that you wouldn't tell people to buy at that price."* Produces the one signal no import can recover, using the pipeline you already verified.

*(Not onboarding, but build it anyway: the price-drop trigger. It is the strongest commercial feature available and your architecture already pays for it.)*

---

## 9. THE SINGLE MOST LIKELY REASON SHE NEVER OPENS IT AGAIN

**It has no place in her week.**

Once configured, The Fence either runs without her — in which case there is nothing to open — or it needs her, which is worse. The realistic arc: she sets it up, gets the wow, publishes the link, and it becomes invisible infrastructure. Invisible infrastructure gets no attention, drifts, produces a wrong verdict in month two, and gets quietly unpublished. Not with a bang.

The fix is not engagement bait. It is a **weekly artefact she actually wants**: the digest of what her audience asked that she has no answer for (built on E-05.3's 6,219 unanswered "what should I buy" questions), which doubles as her content calendar. That is a reason to open it that serves her, not you.

**Runner-up, and more immediate:** *opening it requires a laptop.* She is one person with a phone (sheet 03: TEAM — Maya). If corrections live in a desktop Canvas2D wall, she will never correct anything, and an uncorrected model drifts into being wrong in public. **The Wall is the judges' surface. Maya's surface is a phone with three controls: confirm, override, record 15 seconds.** Make sure the pitch does not optimise the thing nobody uses twice.