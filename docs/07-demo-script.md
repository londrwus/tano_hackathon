# The 90 seconds — v2

Nine beats, built on `docs/09-GO.md` §7. Product first, no deck. Rehearse twice with a timer.
Every route and endpoint below is in `docs/10-API-CONTRACT.md`; nothing here is invented for stage.

**Open cold on a refusal, not a proof.** A real message and a machine declining to sell is a
stronger first five seconds than any counter.

---

## Presenter's hard rules — read before you rehearse

- [ ] Never say "autonomous", "AI", "clone", or "chatbot". Say **leverage**, **her standard**,
      **calibrated**.
- [ ] Never read a decimal pound or a float aloud. Say the whole pound, or say the band
      (*"about £50 to £55"*).
- [ ] **Always** attach the alternative to a refusal. Her no is worth nothing without what to buy
      instead — say both in the same breath.
- [ ] Name the person. Never "the user". It's @jessica, her sister, her mum.
- [ ] **The retired list. None of these may leave your mouth:** £14 · £7 · *0.7 fewer products* ·
      *0.2 fewer products* · *5/6 diverge* · *3/8 diverge* · *"a dermatologist says three products
      and seventy-two"* · *"forty-six pounds this machine just talked her out of spending"* · any
      *"she saves you money versus a dermatologist"* framing. All disproved by our own re-test.
      Every number in this script is resolved — see the table at the bottom.
- [ ] **Volunteer the 0/8.** It is in beat 3 and it is not cuttable. If there is any Q&A at all, it
      is the first thing you say. A judge who reads the repo finds it in ninety seconds; we say it
      first or we lose the room. Wording: `docs/09-GO.md` §2 Claim 1a.
- [ ] Never put `skippable_category` on screen. It flipped between `makeup` and `serum` across five
      identical extractions (stability 0.60).
- [ ] If anything breaks, keep talking and cut to the backup recording. Never debug on stage.

---

## Timing budget — 90 seconds, 3 cuttable beats

| # | Beat | Seconds | Cuttable if over? |
|---|---|---|---|
| 1 | Cold open — @jessica's DM and the £62 refusal | 18 | No |
| 2 | The scale — 4,800 DMs a month | 6 | **Yes** |
| 3 | Paste handle — fourteen slots, the 0/8, the held-out 3/3 | 21 | No |
| 4 | `/maya` floods — the four-way split | 10 | No |
| 5 | The held card + the referred card | 6 | **Yes** |
| 6 | Priya — it routes like her, 5 runs out of 5 | 6 | **Yes** |
| 7 | Forward the card — the sister re-decides | 9 | No |
| 8 | Flip a switch on `/onboard` | 8 | No |
| 9 | Close + final line | 6 | No |
| | **Total** | **90** | |

Cut beats **5, 2, 6** first, in that order, if the rehearsal runs long — note the order changed:
beat 6 is now the fidelity proof and is the *last* thing to lose. Every other beat is load-bearing:
1 is the cold open and the trust proof, 3 is the headline claim **and the volunteered 0/8**, 4 is
`/maya`, 7 is the share/dark-social payoff, 8 is the honesty beat, 9 is the close.

**Beat 3 may never be cut or trimmed below its two non-negotiable sentences:** the 0/8 and the
three-out-of-three.

---

## Beat 1 — Cold open: the machine declines the sale (18s, not cuttable)

**Spoken — say it exactly like this:**
> "A real DM. @jessica, eighty pounds to spend."
> "'I already have the night serum. Do I need the barrier cream too?'"
> "Her card comes back: no, she doesn't."
> "And look at what else isn't in it. The sixty-two pound serum. Maya rates that one eight out of ten."
> "Her own words, from her own shelf notes: 'Good. Not sixty-two quid good.'"
> "It just turned down the sale."

**Why this and not the old open.** The previous cold open claimed *"a dermatologist says three
products and seventy-two — that's forty-six pounds this machine just talked her out of spending."*
**We disproved it ourselves.** Under the symmetric fourteen-slot test both judges return the same
basket for @jessica; there is no £46 and no dermatologist gap. What replaces it is **stronger**,
because it is evidence rather than arithmetic: `E-04.6` is Maya's own verbatim note on the Glass
Drop, it is in `data/case-001-maya.json`, and no re-run can falsify a sentence she wrote. Per
`docs/research/tano-and-judges-intel.md` §5.4, **a demo that declines the sale is the single
strongest trust proof available in this room, and nobody else will show one.**

