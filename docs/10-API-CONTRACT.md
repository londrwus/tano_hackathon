# 10 — FROZEN API CONTRACT (v2)

**Frozen at H+0. Backend (lane A) and frontend (lane B) build against this and only this.**
If you need a field that is not here, add it — but announce it, never rename or remove one.

Base: `http://localhost:8000`. Frontend dev: `http://localhost:5173`. CORS allows both.
Everything is JSON. Every response carries `"cached": bool` and `"ms": int`.

Money is **always** returned as a preformatted string. `"£26"` / `"about £50–55"`.
**Never a float, never a decimal.** The frontend never formats money.
Probabilities may appear in the payload but the frontend renders them as bands/opacity, never digits.

---

## 1. `GET /api/case`
The case pack. Passthrough of `data/case-001-maya.json` plus derived bits.

```jsonc
{
  "cached": true, "ms": 2,
  "case": { "id": "001", "ref": "SHD-001", "operation": "OPERATION SHADE", "logline": "..." },
  "creator": { "name": "Maya Rao", "handle": "@mayarao", "city": "London",
               "followers_total": 50000, "dms_per_month": 4800, "reply_hours_per_month": 70,
               "creed": "People do not need more products. They need confidence." },
  "shelf": [ { "ref": "E-04.1", "product": "Cloud Cream", "gbp": 38, "price": "£38",
               "type": "Moisturiser", "skin": "Dry", "finish": "Rich",
               "maya_rating": 9.2, "maya_note": "My winter skin saviour.",
               "affiliate": true } ],
  "personas": [ { "id": "emily", "name": "Emily", "tag": "PRICE SENSITIVE", "says": "..." } ]
}
```

---

## 2. `GET /api/standard`
Her standard, **extracted** — the honest headline. Typed slots, each with the caption it came from.
Renders the side-by-side table in demo beat 3 and the switch rows on `/onboard`.

```jsonc
{
  "cached": true, "ms": 670, "extraction_seconds": 0.67, "slot_count": 9,
  "slots": [
    { "key": "routine_size", "label": "How many products",
      "maya":  { "level": "The fewest possible products", "value": 0.1,  "confidence": 0.94 },
      "derm":  { "level": "A small routine",              "value": 1.16, "confidence": 0.88 },
      "agrees": false,
      "source_caption": "my 5 minute morning routine. two products. that is it.",
      "evidence_ref": "E-03.5",
      "toggleable": true }
  ],
  "agree_count": 3, "disagree_count": 3,
  "headline": "Same six questions. They agree on three and disagree on three."
}
```

`toggleable: true` slots appear as switches on `/onboard`. Non-toggleable ones are display-only.

### `POST /api/standard/override`
Body: `{ "overrides": { "routine_size": 2, "price_refusal": 0.69 } }`
Returns the **whole `/api/queue` payload recomputed** under those overrides (cached per override
hash). This is demo beat 8 — flip a switch, the queue re-ranks. Must return in < 400ms from cache.

---

## 3. `GET /api/queue`  ← `/maya`, the morning approval queue
The hero screen. 50 DMs triaged four ways.

```jsonc
{
  "cached": true, "ms": 850,
  "stats": { "dms": 50, "judgments": 250, "seconds": 0.85,
             "answered": 30, "asked_back": 9, "held": 4, "referred": 7,
             "handled_pct": 78, "held_pct": 8, "referred_pct": 14,
             "at_real_volume": { "dms_per_month": 4800, "handled": 3744,
                                 "held_per_day": 12, "referred": 672 },
             "header_line": "you approved 30 replies in 4 minutes" },
  "cards": [
    { "id": "q-001", "ref": "E-01.3", "from": "@jessica", "text": "I already have the night serum...",
      "lane": "answered",
      "confidence": 0.91,
      "job": "do_i_need_it",
      "draft_reply": "No. Just the SPF. Twenty-six pounds.",
      "question_back": null,
      "hold_reason": null,
      "refusal": null,
      "card_id": "c-8f2a1b",
      "basket_summary": "SPF 50 · £26" }
  ]
}
```

`lane` is one of `answered` | `asked_back` | `held` | `referred`.
`question_back` is set when lane is `asked_back`. `hold_reason` is a human-readable sentence, set
when lane is `held`. `refusal` is set when lane is `referred`:
`{ "why": "...", "refer_to": "..." }`. `card_id` may be null. `basket_summary` may be null.

**Lane semantics — these words appear on screen, do not change them:**
`answered` → drafted in her voice · `asked_back` → it asks one of her intake questions ·
`held` → below the confidence gate, she decides · `referred` → out of scope, medical, refused.

### `POST /api/queue/{id}/action`
Body: `{ "action": "send" | "edit" | "hold", "text": "optional edited reply" }`
→ `{ "ok": true, "action": "edit", "correction_written": true, "standard_moved": "price_refusal +0.1" }`
**It never actually sends anything.** It records. Say that on stage.

---

## 4. `POST /api/ask`  ← `/ask`, the public link
Three chip taps, no text box required.

```jsonc
{ "skin": ["dry", "redness"],
  "budget": 60,
  "how_many": 2,
  "owns": [],
  "text": null }
```

