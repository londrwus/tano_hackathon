# Jev / TypeSafe Engineering Playbook — Tano x Corgi Creator Heist

Compiled 2026-09-20 from live docs at `docs.typesafe.ai`. Every number and quoted string below is from the docs unless marked MEASURED (our own verified call) or ESTIMATE.

---

## 0. TL;DR for the team

- `pip install typesafe-sdk`, `export TYPESAFE_API_KEY=...`, `model="jev-latest"` → `jev-1.13.0`.
- **$0.042 per 1M input tokens. Output tokens are free.** A batch of ~5,000 judgments costs about **5 pence**. This is not a cost you need to engineer around; it is a cost you should *show on screen*.
- Rate limits: **250,000 tokens/second, 1,200 requests/minute**. Context: **64k total per request, 32k for state + longest question**.
- The whole game is: **one state, many atomic typed questions, evaluated in parallel, recombined by code.** Every serial round trip you add is a design failure.
- The single most demo-winning property: `score`/`choice` return **full probability distributions**. Score 20 atomic dimensions **once**, then let sliders re-weight them in the browser at 0ms and £0. That is an interactive product that never re-runs inference.

---

## 1. The mental model in five sentences

1. Jev is a **System One** model: it does not write replies, produce code, or generate explanations of its reasoning — it converts unstructured text into **typed, calibrated judgments** your code can threshold, sort and combine.
2. It is *for* narrow, atomic, snap judgments a knowledgeable person makes in seconds ("does this person's stated budget constraint appear in the message?", "how much does this read as wanting a verdict rather than information?"), asked **many at a time over one shared state**.
3. It is *not* for generation, arithmetic, counting, date ordering, numeric proximity, or multi-hop reasoning — all of that belongs in Python.
4. Because every output is constrained to options you supplied, you get a **probability distribution**, never a hallucinated value outside your schema, and never a parse step.
5. The architecture is "AI-powered software", not an agent: **code owns the control flow**, and the model appears only where the system needs programmable common sense — "build a normal software workflow and insert System One only where AI is needed."

> **The line to say to the judges:** "We didn't ask a model what Maya would say. We asked it 40 small questions Maya already asks herself, and then we let code do Maya's arithmetic."

---

## 2. Exact request/response contract

### Install

```bash
pip install typesafe-sdk
# or
uv add typesafe-sdk
```

Cookbooks pin a newer build from TypeSafe's own index (needed only if you want their `cooksafe` caching helper):

```bash
pip install "typesafe-sdk>=0.5.7" cooksafe --extra-index-url https://pypi.typesafe.ai/
```

Environment variables read by the SDK: **`TYPESAFE_API_KEY`** (required), `TYPESAFE_DEFAULT_MODEL`, `TYPESAFE_BASE_URL`, `TYPESAFE_LOG_LEVEL`. Keys at `https://console.typesafe.ai/keys`.

### Raw HTTP (the ground truth)

```http
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

```json
{
  "state": "is the cloud cream actually worth £38 or am i being influenced",
  "model": "jev-latest",
  "questions": {
    "q_seeks_verdict": {
      "type": "noul",
      "instructions": "Is the sender asking for a personal verdict rather than product information?",
      "criteria": { "true": "Wants someone's judgement", "false": "Wants a fact or spec" }
    }
  }
}
```

Response:

```json
{
  "model": "jev-1.13.0",
  "answers": {
    "q_seeks_verdict": { "type": "noul", "noul": 0.95 }
  },
  "usage": { "input_tokens": 296, "output_tokens": 20 }
}
```

### Three question shapes — exact fields

| Type | required | `criteria` | Answer fields |
|---|---|---|---|
| `noul` | `type`, `instructions` | **optional** object `{true, false}` | `noul` (0–1). **No `confidence`.** |
| `choice` | `type`, `instructions`, `criteria` | `map<string, string\|object\|array\|null>` — **max 255 options** | `choice`, `probabilities` (sum to 1), `confidence` |
| `score` | `type`, `instructions`, `criteria` | **ordered array**, ≥2 levels, **API accepts up to 10** | `score` (probability-weighted, lands between levels), `legend`, `probabilities`, `confidence` |

`score` is literally `Σ(level_i × p_i)`. Docs example: `(0×0.0)+(1×0.57)+(2×0.43) = 1.43`.

`instructions` and every criteria value accept **string | object | array** (the docs call this `EntryType`).

### Correct Python async example — in our domain

```python
# maya_engine.py
import asyncio, os
from typesafe_sdk import (
    AsyncTypeSafeClient, Choice, Noul, NoulCriteria, Score, RetryPolicy,
)

