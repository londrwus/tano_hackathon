JUDGE — Tano x Corgi Creator Heist. Station 13 of 13. 19:50.

═══════════════════════════════════════════════════
SCORES
═══════════════════════════════════════════════════

**Value to a real audience member — 5/10**
The named user is Priya (E-01 associates sheet) or Emily/22 with £60 (E-01, associates sheet). But look at what the product actually requires of her: she must already know Maya, already have a product photo, and — this is the killer — **already know the asking price**. `scripts/vision_to_jev.py` has the signature `def judge(attrs, price)` and puts `asking_price_gbp` into state as a *caller-supplied argument*. `data/real-catalogue-openbeautyfacts.json` has exactly six fields (`brands, ecoscore_tags, categories_tags_en, code, product_name, image_url`) — **there is no price in your catalogue anywhere**. So a product whose entire thesis is "her endorsement is a function of price" cannot obtain the price for any product that isn't one of her ten. Emily has to type it in. That is the audience member doing the data entry for your headline mechanic. 5, and I am being generous because the refusal ("don't spend £62") is genuinely valuable when it fires.

**Fidelity to the creator's voice — 8/10**
Strongest axis. The fact that the only two products falling below sticker are Oil Balm ("Beautiful, but too much for me", E-04.8) and Glass Drop ("Good. Not £62 good.", E-04.6) is a real result and it is the right two. SPF 50 topping the headroom table because of "Non-negotiable" (E-04.5) is the correct emergent behaviour. CeraVe/Cetaphil scoring top on the wall against her own "Boring in the best way" (E-04.7) is a nice, unforced echo. Not a 9 or 10 because "voice" in this file is *dry, funny, decisive* (subject sheet, SHEET 03/17) and your product emits no language at all — you have modelled her **standard**, not her **voice**. Those are different, and the criterion says voice. Own that trade rather than blurring it.

**Use of the evidence — 9/10**
Best in the room today, comfortably. Every number traces to E-04. You read E-08.1 and didn't build the DM bot. You read E-08.3 and made the £62 contradiction load-bearing instead of an anecdote. You explicitly refused to weaponise "DO NOT RECOMMEND RETINOL" because it sits on E-02.4, an unrelated to-do list — I checked, it does, between "CALL SARAH" and "BUY MORE BROWN LIP LINER", and you are the only team who would have noticed. Docked one point: you use E-01, E-04, E-08 heavily and **E-09/E-10 barely at all** (see criterion #1 below). The 16:00 drop was a test and you half-sat it.

**Does it work — 7/10**
The Layer-1 sweep is real and I believe the 0.97s/561-judgment number. But your own counter says `359 PRODUCTS · 718 JUDGMENTS` = 2 questions × 359, while `scripts/catalogue_wall.py` filters twice before Jev ever sees anything: a hardcoded `BAD` keyword list (`"body","hand","hair","shampoo","deodorant","soap bar","lip balm","baby","shaving"`) and then `seen=[s for s in seen if s.get("is_face_skincare")]` — a boolean from gpt-4o-mini. Your measured run judged 60 *survivors of that filter*, not 60 of 359. So the on-stage counter and the verified pipeline are not the same pipeline. Pick one and make it true before 20:00.

**Would I use it (as a creator) — 6/10**
The drag handle is the answer to this question and it is a good one. But Layer 1 covers ten products. Maya's real shelf is every product she has mentioned in three years. Nothing in the build gets from 10 → 400, and nothing keeps it current when she changes her mind in November.

**Would I trust it with my audience — 7/10**
High, because it refuses to sell and because you never put words in her mouth — you've read the disclosure-penalty literature and built the correct answer to it. Capped at 7 by one thing: `UNPROVEN` and `NOT HER LANE` are **stamps with a real brand's name under them**, rendered at scale, from a gpt-4o-mini reading of a 400px packshot. If "M. Asam Vinolift" is stamped UNPROVEN on a public URL under Maya's name, that is her legal exposure, not yours. Nobody in the room will raise this tonight. A brand lawyer will raise it on Monday.

**Would my audience use it — 4/10**
It is one-shot and synchronous. E-09.5 says the median purchase lag is 4.6 days. E-10 shows Rina (0 DMs, 8 saves, 3 shares, bought at 4d), Tara (0 DMs, 11 saves, £122), Zoe (0 DMs, 9 saves, £86). The Fence has no save, no return, no notification, no memory. It serves the moment of asking. E-09.2 says 61% of repeat buyers never ask.

