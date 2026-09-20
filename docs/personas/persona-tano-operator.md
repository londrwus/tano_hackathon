# TANO OPERATOR ASSESSMENT — THE FENCE
*Will Caplan × Sagar Shah seat. Adversarial by request. Grounded in `C:\Users\Lenovo\Documents\tano_hackathon\docs\evidence\case-001-operation-shade.txt` and `docs\02-the-pick.md`.*

---

## 1. Real problem, or demonstrable problem?

**Partly real, and narrower than you think.** Count the documented demand. E-01 gives twelve intercepts. Exactly **one** is a price-worth question (E-01.4, *"is the cloud cream actually worth £38 or am i being influenced"*). One more is partially price-bounded (E-01.2, *"dry skin + redness and £60"*). The other ten are: shade lookup (E-01.1), pick-one (E-01.3), stack redundancy (E-01.5), *"i dont even know what my skin type is"* (E-01.6), trust statement (E-01.7), occasion (E-01.8), a two-product constraint (E-01.9), delayed intent (E-01.10), transfer of trust (E-01.11), personalisation (E-01.12).

The Fence, as described, serves **1–2 of 12**. And its entry gesture — drop a photo — requires the user to have already narrowed to a single candidate. Sheet 04's Hannah (*"There are 500 versions of this. Just tell me"*) and Grace (*"I have 5 mins, give me the two things"*) cannot start. Neither can E-01.2 or E-01.9. Those are **build-me-a-basket** requests; you built a **judge-this-one** machine.

**Concrete fix, near-zero cost:** invert the query. You already hold 359 scored products and ten price curves. A query of `{£60, dry, redness, max 2 items}` is a filter-and-sort over a precomputed array — *zero inference at query time*, the same trick as your draggable line. That converts E-01.2, E-01.5, E-01.9 and E-01.12 from unserved to served for roughly a morning's work. Do it before you polish the scan line.

## 2. Autonomy: currently for the audience, not for Maya

Sheet 02 states the mission: *"gets her out of the loop."* 4,800 DMs, **70+ hrs/month**. The Fence removes **zero** messages from her inbox, because it does not sit where messages arrive. She ends the week with a beautiful wall and 4,800 DMs.

Don't build a DM bot — E-08.1 kills it by name. But the verdict card *is* the reply. One "copy reply link" button is the only honest bridge between *"value to a real audience member"* and *"gets her out of the loop."* Without it, "we make her work autonomous" is false and sheet 02 is sitting in the judges' hands.

Then **name what you don't take.** E-01.8 (*"first date Friday HELP"*) is not yours and should not be. A product that states its own coverage reads as more credible than one that implies omniscience.

## 3. Onboarding — your answer exists in the repo and is not in the product

The case file handed you a fabricated luxury: E-04 is ten rows with price, numeric rating *and* a verbatim reservation, pre-scored. **No real creator has that file.** It exists because Tano's organisers built it. Your own §5 proves the sentences matter — held-out Glass Drop moves 0.14 → 0.08. Strip the notes across the board and you regress toward your documented Attempt-1 failure (the generic £20–28 prior).

Your onboarding is already measured and sitting unused: **voice → typed judgement, 12s of speech, 1.4s to verdicts, `no_signal` on the seven products she didn't mention.** That `no_signal` behaviour is the whole prize — it means capture is **incremental and honest**. She doesn't fill a form; she talks about what she used this week, coverage accretes, the rest stays visibly blank instead of hallucinated.

Two things you must say out loud rather than imply:
- **Time to first value: one 12-second voice note.** But 12 seconds covers 2–3 products. Ten-row density is ~4–6 minutes cumulative, spread across days. State that number; don't let a judge do the arithmetic for you.
- **Don't make her type the product list.** She already maintains one — her affiliate/ShopMy feed, because she gets paid from it. Import the list, speak the opinions. That is the difference between a form and a conversation.

And on day one, **show wide confidence bands**. A system that says *"I don't know her well enough on this one yet"* and narrows over two weeks is more trustworthy and creates the return loop. Your `docs\03-build-plan.md` and `docs\05-backend-architecture.md` contain **zero** occurrences of "onboarding" — this is currently unbuilt and unplanned.

**Demo move:** start from an *empty* standard, record Maya live at 17:00, show the wall re-rank. Far stronger than a pre-computed sweep, and it answers sheet 16's *"what feels like work?"* in one gesture.

