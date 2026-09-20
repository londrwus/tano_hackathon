# ENGINEERING PLAYBOOK — Tano x Corgi Creator Heist Hack
## Modal, Pen, Frontend, Demo Rig
*Optimised for: working demo in 8 hours, WOW in 90 seconds, commercial story, elegance, inventiveness.*

---

## 0. The one decision that shapes everything else

Your hero asset is **one number plus one picture**: *N thousand calibrated judgments, made in M seconds, for P cents* — rendered as a field of moving dots that resolve into a decision. That is the Jev signature move, it is the "most inventive" and "most elegant" argument, and it is the only thing on your critical path that genuinely benefits from Modal.

Everything below is arranged around protecting that one moment.

---

# A. MODAL

Verified against current docs (2026-09-20) and `modal` CLI **1.5.2** installed locally.

## A.0 Facts that constrain you

| Fact | Consequence |
|---|---|
| CPU billed at **$0.0000131 / core-sec**, min **0.125 cores**; RAM **$0.00000222 / GiB-sec** | A CPU container costs ~**$0.01/hour**. 100 of them ~**$1/hour**. CPU is effectively free. |
| Starter plan: **100 concurrent containers, 10 GPU** | Your 100-container cap is a *scheduling* limit, not a cost limit. |
| Hard cap **4,000 concurrent containers** per Function (irrelevant to you) | — |
| GPUs are what burn the ~$100 | **Never pass `gpu=` anywhere in this project.** Jev is an HTTPS call. |
| `@modal.web_endpoint` renamed → **`@modal.fastapi_endpoint`** (since v0.73.82) | Use the new name. |
| `allow_concurrent_inputs=` deprecated → **`@modal.concurrent(max_inputs=, target_inputs=)`** | Use the decorator. Old kwarg will warn or break. |

## A.1 (i) Minimum viable web endpoint serving the frontend's API calls

One file. `modal serve` it all day, `modal deploy` it before judging.

```python
# api.py
import json, os
import modal

app = modal.App("heist-api")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("fastapi[standard]==0.115.*", "httpx==0.27.2")
    # bake the built frontend + precomputed results into the image
    .add_local_dir("web/dist", remote_path="/assets", copy=True)
    .add_local_dir("data",     remote_path="/data",   copy=True)
)

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("typesafe")],
    min_containers=1,          # ← ON only during the demo window. See A.6.
    scaledown_window=300,
)
@modal.concurrent(max_inputs=100)     # one container serves the whole room
@modal.asgi_app()
def web():
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles

    api = FastAPI()
    api.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )

    CACHE = json.load(open("/data/precomputed.json"))

    @api.get("/api/health")
    def health():
        return {"ok": True, "judgments": len(CACHE["rows"])}

    @api.get("/api/run/{run_id}")
    def run(run_id: str):
        return CACHE                       # instant, no inference, always works

    @api.post("/api/judge")
    async def judge(body: dict):
        # the ONE live path. Everything else is cache.
        return await judge_one.remote.aio(body)

    # serve the React build at "/" — mount LAST so /api/* wins
    api.mount("/", StaticFiles(directory="/assets", html=True), name="static")
    return api
```

```bash
modal secret create typesafe TYPESAFE_API_KEY=sk-...
modal serve api.py     # hot-reloading dev URL, dies when you Ctrl-C
modal deploy api.py    # → https://<workspace>--heist-api-web.modal.run  (survives)
```

**Why `@modal.asgi_app()` and not `@modal.fastapi_endpoint()`:** you get routing, static files, CORS and the SPA fallback (`html=True`) in one container and one URL. No CORS debugging at 17:30. Use `fastapi_endpoint` only for a throwaway single-route probe.

## A.2 (ii) Fan-out of thousands of *network-bound* calls to Jev — the correct primitive

**The answer: `@modal.concurrent` on an `async` function, driven by `.map()`. CPU only. No GPU. No `.spawn()` loop.**

Here is why each alternative is wrong:

| Approach | What actually happens with 5,000 Jev calls | Verdict |
|---|---|---|
| `f.map(items)` on a **sync** fn, no `@modal.concurrent` | 1 input per container. Capped at 100 containers → 50 sequential waves × ~0.9 s = **~45 s + 100 cold starts**, and 100 containers sit blocked on `recv()` doing nothing. | ❌ Wastes your container cap on idle sockets |
| `for i in items: f.spawn(i)` | 5,000 `FunctionCall` objects, 5,000 control-plane round trips from your laptop, then you poll. Slower to *submit* than to *run*. | ❌ Only for true fire-and-forget |
| `f.spawn_map(items)` | Same fan-out, no results returned. You then need a Dict to collect. Extra moving part. | ❌ Unnecessary indirection |
| Single container, `asyncio.gather` over 5,000 | One event loop, one process. Works, but one flaky container = whole run lost, and you get one machine's egress. | ⚠️ Fine as fallback |
| **`.map()` + `@modal.concurrent(max_inputs=N)` on an `async` fn** | Each container multiplexes N in-flight HTTPS calls on one event loop. 10 containers × 50 = 500 in flight. **5,000 calls ≈ 10 s wall clock, ~$0.0005.** | ✅ **This one** |