SHELF = [
    {"ref": "E-04.1", "name": "Cloud Cream", "gbp": 38, "type": "moisturiser",
     "skin": "Dry", "finish": "Rich", "maya_rating": 9.2, "maya_note": "My winter skin saviour."},
    {"ref": "E-04.3", "name": "Red Reset", "gbp": 32, "type": "serum",
     "skin": "Sensitive", "finish": "Calm", "maya_rating": 9.5, "maya_note": "For angry skin days."},
    {"ref": "E-04.6", "name": "Glass Drop", "gbp": 62, "type": "serum",
     "skin": "All", "finish": "Dewy", "maya_rating": 8.1, "maya_note": "Good. Not £62 good."},
]

def build_state(asker: dict, product: dict) -> dict:
    # Only what these questions need. Nothing else. See jaggedness #7.
    return {
        "asker": {
            "message": asker["message"],
            "stated_skin": asker.get("skin"),
            "already_owns": asker.get("owns", []),
        },
        "product": product,
        "creator_voice": {
            "principles": [
                "Say when something is not worth the money.",
                "Fewer steps beats more steps.",
                "Do not recommend retinol to everyone.",
                "Fragrance is a risk for sensitive skin.",
            ],
            "register": "Dry, funny, decisive. Never corporate. Never hedging.",
        },
    }

QUESTIONS = {
    # --- atomic fit dimensions, scored once, re-weighted later in code ---
    "d_skin_fit": Score(
        instructions={
            "question": "How well does this product suit the asker's skin as described?",
            "compare": ["`asker.message`", "`asker.stated_skin`", "`product.skin`"],
            "focus": "Judge skin-type suitability only. Ignore price and ignore how much Maya likes it.",
        },
        criteria=[
            {"what": "Actively wrong for this skin", "signals": ["Known irritant for them", "Opposite skin type"]},
            {"what": "Tolerable but not chosen for them", "signals": ["Generic 'all skin types' match"]},
            {"what": "A deliberate match for this skin", "signals": ["Product's stated skin equals theirs"]},
            {"what": "The obvious pick for this exact skin", "signals": ["Targets the specific complaint they named"]},
        ],
    ),
    "d_maya_conviction": Score(
        instructions={
            "question": "How strongly does Maya's own note endorse this product?",
            "inspect": "`product.maya_note`",
            "focus": "Read the note's conviction, not the numeric rating.",
        },
        criteria=[
            {"what": "She has a reservation about it", "signals": ["Price caveat", "'Good, not X good'"]},
            {"what": "She rates it but without heat", "signals": ["Flat, functional praise"]},
            {"what": "She would defend this one", "signals": ["Possessive language", "'Non-negotiable'", "'saviour'"]},
        ],
    ),
    # --- the 16:00-drop dimension: decide-without-asking ---
    "d_survives_forward": Noul(
        instructions={
            "question": "Would this recommendation still make sense if the asker forwarded it to a friend with no other context?",
            "focus": "Judge self-containment of the reason, not the quality of the product.",
        },
        criteria=NoulCriteria(
            true={"what": "The reason to buy is legible to a stranger",
                  "examples": ["Names the specific problem it solves"]},
            false={"what": "Only makes sense if you already follow the conversation",
                   "not_for": "A reason that is simply short",
                   "examples": ["'the good one'", "'as I said last week'"]},
        ),
    ),
    "d_voice_violation": Noul(
        instructions={
            "question": "Would recommending this product contradict one of `creator_voice.principles`?",
            "compare": ["`product`", "`creator_voice.principles`"],
        },
        criteria=NoulCriteria(
            true={"what": "Breaks a stated principle", "examples": ["Pushing a £62 serum she called not worth it"]},
            false={"what": "Consistent with all stated principles"},
        ),
    ),
}