**Would I share it — 3/10**
Lowest score on the sheet and the one I'd fix first. E-09.4: 41% of high-value buyers first met Maya through **a friend's share**. There is no shareable object here. A verdict card is screenshot-able; that is not the same as forwardable, and it isn't designed to be received by someone who has never heard of Maya. You identified this white space in your own market brief (§6, "the receiver of the share… it is the only one that compounds") and then built the thing that doesn't do it.

**Best commercial potential — 8/10**
"This is Charlie, pointed the other way" will land with Sagar, and the pre-campaign brand screen ("is her endorsement of your £62 product credible to her own audience, priced") is a genuine line extension on a company doing ~$35–45/creator. It is the most sellable thing I have seen today. Not a 9: the sale is to the brand, and the primary judging criterion is the audience member, so the commercial story and the scoring sheet pull against each other. Don't let the commercial pitch eat the demo.

**Most elegant — 8/10**
One primitive, one question, fifty rungs, and the answer is a curve. That is genuinely elegant and it is the correct use of `noul`. Minus two: the elegance is contaminated by the `price_context_note` — a hand-written paragraph telling the model "She routinely endorses GBP 32-42 items." That is a thumb on the scale wearing a state field's clothing. See below.

**Most inventive — 9/10**
Pricing a person's integrity as an elasticity curve is the only idea today I had not seen a version of. ~187 builds on madewithjev in five days and none of them is this shape. This is your prize.

═══════════════════════════════════════════════════
DOES IT WAKE ME UP, AND WHEN
═══════════════════════════════════════════════════

Yes, but **not where you think, and not at second 0**.

The wall does not wake me up. I have seen four grids today and a grid that dims is still a grid — at 19:50 a field of dimming squares reads as a screensaver, and my eye has nowhere to land because 340 cells are going dark simultaneously and none of them is a story.

I wake up at the moment a single row reads:

```
GLASS DROP      £62 sticker      £40 line      −£22
                "Good. Not £62 good."
```

That is roughly **second 38–44** of your 90, if you get there fast. The number and her sentence in the same frame is the whole product, and it is the only thing tonight that made me sit up. The second-best moment is the drag handle at the end.

Which tells you your running order is wrong. **You are spending your first 30 seconds on your weakest asset.** Lead with the one row. Earn the wall.

═══════════════════════════════════════════════════
THE QUESTION YOU WOULD STRUGGLE TO ANSWER
═══════════════════════════════════════════════════

> **"Run the held-out test on SPF 50 instead of Glass Drop. Right now. What does it say?"**

I read `scripts/price_curve_sweep.py`. Your held-out run deletes `maya_note` — and leaves everything else standing:

- `maya_rating: 8.1` stays in the payload. That is Maya's own numeric judgement, still present.
- The other nine shelf rows stay in `her_shelf_for_price_context`, **with their notes and prices**.
- And `price_context_note` is still there, saying verbatim: *"This is the full range of what Maya actually recommends: GBP 20 to GBP 62. She routinely endorses GBP 32-42 items."*

Held-out Glass Drop lands at **£41.7**. The top of the band your own prompt supplied is **£42**.

So the sceptic's hypothesis is: *a note-free product with a mid rating lands at the top of the stated anchor band, because that is what the anchor band says.* Under that hypothesis the test "passes" for Glass Drop by coincidence — its true line genuinely is below sticker. It would "pass" identically, and be **wrong**, for SPF 50, whose with-note line is £60.4. If you hold out SPF 50's note and it also collapses to ~£42, your calibration proof is a prior, not a person.

You have n=1, and you selected the one where the prior and the truth agree.

**Fix (20 minutes, and it is worth more than any pixel you will change tonight):** run the leave-one-note-out sweep across all ten. Report mean absolute error in £ and, crucially, **rank correlation between held-out lines and with-note lines**. If SPF still ranks first and Glass Drop still ranks last without any note, you have a real result and it is a better one than you currently claim. If it doesn't, cut the word "proves" and say "her sentence sharpens a signal that is already there" — which is true, defensible, and still good. Also delete `"She routinely endorses GBP 32-42 items"` from the state and re-run; if the result survives without the anchor, say so on stage and you have pre-empted the only smart attack available to me.