### The skeleton to actually ship

Use a **class** so the `httpx.AsyncClient` (and its connection pool) is created once per container in `@modal.enter()`, not once per input. Creating a client per input is the #1 cause of "why is this slow" in network fan-outs.

```python
# fanout.py
import os, json, asyncio, time
import modal

app = modal.App("heist-fanout")

image = modal.Image.debian_slim(python_version="3.12").pip_install("httpx==0.27.2")

@app.cls(
    image=image,
    secrets=[modal.Secret.from_name("typesafe")],
    max_containers=10,                 # ← HARD GUARDRAIL. See A.6.
    timeout=900,
    retries=modal.Retries(max_retries=3, backoff_coefficient=2.0, initial_delay=1.0),
)
@modal.concurrent(max_inputs=60, target_inputs=50)   # 10 × 50 = 500 in flight
class Jev:
    @modal.enter()
    def boot(self):
        import httpx
        self.client = httpx.AsyncClient(
            base_url="https://api.typesafe.ai",
            headers={"Authorization": f"Bearer {os.environ['TYPESAFE_API_KEY']}"},
            timeout=httpx.Timeout(60.0, connect=10.0),
            limits=httpx.Limits(max_connections=200, max_keepalive_connections=200),
        )
        self.sem = asyncio.Semaphore(60)   # belt & braces vs. 429s

    @modal.method()
    async def judge(self, item: dict) -> dict:
        t0 = time.time()
        async with self.sem:
            r = await self.client.post(
                "/v1/systemone",
                json={
                    "state": item["state"],
                    "model": "jev-latest",
                    "questions": item["questions"],
                },
            )
        if r.status_code == 429:
            raise RuntimeError("rate limited")     # let Modal's Retries handle it
        r.raise_for_status()
        return {"id": item["id"], "ms": int((time.time() - t0) * 1000), **r.json()}


@app.local_entrypoint()
def main(infile: str = "data/items.json", outfile: str = "data/precomputed.json"):
    items = json.load(open(infile))
    t0 = time.time()
    rows = list(Jev().judge.map(items, return_exceptions=True, order_outputs=False))
    ok  = [r for r in rows if not isinstance(r, Exception)]
    bad = len(rows) - len(ok)
    elapsed = time.time() - t0
    json.dump(
        {"rows": ok, "n": len(ok), "failed": bad, "seconds": round(elapsed, 1)},
        open(outfile, "w"),
    )
    print(f"{len(ok)} judgments in {elapsed:.1f}s ({bad} failed)")
```

```bash
modal run fanout.py                      # runs local_entrypoint, writes data/precomputed.json
```

`order_outputs=False` streams results as they land — that is what lets your frontend animate dots resolving **live** rather than all at once. `return_exceptions=True` means three flaky calls don't kill a 5,000-item run at 15:55.

### Streaming into the UI (the version that produces the WOW)

If you want the dots resolving on screen while the fan-out runs, expose the map as a server-sent-event stream:

```python
@api.get("/api/stream")
async def stream():
    from fastapi.responses import StreamingResponse
    async def gen():
        async for row in Jev().judge.map.aio(ITEMS, order_outputs=False,
                                             return_exceptions=True):
            if not isinstance(row, Exception):
                yield f"data: {json.dumps(row)}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")
```

Frontend: `new EventSource('/api/stream')`. This is ~15 lines and it is the difference between a chart and a spectacle.

### Two-tier variant (only if you exceed ~20,000 calls)

Chunk, then `asyncio.gather` inside each chunk. Fewer Modal inputs = less control-plane overhead.

```python
@app.function(image=image, secrets=[...], max_containers=10, timeout=900)
async def judge_chunk(chunk: list[dict]) -> list[dict]:
    import httpx
    sem = asyncio.Semaphore(50)
    async with httpx.AsyncClient(base_url="https://api.typesafe.ai",
                                 headers={...}, timeout=60) as c:
        async def one(it):
            async with sem:
                r = await c.post("/v1/systemone", json={...})
                return {"id": it["id"], **r.json()}
        return await asyncio.gather(*(one(i) for i in chunk), return_exceptions=True)

# caller
chunks = [items[i:i+250] for i in range(0, len(items), 250)]
out = [r for c in judge_chunk.map(chunks) for r in c]
```

### FIRST THING IN THE MORNING: find the real ceiling

Before you design around 5,000 concurrent, **measure Jev's rate limit**. 10 minutes, saves you two hours:

