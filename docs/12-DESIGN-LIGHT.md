# 12 — LIGHT DESIGN SYSTEM (v3) — FROZEN

**This replaces `docs/04-visual-language.md` entirely.** The dossier/dark direction is cut:
it read as hard to understand, and clarity beats theme. `04` stays in the repo as the audit
trail; nothing builds from it any more.

**Direction: the soft pastel iOS health-app look.** Not austere system-white — that version was
built, reviewed and rejected as too generic. The reference is a fitness/nutrition app UI: a soft
lilac-grey page, white cards floating on it with diffuse shadows, and **bento tiles each carrying
its own pastel tint and its own ink colour**. Rounded generously. Soft pill progress bars instead
of charts. Friendly, warm, immediately readable.

Rules of the look:
- **One tint per metric**, used consistently — the same idea always gets the same colour.
- **Tinted tiles carry no shadow and no border.** White cards carry a soft shadow and no border.
- Numbers are big, bold, and in the tile's ink colour. Labels stay grey.
- Confidence and progress are **soft pill bars**, never digits, never a chart axis.
- Nothing is a rectangle with a 1px grey border. That was the generic tell.

The canonical rendering of this is the `V4 /onboard - pastel` frame in `tano.pen`, exported to
`design/v4c/`. When this document and that frame disagree, the frame wins.

Everything below is frozen. Build against this file and only this file.

---

## 1. Principles — in priority order

1. **One idea per screen, stated in plain English at the top.** If a judge can't say what a
   screen is for in five seconds, the screen is wrong.
2. **Whitespace is the layout.** Apple separates things with space, not with lines and boxes.
   Default to no border and no card. Earn every container.
3. **Type carries the hierarchy.** Two or three sizes per screen, big jumps between them.
   Never solve a hierarchy problem with colour.
4. **Motion explains, never decorates.** The only things that move are things that are
   genuinely happening: judgments landing, a number counting, a panel resolving.
5. **Colour is for state and data only.** Everything else is black on white.
6. **Show the work.** The Jev fan-out is the product. It gets the biggest thing on the page.

---

## 2. Tokens

**`frontend/src/styles/tokens.css` is already written and IS the authoritative copy.** Read it,
consume it, do not edit it. Extract below for reference.

```css
:root {
  color-scheme: light;

  /* surfaces — page is soft lilac-grey, white cards float on it */
  --bg:              #f3f2f8;
  --bg-card:         #ffffff;
  --bg-sunken:       #f5f5f7;
  --bg-raised:       #ffffff;
  --bg-hover:        #ecebf3;
  --hairline:        #d2d2d7;
  --hairline-soft:   #e8e8ed;

  /* TINTS — pastel fill + a dark ink that passes contrast on it. One tint per metric,
     used consistently. Text on a tint is --ink or the matching *-ink, NEVER the tint. */
  --mint:   #e6f6ec;  --mint-ink:   #0a7d3f;
  --sky:    #e6f0fd;  --sky-ink:    #0b5fc0;
  --butter: #fdf4e2;  --butter-ink: #8a5c07;
  --blush:  #fdeaf0;  --blush-ink:  #c02a5c;
  --lilac:  #eeeafc;  --lilac-ink:  #5a3fc0;
  --peach:  #fdeee3;  --peach-ink:  #b0511b;

  /* ink */
  --ink:             #1d1d1f;   /* Apple near-black. NEVER pure #000 */
  --ink-secondary:   #6e6e73;
  --ink-tertiary:    #86868b;
  --ink-on-accent:   #ffffff;

  /* accent */
  --accent:          #0066cc;   /* 4.6:1 on white */
  --accent-hover:    #0055aa;
  --accent-wash:     #e8f1fc;

  /* state — all >=4.5:1 on --bg for text, >=3:1 for marks */
  --ok:              #0a7d3f;   --ok-wash:      #e6f4ec;
  --info:            #0066cc;   --info-wash:    #e8f1fc;
  --warn:            #9a5b00;   --warn-wash:    #fdf1e0;
  --danger:          #d70015;   --danger-wash:  #fdeaec;

  /* data — categorical, max 3, all-pairs distinguishable on white */
  --series-1:        #0066cc;
  --series-2:        #b8500f;
  --series-3:        #0a7d3f;
  --series-muted:    #c7c7cc;

  /* elevation — Apple shadows are almost invisible. Resist deepening these. */
  --shadow-sm:  0 1px 2px rgba(0,0,0,.04), 0 1px 1px rgba(0,0,0,.03);
  --shadow-md:  0 2px 6px rgba(0,0,0,.05), 0 8px 24px rgba(0,0,0,.05);
  --shadow-lg:  0 4px 12px rgba(0,0,0,.06), 0 16px 48px rgba(0,0,0,.08);

  /* radius */
  --r-sm: 8px;  --r-md: 12px;  --r-lg: 18px;  --r-xl: 28px;  --r-pill: 980px;

  /* space — 4pt scale. Use these, never arbitrary px. */
  --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:24px;
  --s6:32px; --s7:48px; --s8:64px; --s9:96px; --s10:128px;

  /* type */
  --font: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text",
          "Segoe UI Variable Display", "Segoe UI", Inter, system-ui, sans-serif;
  --font-num: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", system-ui, sans-serif;
}
```