═══════════════════════════════════════════════════
WHERE THE DEMO OVERCLAIMS — THE WEAKEST FACTUAL LINK
═══════════════════════════════════════════════════

**1. The wall has no price in it. (Worst one.)**
`scripts/catalogue_wall.py` asks Jev exactly two questions per product: `|fit` (a 5-level score, "how enthusiastically would she tell her audience about this") and `|why` (a 5-way choice of reservation). **Neither is a price question.** No ladder, no crossing, no line. So your hero visual — the thing the product is named after — contains zero fence. It is a taste classifier. You are calling a taste classifier "The Fence" and the mechanism you spent the day proving applies to 10 of 359 products. If I click a survivor expecting "its price curve," you have to synthesise a price you do not have.

**2. "~90% dim" is not Maya's standard rejecting them.**
A regex and a gpt-4o-mini boolean kill most of them before Jev is consulted. Your own catalogue's category tags include `candles`, `home-fragrances`, `skin-insect-repellent`, `Incorrect product type` (19 items) and `non-food-products` (19). A soy wax candle stamped `NOT HER LANE` is a `categories_tags_en` lookup wearing a taste judgement's costume. Break the counter into two honest numbers: `N filtered (not face skincare) · M judged by Maya's standard · K survive`. The honest version is *more* impressive, because K/M is a discrimination rate and K/359 is a data-cleaning rate.

**3. "Nothing fabricated."**
True of the photos and names. Not true of the prices, which do not exist in the data and which your consumer gesture requires. Say "real products, real photography, prices supplied by the user" before someone else says it for you.

**4. "$0.009" / "$0.03".**
Jev-only. The vision pass is ~10× the Jev cost by your own numbers (~$0.029 vs ~$0.0011 for 60). Jev's own engineering guidance is *measure cost per finished task, not per call* — quoting the Jev line only, to a room containing TypeSafe people, is the one thing that will read as a hackathon hack to the exact person you want to impress. Put the honest end-to-end number up. It is still under thirty cents. Thirty cents is still an astonishing number.

**5. Operational, not scoring, but fix it tonight:** live OpenAI and TypeSafe API keys are hardcoded at the top of `scripts/vision_to_jev.py` in a git repo you are about to push. Rotate them.

═══════════════════════════════════════════════════
IS THE WALL IMPRESSIVE, OR A LOT OF SQUARES
═══════════════════════════════════════════════════

Honestly: **it is a lot of squares, and it is squares of the wrong products.**

I sampled your catalogue. The first three entries are a Turkish acne kit ("Acnemix", BİLİM İLAÇ), a Laline body oil, and a French soy candle. 91 sunscreens, 49 lipsticks. This is an open crowdsourced database, and it looks like one: mixed languages, inconsistent packshots, 400px thumbnails on inconsistent backgrounds. Projected at Shoreditch at 19:50 on a near-black screen, that grid will read as *noise*, not as *inventory*. Nobody in the room recognises BİLİM İLAÇ. Your entire "this is not a mockup" argument depends on the audience recognising brands, and most of these are unrecognisable to a London room.

What would actually be impressive is **twelve squares, not 359**. Twelve products a beauty person in that room recognises on sight — CeraVe, Cetaphil, La Roche-Posay, The Ordinary, Drunk Elephant, Charlotte Tilbury, an Augustinus Bader at £205 — with the scan resolving in 1.2 seconds and Bader going dark. One recognisable expensive thing being refused is worth three hundred anonymous squares. The "359" belongs as a line of text under the twelve, not as the visual.

You are trading legibility for a number, at an hour when nobody has any legibility left.

═══════════════════════════════════════════════════
ADJUDICATION: AUDIENCE TOOL, OR CREATOR/BRAND TOOL IN A CONSUMER COSTUME?
═══════════════════════════════════════════════════

**Ruling: it is a brand-side screening tool with a consumer gesture bolted on, and I can prove it from your own artefacts.**

The evidence:
1. Layer 1 output is a **rate card** — its natural reader is whoever is deciding whether to pay Maya. That is Tano's customer, not Priya.
2. Layer 2's state literally frames it brand-side. `catalogue_wall.py`, `context` field, verbatim: *"A brand has sent Maya these products hoping she will feature them."* That is a gifting-triage queue. Priya is not a brand sending Maya PR boxes.
3. Layer 2 asks `on_brand`: *"If Maya endorsed this, what happens to her credibility?"* That is a question about Maya's business. Priya does not care what happens to Maya's credibility; she cares whether her face will react.
4. Layer 3 is the only audience-facing surface, and it requires the audience member to supply the price — which is the one fact she came to you to be told.