```bash
python -c "
import asyncio, httpx, os, time
async def main():
  async with httpx.AsyncClient(timeout=60) as c:
    for n in (10, 50, 200, 500):
      t=time.time()
      rs=await asyncio.gather(*[c.post('https://api.typesafe.ai/v1/systemone',
          headers={'Authorization':'Bearer '+os.environ['TYPESAFE_API_KEY']},
          json={'state':'hello','model':'jev-latest',
                'questions':{'q':{'type':'noul','instructions':'Is this a greeting?'}}})
        for _ in range(n)], return_exceptions=True)
      codes=[getattr(r,'status_code',type(r).__name__) for r in rs]
      print(n, round(time.time()-t,2),'s', {c:codes.count(c) for c in set(codes)})
asyncio.run(main())"
```

Set `max_containers × target_inputs` to ~80% of the first level where you see 429s. **Your bottleneck is Jev's rate limit, not Modal.**

## A.3 Cold-start mitigation

Order of effort-to-payoff:

1. **`min_containers=1`** on the web endpoint, switched on at ~17:00 and off after prizes. Costs ~$0.01/hr. Eliminates the 3–8 s first-request stall that will otherwise happen in front of judges. **Do this.**
2. **Thin image.** `debian_slim` + `httpx` + `fastapi` only. No torch, no transformers, no `modal.Image.from_registry`. Your image should build in <30 s and pull in <3 s.
3. **`@modal.enter()`** for the HTTP client / loading precomputed JSON — Modal won't route inputs until it returns, so no input ever hits a half-booted container.
4. **`buffer_containers=2`** on the fan-out function if you'll trigger it live — pre-warms idle capacity so the first wave doesn't queue.
5. **`scaledown_window=300`** so the container you warmed at 17:00 is still warm at 19:45.
6. **Ignore `enable_memory_snapshot`.** It's for multi-GB model loads. You have none.

## A.4 Secrets

```bash
modal secret create typesafe TYPESAFE_API_KEY="sk-..."
modal secret create anthropic ANTHROPIC_API_KEY="sk-ant-..."
modal secret list
```
```python
@app.function(secrets=[modal.Secret.from_name("typesafe")])
def f():
    key = os.environ["TYPESAFE_API_KEY"]
```
`modal.Secret.from_dict({...})` for a quick one-off from your own env. **Never** `.add_local_file(".env")` into the image — it's baked and visible to anyone with the image.

## A.5 Persisting results — Volume vs Dict vs neither

| | Use for | Gotchas |
|---|---|---|
| **`modal.Dict`** | `run_id → result`, live job status your frontend polls. `Dict.from_name("x", create_if_missing=True)`. cloudpickle'd values, `.aio` methods available. | Entries expire after **7 days of inactivity**. Avoid non-primitive keys (cloudpickle is non-deterministic). Not a database — don't put 5,000 rows in as 5,000 keys. |
| **`modal.Volume`** | Big artifacts you want to pull to your laptop: `modal volume get heist-data /precomputed.json .` | Requires `vol.commit()` in the writer and `vol.reload()` in the reader. **Concurrent writers will bite you.** Not worth the ceremony today. |
| **A local JSON file, committed to git** ✅ | Everything on the demo path. | None. This is the right answer. |

**Recommendation:** `modal run fanout.py` writes `data/precomputed.json` on your laptop. That file is baked into the image *and* shipped in the frontend's `public/`. Use a `Dict` only if you add a live "run it now" button that needs a progress bar.

## A.6 Things that will waste your credit or your caps — read this twice

- 🔴 **Any `gpu=` argument.** You need zero GPU. One `gpu="A100"` left in a loop overnight is your whole $100.
- 🔴 **`min_containers` left on after the hackathon.** It bills forever on a *deployed* app. Turn it on at 17:00; `modal app stop heist-api` when you leave. (`modal serve` self-terminates with the terminal — deploy does not.)
- 🔴 **Retries on a 4xx.** A bad API key + `max_retries=3` + 5,000 inputs = 20,000 doomed requests and a possible ban from Jev's side. Only retry 429/5xx/timeouts; `raise_for_status()` on a 401 must fail fast. **Smoke-test with 5 items before you ever run 5,000.**
- 🔴 **No `max_containers`.** A `.map()` over 50,000 items with no cap will happily try to consume all 100 containers and hammer Jev into rate-limit hell. Always set `max_containers=10`.
- 🟠 **`timeout` default is 300 s.** A long fan-out inside one function will be killed mid-run. Set `timeout=900`.
- 🟠 **Re-running the full fan-out casually.** It's cheap in Modal dollars but it burns *Jev quota* and wall-clock. Cache aggressively; add a `--limit 20` flag to your entrypoint for iteration.
- 🟠 **Building a fat image.** Every `pip_install` you add is cold-start seconds you pay for in front of judges.

