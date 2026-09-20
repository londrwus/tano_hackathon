# Backend architecture

Python 3.12 + FastAPI. **No Docker.** This design is concept-independent — it is the machinery any
of our candidate products needs, so it can be built while the product shape is still settling.

---

## Shape

```
backend/
  main.py            FastAPI app — thin. Routes only.
  jev.py             The Jev client. The only file that talks to api.typesafe.ai.
  cases.py           Case-pack loader (data/case-00X-*.json) + validation
  questions.py       Question builders — the prompt layer, kept in ONE place
  engine.py          Composition: builds batches, runs them, shapes the matrix
  cache.py           Disk cache keyed by content hash
  .env               keys, gitignored
data/
  case-001-maya.json  case-002-sofia.json  case-003-aditi.json
cache/
  matrix-<hash>.json  precomputed results
scripts/
  eval_judgement.py   regression gate — run after ANY prompt change
```

Five small modules. Resist adding a sixth.

---

## The one non-obvious design decision

**Separate the judgement layer from the policy layer.**

Jev returns raw calibrated probabilities. *Nothing* in `jev.py` or `questions.py` should decide what
counts as "recommended", what the threshold is, or how dimensions combine. That belongs in
`engine.py` and, better still, in the frontend.

Why this matters for the demo: it is the `composite-scoring` pattern from the TypeSafe docs, and it
buys us **instant interactivity with zero inference**. Judgments are cached once; a slider that
changes "how much does budget matter?" re-ranks 3,000 cached judgments in JavaScript at 60fps.

> Changing a weight or a display filter must never re-run inference. If a slider triggers an API
> call, we have built it wrong.

It also lets us answer the sharpest question a technical judge can ask — *"isn't this just an LLM
call?"* — by showing a live control that re-weights thousands of calibrated judgments instantly.
A chat model cannot do that.

---

## `jev.py` — the client

Everything measured in `docs/research/jev-measured-benchmarks.md` is encoded here.

```python
import asyncio, hashlib, json, os
import httpx

URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"

class Jev:
    def __init__(self, key: str | None = None, concurrency: int = 100):
        self.key = key or os.environ["JEV_API_KEY"]
        self._sem = asyncio.Semaphore(concurrency)
        self._client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=150, max_keepalive_connections=150),
            timeout=httpx.Timeout(120.0),
        )

    async def ask(self, state, questions: dict) -> dict:
        """One request. Every question here is evaluated in parallel against one shared state."""
        payload = {"model": MODEL, "state": state, "questions": questions}
        async with self._sem:
            for attempt in range(5):
                r = await self._client.post(
                    URL, json=payload,
                    headers={"Authorization": f"Bearer {self.key}",
                             "Content-Type": "application/json"},
                )
                if r.status_code in (429, 529):
                    await asyncio.sleep(1.2 * (attempt + 1))   # exponential-ish backoff
                    continue
                r.raise_for_status()
                return r.json()
            r.raise_for_status()

    async def batch(self, jobs: list[tuple]) -> list[dict]:
        """jobs = [(state, questions), ...] — fired concurrently."""
        return await asyncio.gather(*(self.ask(s, q) for s, q in jobs))

    async def aclose(self):
        await self._client.aclose()
```

### Batching rules, from measurement not intuition

1. **Pack ~60 questions per request.** Latency is flat in question count (18q = 0.62s, 60q = 0.38s)
   but shared `state` tokens amortise across them. Measured: 2,535 judgments/sec at 60q × 100-way.
2. **Concurrency 100.** Zero 429s observed at that level. Keep the backoff anyway — the docs
   promise 429/529 and the venue is not our laptop.
3. **One `noul` per (entity × item), not one `choice` over all items.** Gives a full ranked
   distribution, degrades gracefully, and is what makes a sortable visual possible.
4. **Question ids as `{entity}__{dimension}` or `{uid}|{ref}`** so the frontend pivots the flat
   `answers` map into a matrix in one line. Ids are never sent to the model — they are free.

---

## `questions.py` — the prompt layer

Every Jev question lives here and nowhere else, so `scripts/eval_judgement.py` gates all of them.

```python
def would_recommend(product: dict) -> dict:
    return {
        "type": "noul",
        "instructions": {
            "question": ("Would the creator recommend `product` to `shopper`? "
                         "Apply `creator.routing_rules` and her willingness to reject "
                         "a product on price even when she rates it highly."),
            "product": product,
        },
        "criteria": {"true":  "She would put it in their basket",
                     "false": "She would leave it out for this person"},
    }
```

**Things that measurably worked** (see the 100%-recall eval):
- Put the creator's own words in `state`, verbatim. One sentence per product was enough for Jev to
  refuse to upsell a £62 serum she rates 8.1/10.
