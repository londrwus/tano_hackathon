# 13 — `/how-it-works` — THE PIPELINE ANIMATION (frozen spec)

A **single self-running stage** that plays the whole pipeline in **15 seconds**, then holds on a
final card. It is the last beat of the demo.

**Where it sits in the 90 seconds:** ~0:00–0:35 is `/onboard` and `/maya`, talked through by a
human. ~0:35 onwards is the rest of the script. **The last ~12 seconds is this page, playing by
itself while nobody talks.** It is the recap — it should feel like the machine explaining itself.

Design language is v3 pastel, per `docs/12-DESIGN-LIGHT.md`. Nothing here introduces a new colour
or a new component. Stage compositions are locked in `tano.pen`: `V10 anim A/B/C`.

---

## 1. Rules

1. **One stage, three acts.** The content inside a fixed stage frame changes; the stage never
   moves, never scrolls, never resizes. No page transitions, no carousel.
2. **One thing moves at a time.** If two things animate together the viewer reads neither.
3. **Nothing appears instantly.** Everything enters with `opacity 0 → 1` plus a small
   `translateY(8px) → 0` or `scale(0.96) → 1`. 300–400ms, `cubic-bezier(0.25,0.1,0.25,1)`.
4. **Animate `transform` and `opacity` only.** Never `width`, `top`, `background-color`.
   The 50-dot and 24-option groups are hundreds of nodes; compositor-only or it will judder.
5. **Text is never typed out character by character.** It fades in as a whole line. Typewriter
   effects read as a gimmick and cost seconds we do not have.
6. **Every number on screen is the real measured one**, read from the API payload, never a
   constant in the animation code. The step *labels* are hand-written copy; the *numbers* are not.
7. **The elapsed timings shown (0.65s, 0.7s) are measured wire times.** The animation runs
   slower than reality — that is a **replay** and the page says so once, quietly, bottom-right:
   `slowed down so you can see it`.
8. `prefers-reduced-motion: reduce` → no sequence. Render the **final state of all three acts
   stacked** as a static page (which is `V9` in `tano.pen`) and show the controls.

---

## 2. The timeline — 15 seconds

`t` is seconds from start. Each step's content stays on screen until its act ends.

### ACT 1 — "First it learns how she thinks" (0.0 → 5.0)
| t | What happens | Motion |
|---|---|---|
| 0.0 | Act title fades in: **"First, it reads what she has already posted."** | fade + rise |
| 0.4 | **15 post cards** fly in from the left, staggered 40ms each | translateX(-24px) + fade |
| 1.6 | Caption under them: `15 posts · her bio · her captions` | fade |
| 2.0 | **28 dots** burst out of the posts **all at once** and travel right | transform along a path, ALL start on the same frame |
| 2.2 | Label appears: **"It asks 28 questions at the same moment."** | fade |
| 3.0 | Dots land; **5 trait chips** pop in: `fewest products` · `SPF always` · `price decides` · `dry, funny, short` · `no medical` | scale(0.9)→1, staggered 80ms |
| 4.2 | Timing pill lands bottom-right of the stage: **`0.65 seconds`** | scale + fade |
| 5.0 | Act 1 content fades out together (250ms) | fade |

### ACT 2 — "Then someone messages her" (5.0 → 11.0)
| t | What happens | Motion |
|---|---|---|
| 5.2 | Act title: **"Then, at 3am, someone messages her."** | fade + rise |
| 5.6 | **Message bubble** slides in from the right: *"i have dry skin + redness and £60, tell me what to buy"* | translateX(24px) + fade |
| 6.4 | **20 dots** burst around the bubble simultaneously; label **"20 questions, all in one go."** | same-frame start |
| 7.2 | Three chips resolve beneath: `dry + redness` · `£60` · `wants a pick` | scale, staggered |
| 7.8 | Safety stamp slides in: `not medical · in her scope` (mint) | fade + rise |
| 8.4 | **24 option circles** appear in a loose grid — every basket she could send | scale, staggered 20ms |
| 9.2 | 23 of them fade to 15% opacity; **one grows and turns green** | opacity + scale |
| 9.6 | Label: **"24 options priced up. One chosen."** | fade |
| 10.0 | **The reply card** fades up: *"Red Reset and the SPF. Fifty-eight pounds."* | fade + rise |
| 10.4 | Timing pill: **`0.7 seconds`** | scale + fade |
| 11.0 | Act 2 fades out | fade |

### ACT 3 — "It does that all night" (11.0 → 15.0)
| t | What happens | Motion |
|---|---|---|
| 11.2 | Act title: **"It did that for everyone who messaged, all night."** | fade + rise |
| 11.6 | **50 dots** appear in a loose cloud in the centre | scale, staggered 12ms |
| 12.4 | The dots **fly apart into four labelled groups**, each taking its lane colour | transform, all at once, 700ms |
| 13.2 | Group labels + counts fade in: **24** wrote her reply · **14** asked a question · **4** saved for Maya · **8** refused | fade, staggered |
| 14.0 | Final card rises: **"Every one of them is a draft. Maya presses send."** | rise + fade |
| 15.0 | **HOLD.** Nothing else moves. | — |

---

## 3. Controls

Bottom of the stage, quiet, always visible:
- **`Replay`** — restarts from t=0.
- A **scrubber** of three dots (one per act) — clicking jumps to that act's start. This is how a
  presenter recovers if they want to re-show one part without replaying the whole thing.
- `slowed down so you can see it` — the honesty label, `--ink-tertiary`, 12px.

**Autoplay** on mount, once. It must never loop — a looping animation behind a person talking is
a screensaver.

---

## 4. Data

Everything comes from endpoints that already exist:

| Shown | Source |
|---|---|
| 15 posts, the captions | `GET /api/extract` → `corpus` |
| 28 questions, 2 requests, 0.65s | `GET /api/extract` → `totals` |
| the 5 trait chips | `GET /api/extract` → `slots` (pick the 5 with the highest confidence) |
| the message, the 3 chips | `GET /api/queue` → the `@gracelee` card, or `POST /api/ask` live |
| 24 options, 1 chosen | `GET /api/card/{id}` → `baskets_considered` |
| the reply | `GET /api/card/{id}` → `verdict.in_her_voice` |
| 50 dots, 24/14/4/8 | `GET /api/queue` → `stats` |

**Prefetch all of it before t=0.** The animation must not wait on a network call mid-sequence —
if a request is slow, hold the title card until everything has landed, then start. With the
backend down, run the whole sequence from the mock and show `from cache` beside the honesty label.

---

## 5. What this replaces

`V9` in `tano.pen` (the static three-part page) stays as the **reduced-motion fallback** and as
the thing a judge can read at their own pace afterwards. Same content, same copy, no sequence.