---

# B. PEN (pen.dev) — verified live in this session

## B.1 How it actually works

Pen is an **Electron desktop app** at `C:\Users\Lenovo\AppData\Local\Programs\Pen\Pen.exe`. The MCP server is a sidecar binary:

```
C:\Users\Lenovo\AppData\Local\Programs\Pen\resources\app.asar.unpacked\out\mcp-server-windows-x64.exe
  --app desktop --agent claudeCodeCLI
```

**Critical operational fact I hit and solved:** *every* Pen MCP tool — including `read_skill` and `get_style`, which take no file argument — fails with `A file needs to be open in the editor` unless the desktop app has a `.pen` file open. The `filePath` parameter does **not** open a file; it only selects among already-open editors. To unblock:

```bash
start "" "C:/Users/Lenovo/AppData/Local/Programs/Pen/Pen.exe" "C:/path/to/design.pen"
```

After that, `get_app_state` returned live state. **Do this at 09:05, before you need it.** Current state as of now:

```
Active editor: /C:/Users/Lenovo/Documents/techeu_agentichack/design/orbit.pen
Top-level nodes: qoWrR (frame, reusable component) "Sidebar",
                 oW3i0 "01 Overview", C4KJin "02 Module · Latte Index",
                 fqFiy "03 Rent Radar", zxCv1 "04 Mission Control", BtPQB "05 Ask Orbit"
Browser: no URL loaded
```
That is a previous hackathon's file. **Create a fresh `.pen` for the heist** — do not build on top of `orbit.pen`.

## B.2 What a `.pen` file is

An **encrypted JSON document** describing an infinite canvas with a nested node hierarchy. Node types: `frame`, `group`, `text`, `path`, `icon`, `ref` (component instance), `browser`. Frames have flexbox-like `layout` (`horizontal`/`vertical`/`none`), `gap`, `padding`, `justifyContent`, `alignItems`, and sizing via `fill_container` / `fit_content` / fixed px.

**It is not CSS.** No margin, no percentages, no `alignItems: stretch/baseline`, no line-wrapping unless `textGrowth` is `fixed-width`. Text is invisible without an explicit `fill`. **Never `Read`/`Grep` a `.pen` file** — encrypted, MCP only.

## B.3 The actual tool surface

| Tool | Call shape |
|---|---|
| `mcp__pencil__read_skill` | `{}` for SKILL.md; `{path:"execute.md"}`, `{path:"guide/web-app.md"}`, `{path:"guide/code.md"}`, `{path:"guide/tailwind.md"}` |
| `mcp__pencil__get_app_state` | `{}` — open editor, selection, top-level node ids, components, browser URL |
| `mcp__pencil__execute` | `{filePath, input:"<JS snippet>"}` — **the only mutation path** |
| `mcp__pencil__execute` (retry) | `{filePath, editId, edits:[{find,replace}]}` — **on failure, NEVER resend the snippet**, patch it |
| `mcp__pencil__get_style` | `{}` lists 26 archetypes; `{name}` loads / returns required params; `{name, params}` applies |
| `mcp__pencil__browser` | `{filePath, action:"load-page"\|"import-to-canvas"\|"screenshot-to-canvas"\|"return-element"\|"return-screenshot", url?, target?, querySelector?, nodeId?}` |

`execute` runs JS with exactly this API: `Insert(parent, node) → id`, `Copy(path, parent, data) → id`, `Update(path, data)`, `Replace(path, node) → id`, `Move`, `Delete`, `Get(path, opts)` / `Get(visit, opts)`, `GetVariables()`, `SetVariables({name:{type,value}})`, `FindEmptySpace({width,height,direction,padding,nodeId}) → {x,y}`, `Print(...)`, `TakeScreenshot([ids])`, `Generate(type,nodeId,prompt)`, `Export(ids, format, outputPath, opts)`.

Scope rules that bite: each `execute` has its **own scope** — use bare `myId = Insert(...)` (no `const`/`let`) to persist across calls. Every node needs a human-readable `name`. Never set `id`. Mark in-progress root frames `placeholder: true`.

## B.4 Design → frontend code: the two real paths

**Path 1 — HTML/Tailwind export (fastest, ~2 minutes):**
```js
Export([screenId], "html-tailwind", "./web/design-ref/dashboard.html")
```
Writes a self-contained HTML file with Tailwind classes and `data-*` layer names. You then port it into React by hand or with an agent. Images are referenced by relative path, **not embedded** — copy the asset dir too.