async def judge_shelf(asker: dict, shelf=SHELF, concurrency: int = 16):
    sem = asyncio.Semaphore(concurrency)
    async with AsyncTypeSafeClient(
        model="jev-latest",
        retry=RetryPolicy(max_retries=4, backoff_initial=0.25, backoff_max=4.0, timeout=20.0),
        timeout=15.0,
    ) as client:
        async def one(product):
            async with sem:
                r = await client.system_one(state=build_state(asker, product), questions=QUESTIONS)
            return {
                "ref": product["ref"],
                "name": product["name"],
                "gbp": product["gbp"],
                # typed accessors
                "skin_fit":     r.scores["d_skin_fit"].score / 3.0,        # 4 levels -> /(n-1)
                "skin_fit_conf": r.scores["d_skin_fit"].confidence,
                "skin_fit_dist": r.scores["d_skin_fit"].probabilities,     # KEEP THIS - it's the chart
                "conviction":   r.scores["d_maya_conviction"].score / 2.0, # 3 levels -> /2
                "forwardable":  r.nouls["d_survives_forward"].noul,
                "violates":     r.nouls["d_voice_violation"].noul,
                "usage":        (r.usage.input_tokens, r.usage.output_tokens),
            }
        return await asyncio.gather(*(one(p) for p in shelf))

if __name__ == "__main__":
    asker = {"message": "i have dry skin + redness and £60. tell me what to buy pls",
             "skin": "dry, redness", "owns": ["Night Serum"]}
    rows = asyncio.run(judge_shelf(asker))
    for row in sorted(rows, key=lambda r: -row_score(row)):
        print(row["name"], round(row["skin_fit"], 2), round(row["forwardable"], 2))
```

Response accessors, both forms work:

```python
r.answers["d_skin_fit"].score        # generic map
r.scores["d_skin_fit"].score         # typed maps: .nouls / .choices / .scores
r.nouls["d_voice_violation"].noul
r.choices["x"].choice, r.choices["x"].probabilities, r.choices["x"].confidence
r.usage.input_tokens, r.usage.output_tokens
r.raw_http_response                  # when you need headers / request id
```

Sync equivalent: `with TypeSafeClient() as client: client.system_one(...)`. Questions may also be raw dicts (`{"type": "noul", "instructions": "..."}`) — useful when we load a question bank from JSON, which we should.

---

## 3. How to write a GOOD question

### The rule that matters most

> "Ask the most explicit, narrow, specific, atomic questions you can. Break down complex or ill-defined questions into separate questions that each evaluate one property. **This is probably the most important concept in this guide.** Broad questions hide several judgments behind one answer. Atomic questions expose those judgments so you can inspect, tune, and combine them in code."

And: **"Decomposition does not require more round trips. Questions over the same state run in parallel."**

### instructions vs criteria

- `instructions` = **the judgment**. One judgment. One sentence, or a small object.
- `criteria` = **the answer space**. For Choice, the options and their boundaries. For Score, the ordered levels. For Noul, optional definitions of what yes and no *mean*.
- Treat criteria as an extension of instructions — jaggedness #9: contradictory instructions and criteria degrade accuracy. Same vocabulary in both.

### Structured instructions — use these field names

They are **not reserved**; you invent them, and "the model sees both names and values." The docs' own house style, which we should adopt verbatim for consistency:

| field | use |
|---|---|
| `question` | the actual judgment |
| `focus` | what to judge and, crucially, **what to ignore** |
| `inspect` | the single backticked state path to read |
| `compare` | an **array** of backticked paths when the judgment is a comparison |
| `what` / `not_for` / `examples` | inside Choice options and Noul true/false |
| `summary` / `signals` | inside Score levels |

`not_for` is the highest-leverage field we have. It is how you stop two adjacent taste dimensions from collapsing into each other.

### Backticked paths

Point at nested state with dot-and-index paths **inside backticks**: `` `asker.message` ``, `` `product.maya_note` ``, `` `shelf[0].gbp` ``. This also works for data you put inside `instructions` itself — the resume/`potential_duplicate` pattern. Use it whenever a value comes from our database rather than the message, so we never string-template into a prompt.

### Good vs bad — in our domain

**BAD — one broad question hiding six judgments**

```json
{ "type": "noul", "instructions": "Would Maya recommend the Cloud Cream to this person?" }
```

Hides: skin match, budget, redundancy with what they own, routine-length tolerance, Maya's conviction, fragrance risk. A 0.62 here tells you nothing and you can't tune it.

**GOOD — decomposed, each independently inspectable**

```json
{
  "fits_stated_skin":      {"type":"score","instructions":{"question":"How well does `product.skin` match the skin described in `asker.message`?","focus":"Skin suitability only. Ignore price and ignore Maya's opinion."},"criteria":["Actively wrong for this skin","Tolerable, generic match","A deliberate match","The obvious pick for this exact complaint"]},
  "redundant_with_owned":  {"type":"noul","instructions":{"question":"Does the asker already own a product that does the same job?","compare":["`product.type`","`asker.already_owns`"]},"criteria":{"true":"Same job as something they own","false":"Fills a gap they do not have covered"}},
  "adds_a_step":           {"type":"noul","instructions":{"question":"Does adding this product increase the number of steps in the asker's routine?","inspect":"`asker.message`","focus":"Only whether step count rises, not whether that is bad."}},
  "asker_wants_verdict":   {"type":"noul","instructions":{"question":"Is the asker asking for a personal verdict rather than product information?"},"criteria":{"true":{"what":"Wants someone to decide for them","examples":["if u could only keep ONE which one","what would YOU buy"]},"false":{"what":"Wants a retrievable fact","not_for":"A fact question phrased casually","examples":["what shade are u wearing"]}}},
  "maya_conviction":       {"type":"score","instructions":{"question":"How strongly does `product.maya_note` endorse this product?","focus":"Read conviction in the wording, not the numeric rating."},"criteria":[{"what":"She states a reservation","signals":["price caveat","'not £62 good'"]},{"what":"Flat functional praise","signals":["'Easy. No drama.'"]},{"what":"She would defend it","signals":["'saviour'","'non-negotiable'"]}]}
}
```

**BAD — arithmetic dressed as judgment**

```json
{"type":"noul","instructions":"Is `product.gbp` within the asker's £60 budget?"}
```

Jev "will perform better on semantic questions than mathematical ones" and "cannot reliably judge whether two values are near each other." Do this in Python: `product["gbp"] <= budget`. Use Jev only to *extract* the budget into a bucket:

```json
{"type":"choice","instructions":"Which budget band does the asker state in `asker.message`?",
 "criteria":{"under_25":null,"25_to_50":null,"50_to_100":null,"over_100":null,"none_stated":null}}