## 4. Would I ship it inside Tano? Yes — but not the part you're proudest of

The Wall is the lowest-commercial-value object in the build. It is a demo. Here is what I'd ship, in order:

**(a) A Charlie scoring step.** Brand gives Charlie a SKU + price + claims. Today Charlie ranks our database on category, audience and price band — metadata and vibes. Insert the sweep: for each creator with a standard on file, P(endorse at sticker) and headroom. **4,000 creators × 51 rungs = 204,000 nouls; at your measured 2,535/sec that's ~80 seconds and under a dollar.** That is a shippable step this quarter, and it is the single most concrete sentence you can say in the room.

**(b) The pre-emptive decline.** Charlie stops sending briefs to creators whose line sits below sticker. Our $35–45/creator is largely outreach, negotiation and logistics — this kills spend *before* it's incurred, and more importantly it stops burning the creator relationship, which is the half of the business we deliberately do not automate.

**(c) Headroom as the product, not refusal.** You're selling the negative because it's dramatic. The money is in the positive: SPF 50 at +£34 says *this creator can carry your product £34 above its price and her audience will still follow.* That is a per-creator, per-SKU credibility premium that no agency can quote today. Refusal is the trust proof; headroom is the invoice.

## 5. "This is Charlie, pointed the other way"

**Cut it.** It sounds good and dies on the first follow-up. Charlie runs an operational chain — outreach, negotiation, logistics, contracting, reporting. The Fence runs none of it. "Pointed the other way" implies a symmetry that doesn't exist, and I will ask you what runs.

What I actually want to hear:

> *"Charlie knows which creators exist. It does not know what any of them will actually say yes to. We built the missing input: a per-creator, per-SKU, per-price probability of endorsement, across your whole roster in 80 seconds for under a dollar."*

Test any line against *"what does Charlie do differently on Monday?"* If it can't survive that, it's decoration.

## 6. Attribution — you built the answer and filed it as "beat 3"

`grep -i attribut` across `docs\*.md` returns nothing on the 16:00 drop. That is the most expensive omission in the build, because attribution is what we sell ROAS on.

The drop is unambiguous: E-09.2 61% of repeat buyers sent no DM; E-09.3 top-decile savers convert 2.4×; **E-09.4 41% of high-value buyers arrived via a private share from a friend**; E-09.5 median lag 4.6 days. E-10 confirms the shape — Rina (0 DM / 8 saves / £71), Tara (0 / 11 / £122), Zoe (0 / 9 / £86), Alice (0 / 7 / £94) all bought; Liv (4 DMs / 1 save), Ella (3 / 2), Nora (1 / 1) all did not.

The Wall does nothing here. **The verdict card does everything.** A verdict is a shareable object — it is precisely what Megan sent (E-10.2: 1 DM, 6 shares, bought in 1 day). Give each card a permanent id and URL, carry a `parent_card_id`, put the affiliate link on it, and log open / return / click:

- the **save** becomes observable (card opened, returned to);
- the **private share** becomes observable *for the first time* — the friend's open is a measured trust transfer;
- the **4.6-day lag** becomes observable.

No new model work. It is a link schema. It converts the 61–71% dark channel into a measurable chain, and it makes you the first creator-side artifact whose **unit of sharing is also the unit of measurement.** Be honest about the limit — it measures only what flows through the card, not dark social generally — but that claim is defensible and nobody else in the room will make it.

## 7. The bigger business you haven't noticed

Selling Maya a tool is dead — 50K, one person, affiliate income (sheet 03). Creators at that tier don't buy SaaS.

The real move: **pre-campaign credibility underwriting.** Run the standard across the roster and we can tell a brand, *before spend*: "of 4,000 creators, 290 can carry a £62 serum credibly, 41 sit in your audience band, expected decline rate X." Pair that with §6's post-spend chain and you have a **prediction and a measurement in the same object** — which is the loop that lets Tano price on outcome instead of per-creator. That upgrades us from an agency with agents to an underwriter of creator-led spend. Underwriting is a far better business than services, because the number you produce is the thing a brand's finance team actually buys.

Second, quieter move: **the standard is the creator's and she keeps it.** Our binding constraint is creator supply and goodwill. "We'll build your standard, you own it, you take it with you" is a roster-acquisition tool wearing a product costume, and it is the literal execution of Caplan's "unlock the human."

## 8. What it does not do before it touches a real brand campaign

