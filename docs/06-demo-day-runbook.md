# Demo-day runbook

Product decisions live in `02-the-pick.md`. This is the *operational* plan — the things that lose
hackathons for reasons unrelated to the idea.

---

## Timeline with our checkpoints

| Clock | Event | What we must have done |
|---|---|---|
| 09:00 | Doors | Arrive. Wifi, power, seats near a socket |
| 09:00–10:30 | Pre-start | **Do not idle.** `pip install`, `npm create vite`, `.env`, run `scripts/eval_judgement.py` to confirm Jev is healthy on venue wifi |
| 10:30 | Heist starts | Case confirmed. If we are handed a different case than planned, swap the JSON — we have all three packs |
| **12:30** | **Checkpoint: engine** | `/api/simulate` returns a real matrix. If not, cut scope now |
| **14:30** | **Checkpoint: hero screen** | The hero visual renders real data on screen. Ugly is fine. **Feature freeze from here** |
| **16:00** | **Intelligence drop** | Open envelope. We already assumed the twist (see below) |
| 16:00–16:30 | Their 30-min window | We use it to *polish*, not to pivot |
| **17:00** | Creator walks in (Case 001) | Show her the product. Take one note. Do not redesign |
| **17:30** | **Checkpoint: rehearsal** | Demo run end to end, timed, twice. Record the backup video |
| 18:00 | Judging + Q&A | Product first. No deck |
| 19:00 | Top six pitch | |
| 19:45 | Demos | 90 seconds |
| 20:30 | Prizes | |

**The 14:30 feature freeze is the most important line in this document.** Every hackathon is lost
between 17:00 and 19:00 by a team adding one more thing.

---

## The 16:00 drop — pre-planned, not improvised

We know what is in the envelope (all three cases carry the same reversal — see
`01-constraints-and-stack-status.md` §3): **the valuable audience behaviour is invisible to the
obvious metrics.** 61–71% who acted never clicked or DM'd; savers convert 2.2–3.1×; 41–44% of
high-value action follows a private share.

**Our play:** build for the post-drop brief from hour one, and hold back one view that *activates*
at 16:00. While the room pivots, we add a panel we already built.

Do **not** announce at 16:05 that we predicted it. Just show a product that already answers it, and
let a judge notice. If asked directly, the honest answer — *"all the evidence pointed there: E-03
showed the 18K-view post outperforming the 74K one, and E-08.5 flagged the silent customer"* — is
much stronger than a boast.

---

## Bulletproofing the 90 seconds

The demo is 90 seconds, product-first, no deck. Things that reliably go wrong:

| Risk | Mitigation |
|---|---|
| **Venue wifi dies** | Warm cache committed to git; `?cached=1` flag. Demo runs offline and is still honest — those are real judgments we really computed |
| **Jev is slow/down at 19:45** | Same cache. Also: we measured p95 = 1.09s; a 429 backoff is already in the client |
| **Projector kills contrast** | Design for the projector, not the laptop. Bigger type, heavier weights. Test on an external display *before* 17:30 |
| **Projector is 1024×768 or 16:10** | Test the hero screen at 1024×768. No horizontal scroll, no clipped hero number |
| **Laptop sleeps / notifications** | Do Not Disturb on. Sleep disabled. Close Slack, mail, everything |
| **Live typing fails** | Nothing is typed live. Every input is one click on a pre-seeded chip |
| **The 90s overruns** | Rehearse twice with a timer. Cut until it fits at 80s |
| **Browser zoom/state weirdness** | Fresh window, one tab, bookmark the URL, reload before walking up |

**Record a 90-second screen capture at 17:30.** If anything fails live, we play it and keep talking.
Never spend demo seconds debugging.

---

## The 90-second structure

The case file gives us the structure; use it verbatim.

```
30s  THE TARGET   What were you stealing?
90s  THE HEIST    Show what you built.
60s  THE SCORE    What changed? Time, confidence, conversion, trust?
```

Rules for the script:
- **Name the person and the decision in the first sentence.** The brief says a product without a
  named person and decision is not a product. Start there: *"This is Priya. Sensitive skin.
  She is about to spend £62 on the wrong serum."*
- **Show, do not tell.** The brief is explicit: *"don't just tell what you've built — show how it
  makes their life easier."*
- **One number, said once.** Not a tour of metrics.
- **End on the final line from the case file:** *"Maya no longer needs to ____ because ____."*
  Closing on their own sentence is a gift to the room.
- **Do not ask "do you like our app?"** The case file explicitly forbids it. Ask about the
  behaviour we observed.

---

## Answers to the five questions the judges will actually ask

Rehearse these. They are worth more than another feature.

1. **"Would I trust this with my audience?"**
   → Show the honest NO. The product refuses to recommend the £62 serum she rates 8.1/10, because
   she said *"Good. Not £62 good."* A machine that turns down a sale is the trust proof.

2. **"Isn't this just an LLM wrapper?"**
   → No, and here is why measurably: 3,000 calibrated judgments in 1.18s with probabilities and
   confidence we can draw. Then drag the weight slider and re-rank all 3,000 instantly with zero
   further inference. A chat model cannot do that.

3. **"How do you know it sounds like me?"**
   → 100% recall against her own documented decision tree (E-02.2), zero violations. Every
   recommendation cites the exhibit it came from. SPF 50 tops every shopper because she wrote
   "Non-negotiable" — nobody coded that rule.

4. **"What's the business?"**
   → Answer with who pays and how much. See `02-the-pick.md`. Do not hand-wave.

5. **"What would you build next?"**
   → One sentence, concrete, and ideally something the 16:00 data implies. Not a roadmap.

---

## Team split (3 people)

| Role | Owns | Hard rule |
|---|---|---|
| **Engine** | `jev.py`, `questions.py`, `engine.py`, the eval gate | Owns accuracy. Nobody else edits `questions.py` |
| **Screen** | The hero visual, motion, the Pen design | Owns the projector test |
| **Story** | The 90-second script, evidence citations, judge Q&A prep, backup recording | **Starts writing the script at 12:00, not 18:00** |

The Story role is the one hackathon teams skip and the one that decides the prize. Assign it.

---

## Pre-flight checklist (run at 17:30)

```
[ ] eval_judgement.py -> 100% recall, 0 violations
[ ] Hero screen renders at 1024x768 with no scroll
[ ] Cached matrix committed; ?cached=1 verified with wifi OFF
[ ] 90s backup recording saved locally AND somewhere reachable
[ ] Do Not Disturb on; sleep disabled; one browser tab
[ ] Tested on the external display
[ ] Script rehearsed twice under 90s
[ ] Final line written down, memorised: "____ no longer needs to ____ because ____."
[ ] Public URL live (Modal) and opens on a phone
```