`skin` is **multi-label** — an array, never a single string (bug #1).
`budget` is one of 30 | 60 | 100. `how_many` is 1 | 2 | 4 (meaning "a few").
`text` is the optional free-text fallback, routed through the DM router.

→ `{ "card_id": "c-8f2a1b", "ms": 620 }` — frontend then navigates to `/c/c-8f2a1b`.

---

## 5. `GET /api/card/{card_id}`  ← `/c/<id>`, the verdict card
**Re-decides on open.** No scheduler, no fake clock. `cached` may be true; `re_decided_at` is
always now.

```jsonc
{
  "cached": false, "ms": 610, "re_decided_at": "2026-09-20T09:14:02Z",
  "card_id": "c-8f2a1b", "parent_card_id": null,
  "asker": { "name": "@jessica", "said": "I already have the night serum. Do I need the barrier cream too?",
             "skin": ["normal"], "budget": 80, "owns": ["Night Serum"] },
  "verdict": { "headline": "No. Just the SPF.",
               "in_her_voice": "No. Just the SPF. Twenty-six pounds.",
               "is_refusal": true },
  "basket": [ { "product": "SPF 50", "price": "£26", "type": "SPF", "ref": "E-04.5",
                "maya_note": "Non-negotiable.", "affiliate": true, "why": "Her defended category." } ],
  "total": "£26",
  "unspent": { "amount": "£54", "line": "She left £54 of your £80 on the table." },
  "left_out": [ { "product": "Barrier Cream", "price": "£34",
                  "why": "You already have the night serum doing that job.",
                  "instead": "Nothing. Save it." } ],
  "ceiling": { "band": "about £50–55", "provenance": "Estimated from Maya's own posts — she sets the line",
               "evidence_ref": "E-04.6" },
  "money_line": { "affiliate_count": 1, "basket_value": "£26",
                  "note": "1 of 1 products is affiliate-linked." },
  "indifference_band": "Between £40 and £80 her answer does not change.",
  "og_image": "/api/card/c-8f2a1b/og.png",
  "share_url": "/c/c-8f2a1b"
}
```

### `POST /api/card/{card_id}/redecide`  ← "Do it for me instead"
Body: `{ "skin": ["oily"], "budget": 40, "owns": [] }`
→ full card payload of a **new child card** with `parent_card_id` set to the original.

### `GET /api/card/{card_id}/og.png`
1080×1350 PNG. Served with `Cache-Control: public, max-age=31536000`.
The frontend `/c/:id` page must render **the same component** the image is generated from.

---

## 6. `GET /api/onboard?handle=@mayarao`  ← `/onboard`
```jsonc
{ "cached": true, "ms": 670, "handle": "@mayarao",
  "heard": [ { "trait": "The fewest possible products",
               "caption": "my 5 minute morning routine. two products.",
               "evidence_ref": "E-03.5", "confidence": 0.94, "slot_key": "routine_size" } ],
  "accuracy": "89% correct against her documented self",
  "first_verdict_card_id": "c-8f2a1b" }
```

---

## 7. Errors
Every failure: HTTP 200 with `{ "error": "human sentence", "fallback": true, ...cached payload }`.
**Nothing on stage may render a 500.** If Jev is unreachable, serve the frozen cache and set
`"cached": true, "live": false`.

---

## 8. Cache
`cache/` — gitignored except the frozen demo set, which IS committed:
`cache/standard.json` · `cache/queue.json` · `cache/cards/<card_id>.json` · `cache/og/<card_id>.png`

`?live=1` on any GET bypasses the cache and runs real inference.
`python -m backend.warm` regenerates the whole frozen set. Run it before the demo.

---

## 9. Frozen demo card ids
These four must exist in the committed cache and must never 404:

| id | who | why it is in the demo |
|---|---|---|
| `c-jessica` | @jessica, owns Night Serum, £80 | Beat 1 — the cold-open refusal. "No. Just the SPF." |
| `c-sister`  | oily, £40 | Beat 7 — the forward. Child of `c-jessica`. |
| `c-mum`     | dry, £100 | Beat 7 — keeps £36 unspent. Child of `c-jessica`. |
| `c-priya`   | sensitive + redness, £80 | Fidelity proof — she must get Red Reset. |

---

## 10. `GET /api/extract`  ← the hero visual on `/onboard`
**Added after the freeze. Additive only — nothing above changed.**

The replay payload behind `docs/12-DESIGN-LIGHT.md` §5: watch Jev read her channel and
resolve her standard. `/api/standard` gives you the answers; this gives you the *act of
extraction* — what went into the prompt, what was asked, and what came back when.

### The honesty rule, and it is the point of this endpoint
Jev answers **all fourteen questions of a judge in one response**. There is **no genuine
per-slot arrival time**, so this payload does not contain one and never will. Every latency
here is **per REQUEST** and was measured on the wire. All fourteen slots of a request became
known at the same instant; that is the truth and it is what the wire says.
**The per-slot reveal in the browser is a replay and the UI must label it one.**
Per slot you get `confidence`. You never get `ms`. `scripts/check_contract.py` fails the
build if a per-slot time ever appears in the payload or in a stream event.

```jsonc
{
  "cached": false, "ms": 359, "live": true, "measured": true,
  "handle": "@mayarao",

  // every string that goes into HER prompt, in the order the state carries it:
  // the bio line, then the six post titles, then the eight captions. 15 entries.
  "corpus": [
    { "id": "post-E-03.1", "text": "3 things I would repurchase with £50",
      "evidence_ref": "E-03.1", "kind": "post", "verbatim": true,
      "views": 48000, "saves": 1900 },
    { "id": "c4", "text": "my 5 minute morning routine. two products. that is it. ...",
      "evidence_ref": "E-03.5", "kind": "caption", "verbatim": false }
  ],
  "corpus_note": "The six post titles are verbatim from the case pack ... the caption bodies and the bio line are a reconstruction ...",
  "derm_corpus": [ { "id": "d1", "text": "A complete daily routine is ...", "evidence_ref": null,
                     "kind": "guidance", "verbatim": false, "written_by_us": true } ],
  "derm_corpus_note": "The dermatologist's corpus is 100% written by us. It is the control, not evidence.",

  // the 28 lines the hero draws. `text` is the literal `instructions` string sent to Jev.
  "questions": [
    { "id": "q-maya-routine_size", "slot_key": "routine_size", "judge": "maya", "type": "score",
      "text": "Does this person favour the fewest possible products, or a complete multi-step routine?" }
  ],

  // one entry per REAL HTTP request. Two, because a judge's fourteen travel together —
  // that is why it is 0.65s and not fourteen round trips.
  "requests": [
    { "id": "r-maya", "judge": "maya", "question_count": 14,
      "question_ids": ["q-maya-routine_size", "..."], "slot_keys": ["routine_size", "..."],
      "at_ms": 0, "ms": 348, "input_tokens": 4134, "measured": true }
  ],

  // the resolved slots: /api/standard's shape, plus question_ids and request_ids.
  "slots": [
    { "key": "routine_size", "label": "How many products", "type": "score",
      "maya": { "level": "The fewest possible products", "value": 0.18, "confidence": 0.82 },
      "derm": { "level": "A small routine",              "value": 1.20, "confidence": 0.45 },
      "agrees": false,
      "source_caption": "my 5 minute morning routine. two products. that is it. ...",
      "evidence_ref": "E-03.5", "toggleable": true,
      "question_ids": ["q-maya-routine_size", "q-derm-routine_size"],
      "request_ids": ["r-maya", "r-derm"] }
  ],

  "totals": { "questions": 28, "requests": 2, "seconds": 0.35, "input_tokens": 7661,
              "agree": 11, "disagree": 3, "slot_count": 14 },
  "model": "jev-latest",                     // what was sent; the frozen file records jev-1.13.0
  "replay_note": "Jev answers all fourteen questions of a judge in ONE response, so there is no per-slot arrival time ...",
  "generated_by": "scripts/engine_decontaminated_v2.py"
}
```

`kind` is `caption` | `post` | `bio`. `verbatim` says whether that exact string is in the case
pack — the six post titles are, the caption bodies and the bio are our reconstruction
(`docs/11-honest-headline.md` §5.1). Say **"reconstructed from her posts"**, never "scraped".

`measured: true` means the timings and token counts in this payload came from a real run.
`?live=1` bypasses the cache and runs it for real; without it you get `cache/extract.json`,
which `python -m backend.warm` fills from a real run. When the cache is the *only* source and
no run has ever been recorded, `requests[].ms`, `requests[].at_ms`, `requests[].input_tokens`
and `totals.input_tokens` are **`null`** and `measured` is `false` — the shape of the fan-out
is still true, but a number we did not measure is null, never invented.

`agree` / `disagree` come out of the run that produced the payload. `skippable_category` is
unstable (`docs/11` §5.8), so 10/4 and 11/3 both occur. Do not hard-code either.

### `GET /api/extract/stream`
Server-sent events, `text/event-stream`. Runs the extraction for real and emits as it happens.
Both requests are fired before either is awaited, and `asyncio.as_completed` means events land
in genuine completion order — whichever judge comes back first is the one you see first.

| event | data |
|---|---|
| `corpus`   | `{ corpus, corpus_note, derm_corpus, derm_corpus_note, questions, replay_note, at_ms }` — immediately, before anything is fired |
| `dispatch` | `{ request_id, judge, question_ids, question_count, at_ms }` — a request was **actually fired**, `at_ms` after stream start |
| `resolved` | `{ request_id, judge, slot_keys, ms, input_tokens, dispatched_at_ms, at_ms, cached }` — that request **genuinely came back**; `ms` is its wire time |
| `slot`     | `{ request_id, judge, slot_key, label, type, level, value, confidence, source_caption, evidence_ref, question_id, at_ms, cached }` — one per slot |
| `done`     | `{ totals, cached, live, ms, measured, replay_note }`, plus `error` / `error_detail` / `fallback` if it fell back |

Every `slot` of a request carries **that request's** `at_ms` — they all arrived together, in one
response. That repetition is not a bug; it is the honest shape of the data, and it is why the
frontend owes the viewer a `REPLAY` label and a speed control.

A typical run: `corpus` → `dispatch` ×2 → `resolved` → `slot` ×14 → `resolved` → `slot` ×14 → `done`.
34 events.

### When Jev is unreachable
`/api/extract` returns **200** with the frozen extraction, `"cached": true, "live": false,
"fallback": true` and an `error_detail`. The stream emits the same event sequence from the cache:
`resolved` and `slot` carry `"cached": true` and `ms` / `at_ms` **`null`** rather than a made-up
number, and `done` carries `"cached": true`. Verified against a bogus `JEV_API_KEY`: both
endpoints 200, full sequence, no fabricated timing. Nothing here renders a 500.

`cache/extract.json` joins the committed frozen demo set (§8) and is written by
`python -m backend.warm`.

---

## 11. `GET /api/creators` ← the subject list

**Added after the freeze. Additive: nothing above changed.**

Proof that the engine is not hardcoded to a fictional creator. It lists every subject the
same fourteen slots can be run against: the case-pack creator plus every real corpus in
`data/corpus-*.json`.

```jsonc
{
  "cached": true, "ms": 2, "live": false,
  "count": 2, "real_count": 1, "slot_count": 14,
  "creators": [
    { "slug": "maya", "handle": "@mayarao", "display_name": "Maya Rao",
      "what_she_is": "Beauty creator, London. The case-pack creator this engine was built for.",
      "source": "case-pack", "source_url": null, "fetched_at": null,
      "item_count": 15, "char_count": 998,
      "why_this_creator": "The case pack. ...",
      "real": false, "verbatim": false,
      "provenance": "Ours, partly. The six post titles are verbatim from the case pack ...",
      "corpus_file": "data/case-001-maya.json",
      "cached_extraction": true, "extract_url": "/api/extract?subject=maya" },

    { "slug": "labmuffin", "handle": "@labmuffinbeautyscience", "display_name": "Michelle Wong",
      "what_she_is": "Cosmetic chemist, PhD. Writes Lab Muffin Beauty Science.",
      "source": "rss", "source_url": "https://labmuffin.com/feed/",
      "fetched_at": "2026-09-20T13:42:37+00:00",
      "item_count": 10, "char_count": 57015,
      "why_this_creator": "Chosen as a real-world match for Maya: sceptical of hype, heavy on sunscreen ...",
      "cleaning_note": "Repeated site boilerplate (affiliate disclosure, citation block, nav, footer) stripped before extraction. Her actual prose is untouched.",
      "real": true, "verbatim": true,
      "provenance": "Real. Her own public writing, verbatim, fetched from https://labmuffin.com/feed/ on 2026-09-20. Not written by us.",
      "corpus_file": "data/corpus-labmuffin.json",
      "cached_extraction": true, "extract_url": "/api/extract?subject=labmuffin" }
  ],
  "control": { "slug": "derm", "display_name": "A board-certified dermatologist",
               "real": false, "provenance": "Ours, entirely. Twelve statements ..." }
}
```

`real` is the field that matters and it is not decoration. **`real: true` means every word in
that corpus is that person's own public writing, fetched verbatim.** `real: false` means the
words are ours — Maya's caption bodies are a reconstruction (`docs/11` §5.1) and the
dermatologist is written by us end to end (`docs/11` §5.2). A judge should be able to tell
which subject is a real human being from this payload alone, without reading any docs.
`provenance` says the same thing in one sentence, and names the URL and the date.

The **corpus fetch is prefetched and committed** — `scripts/fetch_corpus.py`, run by hand,
before the demo, never at request time. It is slow and network-fragile (Instagram returns 429
on the first logged-out request from a residential IP, and worse from datacenter ranges —
`scripts/probe_modal_ip.py` is the measurement). **The extraction is what runs live**, and
that is the number on screen, so the timing is genuinely real.

The control (`derm`) is deliberately not in `creators`. It is not a subject you choose; it is
the same yardstick every subject is measured against.

---

## 12. `GET /api/extract?subject=<slug>` ← the same fourteen questions, a different person

**Added after the freeze. `GET /api/extract` with no `subject` is byte-for-byte what §10
specifies and is verified as such in `scripts/check_contract.py`.** `subject=maya` is a synonym
for omitting it.

Any other slug from `/api/creators` runs the **same fourteen typed slots** — the same
`instructions`, the same `criteria`, the same `shelf` in `state` — against that subject's
`public_profile`, alongside the same dermatologist control. Two requests, fourteen questions
each, exactly as §10.

The payload is §10's shape, with the subject's own side keyed **`subject`** instead of `maya`,
plus the provenance block:

```jsonc
{
  "cached": true, "ms": 10, "live": false, "measured": true,
  "subject": "labmuffin", "handle": "@labmuffinbeautyscience",
  "display_name": "Michelle Wong",
  "what_she_is": "Cosmetic chemist, PhD. Writes Lab Muffin Beauty Science.",
  "real": true,
  "provenance": "Real. Her own public writing, verbatim, fetched from https://labmuffin.com/feed/ on 2026-09-20. Not written by us.",
  "source": "rss", "source_url": "https://labmuffin.com/feed/",
  "fetched_at": "2026-09-20T13:42:37+00:00",

  // her corpus. every item says where it came from and when we took it.
  "corpus": [
    { "id": "labmuffin-01", "kind": "post",
      "text": "Why are skin cancer rates rising with more sunscreen? ...",
      "verbatim": true, "source_url": "https://labmuffin.com/sunscreen-isnt-preventing-cancer/",
      "published": "Tue, 07 Jul 2026 11:44:04 +0000", "fetched_at": "2026-09-20T13:42:37+00:00",
      "evidence_ref": null, "chars": 5707 }
  ],
  "corpus_note": "Repeated site boilerplate ... stripped before extraction. Her actual prose is untouched.",
  "caption_note": "This subject's slots carry no per-slot caption. Maya's do, because the case pack pins each slot to a post and we wrote that mapping by hand ...",

  "derm_corpus": [ "..." ], "derm_corpus_note": "... 100% written by us ...",
  "derm_provenance": "Ours, entirely. ...",

  "questions": [ { "id": "q-labmuffin-routine_size", "slot_key": "routine_size",
                   "judge": "labmuffin", "type": "score",
                   "text": "Does this person favour the fewest possible products, or a complete multi-step routine?" } ],
  "requests":  [ { "id": "r-labmuffin", "judge": "labmuffin", "question_count": 14,
                   "at_ms": 0, "ms": 487, "input_tokens": 17037, "measured": true },
                 { "id": "r-derm", "judge": "derm", "question_count": 14,
                   "at_ms": 1, "ms": 266, "input_tokens": 3527, "measured": true } ],
  "slots": [
    { "key": "price_refusal", "label": "Price", "type": "score",
      "subject": { "level": "Mentions price occasionally", "value": 0.72, "confidence": 0.44 },
      "derm":    { "level": "Mentions price occasionally", "value": 1.04, "confidence": 0.95 },
      "agrees": true,
      "source_caption": null, "evidence_ref": null, "toggleable": true,
      "question_ids": ["q-labmuffin-price_refusal", "q-derm-price_refusal"],
      "request_ids": ["r-labmuffin", "r-derm"] }
  ],
  "totals": { "questions": 28, "requests": 2, "seconds": 0.49, "input_tokens": 20564,
              "agree": 9, "disagree": 5, "slot_count": 14 }
}
```

### The symmetry rule, and it is the whole methodological claim

**The fourteen questions are byte-identical for every subject.** Same `instructions`, same
`criteria`, same order, same `shelf` in `state`; only `public_profile` differs. This is
*asserted*, not intended: `engine.assert_question_symmetry()` runs inside every
`extract_plan()` and raises `QuestionDrift` — uncaught, deliberately — if the serialised
question block or the slot order ever differs from the canonical fourteen, or if the same slot
is asked with different words of different judges. `scripts/check_contract.py` checks the same
thing from the wire, comparing `questions[].text` per `slot_key` across subjects. Different
values, same questions. If that ever stops being true, every comparison in this product is
meaningless and it is better to fall over loudly.

### `source_caption` is `null` for a fetched corpus, on purpose

Maya's slots quote a caption because the case pack pins each slot to a post and **we wrote
that mapping by hand** (`SLOT_META`). There is no such mapping for a real corpus. Jev reads all
57,015 characters in one request and does not report which sentence moved which slot, so
picking a quote by keyword would be our guess wearing the costume of evidence. The field is
`null` and `caption_note` says why. The full corpus is in `corpus` and anyone can read it.

`?live=1` bypasses the cache and really runs it; without it you get
`cache/extract-<slug>.json`, written by `python -m backend.warm`. `live` is never true for a
cached payload. If there is no cache and Jev is unreachable, the scaffold comes back — the
corpus, the fourteen questions, the two requests — with **every value and timing null**, an
`error`, and `measured: false`. An unknown slug returns **200** with an `error`, an empty
`slots` list and `known_subjects`.

---

## 13. `GET /api/compare?a=maya&b=labmuffin` ← two standards, side by side

**Added after the freeze.** Runs both subjects (from cache unless `?live=1`) and aligns them
slot by slot. `b` defaults to the first non-`a` subject. Uses the same `levels_agree()` the
extraction itself uses, so the table can never disagree with the payloads it was built from.

```jsonc
{
  "cached": true, "ms": 25, "live": false,
  "a": "maya", "b": "labmuffin",
  "headline": "Same fourteen questions, asked of Maya Rao and Michelle Wong. They agree on nine and disagree on five.",
  "questions_identical": true,             // asserted in extract_plan(), not assumed
  "subjects": [
    { "slug": "maya", "display_name": "Maya Rao", "real": false,
      "provenance": "Ours, partly. ...",
      "seconds": 0.27, "input_tokens": 7661, "measured": true, "live": false },
    { "slug": "labmuffin", "display_name": "Michelle Wong", "real": true,
      "provenance": "Real. Her own public writing, verbatim, fetched from https://labmuffin.com/feed/ on 2026-09-20. Not written by us.",
      "seconds": 0.49, "input_tokens": 20564, "measured": true, "live": false }
  ],
  "slots": [
    { "key": "price_refusal", "label": "Price", "type": "score",
      "question_text": "How willing is this person to say something is good but not worth its price?",
      "a": { "level": "Price is central to their judgement", "value": 2.74, "confidence": 0.74 },
      "b": { "level": "Mentions price occasionally",         "value": 0.72, "confidence": 0.44 },
      "agrees": false,
      "a_agrees_with_derm": false, "b_agrees_with_derm": true,
      "a_source_caption": "the 62 pound serum everyone is posting. it is good. it is not 62 pounds good.",
      "b_source_caption": null,
      "question_ids": ["q-maya-price_refusal", "q-labmuffin-price_refusal"] }
  ],
  "agree_count": 9, "disagree_count": 5,
  "totals": { "slot_count": 14, "agree": 9, "disagree": 5,
              "questions": 56, "requests": 4, "input_tokens": 28225, "seconds": 0.49,
              "a": { "subject": "maya", "seconds": 0.27, "input_tokens": 7661,
                     "measured": true, "live": false, "cached": true },
              "b": { "subject": "labmuffin", "seconds": 0.49, "input_tokens": 20564,
                     "measured": true, "live": false, "cached": true } },
  "note": "The fourteen questions are byte-identical for both subjects ... `seconds` is the slower of the two runs, not their sum: they were two separate fan-outs."
}
```

`totals.seconds` is the **slower of the two runs, not their sum** — they are two independent
fan-outs and adding them would overstate the cost. `a_agrees_with_derm` / `b_agrees_with_derm`
are each subject's own agreement with the shared control, carried through so the table can show
all three columns without a third request.

`?live=1` runs both for real, concurrently. `live` at the envelope is true only when **both**
sides ran live; if either fell back, `cached` is true and `error` / `fallback` are set. No
per-slot timings anywhere, here or in §12 — Jev answers a whole request at once and this
product does not invent a number it did not measure.

### When Jev is unreachable
Verified against a bogus `JEV_API_KEY`: `/api/creators`, `/api/extract?subject=<slug>`
(with and without `live=1`) and `/api/compare` (with and without `live=1`) all return **200**
from `cache/extract-<slug>.json` with `"live": false, "cached": true` and, where a live run was
attempted, `"fallback": true` plus an `error_detail`. Nothing renders a 500.

`cache/extract-labmuffin.json` joins the committed frozen demo set (§8) and is written by
`python -m backend.warm` alongside `cache/extract.json`.

---

## 14. Measured: Maya vs Michelle Wong, 2026-09-20

The run behind §13, `jev-latest`, from `cache/extract-labmuffin.json`. Fourteen questions,
byte-identical on both wires. **Values differ; questions do not.**

| Slot | Maya Rao (ours, reconstructed) | Michelle Wong (real, verbatim) | |
|---|---|---|---|
| routine_size | The fewest possible products `0.77` | A moderate routine `0.30` | ✗ |
| budget_behaviour | NO `0.76` | NO `0.66` | = |
| **price_refusal** | **Price is central to their judgement** `0.74` | **Mentions price occasionally** `0.44` | ✗ |
| subtraction | YES `0.73` | NO `0.76` | ✗ |
| hype | Actively sceptical of hype `0.98` | Actively sceptical of hype `0.94` | = |
| defended_category | spf `1.00` | spf `0.87` | = |
| interchangeable_category | cleanser `0.99` | cleanser `0.33` | = |
| skippable_category | serum `0.42` | makeup `0.42` | ✗ |
| starting_from_zero | Three - a short but complete routine `0.54` | Three - a short but complete routine `0.02` | = |
| subtraction_scope | crowded_routine_only `1.00` | never `0.60` | ✗ |
| route_reacting | Red Reset `0.32` | Red Reset `0.45` | = |
| route_redness | Red Reset `1.00` | Red Reset `1.00` | = |
| route_dry | Cloud Cream `1.00` | Cloud Cream `1.00` | = |
| route_oily | Daily Gel `0.84` | Daily Gel `0.82` | = |

**Nine agree, five disagree.** Measured: **0.49 s – 1.04 s** per extraction (two parallel
requests), **20,564 input tokens** for Michelle Wong's run (17,037 of them her 57,015
characters of prose) against **7,661** for Maya's. Stable: fourteen of fourteen slots returned
the same level across three consecutive live runs.