**Dark mode: do not ship one.** Set `color-scheme: light` and stop. If the OS is in dark mode
the page stays light.

---

## 3. Type scale — frozen

| Role | Size / line-height / weight / tracking | Notes |
|---|---|---|
| Display | 72 / 1.05 / 700 / -0.025em | One per screen, maximum |
| Title 1 | 48 / 1.08 / 700 / -0.022em | Screen headline |
| Title 2 | 32 / 1.15 / 600 / -0.018em | Section |
| Title 3 | 24 / 1.25 / 600 / -0.012em | Card headline |
| Body L | 19 / 1.5 / 400 / -0.005em | Her voice, verdicts, anything a human reads |
| Body | 17 / 1.5 / 400 / 0 | Apple's default body size |
| Caption | 14 / 1.4 / 400 / 0 | `--ink-secondary` |
| Label | 12 / 1.3 / 600 / 0.02em | Uppercase allowed HERE ONLY, sparingly |
| Metric | 56 / 1 / 600 / -0.02em / `tabular-nums` | Counters |

**No monospace anywhere except a raw evidence ref (`E-04.6`) and live numbers mid-count.**
The letter-spaced-uppercase-monospace chrome from v2 is **deleted**. It is the main reason the
old design read as hard.

Set `font-variant-numeric: tabular-nums` on every number that animates.

---

## 4. Components

- **Card** (`.card`) — white, `--r-lg` (20px), `--shadow-sm`, padding `--s5`. **Never a border.**
- **Tinted tile** (`.tile .tile-<tint>`) — pastel fill, **no shadow, no border**, `--r-lg`.
  This is the bento unit. A grey label on top, a big number in the tile's `*-ink` beneath it,
  an optional 17px lucide icon in the same ink top-right, and a `.meter` pill bar at the foot.
- **Meter** (`.meter` + `.meter-fill`) — an 8px pill. Track is 85% white on a tint, or `--bg` on
  white. The fill is the tint's ink colour and its **width** is the value. This is how confidence
  and progress are shown everywhere. **Never print the number.**
- **Tab bar** — a floating white pill with `--shadow-sm`; the active tab is a `--lilac` pill with
  `--lilac-ink` text.
- **Button** — pill. Primary: `--accent` fill, white text, 17px/600, padding 12/24.
  Secondary: `--bg-sunken` fill, `--ink` text, no border. Tertiary: text-only `--accent`.
- **Chip** (the `/ask` taps) — pill, `--bg-sunken`, 17px. Selected: `--accent` fill + white,
  **and** a check glyph. Min height 44px, the Apple touch target.
