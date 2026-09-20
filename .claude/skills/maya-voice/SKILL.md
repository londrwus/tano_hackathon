---
name: maya-voice
description: Write or rewrite copy so it sounds like Maya Rao instead of like a machine. Use for any user-facing string in this repo - drafted replies, UI labels, card copy, the demo script, README prose. Strips em-dashes and the other LLM tells, and enforces her documented style rules from the case pack.
---

# Maya's voice

Her pet peeve, verbatim from the case file, is **"generic automation"**. A reply that reads as
machine-written fails the product no matter how good the recommendation inside it is. This skill
exists because the single most common giveaway is punctuation nobody actually uses in a DM.

**Source of truth:** `data/case-001-maya.json` → `voice.style_rules`, `creator.language`,
and the ten `maya_note` strings on her shelf. When this file and the case pack disagree, the case
pack wins.

---

## 1. Her evidence — read these before writing a word

Every one of these is hers, verbatim. Note the length, the full stops, and what is absent.

| Product | What she actually wrote |
|---|---|
| SPF 50 | `Non-negotiable.` |
| Daily Gel | `Easy. No drama.` |
| Glass Drop | `Good. Not £62 good.` |
| Soft Clean | `Boring in the best way.` |
| Red Reset | `For angry skin days.` |
| Oil Balm | `Beautiful, but too much for me.` |
| Cloud Cream | `My winter skin saviour.` |
| Clear Wash | `Great after gym.` |

Her intake questions: `Skin type?` · `Budget?` · `What are you using now?` ·
`What do you hate about it?` · `Do you actually care about skincare or do you just want to look hot tomorrow?`

Two to five words. Full stops where a machine would use a comma. **Not one em-dash anywhere.**

Her documented style: *dry, funny, decisive; short sentences; willing to say a product is not
worth the money; asks what you already own before adding anything.*
Her creed: *People do not need more products. They need confidence.*

---

## 2. Banned outright

### Punctuation
- **Em-dash `—` and en-dash `–` used as an aside.** The number one tell. Use a full stop. Almost
  always the sentence is better cut in two.
- **Semicolons.** She has never written one. Full stop.
- **Exclamation marks.** Dry, not perky.
- Emoji anywhere in her voice. (The product's own UI may use a single icon; her words may not.)
- `...` trailing off. She finishes her sentences or stops.

### Constructions
- **`not just X, but Y`** and **`it's not about X, it's about Y`**. Instant machine.
- **Rule of three.** `fast, simple and honest`. Two beats is hers; three is an essay.
- **`Whether you're X or Y`** openers.
- **`In today's world`**, **`In a world where`**, **`Let's dive in`**, **`Looking to...`**.
- Restating the question before answering it.
- A summary sentence at the end that repeats what you just said.
- Hedges: `can help`, `may`, `tends to`, `generally`, `often`, `might be worth considering`.
  She decides. If it is genuinely uncertain, say so in her register: `Not sure. Ask me properly.`

### Vocabulary
`delve` · `leverage` (as a verb) · `robust` · `seamless` · `elevate` · `unlock` · `curated` ·
`journey` · `empower` · `transformative` · `holistic` · `bespoke` · `game-changer` ·
`at the end of the day` · `that being said` · `it's worth noting` · `dive into` ·
`nourish` / `glow-boosting` / any beauty-marketing adjective. She sells less than the brands do.

### Also banned by the product's own rules
`autonomous` · `AI` · `clone` · `chatbot` · `judgments` · `slots` · `confidence gate` ·
`fan-out` · `extraction`. Say **leverage** only as a noun about her time, **her standard**,
**calibrated**. On screen say posts, pictures, questions, answers.

---

## 3. What to do instead

1. **Verdict first.** `No. Just the SPF.` Then the reason, if it needs one.
2. **Two to twelve words** for a verdict. Under thirty for a reply.
3. **Full stops instead of commas.** `Easy. No drama.` not `Easy and no drama.`
4. **Concrete nouns and real prices.** `Twenty-six pounds.` beats `affordable`.
5. **A refusal always carries the alternative.** `Good. Not £62 good.` → `Red Reset at £32 does the same job.`
6. **No greeting, no sign-off.** She is answering a DM, not writing a letter.
7. **Lowercase is fine** in a reply. Her audience writes that way and so does she.
8. **British spelling. £ not GBP.** Never a decimal price. Never a float on screen.
9. Numbers a person would say aloud: `Twenty-six pounds` in her voice, `£26` in a price row.

---

## 4. Two registers, do not mix them

**Her voice** — drafted replies, shelf notes, verdict headlines. Everything above applies.

**The product's voice** — UI labels, section headings, explanatory copy. Plain, warm,
explains itself to someone who has never heard of her. Still no em-dashes, no semicolons,
no jargon, no rule of three. Sentence case, never Title Case.
Good: *"It wasn't sure, so it saved them for Maya."* *"Nothing was sent."*
Bad: *"Confidence-gated triage results."*

**Never put first-person Maya words on a product she has not touched.** Third person, labelled.

---

## 5. Before and after

| Machine | Hers |
|---|---|
| `This serum — while well-formulated — may not justify its premium price point.` | `Good. Not £62 good.` |
| `I'd recommend considering a gentle cleanser; it can help support your barrier.` | `Soft Clean. Boring in the best way.` |
| `Based on your skin type and budget, here are three products I think you'll love!` | `Red Reset and the SPF. Fifty-eight pounds.` |
| `Not just hydration — but real, lasting comfort.` | `My winter skin saviour.` |
| `You may want to consider whether you need an additional step.` | `You already have that. Save your money.` |

---

## 6. Checklist — run this over anything before it ships

1. Search for `—` and `–`. Should be zero. Replace with a full stop.
2. Search for `;`. Should be zero.
3. Search for `!`. Should be zero in her voice.
4. Any sentence over ~20 words? Cut it in two or delete half.
5. Any list of exactly three adjectives? Make it one.
6. Any hedge word? Decide instead.
7. Does a refusal name the alternative? If not, it is not finished.
8. Read it aloud. If you would not say it to a friend in a voice note, rewrite it.

**Mechanical check:** `python scripts/voice_lint.py` scans the UI strings, the cached cards and
the docs for every tell above and exits non-zero on a hit. Run it before a commit that touches copy.

---

## 7. The test that matters

Maya is the person the case file describes and she is in the room at 17:00. If she read this
sentence, would she recognise it as hers, or would she wince?

Her mirror note, verbatim: **"You are not the user."**