**Path 2 — agent-driven port (higher fidelity, what `guide/code.md` prescribes):**
1. `Print(Get(componentId, {depth: 5}))` to dump a component's full tree
2. `Print(GetVariables())` → map `$tokens` to Tailwind v4 `@theme` CSS variables **once**
3. Build **one component at a time**: extract → write `.tsx` → `TakeScreenshot` the Pen node → compare → fix → next
4. `Print(Get(id, {includePathGeometry: true}))` for exact SVG `d` attributes — **never approximate a path**
5. `Get(screen, (n,c) => c.problems && Print(n.name, c.problems))` catches clipping/overflow before you port it

**Fastest path to a running React app:** `npm create vite` first (see D), build the component shells, *then* design in Pen, then `Export(..., "html-tailwind", ...)` and port. Working front-end first, Pen for visual direction and hero screens. Don't let Pen become the critical path.

## B.5 The one inventive Pen trick worth 10 minutes

`mcp__pencil__browser` closes the loop:
```js
// 1. import Maya's / Sofia's real Instagram aesthetic onto the canvas
browser({filePath, action:"load-page", url:"https://..."})
browser({filePath, action:"import-to-canvas"})   // → editable Pen layers, not a screenshot

// 2. later, review your own running app and iterate
browser({filePath, action:"load-page", url:"http://localhost:5173"})
browser({filePath, action:"return-screenshot"})  // you look at it, then fix
```
Importing the creator's actual visual language in the first hour is the cheapest available win on **"fidelity to the creator's voice"** — a judging criterion that is usually lost to generic AI-dashboard grey.

## B.6 Use a style archetype, don't invent one

`get_style({})` lists 26. For a spy-dossier / intelligence-brief product, start from **Blueprint Technical**, **Editorial Scientific**, **Product Data Grid**, or **Dark Centered Platform**. Ten seconds of tool call beats an hour of colour bikeshedding, and it directly serves "most elegant."

---

# C. DO YOU ACTUALLY NEED MODAL?

## The honest answer

**No — not for correctness. Yes — for one specific 10-second stretch of the demo, and for the commercial story.**