```

**BAD — compound condition**

> "Ask one yes/no question per Noul. If a question has two conditions, such as 'Is the customer angry and asking for a refund?', the model has to judge both at once and the value means less."

`"Is the asker sensitive-skinned AND on a budget?"` → two Nouls, `and` in Python.

**BAD — double negative**

`"Is it not the case that Maya would avoid recommending this?"` → jaggedness #6, indirection. Always phrase so **high = yes**.

### How many questions per request

As many as are about the same state. The parallel-questions cookbook batched **13 questions (8 noul, 2 choice, 3 score)** over a ~54,000-character document: **1 call, $0.000497, 0.27s** versus 13 calls, $0.006090, 2.71s — **12.2x cheaper, 10.0x faster**, with "statistically identical answers", most stddevs exactly 0.0. The function-calling cookbook runs **54 questions per command**. We should be comfortable at 20–40 questions per request.

The only ceiling is context: **64k total, 32k for state + longest question.**

### What breaks accuracy

Directly from the docs: large irrelevant state ("unrelated detail acts as a distractor"), indirection/double negatives, contradictory instructions vs criteria, compound questions, vague Score levels ("Moderately severe" — use concrete situations like "Broken feature with workaround"), and numeric/date/counting anything. Score levels are "evaluated independently; the model doesn't see level numbers or neighbors" — so each level description must stand alone, not read as "more than the last one."

---

## 4. Calibration and confidence

### What confidence is

"A statistic computed from the probability distribution the answer already gives you… concentrated on one outcome means a confident answer, spread out means an uncertain one." The docs give the 3-option instance: **`(3 × p_max − 1) / 2`** — i.e. generally `(k·p_max − 1)/(k − 1)` for k options/levels, which is 0 at uniform and 1 at certainty.

- **Choice**: distribution over your options.
- **Score**: distribution over your levels. Note the trap — `score = 1.43` with `probabilities {1: 0.57, 2: 0.43}` gives **confidence 0.35**. The mean looks decisive; the model is actually torn between two levels. **Always read `.confidence` next to `.score`.**
- **Noul**: **no confidence field, by design.** "A Noul's probability distribution has only two outcomes, yes and no, so the single `noul` value describes it completely."

### What a noul of 0.5 means

It means the model gives yes and no similar probability — not "50% of the time yes". Never threshold hard at 0.5 on anything that matters. Use the **three-band** pattern from the consistency cookbook:

```python
if p < 0.30:   verdict = "no"
elif p > 0.70: verdict = "yes"
else:          verdict = "uncertain"   # never auto-act
```

The docs' rationale is exactly our situation: the band "prevents opposite automatic decisions for values near 0.5, absorbing inherent model variance without requiring additional API calls."

### Picking thresholds

> "A confidence threshold is not one number. Different actions within the same system should be gated at different levels depending on the consequences of getting it wrong."

Working numbers lifted from the docs, as our starting constants:

| Situation | Threshold | Source |
|---|---|---|
| Noul → yes | `> 0.70` | consistency cookbook |
| Noul → no | `< 0.30` | consistency cookbook |
| Choice, low-risk auto-action | `confidence ≥ 0.6` | confidence-routing |
| Choice, high-risk auto-action | `confidence ≥ 0.85` | confidence-routing |
| Choice, commit to a fine-grained label | `confidence ≥ 0.9` | classification-using-confidence |
| Escalate to human | `confidence < 0.75` | how-to-build worked example |
| Composite spam-style score, uncertain band | `0.4 < s < 0.6` | how-to-build worked example |

**Put every threshold in one `THRESHOLDS` dict.** The RAG cookbook does this explicitly so they "live in `THRESHOLDS` for easy adjustment without API calls." At 16:00 when the intelligence drop lands, we will be changing thresholds, not code.

### Self-consistency

Jev is designed for stability. Measured in the consistency cookbook over **15 repeats** of a 14-question rubric: **mean per-question probability stddev `0.0102`**, below every LLM condition tested — including LLMs at temperature 0, which "move from run to run… at temperature `0` too". Latency `111ms`, cost `$0.000043` per call, vs claude-haiku-4-5 at 16.0x slower / 42.2x costlier and gpt-5.5-reasoning at 100.2x slower / 778.9x costlier.

**Mechanic to know:** to draw independent samples the cookbook adds a **fresh throwaway `uid` field to the state** per repeat (which also defeats caching). If a dimension sits inside our uncertain band and matters, sample it 5× with different `uid`s and take the mean — 5 extra calls cost about £0.0002. Don't do this for everything; the model is already stable enough that it's wasted latency.

### The escalation ladder (ours)

1. High confidence → render the verdict.
2. Medium → render the verdict **with the hedge Maya would actually use** ("if you're not sure, this is the safer one").
3. Low → **back off to the parent level**, don't escalate. This is the cookbook's best trick: when confidence < 0.9 they report the *division* instead of the *group*, converting **40% accuracy into 70%** with zero extra calls. Our version: instead of naming Cloud Cream, say "for dry + redness, you want a rich barrier moisturiser under £40 — here are the two on Maya's shelf." **That is more in Maya's voice than a confident wrong answer, and it demos as taste rather than as a fallback.**

---

## 5. The five patterns that matter for us

### 5.1 Speculative fan-out — ask questions you might not need

"All questions are evaluated in parallel, so adding more questions usually has little effect on response time." And: "Speculative questions are ignored when irrelevant and save a round trip when they are not."

Practically: send the *whole* question bank — budget-band, skin-type, verdict-vs-fact, overwhelm, sensitivity risk, forwardability, routine-length tolerance, first-date urgency — on **every** message. Code picks which answers matter after it sees the classification. We never branch-then-call.

### 5.2 Composite scoring — **this is our demo**

Score many atomic dimensions **once**, normalise, then re-weight in **code**:

```python
def normalise(score, n_levels):        # docs: divide by (n_levels - 1)
    return score / (n_levels - 1)