Read it honestly. `price_refusal` is the headline — she is science-led, not price-led, which is
exactly what `why_this_creator` predicted before the run. But `price_refusal 0.44`,
`interchangeable_category 0.33` and `starting_from_zero 0.02` are **low-confidence** answers on
a corpus that barely discusses shopping, and `subtraction_scope: never` is the extractor
correctly reporting that a chemist writing about UV filters does not tell anyone to throw
products away. Do not present the low-confidence rows as findings. The four route_* slots agree
with Maya because both are being asked to pick from **Maya's shelf**, which is the price of
keeping the questions identical, and it should be said out loud rather than read as independent
corroboration.

---

## 15. Her pictures — `image_count` and `corpus[].images`

**Added after the freeze. Additive: nothing above changed, no endpoint changed shape, and the
fourteen questions are byte-identical with and without images (`assert_question_symmetry()`
passes for `maya`, `derm` and `labmuffin`, both ways).**

A real corpus is not only text. `scripts/enrich_images.py` re-opens each post, pulls the
images that were **already in that page's HTML** (`og:image` plus in-article `<img>` over
200px, avatars / logos / tracking pixels / lazy-load placeholders skipped, capped at 2 per
post and 15 in total), and writes typed attributes back into `data/corpus-<slug>.json`.

### Who did what — say this, do not blur it