**But** — and this is why you still rank near the top of my sheet — Layer 3 is *genuinely* audience-facing in intent, and the refusal verdict is real consumer value. The costume is not fraudulent; it's just unfinished. The problem is that the two layers you built beautifully serve the brand, and the layer that serves Priya is the one you have specified least.

And criterion #1 is not "value to a real audience member *eventually*". Maya is in the room. She will ask who this is for. Have one sentence ready.

═══════════════════════════════════════════════════
THE TEAM'S FOUR WORRIES — ADJUDICATED
═══════════════════════════════════════════════════

**1. Real problem, or merely demonstrable?**
Real *for Maya*, narrower than you think *for the inbox*. Score the twelve E-01 intercepts against what The Fence answers:

- Answers cleanly: **E-01.4** ("is the cloud cream actually worth £38 or am i being influenced") and **E-01.11** ("what would you do if it was your money"). That's 2.
- Partially: E-01.3 (keep ONE), E-01.12 (the one you'd buy if you were me), E-01.2 (dry + redness + £60 — you can rank but you cannot *build the routine* she asked for), E-01.10 (payday — you have no mechanism for the 4.6-day lag it describes).
- Cannot touch: **E-01.1** (shade — needs her current foundation per E-02.2), **E-01.5** (do I need the barrier cream *too* — product stacking/redundancy), **E-01.6** ("i dont even know what my skin type is"), **E-01.8** ("first date Friday"), **E-01.9** ("2 products bc i will not do 8 steps"), E-01.7.

**2 of 12 clean.** That is a real problem, precisely identified — it is also the *narrowest* of the twelve. You have built a specialist instrument for the value question, on a wall of evidence showing the value question is a sixth of the traffic. Say the number yourself on stage before I say it: "we answer the one question she can't answer at scale, and we answer it completely."

**2. Gap that makes it unusable in her actual week?**
Yes, one, and it is the price gap. Her week contains PR boxes and brand briefs with prices on them — that path works. Her week also contains an audience seeing products on TikTok with no price attached — that path does not. Second gap: there is **no write-back**. She drags the handle, the wall re-ranks, and then what? Nothing persists to her audience, her link-in-bio, her DMs. E-02.3 is her own stated ask — *"Need to turn all this into something people can use without me answering 200 questions a day"* — and "something people can use" is the part you have not shipped. She corrects a number on a screen and the 4,800 DMs still arrive.

**3. Onboarding — this is your strongest unplayed card, and you have buried it.**
Time-to-first-value is genuinely excellent and you are not saying so. Layer 1 needs ten rows she already has in her head. The voice path — 12 seconds of speech, transcribe, whole-shelf verdicts in 1.4s, correctly returning `endorse_with_caveat` on Glass Drop *unprompted* and `no_signal` on the seven she didn't mention — is the single most creator-native thing in this build and it is sitting in "verified but not placed." **That `no_signal` is the best trust artefact you have** and you're not showing it: a system that declines to guess about seven products she didn't mention is a system that will not put words in her mouth. That is criterion "would I trust this with my audience", answered in one word.

**Put the voice note in the demo. Replace ten seconds of wall with it.** "Maya's onboarding is ninety seconds of talking. Here it is." Nobody else in this room has an onboarding under five minutes; most have a form.

The onboarding that *is* heavy is the one you haven't costed: getting from her 10 products to the several hundred she has actually endorsed, with prices. Don't claim it's solved. Claim the 10 is enough to start and the line moves as she talks.

**4. Autonomous?**
No, and don't claim it. It makes zero DMs go away tonight, because it has no surface where her audience meets it. What it *does* make autonomous is a decision she currently makes one product at a time in her head — it is the first system that can apply her standard to something she has never seen, at 16 products/second. That is leverage (E-06.3: *"She is not asking for less relationship. She is asking for leverage."*), and leverage is the honest word. Use "leverage". If you say "autonomous" I will ask which DM stopped arriving, and you will not have an answer.

═══════════════════════════════════════════════════
WITH 2 HOURS LEFT — WHAT I'D CHANGE
═══════════════════════════════════════════════════

In priority order. Do 1–3 even if you do nothing else.

1. **(40 min) Fix the held-out claim.** Leave-one-note-out across all ten, report MAE and rank correlation, drop the `"£32-42"` anchor sentence from state and re-run. Put whatever you actually get on screen, including if it's worse. A number that survives an attack beats a number that dodged one — and this is the only place a TypeSafe judge can break you.
2. **(20 min) Re-cut the demo. New order:** (a) Glass Drop row, one frame, `−£22` + "Good. Not £62 good." — **seconds 0–12**. (b) "She never told us that. We deleted her note and it still said £41.7" — 12–25. (c) Twelve recognisable products, scan, Bader refused — 25–45. (d) "359 of them, 718 judgments, 3.9 seconds, twenty-eight cents end to end" as a *line of text* — 45–52. (e) Voice-note onboarding, ninety seconds of talking, `no_signal` on the seven — 52–70. (f) Hand Maya the handle: "Is £44 right? Move it." — 70–90.
3. **(15 min) Make the counter honest** — split filtered vs judged, quote end-to-end cost including vision.
4. **(25 min) Ship the share object.** One verdict card with a share button that produces something a person who has never heard of Maya can read cold: product, verdict, her line, the refusal, and *why she's worth trusting*. This costs you almost nothing and it is the difference between 3/10 and 7/10 on "would I share it" — and it is the only thing in your power tonight that touches E-09.4 (41% arrive via a private share). Your own market brief says this is the unoccupied ground. Occupy two inches of it.
5. **(10 min) One slide-free sentence for the brand/Tano angle**, delivered *after* the product, not during: "This is Charlie, pointed the other way." Then stop talking about brands.
6. Rotate the keys.

═══════════════════════════════════════════════════
WHAT MAKES THIS LOSE TO A SIMPLER PRODUCT
═══════════════════════════════════════════════════

Three ways, all live tonight:

**(a) Distribution beats fidelity.** A team ships something dumber inside Instagram DMs — send a photo to Maya's account, get back a one-line verdict. Yours is more intelligent and theirs is *where Priya already is*. When Maya is asked "would your audience use this", she will picture where it lives. Yours lives on a laptop at a URL. If you cannot ship a surface in two hours, **say the sentence anyway**: "this is one webhook from living in her DMs, and it never types as her." Free, honest, and it closes the gap.

**(b) The saver/nudge build.** Team 11 in your own map — "you saved this 7 days ago, Maya's line on it is £40, it's £32 today." One notification, aimed squarely at E-09.5 (4.6-day median lag) and E-10 (Rina 8 saves, Tara 11 saves, Zoe 9 saves, all 0 DMs, all bought). Far less inventive than you. Aimed at the actual buyer. If a judge is scoring criterion #1 strictly, that beats you.

**(c) Your own complexity.** Standing order, sheet 02: *"You do not get extra points for complexity."* Three layers, a vision pipeline, a voice pipeline, a 359-cell canvas — and the thing that actually wins is one row and one draggable handle. If the wall stutters, or the live sweep hangs on venue wifi for four seconds at second 30, a clean two-screen demo takes the £500 from you and every one of your good ideas dies unheard. **Rehearse the fallback keypress. Twice.**

═══════════════════════════════════════════════════
BOTTOM LINE
═══════════════════════════════════════════════════

After twelve demos: three DM bots, four quizzes, and this. It is the only build today with an idea in it — "a creator's taste is a standard, and a standard has a price" is a sentence I will still be thinking about on the train. As it stands I rank it **2nd overall**, 1st on Most Inventive, 2nd on Commercial.

It is 2nd and not 1st for one reason, and it is not a technical one: **you built the instrument and not the place where a person meets it.** Fix the held-out claim so nobody can take the idea away from you, put the voice note and the share card in, lead with the £62 row, and you win the £500.

Leave it as is and you win the headphones.

Files I read: `C:\Users\Lenovo\Documents\tano_hackathon\docs\evidence\case-001-operation-shade.txt`, `docs\02-the-pick.md`, `docs\research\market-and-prior-art.md`, `docs\research\tano-and-judges-intel.md`, `scripts\price_curve_sweep.py`, `scripts\catalogue_wall.py`, `scripts\vision_to_jev.py`, `data\real-catalogue-openbeautyfacts.json`.