```

The docs' resume example scores 4 dimensions on 5-point scales, then applies two different weight vectors — Senior IC `{python .40, leadership .10, design .40, generalist .10}` vs Engineering Manager `{.15, .40, .20, .25}` — and states the point plainly: the weights change "relative importance of each dimension, without losing any of the nuance of the individual scores", allowing recalibration **without re-running inference**.

**Our build:**

```python
PERSONAS = {                      # the six Known Associates, as weight vectors
    "emily_price_sensitive": {"skin_fit":.20, "value_for_money":.45, "conviction":.15, "simplicity":.20},
    "priya_sensitive_skin":  {"skin_fit":.45, "irritation_risk":.35, "conviction":.10, "simplicity":.10},
    "hannah_overwhelmed":    {"simplicity":.45, "conviction":.30, "skin_fit":.20, "value_for_money":.05},
    "alex_silent_browser":   {"forwardable":.40, "conviction":.30, "skin_fit":.20, "simplicity":.10},
}

def rank(rows, weights):          # pure python, 0ms, £0
    return sorted(rows, key=lambda r: sum(w * r[k] for k, w in weights.items()), reverse=True)
```

**Demo choreography (90 seconds):** judge the shelf once on stage — show the latency and the token cost on screen — then drag a persona selector or four sliders and watch the ranking reorder instantly. Say out loud: *"No model ran just then. We asked Jev the small questions once; everything after that is arithmetic."* That is simultaneously the elegance point, the inventiveness point and the commercial point (unit economics: judge once, serve forever).

### 5.3 Confidence-gated routing

"The answer tells you what; confidence tells you whether to act." Tiered, by consequence:

```python
topic = r.choices["asker_need"]
if topic.confidence < 0.60:            return ask_one_clarifying_question()   # Maya's own first question
if topic.choice == "shade_match":      return ask_current_foundation()        # from E-02.2, deterministic
if topic.choice == "buy_decision":
    return verdict(rows) if topic.confidence >= 0.85 else shortlist_of_two(rows)