- **Lane badge** — wash background + matching ink + an icon + the word. Never colour alone.
- **Stat** — the metric size number over a `--ink-secondary` caption. No box.
- **Evidence ref** — 12px `--ink-tertiary`, plain. It is a footnote, not a stamp.

**Deleted from v2, do not reintroduce:** redaction bars, `CLASSIFIED` / `SEALED` / `TOP SECRET`
marks, `SHEET 05/17`, the stamp tilt, letter-spaced uppercase chrome, dossier black.

---

## 5. ⭐ THE HERO — "Watch it read her channel"

**This is the single most important thing in the build and it gets the most design effort.**
It lives on `/onboard` and it is demo beat 3. Everything else is supporting cast.

The moment: you paste `@mayarao`, and you **watch Jev read her public posts and resolve her
standard in real time.** Right now that is a static list of rows and it wastes the best asset
we have.

### What is on screen, in order

1. **Her captions stream in** as small cards — the real strings from her public posts.
   They land fast, ~8 of them, and settle into a quiet column on the left.
2. **The fan-out.** From those captions, **28 questions fire at once** (14 slots × 2 judges) —
   drawn as lines/dots leaving the captions and arriving at the slot list. They must visibly
   go *in parallel*, not one at a time. That parallelism IS the point: it is what Jev is.
3. **Slots resolve.** Each of the 14 slots flips from pending to its answer as it lands,
   with a **confidence** shown as a filling ring or bar — never a printed decimal.
4. **A live counter** in the corner, counting up in tabular-nums as it runs:
   `28 questions · 2 requests · 0.65s`
5. **Each resolved slot shows the caption it came from** — a one-line quote and its `E-0x` ref.
   That is the whole credibility of the product and it must be visible without a click.
6. **When it settles**, the Maya-vs-dermatologist comparison resolves underneath:
   10 agree, 4 disagree, with the 4 disagreements highlighted.

### Honesty rules — non-negotiable, a judge will ask

- The **elapsed counter must show real measured time**, from the API response. Never a
  hand-tuned duration dressed up as a measurement.
- Jev returns all answers in **one response per judge** — there is no genuine per-slot arrival
  time. So: the reveal is a **replay**, and it says so. A small `REPLAY` label, and a speed
  control (`1× · 0.25×`) where **0.25× is honestly labelled "slowed down to be watchable"**.
  At 1× it runs in the real 0.65s and is a blur — that is the honest default and it is
  genuinely impressive.
- **Never invent a per-slot latency number.** Per-slot you may show confidence, never ms.
- If the API is unavailable, replay from the frozen cache and say `from cache` quietly.

### The second visual — 1,000 judgments (on `/maya`)
The queue's counter should animate `0 → 1,000 judgments · 1.65s` in tabular-nums as the four
lanes fill. One animation, real numbers, then it stops. Do not loop it.

---

## 6. Motion

- Easing: `cubic-bezier(0.25, 0.1, 0.25, 1)`. Durations: 200ms UI, 400ms panel, 600ms+ reveal.
- Animate `transform` and `opacity` only.
- **One hero animation per screen.** Everything else is still.
- `prefers-reduced-motion: reduce` → everything lands instantly in its final state, the
  counters show their final values, and the replay control still works.

---

## 7. Layout

- Max content width **1120px**, centred, `--s7` side gutters. `/c/<id>` caps at **560px**.
- Design for a projector at 1440×900 **and** a real phone at 390×844. Both get tested.
- 16px minimum side gutter on phone. No horizontal scroll at any width, ever.
- Touch targets ≥44×44.

---

## 8. Hard rules (carried over — these are judged)

- **Never a decimal pound or a float on screen.** Money is whatever string the API returned;
  the frontend never formats it. Confidence is a ring or a bar, never digits.
- **Colour never carries meaning alone** — always an icon and a word too.
- **Her voice is never set in a system-chrome style.** It reads as a person talking.
- Every verdict carries its evidence ref and the caption behind it.
- A refusal always shows the alternative.