> **GPT-4o-mini reads the pictures. Jev judges the attributes. Jev never sees a pixel.**

That is the house pattern — an LLM writes, Jev decides, code acts — and the wire carries the
evidence: `vision_model` is on the creator row, on every image and inside `public_profile`,
and every image also carries a `read_by` string saying it in words. **Nothing in any payload
may imply Jev did the seeing.**

### `GET /api/creators` — new fields on a corpus row

```jsonc
{ "slug": "labmuffin",
  "image_count": 15,                        // pictures we actually READ. The number the UI may say.
  "image_candidate_count": 15,              // pictures we selected (read or failed)
  "vision_model": "gpt-4o-mini",
  "vision_enriched_at": "2026-09-20T14:13:30+00:00",
  "vision_note": "The images are read by gpt-4o-mini under a strict json_schema, not by Jev. ...",
  "images_in_state": true }                 // false if CORPUS_IMAGES=0 for the A/B
```

`maya` carries none of these keys: her corpus has never been through the enrichment. **A
missing `image_count` means "we never looked", not "zero".** So
*"10 posts and 15 pictures"* is a sentence the frontend may print for `labmuffin` and may not
print for `maya`.

### `GET /api/extract?subject=<slug>` — `corpus[].images`

Each corpus item gains an `images` array. The URL is **hers, on her server** — we reference
the original and never download or re-host it, so a thumbnail in the UI is a hotlink to the
picture she published.