- Use backticked paths (`` `shopper` ``, `` `creator.routing_rules` ``) to point at `state`.
- Use structured `instructions` — question in one field, the item in another — when the question
  needs to reference a specific record.
- Always give `criteria` for a `noul`. It sharpens the decision boundary.

**Things to avoid:**
- Vague scores without concrete level descriptions. Score levels must describe *situations*.
- Bundling independent dimensions into one question. Split them; they run in parallel anyway.
- Asking Jev to generate or explain. It returns judgments. Text comes from the evidence itself.

---

## `cache.py`

```python
def key(case_id: str, payload: dict) -> str:
    return hashlib.sha256(
        (case_id + json.dumps(payload, sort_keys=True)).encode()
    ).hexdigest()[:16]
```

Write results to `cache/matrix-<key>.json`. **On the day, warm the cache before the demo and keep
the file in git.** If the venue wifi dies at 19:44, the demo still runs — and it is still honest,
because those are real judgments we really computed.

Ship a `?live=1` flag that bypasses the cache, so we can run it genuinely live when the network is
healthy — which is the better demo.

---

## Endpoints

Keep it to four. One page, remember.

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/case` | The case pack: creator, personas, shelf, evidence. Frontend renders from this |
| `POST` | `/api/judge` | One person + context → verdict card. The audience-facing answer |
| `POST` | `/api/simulate` | The big batch. Streams progress (see below) |
| `GET` | `/api/matrix/{id}` | A cached matrix |

### Streaming the batch
The hero animation wants results *as they land*, not after. Use SSE — it is ~15 lines in FastAPI,
works with plain `EventSource` in the browser, and needs no websocket plumbing.

```python
from fastapi.responses import StreamingResponse

@app.post("/api/simulate")
async def simulate(req: SimReq):
    async def gen():
        async for chunk in engine.run_streaming(req):
            yield f"data: {json.dumps(chunk)}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")
```

Use `asyncio.as_completed` over the request futures so chunks emit in completion order. With 50
requests over ~1.2s that is ~40 visual updates — enough to feel alive, not enough to thrash.

---

## CORS and serving

Vite dev server on `:5173`, FastAPI on `:8000`. Add `CORSMiddleware` with
`allow_origins=["http://localhost:5173"]` in the first five minutes — forgetting this costs
twenty confused minutes later.

For the final build, `app.mount("/", StaticFiles(directory="frontend/dist", html=True))` so one
process serves everything. That also makes the Modal wrapper trivial.

---

## Modal — only at the end, only for a URL

Not needed for throughput (measured: one process does 2,535 judgments/sec — the workload is
network-bound and Jev's servers are the parallelism). Needed only so judges can open it on their
own phones, which speaks to *"Would I share it?"*.

Keep `main.py` exporting a plain ASGI `app`, then:

```python
import modal

app_ = modal.App("heist")
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("fastapi[standard]==0.115.*", "httpx==0.27.2")
    .add_local_dir("frontend/dist", remote_path="/assets", copy=True)
    .add_local_dir("data", remote_path="/data", copy=True)
)

@app_.function(
    image=image,
    secrets=[modal.Secret.from_name("jev")],
    min_containers=1,        # ON only during the demo window — otherwise it idles on credit
    scaledown_window=300,
)
@modal.concurrent(max_inputs=100)   # one container serves the whole room
@modal.asgi_app()
def web():
    from main import app          # mount StaticFiles LAST so /api/* wins
    return app
```

```bash
modal secret create jev JEV_API_KEY=apikey_...
modal serve api.py     # hot-reloading dev URL
modal deploy api.py    # → https://<workspace>--heist-web.modal.run
```

**API names changed recently — use the current ones:**
- `@modal.web_endpoint` → **`@modal.fastapi_endpoint`** (since v0.73.82). We use `@modal.asgi_app()`
  anyway, which gives routing + static files + CORS + SPA fallback in one container and one URL.
- `allow_concurrent_inputs=` kwarg → **`@modal.concurrent(max_inputs=...)`** decorator.

**Never pass `gpu=` anywhere in this project.** Jev is an HTTPS call; a CPU container costs ~$0.01/hr
and GPUs are what would burn the ~$100. Our 100-container cap is a scheduling limit, not a cost one.

No local Docker involved — Modal builds the image remotely from that spec. Deploy at ~17:00,
not at 10:30.

---

## Build order (first 90 minutes)

1. `pip install fastapi uvicorn httpx python-dotenv` · `.env` · CORS
2. Port `scripts/simulate_audience.py` into `jev.py` + `engine.py` — it already works
3. `GET /api/case` returning `data/case-001-maya.json`
4. `POST /api/simulate` non-streaming, write to cache
5. **Run `scripts/eval_judgement.py`. It must print 100% / 0 violations.** That is the gate
6. Only then add SSE and the frontend

Do not start with the frontend. The matrix data shape determines the layout, and we already know
the data is good.