| | Local FastAPI + precomputed JSON | Modal |
|---|---|---|
| Time to working | **5 minutes** | 25–40 min incl. first deploy debugging |
| Fails during demo because… | nothing (it's on disk) | wifi, cold start, rate limit, expired token |
| Venue wifi dependency | **zero** | total |
| Judges can open it on their phone | no (unless you tunnel) | **yes — a real URL** |
| "Is this a product?" signal | it's a laptop | **it's deployed** |
| Supports the "5,000 judgments in 41 s for 31¢" claim | you can still make the claim from a recorded run | **you can make it live** |
| Cost | £0 | ~£0.01 |

The trap is treating this as either/or. It isn't.

## Recommendation — three-layer architecture, built in this order

```
Layer 1  (hour 1–2)   Vite + React reading  /public/data/precomputed.json
                      Works offline. Works with a dead API key. This is the demo.

Layer 2  (hour 3)     One script, run ONCE locally: hits Jev, writes precomputed.json.
                      Now the numbers on screen are REAL. This is what makes it honest.

Layer 3  (hour 5–6)   Modal: the same script as a fan-out + a deployed URL.
                      Gives you (a) a live "run it again" button, (b) a QR code,
                      (c) the scale claim you can actually defend.
```

**The switch is one environment variable:**
```ts
// web/src/data.ts
const LIVE = import.meta.env.VITE_MODE === "live";
export const load = () =>
  LIVE ? fetch(`${import.meta.env.VITE_API}/api/run/latest`).then(r => r.json())
       : fetch("/data/precomputed.json").then(r => r.json());
```
Default is **replay**. You flip to live only if the wifi is good at 19:40. Never the reverse.

**Ship Layer 3 only if Layers 1 and 2 are done by 15:00.** The 16:00 intelligence drop will force a rethink of your data model; you want spare capacity then, not a half-deployed Modal app.

### Why Modal still earns its place

The intelligence drop says the valuable behaviour is *invisible* — 61–71% never clicked or DM'd, savers convert 2.2–3.1×, 41–44% of high-value action follows a private share. The product implication is that you must **reason about thousands of people who never spoke to the creator**. That is literally massive parallel calibrated judgment. Modal + Jev is not a flex bolted on; it is the honest implementation of the insight the organisers hand you at 16:00. Saying *"this ran over every one of Maya's 4,800 DMs and 12,000 silent savers in 41 seconds for 31 pence, and here's the receipt"* is the **best commercial-potential** line available to any team in the room — it is a unit-economics claim, and unit economics is what "commercial potential" means to a judge from Tano.

---

# D. FRONTEND

## D.1 Stack — Vite, not Next.js

```bash
npm create vite@latest web -- --template react-ts
cd web && npm i
npm i tailwindcss @tailwindcss/vite motion d3-scale d3-force lucide-react
```

```ts
// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
export default defineConfig({ plugins: [react(), tailwindcss()], server: { host: true } });
```
```css
/* src/index.css */
@import "tailwindcss";
@theme {
  --color-ink:    #07070a;
  --color-paper:  #f4f1ea;
  --color-signal: #ff4d2e;   /* one accent. ONE. */
  --color-muted:  #6b6b76;
  --font-display: "Instrument Serif", serif;
  --font-mono:    "JetBrains Mono", monospace;
}
```

**Why Vite over Next.js, specifically for this:**
- `npm create vite` → running app in ~20 s. Next's first build + RSC/`"use client"` boundaries cost you 30–45 minutes you do not have.
- Framer Motion / canvas / `EventSource` are all client-side. SSR buys you literally nothing.
- HMR is instant; Next's dev compile stutters exactly when you're iterating fastest.
- `vite build` → a `dist/` folder you can drop into Modal's `StaticFiles`, into `python -m http.server`, or onto Vercel in one command. Maximum optionality for the demo rig.
- **The only reason to choose Next.js** is if you want API routes co-located and you're *not* using Modal/Python. You are. Skip it.

Deploy the static build: `npx vercel --prod` (~40 s) as a second, wifi-independent fallback URL.

## D.2 Rendering 1,000+ animated dots at 60fps

Measured reality on a typical laptop driving an external projector:

| Technique | Ceiling at 60fps | Setup cost | Verdict |
|---|---|---|---|
| React + one `<circle>` per dot, state-driven | **~300** | 0 | ❌ Guaranteed to stutter in front of judges |
| SVG, direct DOM mutation (no React in the loop) | ~1,000–1,500 | low | ⚠️ Fine for ≤800, risky above |
| **Canvas 2D, one `<canvas>`, RAF loop** | **5,000–20,000** | **~30 lines** | ✅ **Use this** |
| WebGL — **PixiJS v8** `ParticleContainer` | 100,000+ | 1–2 hrs | Only above ~20k, or if you want shaders/bloom |
| `@react-three/fiber` `<Points>` | 1,000,000 | 2+ hrs | Overkill. Will eat your afternoon. |

**Canvas 2D is the right answer for your scale.** Non-negotiable rules:

1. **Never** store dot positions in React state. `useRef(new Float32Array(n * 4))` — x, y, targetX, targetY.
2. Cap `devicePixelRatio` at **2**. A 3× retina backing store quadruples fill rate for no visible gain and is the #1 cause of "it was 60fps on my machine."
3. **Batch by colour.** Every `ctx.fillStyle =` is a state change. Sort dots by colour, set fillStyle once per group.
4. Above ~5,000 dots, pre-render one dot to a 16×16 offscreen canvas and `drawImage` it, instead of `ctx.arc()` + `fill()` per dot. 3–5× faster.
5. **No physics engine.** Precompute target positions deterministically, lerp toward them. Always 60fps, always identical, replayable frame-for-frame — which is exactly what a demo needs.

```tsx
// src/DotField.tsx
import { useEffect, useRef } from "react";

type Dot = { x: number; y: number; tx: number; ty: number; c: number };

export function DotField({ dots, palette }: { dots: Dot[]; palette: string[] }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const state = useRef(dots);
  state.current = dots;

  useEffect(() => {
    const cv = ref.current!, ctx = cv.getContext("2d", { alpha: false })!;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const fit = () => {
      const r = cv.getBoundingClientRect();
      cv.width = r.width * dpr; cv.height = r.height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    fit(); addEventListener("resize", fit);

    // pre-rendered sprite per palette colour
    const sprites = palette.map(col => {
      const s = document.createElement("canvas"); s.width = s.height = 12;
      const c = s.getContext("2d")!;
      c.fillStyle = col; c.beginPath(); c.arc(6, 6, 3.2, 0, 6.2832); c.fill();
      return s;
    });

    let raf = 0;
    const tick = () => {
      const w = cv.width / dpr, h = cv.height / dpr;
      ctx.fillStyle = "#07070a"; ctx.fillRect(0, 0, w, h);
      const ds = state.current;
      for (let i = 0; i < ds.length; i++) {
        const d = ds[i];
        d.x += (d.tx - d.x) * 0.085;          // critically damped-ish, no jitter
        d.y += (d.ty - d.y) * 0.085;
        ctx.drawImage(sprites[d.c], d.x - 6, d.y - 6);
      }
      raf = requestAnimationFrame(tick);
    };
    tick();
    return () => { cancelAnimationFrame(raf); removeEventListener("resize", fit); };
  }, [palette]);

  return <canvas ref={ref} className="w-full h-full block" />;
}
```

Driving it: change each dot's `tx`/`ty` when the narrative beat changes (scattered cloud → clustered by decision-archetype → resolved into a ranked list). Positions per cluster via `d3-force`'s `forceSimulation` run **once, offline**, results baked into JSON. Zero physics at runtime.

## D.3 The rest of the animation layer

- **`motion`** (the current package name for Framer Motion) for all the chrome: card reveals, `AnimatePresence`, and above all **`layoutId`** — the shared-element morph from *a dot in the field* → *a full decision card*. That single transition is the highest wow-per-line-of-code effect in web animation and it visually argues your whole thesis: "this anonymous saver is a person with a decision." It is your "most elegant" moment.
- **Number count-ups** with `useMotionValue` + `animate()` + `useTransform`. A counter racing to `5,143` while dots resolve is worth more than any chart.
- **Charts:** hand-roll bars and donuts as flex divs + `motion.div` with animated `width`/`height`. Faster to write than configuring Recharts, and it will look better. Only reach for a charting library if you genuinely need axes and ticks.
- **Icons:** `lucide-react`. **Fonts:** exactly two families, three weights total, via Google Fonts `<link>` with `display=swap`.

## D.4 Visual direction (serves "most elegant")

Dossier/intelligence aesthetic, earned from the case files: near-black `#07070a`, one hot accent, monospace for all data and labels (numbers in mono read as *evidence*, numbers in Inter read as *a dashboard*), generous negative space, hairline 1px rules, no card-in-card-in-card. **Resist the Tailwind-default-startup-dashboard look.** Fifty-four builders will ship purple gradients and rounded-2xl cards. One dark, typographic, data-dense screen with one moving thing on it wins the room.

---

# E. DEMO RIG — making 90 seconds bulletproof

## E.1 The architecture of not failing

```
web/public/data/precomputed.json    ← real Jev output, committed to git
web/public/data/timings.json        ← real per-call latencies from the real run
VITE_MODE=replay                    ← the default, always
VITE_MODE=live                      ← only if wifi is good at 19:40
demo/backup.mp4                     ← 90s clean recording, open in a second tab
```
**Rule: the demo must run with the laptop in airplane mode.** Test this literally. Turn off wifi at 18:00 and run the full 90 seconds. If it breaks, you don't have a demo, you have a hope.

## E.2 Precomputed caches

Run the real fan-out at ~15:00 and again at ~17:30 (post-drop). Commit the output. The UI reads from disk at ~0 ms, then you *deliberately re-introduce the real pacing* (below). Also keep `precomputed.v1.json` around — if the post-drop rebuild breaks something at 19:30, you `git checkout` your way back to a working demo in 10 seconds.

## E.3 "Fake-but-honest latency" — the line, precisely

**The rule: the numbers must be real; the pacing may be staged; you say which in one clause, out loud.**

- ✅ Honest: replaying real recorded per-call timings so the dots resolve at the speed they actually resolved. Say: *"this is a replay of the 14:22 run — 5,143 judgments, 41 seconds, 31 pence."*
- ✅ Honest: compressing 41 s of real results into 8 s of animation with a visible `12× speed` badge on screen.
- ❌ Dishonest, and you will be caught: a fake spinner in front of a hardcoded result; invented latency numbers; saying "live" over a cached file.

Judges include engineers from Tano. Half of them have shipped this exact trick. **Saying "this is cached, here's the run that produced it" costs you nothing and buys the whole "WOULD I TRUST IT?" criterion outright.** Getting caught costs you the prize.

```ts
// replay real timings, honestly
export async function replay(rows: Row[], onRow: (r: Row) => void, speed = 8) {
  const t0 = performance.now();
  const sorted = [...rows].sort((a, b) => a.ms - b.ms);
  for (const r of sorted) {
    const due = r.ms / speed;
    const wait = due - (performance.now() - t0);
    if (wait > 0) await new Promise(res => setTimeout(res, wait));
    onRow(r);
  }
}
```

## E.4 Seeded, deterministic everything

```ts
// mulberry32 — 6 lines, deterministic, no dependency
export const rng = (seed: number) => () => {
  seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
  let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};
```
**Zero `Math.random()` and zero `Date.now()` anywhere on the demo path.** You are going to run this 30 times in rehearsal and 1 time that counts — all 31 must be identical. Add a `?seed=7` URL param so you can lock the exact run you rehearsed.

## E.5 Resettability

Bind a key. You will need it.
```ts
useEffect(() => {
  const h = (e: KeyboardEvent) => {
    if (e.key === "r") reset();                  // back to frame 0, instantly
    if (e.key === "ArrowRight") nextBeat();      // manual advance — NEVER rely on autoplay
    if (e.key === "l") toggleLive();             // live ↔ replay
  };
  addEventListener("keydown", h); return () => removeEventListener("keydown", h);
}, []);
```
**Manual beat advance beats autoplay.** If a judge interrupts with a question at second 40, autoplay runs on without you and you've lost the room. One arrow key = you control the clock.

## E.6 Screen-recording backup

- OBS or Windows `Win+Alt+R`. Record a **clean 90 s run at 1920×1080, 60fps**, with no notifications, no mouse wandering, no browser chrome (F11 fullscreen).
- Keep it **open and paused** in a second browser tab — not sitting in a folder. Recovery time from "the app just white-screened" must be one `Ctrl+Tab`, not a file-manager hunt.
- Also export a 10–15 s GIF/MP4 of just the dot resolve. That is the clip that gets posted afterwards and it is where your **commercial potential** story travels.
- Have the built `dist/` on a USB stick and on Vercel. Three copies, three failure domains.

## E.7 Laptop & projector gotchas (this list is from things that actually go wrong)

**Night before / morning:**
- Test the exact adapter on the exact projector if you can get 2 minutes at 09:15. **HDMI/USB-C dongle in your bag — assume the venue has none.**
- **Mirror, don't extend.** Extended displays move your window, reshuffle your desktop, and break fullscreen. Mirror at 1920×1080 @ 60 Hz.
- Set display scaling to 100% while mirrored. 125%/150% scaling + mirroring is how layouts explode 30 seconds before you present.

**Ten minutes before:**
- Do Not Disturb / Focus Assist **on**. Quit Slack, Discord, Mail, Calendar. One notification banner across your hero viz is a lost prize.
- Close every other browser tab and every other app — background tabs steal RAF frames and your 60fps canvas becomes 30fps.
- **Plug in the charger.** Battery saver throttles the GPU and caps frame rate. This silently halves your animation smoothness.
- Disable screen sleep and screensaver.
- Browser at **100% zoom**, F11 fullscreen, cursor parked off-screen.
- Kill any file-watcher or auto-rebuild. Serve the **built** `dist/`, never the dev server — a stray HMR reload mid-demo is fatal. `npx serve web/dist -l 5000`.

**Projector-specific design constraints — apply these to the UI now, not at 19:30:**
- Projectors crush contrast and shift warm. **Pure `#000` backgrounds bloom into grey; thin 200/300-weight type disappears entirely.** Use `#07070a`–`#0d0d12` backgrounds, minimum 500 weight for body text, 16px minimum, and your accent at high saturation.
- Subtle is invisible at 10 metres. Opacity 0.4 muted text reads as blank. Anything that matters gets ≥70% contrast.
- Check it by standing 3 metres from your own laptop. If you can't read it there, the back row can't read it at all.

## E.8 The 90-second shape

```
0:00–0:10  Name the person and the decision. "This is Rina. She saved Maya's post
           eight times, shared it with three friends, never sent a DM, and bought
           four days later. Maya has never heard of her."
0:10–0:35  THE MOVE. 5,000 dots. They resolve. Counter races. One clause of honesty:
           "replay of our 14:22 run — 5,143 judgments, 41 seconds, 31 pence."
0:35–1:05  layoutId morph: one dot → Rina's decision card. Show the actual output.
           This is "value to a real audience member" and "does it work", demonstrated.
1:05–1:20  The creator's side. One screen. What Maya sees and what she no longer has
           to type. This is "would I use it".
1:20–1:30  The unit economics, in one sentence. Hand over the URL / QR code.
```

The brief says *"don't just tell what you've built — show how it makes their life easier"* and *"if you cannot name the person and the decision, you do not have a product yet."* Open by naming the person. Not the architecture, not the stack, not Jev. **Rina.** Everything in this playbook exists to make those 90 seconds run without a stutter.

---

## Build order (timeboxed)

| Time | Do |
|---|---|
| 09:05 | Launch Pen with a fresh `.pen` (it must be open or every Pen tool fails). Probe Jev's rate limit (A.2). `npm create vite`. |
| 09:30 | Pick the case. Name the person and the decision, in writing, in one sentence. |
| 10:30 | Layer 1: React app reading hand-written `precomputed.json`. Fake data, real layout. |
| 12:00 | Layer 2: local script → real Jev output → real `precomputed.json`. **Numbers become true.** |
| 13:00 | `DotField` canvas + `layoutId` morph. The hero moment, working. |
| 15:00 | Layer 3 (optional): Modal fan-out + `modal deploy`. Only if 1 & 2 are done. |
| 16:00 | **Intelligence drop. Stop building. Re-read. Adapt the data model.** Budget 90 minutes. |
| 17:30 | Re-run the fan-out post-drop. Commit `precomputed.json`. Freeze features. |
| 18:00 | **Airplane-mode test.** Record the backup video. Rehearse 5×. |
| 19:00 | `min_containers=1`, projector check, DND on, charger in. Rehearse 3× more. |
| 19:45 | Demo. |

**If you are behind at 15:00, cut Modal. If you are behind at 17:30, cut features, not rehearsal.** An un-rehearsed demo of a better product loses to a rehearsed demo of a simpler one — and the brief tells you so in its own words: *"a simple product that works beats a complicated demo."*