**⛔ Do not speak a basket total, a dermatologist comparison, or any saving in this beat.** The
refusal is the beat. Numbers here: £80 (her budget, E-01.5 context), £62 and *eight out of ten*
(E-04.6). Nothing else.

**On screen:** `/c/c-jessica`, already warm. The verdict headline animates in first — the refusal —
then the card scrolls to **"what she left out and why"**, which must carry the £62 Glass Drop row
with `maya_note: "Good. Not £62 good."` and its alternative. Her ceiling shows as a **band**, never
a decimal.

**Route/endpoint:** `GET /api/card/c-jessica` — a frozen demo id, guaranteed never to 404
(contract §9). Fields used: `verdict.is_refusal`, `left_out[]`, `ceiling.band`,
`ceiling.evidence_ref` (`E-04.6`).

**⚠ Lane A action, before rehearsal:** `cache/cards/c-jessica.json` must contain the £62 Glass Drop
in `left_out[]`, with its `instead`. This is a cache-content requirement, not a contract change —
`docs/10-API-CONTRACT.md` §9 already names `c-jessica` as the cold-open refusal card and already
cites `E-04.6` as its ceiling provenance. If the Glass Drop row cannot be in that card by the 14:30
freeze, the presenter reads the same two sentences over the card's existing refusal row, changing
*"look at what else isn't in it"* to *"and here's what she does with a sixty-two pound serum"* — the
refusal is still hers, still verbatim, and the beat still lands.

**If it breaks:** the frontend must already have failed over to `cache/cards/c-jessica.json` +
`cache/og/c-jessica.png` before this beat starts — `cached: true` on screen is fine, do not
apologise for it. If the whole frontend is down, cut straight to the 90-second backup recording
(fallback ladder rung 4, `docs/03-build-plan.md` §7) and keep narrating over it.

---

## Beat 2 — The scale (6s, **cuttable**)

**Spoken:**
> "Maya gets four thousand eight hundred messages like that a month."
> "She personally answers eighteen hundred."
> "The rest get silence."

**On screen:** a stat tile overlay on the same card screen — `4,800 DMs/month · 1,800 answered ·
70 hours`.

**Route/endpoint:** `GET /api/case` (`creator.dms_per_month`, `creator.reply_hours_per_month`).

**If it breaks:** these are static case-file facts. Bake them into the frontend as constants so
this beat never depends on a network call. If cutting for time, skip straight to Beat 3 — the
handle-paste beat carries the demo either way.

---

## Beat 3 — Paste handle: fourteen slots, the 0/8, the held-out 3/3 (21s, not cuttable)

**Spoken — say it exactly like this:**
> "Watch. I paste her handle."
> "Fourteen typed questions — her captions on one side, a dermatologist's clinical guidance on the
> other. Both answers back in under a second."
> "They agree on ten. They disagree on four."
> "And before anyone asks — the baskets come out identical. Eight shoppers out of eight."
> "Here's what does hold. Maya keeps a routing sheet in her head. This machine never saw it."
> "Dry, oily, redness — it matched three out of three."

**The two sentences that cannot be trimmed:** *"eight shoppers out of eight"* and *"three out of
three"*. The first is the honesty; the second is the claim. Cut words anywhere else in this beat.

**Why the old version is gone.** It said the disagreement *"changes real advice — three of eight
shoppers get a different basket, 0.2 fewer products, £7 less spent."* Re-measured over five full
repeats with fourteen symmetric slots, that is **0/8, 0.00 products, £0** — verified across ten
sweeps and four configurations. The four-slot disagreement is real and stays on screen; it simply
does not move a basket. **We volunteer that, we do not wait to be caught on it.**
(`docs/11-honest-headline.md` §2; `docs/09-GO.md` §2 Claim 1a.)

**On screen:** `/onboard` — handle-paste animation, then the side-by-side table (Maya column,
dermatologist column), each row showing its source caption and evidence ref. **Thirteen rows on
screen** — the fourteen slots minus `skippable_category`, which is **never rendered** (stability
0.60). Under the table, permanently
visible for the whole beat, in the same type as the rest of the card:

