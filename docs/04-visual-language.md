# Visual language — the dossier

> # ⛔ SUPERSEDED — DO NOT BUILD FROM THIS FILE
>
> **Replaced in full by [`12-DESIGN-LIGHT.md`](./12-DESIGN-LIGHT.md) (v3, light/Apple).**
>
> The dark dossier direction below was built and reviewed, and it was cut: it read as hard to
> understand. Its letter-spaced uppercase monospace chrome was the main offender. Clarity beats
> theme, so v3 is light, Apple-like, and puts the Jev extraction visual at the centre instead of
> the evidence-envelope styling.
>
> Kept here as the audit trail. The palette-validation method in §2 and the encoding rules in
> §4 were sound and their logic carries over to v3's tokens; the colours themselves do not.

The case files hand us a complete art direction for free. **Use it.** Every team will build a
generic SaaS dashboard in Inter-on-white. We build the thing that looks like it was pulled out of
the evidence envelope they handed us that morning.

This matters mechanically, not just aesthetically: the judges spend 90 seconds with us. A screen
that visually rhymes with the dossier in their hands says *"we read the evidence"* before we say
a single word — and *"use of the evidence"* is an explicit judging criterion.

---

## 1. The source material

From the PDFs: `TOP SECRET` · `EYES ONLY // DO NOT DUPLICATE` · `CLASSIFIED` · `REF SHD-001-E04` ·
`SHEET 05/17` · `CHAIN OF CUSTODY` · `SURVEILLANCE PHOTO WITHHELD` · `Sealed` ·
letter-spaced capitals · monospace reference codes · redaction bars · evidence numbering (`E-01.3`).

Three details worth stealing precisely:

1. **Everything is numbered and referenced.** Every card in our UI carries its source tag
   (`E-04.6`, `E-09.2`). This is free credibility and it is *literally* citing our evidence.
2. **`WITHHELD` / redaction.** The case file redacts photos. We can redact too — and un-redact as
   a reveal animation. A black bar that wipes away to expose Maya's verdict is a one-line CSS
   transition and it is the most on-theme reveal available to us.
3. **Sheet count.** `SHEET 05/17` in the corner. Costs nothing, sells the whole frame.

---

## 2. Tokens

Adapted from the validated reference palette (`dataviz` skill). **The data colours below were
re-validated against our actual surface** — `node scripts/validate_palette.js "#3987e5,#d95926,#199e70"
--mode dark --surface "#131311" --pairs all` → **ALL CHECKS PASS** (CVD ΔE 9.4, normal-vision ΔE 20.9,
all ≥3:1 contrast). Do not substitute hues without re-running that command.

```css
.dossier {
  color-scheme: dark;

  /* surfaces — dossier black, warm not blue */
  --page:            #0a0a08;   /* the desk */
  --surface-1:       #131311;   /* the sheet (validated chart surface) */
  --surface-2:       #1c1c18;   /* raised card */
  --redaction:       #000000;

  /* ink */
  --text-primary:    #f4f2e9;   /* typewriter cream, not pure white */
  --text-secondary:  #c3c2b7;
  --text-muted:      #898781;   /* axis + labels + ref codes */
  --rule:            #2c2c2a;   /* hairline gridline */
  --baseline:        #383835;

  /* the stamp — used for CLASSIFIED marks and the honest NO. Never for a data series. */
  --stamp:           #d03b3b;   /* = status/critical */

  /* data — diverging, for P(the creator recommends this) */
  --div-yes:         #3987e5;   /* high probability  */
  --div-mid:         #383835;   /* neutral gray midpoint — never a hue */
  --div-no:          #d03b3b;   /* low probability   */

  /* data — categorical, max 3 slots (all-pairs validated) */
  --series-1:        #3987e5;
  --series-2:        #d95926;
  --series-3:        #199e70;

  /* status — icon + label always, never colour alone */
  --good:            #0ca30c;
  --warning:         #fab219;
  --serious:         #ec835a;
  --critical:        #d03b3b;
}
```

**Light mode:** skip it. This is a single-screen demo shown once, in a room, on our machine.
Shipping a second validated palette is hours we do not have. Set `color-scheme: dark` and move on.

---

## 3. Type

| Role | Face | Notes |
|---|---|---|
| Reference codes, metrics, labels | `ui-monospace, "SF Mono", "Cascadia Mono", Consolas, monospace` | `letter-spacing: 0.18em; text-transform: uppercase` for headers — this single rule does 80% of the dossier look |
| Body / verdicts / the creator's voice | `system-ui, -apple-system, "Segoe UI", sans-serif` | Her words must read as *hers* — plain, warm, not stencilled |
| Hero number | system sans, `font-variant-numeric: tabular-nums` | Per the dataviz skill: no display or serif face anywhere |