```

Note we encoded Maya's **actual** routing table (E-02.2: DRY → Cloud Cream + Barrier Oil; SENSITIVE → avoid fragrance; shade questions → ask current foundation) as **code**, not as model judgment. Jev decides *which branch*; Maya's notebook decides *what happens there*. That is "fidelity to the creator's judgement" as an architecture, and it is the single easiest thing to say convincingly to a judge who is also the creator.

### 5.4 Reranking

BM25 (or any cheap retrieval) → top-30 → one Noul per candidate → sort by noul:

```python
nouls = {c: ask_typesafe(query, c) for c in shortlist}
reranked = sorted(shortlist, key=lambda c: nouls[c], reverse=True)
```

CLERC legal benchmark, 3,565 passages, 40 queries: **top-1 5% → 18%, top-5 15% → 35%, top-10 38% → 62%**. Cost of the whole thing: **1,200 calls, 1,536,002 input tokens, $0.0645**.

**Our use:** rerank Maya's own back catalogue against an incoming question, so the answer cites *her own video* ("she covered this in 'Luxury vs drugstore'") rather than inventing prose. Cheap, and it is the strongest possible "use of the evidence" signal.

### 5.5 One Choice over the entire shelf

A Choice takes **up to 255 options** and returns a probability for every one, summing to 1. So:

```json
{"type":"choice",
 "instructions":{"question":"Which single product on Maya's shelf would she tell this person to buy?",
                 "focus":"Assume they buy exactly one thing."},
 "criteria":{"Cloud Cream":{"what":"Rich moisturiser, dry skin, £38","note":"My winter skin saviour."},
             "Red Reset":{"what":"Calming serum, sensitive/redness, £32","note":"For angry skin days."},
             "Glass Drop":{"what":"Dewy serum, all skin, £62","note":"Good. Not £62 good."}}}
```

One call, and the `probabilities` map **is a bar chart** — Maya's hesitation, rendered. Pair it with the composite ranking as a cross-check: where the direct Choice and the weighted composite disagree, that is a genuinely hard case and a great thing to surface in the UI ("Maya would go back and forth on this one").

---

## 6. Throughput and cost engineering

### The numbers

| | value |
|---|---|
| Price | **$0.042 / 1M input tokens**; **output free** |
| Rate limit | **250,000 tokens/sec**, **1,200 requests/min** (docs warn limits "are adjusting dynamically" and may change without notice) |
| Context | **64k/request**, **32k** for state + longest question |
| Latency, docs claim | "Most queries complete in about 100 ms" |
| Latency, cookbook | 111 ms (14 questions); 0.27 s (13 questions over a 54k-char doc) |
| Latency, MEASURED from us | **873 ms for 3 questions, 563 in / 84 out** |

Budget **~0.3–1.2 s per request from London**, not 100 ms. Anything demo-critical gets pre-baked to JSON.

### Retry policy

`RetryPolicy` defaults: `max_retries=2, backoff_initial=0.5, backoff_max=5.0, backoff_jitter=0.25, http_statuses={408, 429, 500–599}, respect_retry_after=True, api_connection_error=True, api_timeout_error=True, timeout=30.0` (total retry budget per SDK call, including the initial attempt and delays).

Errors: `401` bad key, `422` malformed question (body names the offending field), `429` rate limit, `529` overloaded. The docs: "retry the request with exponential backoff instead of retrying immediately. Our client SDKs handle this automatically."

Our settings — tighter budget, more attempts, because an 8-hour hackathon cannot afford a 30s stall on stage:

```python
RetryPolicy(max_retries=4, backoff_initial=0.25, backoff_max=4.0, backoff_jitter=0.25, timeout=20.0)
```

```python
from typesafe_sdk import TypeSafeAPIError
try:
    r = await client.system_one(state=s, questions=Q)
except TypeSafeAPIError as e:
    log.error("typesafe %s request_id=%s", e.status, e.request_id)
    return CACHED_FALLBACK[key]          # the demo NEVER shows a traceback