> `Same fourteen questions, both sides. Ten agree, four disagree. Same basket 8/8 — the difference
> is who it's for, not a cheaper bill. Routing vs her private sheet: 3/3, held out.`

Then the held-out panel: three rows — DRY → Cloud Cream, OILY → Daily Gel, REDNESS → Red Reset —
each ticked against `E-02.2`, labelled **"never shown to the machine"**.

**Route/endpoint:** `GET /api/onboard?handle=@mayarao`, then `GET /api/standard`.

**If it breaks:** fall back to the pre-warmed `cache/standard.json`. The table is static once
loaded, so a live-extraction failure only costs the "watch me paste it live" framing — say "here's
what that extraction produced" instead and carry on.

**If challenged on the 0/8** — the answer, in full, and do not flinch:
> "On the actual baskets, they land in the same place eight times out of eight. Once you ask both
> sides enough questions, the dermatologist and the creator buy the same things. The difference is
> who it's for and how it's explained — not a cheaper bill."

---

## Beat 4 — `/maya` floods: the four-way split (10s, not cuttable)

**Spoken:**
> "Now her inbox. Fifty real messages hit `/maya`."
> "Zero point eight five seconds. Two hundred and fifty judgments."
> "Seventy-eight per cent handled. The rest held, or referred on."

**On screen:** `/maya` — cards flood in and sort into four lanes (answered / asked back / held /
referred). Counter ticks up in tabular numerals. Header line visible: *"you approved 30 replies in
4 minutes."*

**Route/endpoint:** `GET /api/queue`.

**If it breaks:** serve `cache/queue.json`. The counter still ticks from a frozen payload; it just
doesn't re-run live. Never show a spinner past two seconds — the frontend must already have failed
over to cache before this beat starts.

---

## Beat 5 — The held card + the referred card (6s, **cuttable** — cut this one first)

**Spoken:**
> "This card is held. It's below her confidence line. Maya decides."
> "This one is referred. She said she's pregnant."
> "It won't touch it. And it never sends anything by itself. It drafts."

**On screen:** `/maya` — point at one `held`-lane card, then one `referred`-lane card showing the
refusal and `refer_to` field.

**Route/endpoint:** same `/api/queue` payload — `lane: "held"` and `lane: "referred"` cards.
`POST /api/queue/{id}/action` is visible but not pressed.

**If it breaks:** pick any two cards from the frozen queue cache with those lanes — the four-way
split guarantees at least one of each. If time is short, **this is the first beat to cut** — go
straight to Beat 6.

---

## Beat 6 — Priya: it routes like her (6s, **cuttable** — cut this one last)

**Spoken:**
> "Priya says her face freaks out at everything."
> "She gets Red Reset. Five runs out of five."
> "Nobody wrote that rule. It came out of a caption — and it agrees with the sheet in Maya's head."

**Why this beat replaced the £62 one.** The £62 refusal has moved to beat 1, where it is the cold
open. This slot now carries the fidelity proof, which is the other thing that held: **Priya → Red
Reset, 5 runs out of 5, Mode A, nothing forced** (`docs/11-honest-headline.md` §1). Do not repeat
the Glass Drop here.

**On screen:** `/c/c-priya` — the basket with Red Reset in it, and the `sensitive 0.98` condition
chip translated into plain words, never as a raw probability.

**Route/endpoint:** `GET /api/card/c-priya` — a frozen demo id, never 404s (contract §9).

**If challenged on how sure it is:** say the real number. *"That routing slot comes back at
oh-point-three-four confidence — stable in five out of five extractions, but genuinely torn
between Red Reset and telling her to buy nothing. That's the tension in her caption, and we show
it rather than round it up."*

**If it breaks:** serve the cached card. This is the last of the three cuttable beats to go — it is
the fidelity proof.

---

## Beat 7 — Forward the card: the sister re-decides (9s, not cuttable)

**Spoken:**
> "Now she forwards the card to her sister."
> "Oily skin. Forty pounds."
> "It re-decides. Same card. A different answer."
> "That's the forty-one per cent nobody can see."

**On screen:** `/c/c-sister` opens fresh — total and unspent update live, a small "child of"
provenance note visible.

**Route/endpoint:** `POST /api/card/c-jessica/redecide` (live), or open `GET /api/card/c-sister`
directly — a frozen demo id, child of `c-jessica` (contract §9).