The tension between letter-spaced monospace *chrome* and plain sans *content* is the whole look.
Don't set her voice in monospace — it makes her sound like a machine, which is the exact failure
mode the brief warns about.

---

## 4. Encoding rules for our data

Decided by the data's job, per the `dataviz` procedure — **form first, colour last**.

| Quantity | Job | Form | Colour |
|---|---|---|---|
| `P(creator recommends X to person Y)` | polarity around 0.5 | heat cell / dot | **diverging** blue↔red, gray midpoint |
| Trust-risk `score` 0–3 | ordered magnitude | bar or ramp | **sequential**, one hue |
| Audience cohort (Askers / Savers / Sharers) | identity, 3 classes | dot colour | **categorical** slots 1–3 |
| "She would say NO" | state | badge | **status/critical + icon + label** |
| Confidence | certainty, secondary | opacity or ring thickness | not a hue |

**Hard rules we will be tempted to break:**
- **Never a dual axis.** Two measures → two charts.
- **Never cycle categorical hues.** We have three validated slots for all-pairs use. A fourth
  category folds into "Other" or becomes a facet. Our natural cut is exactly three, so this is free.
- **Confidence is not a colour.** Encode it as opacity/ring so it never competes with the verdict.
- **Colour never carries meaning alone.** The NO badge ships with an icon and the word.
- **Text wears text tokens**, never the series colour.

---

## 5. Motion

Motion is where the WOW lives, and we have a rare licence for it: **our judgments genuinely arrive
in ~1.2 seconds for 3,000 of them.** We are not faking a loading bar — we are streaming real results.

| Beat | Motion | Why |
|---|---|---|
| Batch fires | Cells/dots flip from `--div-mid` to their verdict colour as results land | Honest: it is the actual response order |
| The counter | `0 → 3,000 judgments · 1.18s · $0.02` ticking in tabular-nums | The number *is* the argument |
| The reveal | Redaction bar wipes off the verdict card | On-theme, one CSS transition |
| The NO | Card stamps in at a slight angle with `--stamp` | The trust proof deserves its own beat |

Keep it to **one** hero animation. A screen where everything moves reads as a screensaver.

**Performance:** 3,000 animated cells is fine in DOM if they are divs in a CSS grid with
`transform`/`opacity` transitions only (both compositor-driven). Beyond ~5,000 marks, move to a
single `<canvas>`. Do not animate `background-color` on thousands of nodes — animate `opacity` over
a pre-coloured cell. Respect `prefers-reduced-motion` with an instant-fill fallback.

---

## 6. Components

- **Evidence card** — hairline border, ref code top-left in `--text-muted` monospace, content in sans.
- **Stat tile** — big tabular number, monospace caption beneath. Per `choosing-a-form.md`, a single
  headline number is a stat tile, *not* a chart. `4,800 DMs/month`, `70 hrs`, `1 person` want to be
  three tiles, not a bar chart.
- **Verdict card** — the creator's actual words, her rating, the honest price note, and the badge.
- **The matrix** — the hero. CSS grid of cells, diverging colour, hover tooltip on every cell
  (the dataviz skill makes the hover layer a default, not an extra).
- **Redaction bar** — `background: var(--redaction)` with a wipe transition.

---

## 7. Interaction floor (non-negotiable per `dataviz`)

- Every mark gets a **hover tooltip**. For the matrix: person, product, probability, and the
  creator's own note. That tooltip is where "use of the evidence" becomes tangible — a judge
  hovering a random cell should see a real quote from a real exhibit.
- **Filters in one row above the chart**, never beside or below.
- **A table view exists.** Trivial here, and it covers the contrast-relief rule.
- Hit targets larger than the mark.

---

## 8. Pen workflow

The user's sequence is **design first, then frontend**.

> ⚠️ **Blocker to clear first:** the `pencil` MCP tools currently error with
> *"A file needs to be open in the editor"*. Open or create a `.pen` file in the Pen app before
> the design step, then `mcp__pencil__get_app_state` and `mcp__pencil__read_skill` will work.

Design in Pen: (1) the single hero screen at 1440×900 — the projector resolution, not a phone;
(2) the verdict card in both states (YES and the honest NO). That is all we need before code.

**Design for the projector.** Contrast in a bright room at 3m is a different problem than contrast
on a laptop. Ship larger type and heavier weights than feel right on the desk.
