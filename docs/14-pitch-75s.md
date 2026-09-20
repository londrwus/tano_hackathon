# 14 — THE 75-SECOND PITCH

Opens on `/how-it-works`, then walks the surfaces. 231 words. At 185 wpm that is 75 seconds
with two pauses — brisk, which suits a technical room. Every number is measured.

**Delivery:** flat and certain. No adjectives, no rising inflection, no selling. The numbers
persuade. Slow on the refusal and on `3 out of 3`.

**Driving:** `/how-it-works` does not autoplay. You advance each part with `→`, so the page
moves when you say the line. Tabs in order: `/how-it-works` · `/maya` · `/c/c-priya` · `/ask`.

**Why Jev is named out loud, repeatedly:** the room speaks this dialect. Say **fan-out**, say
**typed calibrated judgments**, quote **questions per request** and **measured milliseconds**.
Saying "the AI decided" in this room is the expensive mistake.

---

## The script

### [0:00 — 0:36] `/how-it-works` — the machine

> Three parts. The thing making every decision here is **Jev**.
>
> **Part one.** It reads what Maya already published. Fifteen posts and fifteen of her
> photographs. GPT-4o-mini reads the pictures — **Jev never sees a pixel**. Then twenty-eight
> questions go to Jev **at the same instant**. One fan-out, two requests, typed calibrated
> judgments, not prose. Her standard comes back in **six hundred and fifty milliseconds**.
>
> *[advance]*
>
> **Part two.** Three in the morning, one message arrives. Twenty questions in a single request.
> Code enumerates every basket she could send. Jev scores all of them. One `choice` picks the
> winner. **Seven tenths of a second.**
>
> *[advance]*
>
> **Part three.** It did that for everyone. Fifty-four messages. **One thousand and seventy-two
> judgments.**

*[pause]*

### [0:36 — 0:55] `/maya` — what she wakes up to

> Her morning. **Six need her.** Everything else is written and waiting.
>
> Every row says how sure Jev was. The medical ones get no score at all — they get **passed on**,
> with who to ask.
>
> And nothing was sent. Every one is a draft. She presses send.

### [0:55 — 1:09] `/c/c-priya` — what the person receives

> Two products. Fifty-eight pounds.
>
> And look at what it turned down. A sixty-two pound serum she rates eight out of ten. Her own
> words: **"Good. Not sixty-two quid good."** With the cheaper thing that does the same job.
>
> Refusing a sale is the whole product.

*[pause]*

### [1:09 — 1:15] Close

> Her private routing sheet never entered a prompt. We pulled it out of her captions anyway.
> **Three out of three.**
>
> It is live. Open it on your phone.

---

## The Jev vocabulary, deliberately

Every one of these is true of what we built, and each is a phrase this room uses.

| Say | Where |
|---|---|
| **fan-out** | part one, "twenty-eight questions at the same instant" |
| **typed calibrated judgments, not prose** | part one |
| **two requests**, **+0ms and +14ms** | reserve, if asked about parallelism |
| **`choice` / `noul` / `score`** | part two, "one `choice` picks the winner" |
| **confidence threshold** | `/maya`, "how sure Jev was" and the medical rows |
| **code acts** | part two, "code enumerates, Jev scores, code picks" |
| **Jev never sees a pixel, never hears audio** | part one — the LLM/Jev split |

**Never say:** *autonomous*, *AI*, *clone*, *chatbot*, *the AI decided*.

---

## Criteria coverage

| # | Criterion | Where it lands |
|---|---|---|
| 01 | Creator impact | *"Six need her"* out of fifty-four |
| 02 | Problem insight | Judgement is the bottleneck, not typing. The refusal proves it |
| 03 | Product thinking | *"Nothing was sent. She presses send."* |
| 04 | Technical execution | Fan-out, 1,072 judgments, the two-stage basket, real latencies |
| 05 | Taste | Medical rows get no confidence score. Refusing a sale. No adjectives |
| 06 | Resourcefulness | The held-out test — we kept checking our own work |
| 07 | Creator desirability | Her words, her prices, her shelf, her send button |
| 08 | Potential | Spare beat below, or the reserve answer |

## Cut if over
The second sentence of `/maya` (7s). **Never cut the refusal or `3 out of 3`.**

## Spare beat if under
> Same fourteen questions, pointed at a real cosmetic chemist's public blog, produce a different
> person in under a second. Sceptical of hype like Maya, defends SPF like Maya, and **not** price-led.
> So this is not tuned to one creator.

---

## Reserve ammunition — do not volunteer

**"Isn't this just an LLM call?"**
No. Jev returns typed calibrated judgments with probabilities, never prose. Twenty-eight questions
against one shared state in two requests, measured on the wire at **+0ms and +14ms** — they
genuinely overlap. Code enumerates the baskets, Jev scores them, one `choice` resolves it.
Two-stage, because single-stage gave a different winner between runs.

**"What is Jev actually doing that a chat model isn't?"**
Three primitives — `noul`, `choice`, `score` — returning calibrated probabilities. That is what
lets the confidence gate be a real policy rather than a vibe: below it, the message waits for
Maya. And it is why a medical message can be refused by a `noul` against her own stated scope
instead of a keyword list.

**"Does it diverge from a dermatologist?"**
No. **Zero out of eight.** We built the test expecting a gap, did not find one, and retired the
claim in our own README. The honest finding is the held-out routing match.

**"Did you scrape Instagram?"**
No. Logged out it returns 429 on the first request. We ran six containers on Modal across AWS,
Azure and GCP — four distinct fresh IPs, every one refused instantly. Datacenter IP reputation,
not a rate limit you can wait out. `scripts/probe_modal_ip.py` reproduces it.

**"How do you know the replies are any good?"**
We graded all fifty against the message. Forty-one answered it; inside the ready-to-send lane it
was nineteen of twenty-four. The cause was the question-back taking a 0.27-confidence choice
unconditionally. Now forty-seven of fifty.

**"What about safety?"**
Nine referrals, every planted medical trap caught. One sat exactly on the threshold — *"a bad
reaction, red and peeling"* scored 0.48 to 0.51 across five identical runs and was referred in
one run out of five. The most urgent message in the corpus was a coin flip. A second signal
reads it at 0.96 every time.

**"Voice notes?"**
Whisper transcribes, then the transcript goes through **the same triage as a typed message** —
same questions, same gate. The pregnancy one is referred at confidence 1.0. Jev never hears audio.

**"What did it cost?"**
A full refresh went from 1.14 million input tokens to 386 thousand. The warm was extracting Maya
twice and the second run's values could never reach a payload.

---

## Rules for the room

- Read live numbers off the screen, not from memory. A re-warm moves them.
- Never a decimal price or a float aloud. Bands: *about fifty to fifty-five pounds*.
- Always attach the alternative to a refusal.
- If a number is questioned, give the smaller honest one first. The retraction only works if we
  reach for it before they do.