1. **Consent and provenance.** Nobody asked Maya whether a brand may see her line. Show a brand "her line is £40, you sell at £62" and you've handed them a negotiating weapon against the creator — the exact opposite of our position. **Reframe the draggable handle** from a fidelity mitigation (your §8) into the *ownership and consent* gesture: creator-owned, creator-visible, share-gated per brand.
2. **ASA/CAP disclosure.** UK, and absent from every doc. If a verdict card touches a product she's been paid for, that card is an ad and needs labelling — including one she didn't type. Needs a paid/unpaid flag per item and a disclosure string on the card. Twenty minutes of work; it's the line between a toy and something Skin+Me's legal will open.
3. **Public disparagement of real brands.** The Wall stamps **CeraVe, St. Ives, M. Asam** — named, real, commercial products — as UNPROVEN under a named creator who has never touched them. Two failure modes: a letter to Maya, or a red stamp on a *Tano client's* product on stage at 20:00. **Check the demo wall against our client list tonight.** Structural fix: negatives are private-by-default and shown *to the person who asked* (advice, not broadcast); positives are publishable. Note this collides with your hero beat — the wall of red stamps cannot ship as-is, so know now which version is the demo and which is the product.
4. **Freshness.** A September standard is stale by November. No re-capture loop exists anywhere in the docs. The 12-second voice note is the maintenance mechanism; place it.
5. **Catalogue reality.** Open Beauty Facts is fine for a wall; it is not commerce inventory. Real deployment needs SKU-level, in-stock, current-UK-price, affiliate-linked data — and a **price-change recompute trigger**, which no architecture doc contains. A price-based product with stale prices is wrong in a specific, embarrassing way: your line is £44, the retailer drops to £39, the verdict flips and nobody noticed.
6. **No validation set.** The held-out test proves internal consistency, not external correctness — we have never observed Maya declining at £X. Fine for a hackathon, not for Bloom & Wild. **Your best ask in the room:** *"Tano can backtest this in a week against Charlie's own accept/decline history."* That sentence gets you hired.

## 9. What reads as naive about this industry

- **You think the number is the hard part.** It isn't. Getting a creator to hand over her standard, keep it current, and let a brand see any slice of it is the hard part — and it is a relationship problem, i.e. the half we refuse to automate.
- **You model endorsement as a function of price alone.** It's price × category fit × what she posted last week × **how many other deals she's running this month** × existing exclusivity clauses. Caplan's "four or five brand deals in a single month" is a *saturation* argument, not a price argument. Her line for your serum drops if she posted two other serums this month. **Add recent commercial load as a state field.** One extra field in the noul, and it's the most Tano-native improvement available to you.
- **You assume creators want their refusals made legible.** A system that quantifies where she *won't* vouch also quantifies where she *will* — that is a leverage document in a negotiation. A meaningful share of any roster declines on that basis alone.
- **"UNPROVEN" is a judgement about a marketing word, not a formulation.** From the write-up, the model read *"Renewing"* and *"Tightening"* off packaging. That genuinely tracks her taste — she rejects hype — but don't let it be heard as ingredient-level assessment. Say *"it judges the claim, not the chemistry"* and own it.

## 10. Would I interview you?

**Yes**, and specifically for §5 of `docs\02-the-pick.md`: you ran it, it failed with a generic price prior, you diagnosed *why*, you fixed the framing by giving the model her price universe, you **kept the broken script in the repo** (`scripts\price_curve_sweep_v1_FAILED.py`), and you ran a held-out test against your own claim. You also caught your own n=2 trap on E-03.5 unprompted. That behaviour is rarer than the idea and it's what I hire for.

What would stop me: leading with the scan line and the cost counter instead of the held-out test; saying "Charlie pointed the other way" and having no Monday answer; naming "creators" as the buyer; not having priced the wall against our client list.

**One demo note.** `359 PRODUCTS · 718 JUDGMENTS · 3.9 SECONDS · $0.009` is native dialect for the TypeSafe judge and it's the least interesting number on screen for me. Put **one** Tano number next to it — *"your full 4,000-creator roster screens against one brief in ~80 seconds for under a dollar"* — computed from your own measured 2,535/sec, not asserted. That sentence wins Best Commercial Potential. The wall does not.

**Verdict: a feature today, a company only if you ship the shareable verdict card with an id.** The card is the attribution primitive, the share primitive, the reply primitive and the consent surface all at once. It is currently beat 3 of a screen. It should be the product.