**If it breaks:** `c-sister` is one of the four guaranteed-never-404 ids. Open it directly from
cache if the live redecide call fails — the beat still lands because the card already exists.

---

## Beat 8 — Flip a switch on `/onboard` (8s, not cuttable)

**Spoken:**
> "One more thing. We don't claim to know her standard. She does."
> "Flip this switch."
> "Watch the queue re-rank. Live."

**On screen:** `/onboard` — a toggleable slot switch flips; cut to `/maya` re-sorting.

**Route/endpoint:** `POST /api/standard/override` → returns the recomputed `/api/queue` payload.
Must return in under 400ms from cache (contract §2).

**If it breaks:** if Maya is in the room, she flips it herself — that's the whole beat. If the
override call is slow, do not wait on stage: cut to the recording of a prior successful run and
narrate over it in third person — *"when Maya flips this, the whole queue re-ranks."*

---

## Beat 9 — Close (6s, not cuttable)

**Spoken:**
> "Seventy hours a month becomes twelve cards a day."

**On screen:** a static closing stat tile — `70 hrs/month → 12 cards/day` — fading to black. No
live call; this cannot be the beat that fails.

**Route/endpoint:** sourced ahead of time from `GET /api/queue` →
`stats.at_real_volume.held_per_day` (12). Bake it into the closing slide; do not fetch it live.

**Final line — stop talking after it:**

> **"Maya no longer has to be awake for her audience to get her answer — because her judgement now
> runs without her."**

---

## Numbers — all resolved. No placeholder remains

Lane C finished the re-measurement (`docs/11-honest-headline.md`, from
`scripts/engine_decontaminated_v2.py`, modal over five full repeats against `jev-1.13.0`). Every
`⟦LANE-C: …⟧` token that was in this script is resolved below. **There is no unresolved token left
in this file** — grep for `LANE-C` and you get this table only.

| Former placeholder | Beat | Resolved value | What it means | Source |
|---|---|---|---|---|
| `slot-count` | 3 | **14** | Typed slots the standard is extracted through, both sides | `11-honest-headline.md` §1 · `data/standard-extracted.json` |
| `agree-count` | 3 | **10** | Slots Maya and the dermatologist agree on | §1, the fourteen questions |
| `disagree-count` | 3 | **4** | Slots they disagree on | §1, the fourteen questions |
| `divergence` | 3 | **0 of 8 shoppers** | Shoppers whose basket differs between the two standards | §1 · per-run `[0,0,0,0,0]` |
| `fewer-products` | 3 | **0.00** | Difference in basket size. **Retired as a claim** | §1 |
| `less-money` | 3 | **£0** | Difference in spend. **Retired as a claim** | §1 |
| — *(new)* | 1 | **£62 · eight out of ten · "Good. Not £62 good."** | The refusal the cold open now rests on | `E-04.6`, `data/case-001-maya.json` — evidence, not a measurement |
| — *(new)* | 3 | **3 of 3** | Her private routing sheet (`E-02.2`) recovered from public posts alone, held out of every prompt | §1, held-out check |
| — *(new)* | 3 | **0.65 s** | Extraction time for both standards | §1 |
| — *(new)* | 6 | **5 runs out of 5** | Priya → Red Reset, Mode A, nothing forced | §1 fidelity test |
| — *(new)* | 6 | **0.34** | `route_reacting` confidence — stable, low, and said out loud if asked | §5.7 |

**The three that resolved to zero are not spoken as claims.** `divergence`, `fewer-products` and
`less-money` came back **0/8, 0.00 and £0**. They appear in beat 3 only as the volunteered honesty
line — *"the baskets come out identical, eight shoppers out of eight"* — and nowhere else.

**⛔ The retired list, for the last time.** Never spoken, never on a slide, never in a hallway
answer: `£14` · `£7` · *0.7 fewer products* · *0.2 fewer products* · *5/6 diverge* · *3/8 diverge* ·
*"a dermatologist says three products and seventy-two"* · *"forty-six pounds this machine just
talked her out of spending"*.

**One number in this script does not come from `11-honest-headline.md` and is flagged as such:**
Maya's price ceiling on the Glass Drop, *"about £40"*, traces to `docs/02-the-pick.md` § the fence
table and `scripts/eval_asymmetry.py`, not to the re-measurement. It is therefore **not spoken in
beat 1** — the card shows a ceiling **band**, and the presenter says only the £62 and her words.