```jsonc
"images": [
  { "url": "https://labmuffin.com/wp-content/uploads/2025/05/melanoma-mariam-correlation.jpg",
    "width_hint": 1200, "height_hint": 757,
    "alt": "melanoma mariam correlation",
    "found_in": "og:image",                 // "og:image" | "article"
    "source_page": "https://labmuffin.com/sunscreen-isnt-preventing-cancer/",
    "vision_model": "gpt-4o-mini",
    "read_by": "gpt-4o-mini vision, under a strict json_schema. Not Jev - Jev judges these attributes, it does not see the picture.",
    "seen_at": "2026-09-20T14:12:27+00:00",
    "vision": {
      "shows": "chart",                     // product|demo|diagram|chart|person|packaging|screenshot|other
      "readable_text": "New cases of melanoma in the US correlates with Popularity of the first name Mariam ...",
      "products_named": [],
      "is_instructional": "no",             // yes|no|unclear
      "is_comparison": "yes",
      "shows_a_result": "yes" } }
]
```

Every field is settleable by a human opening `url` and looking. **A picture we could not fetch
or could not read is `"vision": null` with an `"error"` string — never a guess.**

### In `state.public_profile`

`backend/corpora.py` adds `what_her_pictures_show` — a list of the same typed rows plus
`image_url` and `in_post` — and the scalar `pictures_read_by`. **Structured, not prose**:
prose measurably does not fire (`docs/09-GO.md` §5 bug #3). Her captions are byte-identical
with and without it, so the toggle isolates the images and nothing else.

### Measured: do the pictures change the answers? Mostly no — say so

`CORPUS_IMAGES=0` runs the extraction without them. 5 repeats each side, `labmuffin`,
2026-09-20:

| | without images | with images |
|---|---|---|
| input tokens | 20,564 | 22,832 (+2,268, +11%) |
| slot levels changed | — | **2 of 14** |

The two that moved are `interchangeable_category` (cleanser → spf) and `skippable_category`
(makeup → serum). **Both are the lowest-confidence slots on the board** — 0.34 and 0.43 with
images, 0.36 and 0.51 without, against a ~0.33 floor — and `docs/11-honest-headline.md` §5.8
already rules `skippable_category` off the slide for instability. **The twelve slots anyone
would actually quote did not move at all.** One consistent non-level change: `subtraction_scope`
held `never` 5/5 both ways but its confidence rose 0.62 → 0.76.

**The honest claim is therefore about what we READ, not about what it changed:** we parse her
posts *and* her images, the image attributes are on the wire and checkable against the
photographs, and on this corpus they do not move any answer a judge should believe. Do not
claim the pictures changed her extracted standard.

### It is a prefetch, like the corpus fetch

`scripts/enrich_images.py` runs by hand before the demo. **Nothing in `backend/` calls it** —
`backend/corpora.py` only ever reads what it wrote. It is idempotent: an image with a `vision`
block is skipped, a post whose images are all read is not even re-fetched, raw responses are
cached in `cache/vision/<sha1 of url>.json`, and a second run makes zero network calls, costs
$0.00 and leaves the corpus file byte-identical.

---

## 16. `GET /api/queue` — the gap probe (additive, 2026-09-20)

**It only asks when the answer actually depends on it.**

Until now a DM bounced a question back when something was *missing* (no skin type, no
budget, no count). That is the wrong test. The right test is whether the missing thing
**changes what she would send**. So before a message is allowed to ask anything, every
plausible value of every gap is run through the same two-stage basket and the winners
are compared. Same winner everywhere → the question is pointless, answer it. Different
winners → ask, and ask the gap that actually discriminates.

This is `indifference_band` (section 5, "between £40 and £80 her answer does not
change") moved off money and onto intake. **No existing field changed type or
meaning; everything below is new and nullable.**

### New on `stats`

```jsonc
"answer_rate_pct": 48,
"gap_probe": {
  "claim": "It only asks when the answer actually depends on it.",
  "messages_probed": 9,        // asked_back messages that could have had a basket
  "variants_run": 78,          // two-stage baskets run to find out
  "answered_despite_gap": 0,   // messages answered because the gap turned out moot
  "answered_despite_gap_ids": [],
  "gaps_tested": 18,           // (message, gap) pairs actually simulated
  "gaps_that_did_not_matter": 2,
  "still_asked": 9,
  "question_chosen_by_probe": 6,
  "note": "..."
},
// ADDITIVE NOTE (answer-quality pass). `question_chosen_by_probe` counts the
// asked_back cards where the probe measured a discriminating gap AND that gap's
// question is the one actually on the card. Maya's own routing
// (`decision_rules.routing`) now outranks the probe for the `what_is_it` and
// `diagnose_me` jobs, so on the 54-DM corpus this reads 6 of 9, not 9 of 9.
// No key was added or removed and no other field moved.
"safety": {
  "referred": 8,
  "by_signal": { "out_of_scope": 7, "refusal_reason": 1, "both": 0 },
  "rule": "..."
},
"gates": { ..., "refusal_reason_gate": 0.9 }
```

### New on `cards[]`

```jsonc
"answered_despite_gap": false,   // bool. true only in the answered lane
"gap_closed": null,              // "budget didn't matter here" — set only when the above is true
"gap_probe": {                   // null when the message was never probed
  "gaps": ["skin", "budget"],    // detected gaps: skin | budget | count | owns
  "tested": {
    "skin":   { "tested": true, "distinct": 5, "mattered": true,
                "values": ["dry","oily","combination","sensitive","redness"] },
    "budget": { "tested": true, "distinct": 1, "mattered": false, "values": [30,60,100] }
  },
  "variants": [ { "gap": null, "value": null, "basket": ["Soft Clean"] },
                { "gap": "skin", "value": "dry", "basket": ["Cloud Cream"] } ],
  "variants_run": 9,
  "indifferent": false,
  "gaps_that_did_not_matter": ["budget"],
  "discriminating_gap": "skin",  // the gap whose hypotheses produced the most different baskets
  "incomplete": false,
  "rule": "..."
}
```

`variants[0]` is always the baseline — the shopper exactly as the message described
them, with the gap left empty. `distinct` counts the different winning baskets across
that gap's **hypotheses only**, so `distinct == 1` means the gap provably did not move
her answer. The baseline is deliberately excluded from that count: "not stated" is the
absence of a value, not a plausible value of it, and its basket is the engine's best
guess in the dark. When every hypothesis agrees, the basket that goes out is **the one
they agreed on**, not the guess.

When `lane` is `asked_back` and `gap_probe` is present, `question_back` is the intake
question that closes `discriminating_gap`, not Jev's `which_question_back` pick.

### The three rules that keep it honest, all enforced by `scripts/check_contract.py`

1. A gap that was **not simulated** — not probeable, or it would not fit the per-message
   variant cap — always reports `mattered: true`. A capped probe can conclude "ask"; it
   can never conclude "answer".
2. A probe with `incomplete: true` (a hypothesis that did not come back) is never
   indifferent.
3. The probe can only ever move `asked_back` → `answered`. It cannot reach `referred`
   or `held`, so **no safety refusal can be argued away by an indifference result** and
   no confidence gate is involved.

### The second safety signal (`refusal.signal`)

`refusal` now also carries `reason_code`, `signal` (`out_of_scope` | `refusal_reason` |
`both`) and `signal_strength`.

A message is out of scope if `out_of_scope > 0.5` **OR** `refusal_reason` names a
clinical reason at `refusal_reason_gate` (0.90) or better. This is an OR: it can add a
referral, never remove one.

It exists because `out_of_scope` is a single prior and on one message it is a coin flip.
Measured over five identical triage runs, q-046 (*"i had a bad reaction to something,
red and peeling, what do i do"*) came back 0.48 / 0.48 / 0.51 / 0.50 / 0.50 — referred
once, answered four times. `refusal_reason` reads the same question a different way and
is not marginal: `adverse_reaction` at 0.96 in every run, while every message that is
safely hers returns `none` at 0.94+. Over six fresh runs the OR refers 8/8 with all
seven planted medical traps caught every time, and adds no other message.
`refusal_reason_gate` is not derived from her standard and `POST /api/standard/override`
cannot move it — safety is not a slider.

---

## 17. Voice notes — `source: "voice"` and `GET /api/voice` (additive, 2026-09-20)

Her audience sends voice notes. The case pack says so: `voice._source` is
*"E-06.1 voice note (00:52)"*. Four of them are now in the overnight queue.

### The audio is SYNTHETIC and says so in five places

We have no real audience audio and we did not collect any. These four were **spoken by
OpenAI `tts-1`** from scripts we wrote, in four different voices, by
`scripts/transcribe_voice.py --speak`. The label travels with the bytes:

1. the filename — `synthetic-v-003-alloy.mp3`
2. an **ID3v2.3 tag inside the mp3** (`TIT2` "SYNTHETIC demo voice note v-003", `TPE1`
   "OpenAI tts-1 … not a real person", a `COMM` disclosure frame), so it survives the
   file being downloaded on its own
3. `data/voice-notes.json` — `synthetic: true`, `tts_model`, `_comment`
4. the queue card — `voice.synthetic`, `voice.disclosure`, `voice.tts_model`
5. the HTTP response — `X-Synthetic-Audio: true`, `X-Audio-Source`

### Who did what — the same split as the pictures

> **OpenAI transcribes the audio. Jev decides what to do about it.**

`whisper-1` with `response_format=verbose_json`. `seconds` is the duration **the API
reported**, not a constant; `transcribe_ms` is measured around the call. Jev never
receives a waveform — it receives the transcript in `state.message`, the identical
field a typed DM occupies.

### It is not a special lane

A voice note is a message whose text arrived differently. `engine.voice_dms()` puts the
transcript in `text`; `dm_corpus()` appends them; `run_triage()` is handed
`[d["text"] for d in dms]`. **Nothing between the transcript and the reply reads
`source`** — same questions, same `confidence_gate`, same `enough_gate`, same safety
OR in `refers_out()`. `source` and `voice` are labels written onto the finished card.

Measured, one triage fan-out — 4 messages / 72 judgments in **0.87s** — and one basket
fan-out of 0.61s:

| id | audio | lane | job | outcome |
|----|-------|------|-----|---------|
| `v-001` | 6.93s | `answered` | `pick_for_me` | Red Reset £32 + SPF 50 £26, £58 |
| `v-002` | 4.63s | `answered` | `is_it_worth_it` | "Good. Not £62 good. Her line on it is about £40–45." |
| `v-003` | 6.19s | **`referred`** | — | `pregnancy_or_nursing` at 1.0, signal `both` → **a pharmacist or your GP** |
| `v-004` | 5.18s | `held` | `not_a_question` | "Thank you. Genuinely. Nothing to buy today." |

Two of these sit near a gate and move between runs, and that is the pipeline behaving
the same way it does for typed DMs, not something voice introduced. `v-004` ("you're
the only person I trust on this stuff") lands either side of `emotional_gate` — it is
the message the hold lane exists for. `v-001` says "about 60 quid", which is exactly the
`30_to_60` / `60_to_100` band boundary, and Jev splits 0.50 / 0.50 on it; the basket is
£58 or £96 depending which way it falls. The refusal does not move: `v-003` has come
back `referred` at 1.0 on every run.

`scripts/check_contract.py` enforces this: the pregnancy trap matches `v-003` by its
transcript and the run fails if it is not `referred`.

### New on `cards[]`

| field | type | meaning |
|---|---|---|
| `source` | `"text"` \| `"voice"` | how the message arrived. A label, never a gate input. |
| `voice` | object \| `null` | non-null only when `source == "voice"` |

`voice` carries `audio_url` (`/api/voice/<file>`), `file`, `seconds`, `transcript`,
`stt_model`, `transcribe_ms`, `tts_model`, `tts_voice`, `tts_script` (what we asked the
TTS to read, so transcription accuracy is checkable on the wire), `verbatim_match`,
`synthetic`, `disclosure`, `who_did_what`.

Voice refs are `S-VN.1`…`S-VN.4`. `S-` marks evidence that is ours, not the case pack's.

### `GET /api/voice`

The manifest: `{synthetic, disclosure, who_did_what, tts_model, stt_model, built_at,
count, notes[]}`. `notes[]` is `data/voice-notes.json` verbatim — `{file, audio_url,
seconds, transcript, model, transcribe_ms, synthetic, voice, tts_script, usd, sha256}`.

### `GET /api/voice/{name}`

Serves `data/voice/<name>`. **Static, cached, no inference** — a file read and nothing
else. `Cache-Control: public, max-age=31536000, immutable`, `Content-Type: audio/mpeg`,
plus the two disclosure headers. An unknown or traversing name returns a named JSON 404
listing what is available; a readable file that fails to open returns 200 with
`fallback: true`. Never a 500, never a stack trace.

### It is a prefetch, like the corpus fetch and the image enrichment

Nothing in `backend/` calls OpenAI for this. `scripts/transcribe_voice.py` runs by hand
before the demo and caches every transcript under `cache/voice/<sha256 of the audio>.json`,
so a re-run makes **zero API calls, costs $0.00 and leaves `data/voice-notes.json`
byte-identical**. Measured first run: TTS $0.00536, transcription $0.00229 for 22.93s of
audio. Second run: $0.00000.

`--route` merges the four into `cache/queue-judgments.json` in their own fan-out and
re-assembles `cache/queue.json`, so the other 50 DMs are never re-run.

---

## 18. Cost (additive, 2026-09-20)

Nothing in sections 1–17 changed shape. This section records what each operation
costs, what was cut, and the two response fields the cuts added.

### New on `GET /api/card/{card_id}`

Two additive, optional objects. A client that ignores both sees exactly the payload
section 5 describes.

```jsonc
"frozen": {                 // present ONLY on the four ids in section 9
  "read_only": true,
  "decided_at": "2026-09-20T15:31:02Z",
  "why": "…served from the warmed cache so the demo says the same words twice."
},
"memo": {                   // present ONLY on a within-TTL repeat open
  "hit": true,
  "age_seconds": 41,
  "ttl_seconds": 600,
  "decided_at": "2026-09-20T15:31:02Z",
  "note": "…"
}
```

**The four frozen ids are read-only.** `c-jessica`, `c-priya`, `c-sister` and `c-mum`
are served from `cache/cards/*.json` and are not re-decided on open. The basket is a
live two-stage judgement and it is not deterministic — `c-jessica` has come back
*"Not that. The SPF and the cleanser. £48"* where beat 1 of the demo says *"No. Just
the SPF. £26."* So a page view can no longer rewrite the cold open. They carry
`cached: true, live: false, frozen.read_only: true`. To re-decide one, pass `?live=1`
or run `python -m backend.warm cards`; both write the new decision back to disk.

**Every other card gets a 10-minute memo.** "Re-decide on open" is unchanged as a
behaviour: the first open genuinely re-runs the two-stage basket. Repeat opens inside
10 minutes serve that same decision with `cached: true, live: false, memo.hit: true`.
The memo is **in-process**, so `python -m backend.warm` cannot seed it and the first
open after a backend restart is always a real re-decide. `?live=1` always re-decides.
`POST /api/ask` and `/redecide` seed the memo for the id they mint, so the client's
immediate `GET` of that id does not pay for the identical decision twice.

### Removed from `GET /api/queue.cards[]`

`urgency` (a float, undocumented, never asserted, never rendered). It was a Jev
`score` question asked on every DM and read by nothing. Removed with the question.
`wants_verdict_not_facts` was asked on every DM too and never reached the payload at
all. Eighteen triage questions now, not twenty; every remaining id is read by name in
`backend/engine.py`.

### `GET /api/queue.stats.gap_probe` — the probe is OFF by default

Every field in section 16 is unchanged and every honesty rule still holds. What
changed is the default: `gap_cap` is `0`, so `messages_probed` is `0`, `variants_run`
is `0`, and every card carries `gap_probe: null` and `answered_despite_gap: false` —
which is what the 45 unprobed messages already carried. Measured on the 54-DM corpus:
the probe ran 78 extra basket hypotheses, moved **zero** messages into the answered
lane, and changed the wording of **2** ask-backs. Turn it back on to reproduce:

```
GAP_PROBE_MESSAGES=20 python -m backend.warm queue
```

### Measured cost per operation

Requests are exact. Input tokens are the figures Jev returned in `usage.input_tokens`
where an operation was run live, and otherwise a `tiktoken` estimate calibrated on
those returns (`1.0668 × cl100k(body) + 693`, within 1.2% on every measured request).

| operation | before | after | cut |
|---|---|---|---|
| one queue warm (54 DMs) | 255 req / 1,058,268 tok | 80 req / 309,570 tok | **3.42×** |
| one Maya extraction | 2 req / 7,661 tok | 2 req / 7,661 tok | 1.00× |
| one Michelle Wong extraction | 2 req / 22,832 tok | 2 req / 16,473 tok | **1.39×** |
| the standard, inside a warm | 2 req / 2,773 tok | 0 req / 0 tok | discarded work, deleted |
| one card open, four frozen ids | 3 req / ~13,000 tok | 0 req / 0 tok | free |
| one card open, repeat inside 10 min | 3 req / ~13,000 tok | 0 req / 0 tok | free |
| one card open, first in the window | 3 req / ~13,000 tok | 3 req / ~13,000 tok | 1.00× |
| one `POST /api/ask` (free text) | 4 req / 14,592 tok | 4 req / 14,451 tok | 1.01× |
| `python scripts/check_contract.py` | 23 req / 87,560 tok | 9 req / 30,277 tok | **2.89×** |
| **one full `python -m backend.warm`** | **273 req / 1,143,819 tok** | **96 req / 385,989 tok** | **2.96×** |

One full refresh, step by step, and every step is runnable on its own:

| command | requests | input tokens |
|---|---|---|
| `python -m backend.warm standard extract` | 4 | 24,134 |
| `python -m backend.warm queue` | 80 | 309,570 |
| `python -m backend.warm cards` | 12 | 52,285 |
| `python -m backend.warm` (all of the above) | **96** | **385,989** |

`scripts/check_contract.py` no longer re-mints the four frozen cards, asserts that
opening them costs zero Jev requests, and deletes the two throwaway ids it does mint,
so a contract run leaves `cache/cards/` holding exactly the four frozen cards.