```

### Concurrency

`asyncio.Semaphore(16)` is the right default. One `AsyncTypeSafeClient` for the whole process (it owns an httpx connection pool — do **not** construct one per request). 1,200 rpm = 20 rps; at ~0.9s latency, 16–18 in flight sits right at the ceiling without tripping 429s.

### Cost estimate for ~5,000 judgments

Token model, fitted to MEASURED (3 questions / 563 input tokens) and the docs' examples (1 question / 296 tokens):

```
input_tokens ≈ 420 (protocol overhead) + state_tokens + Σ question_tokens   (~40–60 tok/question)
```

| Shape | Requests | Judgments | Input tokens | Cost |
|---|---|---|---|---|
| 12 shelf products × 20 dimensions | 12 | 240 | ~12 × 1,900 = 23k | **$0.001** |
| 50 DMs × 20 questions | 50 | 1,000 | ~50 × 1,700 = 85k | **$0.004** |
| 12 products × 20 personas × 20 dims (**4,800 judgments**) | 240 | 4,800 | ~240 × 1,900 ≈ **456k** | **$0.019** |
| Same, with rich 1,500-token states | 240 | 4,800 | ~240 × 3,400 ≈ 816k | **$0.034** |

**ESTIMATE: ~5,000 judgments = 1.5–4 pence and about 15 seconds wall-clock at concurrency 16.**

Cross-check against the public demos — 21,690 decisions for 22 cents implies ~241 input tokens per decision, i.e. heavy batching. Our numbers are the same order. **Batching is what makes the price look absurd; if we send one question per call we pay ~12x more and it stops being a headline.**

### Show the money

Sum `usage.input_tokens` across the run and render it live: **"4,800 judgments · 18 seconds · £0.015."** That single line does more for "best commercial potential" than any slide, and it is the exact register of the Jev demos that went viral. Log `response.model` too (`jev-1.13.0`) so the number is attributable.

---

## 7. Known jaggedness (jev-1.13) and how we design around it

| # | Failure mode | Docs say | Our mitigation |
|---|---|---|---|
| 1 | **Literal reading** | Answers "the question you wrote, not the one you meant"; scoping words, negations, implied conditions taken at face value | State conditions explicitly; name boundary cases; split ambiguous questions and `and` them in code |
| 2 | **Math** | "will perform better on semantic questions than mathematical ones" | All arithmetic in Python. No exceptions |
| 3 | **Counting** | "does not count reliably" — characters, occurrences, list items; worse as data grows | `len()`. Joanna's "only 2 products" constraint is a slice, not a judgment |
| 4 | **Numeric representations** | "cannot reliably judge whether two values are near each other" (RGB, hex) | **Shade matching must not be RGB.** Convert to named buckets in code and ask semantically ("warm neutral with a golden undertone") |
| 5 | **Dates/times** | "reads dates as text, not as ordered quantities" | Extract only; compare in code. The drop's "3.4–9.2 day lag" is a `timedelta`, never a Noul |
| 6 | **Indirection** | double negatives and multi-hop "answered less reliably" | One hop per question; name the state path; phrase so high = yes |
| 7 | **Large irrelevant state** | "Accuracy falls as the state grows with content unrelated to the decision. Unrelated detail acts as a distractor" | Build a minimal state per question-group. Do **not** dump the whole 17-sheet dossier in |
| 8 | **Adversarial content** | model "does not treat it as hostile by default" | DMs are user input. Keep a `contains_prompt_injection` Noul (the RAG cookbook scored an injected post at **0.99**) and exclude above 0.70 |
| 9 | **Contradictory instructions vs criteria** | degrades accuracy | Criteria are an extension of instructions; same words in both |
| 10 | **No structural invariants** | "P(noul) and 1 − P(not noul) may not be directly comparable" | Never derive a complement. If we need "not suitable", ask it as its own question |
| 11 | **Generation** | "Jev-1.13 is not trained to generate text"; chaining to force generation is "ineffective and slow" | **Jev never writes a word of Maya's copy.** Either Claude writes it from Jev's typed verdict, or — better — we assemble from Maya's own recovered phrasings and let Jev only *select* |

Also: text only, no images/audio/video. English primary; "other languages, including CJK scripts, are accepted but currently have lower accuracy."

> **Demo-safety rule from #11:** the thing on screen at 19:45 must not be a paragraph Jev wrote, because Jev cannot write paragraphs. It must be a **decision, a ranking, or a distribution**. Design the UI so the hero object is a chart or a verdict card, not prose. This is also the most honest framing and the judges will recognise it.

---

## 8. Ten things that will bite us in a hackathon

1. **Question ids are invisible to the model.** "The key is not sent to the underlying model and is not used in inference." Naming a question `is_definitely_worth_the_money` contributes exactly nothing. The meaning must be in `instructions` and `criteria`. Someone will burn 40 minutes on this.
2. **Noul has no `confidence`.** `r.nouls[...].confidence` will `AttributeError` at the worst moment. Nouls give you one number; Choice and Score give you three.
3. **A `score` of 1.43 can have confidence 0.35.** The weighted mean hides a 57/43 split between two levels. If we rank on `.score` alone the ranking will look arbitrary on the exact edge cases judges will poke at. Show the `probabilities` distribution in the UI — it turns a weakness into the most interesting pixel on screen.
4. **Score is capped at 10 levels; Choice at 255 options.** An 11-level rubric is a `422`. And `422` bodies name the offending field — read them instead of guessing.
5. **Budget/price logic will silently rot.** "£60 budget" vs "£62 Glass Drop" is arithmetic (#2, #4). It will *look* like it works on three examples and then fail live on Grace. Filter by price in Python before Jev ever sees the shelf.
6. **Dumping the full dossier into `state` makes everything worse.** Jaggedness #7 is the most counter-intuitive one for a team used to LLMs, where more context usually helps. Here it actively degrades. Minimal state per question-group.
7. **One request per question kills both headline numbers.** 12.2x cost, 10.0x latency. If someone writes a loop that calls `system_one` once per dimension, our "£0.015" line becomes "£0.18" and our 18 seconds becomes 3 minutes. Code-review for this specifically.
8. **The venue wifi.** Measured 873ms in the office is not what Shoreditch will give us at 19:45 with 54 builders on the same AP. **Pre-bake every demo path to a JSON cache and load from it by default**, with a "LIVE" toggle we press once, early, on the safest query. The cookbooks ship exactly this pattern (`json_cache.json`, "reproduction costs nothing; deletion enables live execution"). Copy it.
9. **Rate limits are moving.** Docs explicitly warn limits "are adjusting dynamically… changes possible without notice." A batch that worked at 14:00 can 429 at 19:00 when every team is hammering the same endpoint during judging. Semaphore at 16, `max_retries=4`, and never run a big batch during the demo.
10. **The 16:00 drop rewards thresholds, punishes architecture.** The drop says the valuable behaviour is invisible — savers, silent browsers, private shares, 3.4–9.2 day lags. If our weights and thresholds live in one `THRESHOLDS`/`PERSONAS` dict, absorbing the drop is a 10-minute edit and we can *show* the before/after live, which is itself a killer demo beat. If they are scattered through the code, we lose the afternoon. **Build the dict at 11:00, before we need it.**

**Bonus, 11:** don't demo a chatbot. The brief says "You do not need to use an LLM. You do not get extra points for complexity. A simple product that works beats a complicated demo." Jev's shape and the brief's shape are the same shape. A typed, calibrated, instantly-re-weightable decision surface *is* the elegant answer, and it is the one thing a generation-based team physically cannot build in 8 hours.

---

## 9. Name the person and the decision

The brief: *"If you cannot name the person and the decision, you do not have a product yet."*

- **Person:** Alex, 28. Silent browser. Saves almost everything, sends almost nothing. Per the 16:00 drop she is 61–71% of the people who actually buy, converts 2.2–3.1x, and shares privately to a friend before she acts.
- **Decision:** *"Do I buy the £38 Cloud Cream, or is my dry-with-redness skin actually a £32 Red Reset problem?"*
- **Today:** she never asks. She saves the video, waits 3.4–9.2 days, and either forgets or buys the wrong one.
- **With us:** she answers the four questions Maya asks in real life (E-02.1), and gets Maya's ranked verdict with Maya's own reservation attached — **without Maya being in the loop**, and in a form she can forward to a friend intact.
- **Jev's job in that sentence:** score the shelf on Maya's taste dimensions, gate on confidence, and never write a word.

---

### Reference files

- `C:\Users\Lenovo\Documents\tano_hackathon\docs\research\typesafe-http-api.md` — full HTTP API reference, already saved locally; it is the authoritative contract, read it before writing any request builder.
- `C:\Users\Lenovo\Documents\tano_hackathon\docs\evidence\case-001-operation-shade.txt` — Maya's shelf (E-04), her routing table (E-02.2) and her four questions (E-02.1) are the literal inputs to the engine above.