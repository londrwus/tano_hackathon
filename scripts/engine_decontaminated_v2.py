"""DECONTAMINATION v2 - MORE SLOTS, NOT MORE RULES.

v1 (`engine_decontaminated.py`) removed every hand-written rule from Maya's judge state and
extracted six typed slots from her public posts, asking the SAME six of clinical guidance.
Honest baseline: 3/8 shoppers diverge, 0.2 fewer products, GBP7 less.

v1's failure: the baskets OVER-COLLAPSE. "The fewest possible products" dominates and Maya
returns `SPF 50` alone for almost everyone, including Priya, whose skin reacts to everything
and who should be getting Red Reset. Fidelity got worse as honesty got better.

v2's fix is deliberately NOT "add the missing rule back". It is: her captions already contain
her conditional logic, so EXTRACT MORE OF IT through the same typed-slot machinery.

  * 6 original slots, unchanged, so the before/after diff is one variable.
  * + 4 CATEGORY-PRIORITY / SCOPE slots (what she defends, what she thinks is interchangeable,
      what she drops first, and WHEN her "take things away" rule applies).
  * + 4 ROUTING-CONDITION slots, each phrased as a CONCRETE SITUATION a real person describes
      ("my face freaks out", "my cheeks are red and angry") rather than a bare label.
  * Every one of the 14 is asked of the dermatologist too, word for word, against clinical
    guidance instead of captions.
  * The extracted routing lands in `state` as STRUCTURED DATA under `her_written_routing_rules`
    (as prose it measurably did not fire), identically keyed on both sides.
  * Shoppers' skin is multi-label: one `noul` per condition, extracted, not typed by us.

HELD OUT ON PURPOSE: `data/case-001-maya.json -> decision_rules.routing` (E-02.2) is Maya's own
private routing sheet and it literally says REDNESS -> Red Reset. It is NEVER shown to the
extractor. It is only used at the very end to score the routing we discovered from her PUBLIC
posts. If we had fed it in, the fidelity result would be a tautology.

Run it. Publish whatever number comes out.
"""
import os, sys, io, asyncio, json, time, itertools, statistics

import httpx

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_env():
    """Read .env into the environment. Never printed, never logged."""
    p = os.path.join(REPO, ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_env()

URL = "https://api.typesafe.ai/v1/systemone"
H = {"Authorization": "Bearer %s" % os.environ["JEV_API_KEY"]}

P = json.load(open(os.path.join(REPO, "data", "case-001-maya.json"), encoding="utf-8"))
SHELF = P["shelf"]
BY = {p["product"]: p for p in SHELF}
HELD_OUT_PRIVATE_ROUTING = P["decision_rules"]["routing"]  # E-02.2. NEVER enters a prompt.

# ---------------------------------------------------------------- the corpora
# What a scrape of her public account returns. Nothing private. Each caption carries the
# evidence ref of the post it came from so the UI can cite it.
CAPTIONS = [
    {"id": "c1", "ref": "E-03.1",
     "text": "3 things I would repurchase with 50 quid. SPF, obviously. non negotiable, I will die on this hill."},
    {"id": "c2", "ref": "E-04.6",
     "text": "the 62 pound serum everyone is posting. it is good. it is not 62 pounds good. save your money."},
    {"id": "c3", "ref": "E-03.2",
     "text": "things I bought because tiktok told me to. 4 of them were a waste. here is the 1 that was not."},
    {"id": "c4", "ref": "E-03.5",
     "text": "my 5 minute morning routine. two products. that is it. you do not need eight steps you need consistency."},
    {"id": "c5", "ref": "E-03.6",
     "text": "the product I would NOT rebuy. beautiful packaging, too rich for my skin, I gave it away."},
    {"id": "c6", "ref": "E-03.4",
     "text": "luxury vs drugstore. the cleanser genuinely does not matter. spend it on sunscreen."},
    {"id": "c7", "ref": "E-03.3",
     "text": "if your face freaks out every time you try something new, stop adding things. take things away."},
    {"id": "c8", "ref": "E-06.1",
     "text": "people do not need more products. they need to feel confident about the two they already own."},
]

SCRAPED = {
    "handle": "@mayarao",
    "bio": "skincare, mostly honest. london.",
    "posts": [{"caption": b["title"], "views": b["views"], "saves": b["saves"]} for b in P["broadcast_log"]],
    "captions": [c["text"] for c in CAPTIONS],
    "her_public_notes_on_products_she_has_used": [
        {"product": p["product"], "rating_out_of_10": p["maya_rating"], "what_she_said": p["maya_note"]}
        for p in SHELF],
}

# Written by us as the control. Disclosed in docs/11-honest-headline.md. Deliberately given the
# same breadth as her caption corpus (composition, irritation, redness, dryness, oiliness,
# price, hype) so the comparison is not rigged by starving one side of routing content.
DERM_SOURCE = {
    "who": "A board-certified dermatologist with good taste, writing patient guidance",
    "guidance": [
        "A complete daily routine is cleanser, moisturiser and broad-spectrum SPF.",
        "Barrier support and photoprotection are the foundations of every regimen.",
        "Well-formulated actives at adequate concentrations are worth investing in.",
        "Patients should be advised on the full regimen appropriate to their skin type.",
        "Cosmetic elegance matters for adherence; patients continue what feels good.",
        "Evidence of efficacy should drive selection over marketing claims.",
        "A patient reacting to new products likely has a compromised barrier: pare the regimen "
        "back to a bland cleanser, a ceramide moisturiser and sunscreen, then reintroduce slowly.",
        "Persistent facial erythema should be managed with an anti-inflammatory, fragrance-free "
        "soothing preparation alongside strict photoprotection.",
        "Dry, tight or flaking skin needs an occlusive, lipid-rich emollient applied to damp skin.",
        "Oily and acne-prone skin does better with a light, non-comedogenic gel moisturiser; "
        "moisturiser should not be skipped.",
        "Cost is a real adherence barrier, but under-treating is a false economy.",
        "Cleansing is a necessary step in every regimen and should not be omitted.",
    ],
}

# The v1 control, kept verbatim: the SIX statements engine_decontaminated.py used. v2 added six
# more (irritation, erythema, dryness, oiliness, cost, cleansing) so that the dermatologist is not
# starved of routing content that Maya's captions have. That expansion is OURS, so we ablate it
# below and publish both numbers.
DERM_GUIDANCE_NARROW = DERM_SOURCE["guidance"][:6]
DERM_SOURCE_NARROW = {"who": DERM_SOURCE["who"], "guidance": DERM_GUIDANCE_NARROW}

# The shelf, identical in both extraction states and both judge states.
# v1 put Maya's own ratings and notes ("Non-negotiable.", 9.6) in BOTH judge states. That is
# symmetric, but it means the dermatologist is reading Maya's voice, which biases the two towards
# each other. DECON_OBJECTIVE_SHELF=1 strips them and keeps her notes only inside HER corpus.
OBJECTIVE_SHELF = os.environ.get("DECON_OBJECTIVE_SHELF", "1") == "1"  # default: fully decontaminated
SHELF_FOR_STATE = [dict({"product": p["product"], "gbp": p["gbp"], "type": p["type"],
                         "skin": p["skin"], "finish": p["finish"]},
                        **({} if OBJECTIVE_SHELF else
                           {"creator_rating": p["maya_rating"], "creator_note": p["maya_note"]}))
                   for p in SHELF]

CATS = ["spf", "cleanser", "moisturiser", "serum", "makeup"]


def shelf_options(none_text):
    """Choice criteria generated FROM THE SHELF DATA, not typed out by hand."""
    d = {p["product"]: "%s - a GBP%d %s for %s skin, %s finish"
                       % (p["product"], p["gbp"], p["type"].lower(), p["skin"].lower(), p["finish"].lower())
         for p in SHELF}
    d["none"] = none_text
    return d


# --------------------------------------------------------------- THE 14 SLOTS
# Identical for both judges. Nothing creator-specific is hard-coded in any of them.
# `situation` is reused verbatim as the `when` clause of the structured routing rules, so the
# rule text and the question text can never drift apart.
SLOTS = {
    # ---- the original six, byte-for-byte from engine_decontaminated.py ----
    "routine_size": {"type": "score",
        "instructions": "Does this person favour the fewest possible products, or a complete multi-step routine?",
        "criteria": ["The fewest possible products", "A small routine", "A moderate routine", "A complete multi-step routine"]},
    "budget_behaviour": {"type": "noul",
        "instructions": "Given a budget, would this person spend all of it, or deliberately leave money unspent?",
        "criteria": {"true": "Spends the whole budget", "false": "Happy to leave money unspent"}},
    "price_refusal": {"type": "score",
        "instructions": "How willing is this person to say something is good but not worth its price?",
        "criteria": ["Never talks about price", "Mentions price occasionally", "Will call something overpriced", "Price is central to their judgement"]},
    "subtraction": {"type": "noul",
        "instructions": "Does this person tell people to REMOVE products as often as add them?",
        "criteria": {"true": "Subtraction is part of their advice", "false": "They mostly add"}},
    "hype": {"type": "score",
        "instructions": "How does this person treat trending or heavily marketed products?",
        "criteria": ["Actively sceptical of hype", "Cautious", "Neutral", "Follows trends"]},
    "defended_category": {"type": "choice",
        "instructions": "Which single category does this person treat as non-negotiable, to be bought before anything else?",
        "criteria": {"spf": None, "cleanser": None, "moisturiser": None, "serum": None, "makeup": None, "none": "No clear priority"}},

    # ---- NEW: category priorities ----
    "interchangeable_category": {"type": "choice",
        "instructions": "Someone asks this person which brand of each category to buy. For which ONE category "
                        "would they say the specific product barely matters and any decent one will do?",
        "criteria": dict([(c, "They would say: any decent %s is fine, do not overthink this one" % c) for c in CATS]
                         + [("none", "They think the specific product matters in every category")])},
    "skippable_category": {"type": "choice",
        "instructions": "Someone has less money than a full routine costs and has to leave something out. "
                        "Which ONE category would this person drop first?",
        "criteria": dict([(c, "They would leave the %s out of the basket entirely before dropping anything else" % c) for c in CATS]
                         + [("none", "They would shrink every category rather than drop one outright")])},
    "starting_from_zero": {"type": "score",
        "instructions": "Someone owns no skincare at all, has money to spend, and asks this person what to buy. "
                        "How many products comes back?",
        "criteria": ["Exactly one - only the single thing they consider non-negotiable",
                     "Two - the non-negotiable plus one thing chosen for that person's skin",
                     "Three - a short but complete routine",
                     "Four or more - the full regimen"]},
    "subtraction_scope": {"type": "choice",
        "instructions": "This person sometimes tells people to stop buying and remove products. In WHICH "
                        "situation do they actually say it?",
        "criteria": {
            "crowded_routine_only": "Only to someone already using a lot of products whose skin is unhappy - "
                                    "take things away from what they already have",
            "everyone_always": "To everyone, including someone who owns nothing yet and is starting from scratch",
            "never": "They do not tell people to remove products"}},

    # ---- NEW: routing conditions. Concrete situations, in the asker's own words. ----
    "route_reacting": {"type": "choice",
        "situation": "Someone writes 'every time I try something new my face freaks out'. They own no skincare "
                     "yet and are starting from nothing, with money to spend.",
        "instructions": "Someone writes: 'every time I try something new my face freaks out.' They own no "
                        "skincare yet and are starting from nothing, with money to spend. Which ONE item from "
                        "`shelf` does this person reach for first for her?",
        "criteria": shelf_options("None of them - they would tell her to buy nothing at all and take products "
                                  "away from whatever she is already using")},
    "route_redness": {"type": "choice",
        "situation": "Someone writes 'my cheeks are red and angry today and nothing calms it down'.",
        "instructions": "Someone writes: 'my cheeks are red and angry today and nothing calms it down.' Which "
                        "ONE item from `shelf` does this person reach for first for her?",
        "criteria": shelf_options("None of them - redness is not something they would answer with a product")},
    "route_dry": {"type": "choice",
        "situation": "Someone writes 'my skin is dry and tight all winter and it flakes under makeup'.",
        "instructions": "Someone writes: 'my skin is dry and tight all winter and it flakes under makeup.' "
                        "Which ONE item from `shelf` does this person reach for first for her?",
        "criteria": shelf_options("None of them - dryness is not something they would answer with a product")},
    "route_oily": {"type": "choice",
        "situation": "Someone writes 'I am shiny by 11am and my t-zone never stops'.",
        "instructions": "Someone writes: 'I am shiny by 11am and my t-zone never stops.' Which ONE item from "
                        "`shelf` does this person reach for first for her?",
        "criteria": shelf_options("None of them - oiliness is not something they would answer with a product")},
}

# `situation` is ours-only bookkeeping; the API sees only type/instructions/criteria.
API_SLOTS = {k: {kk: vv for kk, vv in v.items() if kk != "situation"} for k, v in SLOTS.items()}

ROUTE_SLOTS = ["route_reacting", "route_redness", "route_dry", "route_oily"]
# which extracted shopper condition triggers which extracted routing rule
CONDITION_TO_ROUTE = {"sensitive": "route_reacting", "redness": "route_redness",
                      "dry": "route_dry", "oily": "route_oily"}
CONDITIONS = ["dry", "oily", "combination", "sensitive", "redness"]
REPEATS = int(os.environ.get("DECON_REPEATS", "3"))  # one run is not a measurement

# UI renderings. One sentence per POSSIBLE outcome, written before the run, for every outcome,
# so no wording can favour one answer over another. The value chosen is the extracted one.
UI = {
    "routine_size": "Sends {v_lc}.",
    "price_refusal": "On price: {v_lc}.",
    "hype": "On hype: {v_lc}.",
    "starting_from_zero": "From a standing start: {v_lc}.",
    "budget_behaviour": {True: "Spends the whole budget.", False: "Happy to leave money unspent."},
    "subtraction": {True: "Tells people to remove products, not only add them.", False: "Mostly adds products."},
    "defended_category": "Never leaves out: {v}.",
    "interchangeable_category": "Treats as interchangeable: {v}.",
    "skippable_category": "First to drop when money is tight: {v}.",
    "subtraction_scope": "Says 'buy less' {v_lc}.",
    "route_reacting": "Skin reacting to everything -> {v}.",
    "route_redness": "Red and angry -> {v}.",
    "route_dry": "Dry and tight -> {v}.",
    "route_oily": "Oily and shiny -> {v}.",
}
SCOPE_WORDS = {"crowded_routine_only": "only to someone already using a lot of products",
               "everyone_always": "to everyone, including someone starting from scratch",
               "never": "never - they do not tell people to remove products"}


# ------------------------------------------------------------------ plumbing
def slot_summary(a):
    out = {}
    for k in SLOTS:
        x = a[k]
        if x["type"] == "score":
            out[k] = {"level": x["legend"][str(round(x["score"]))], "value": round(x["score"], 2)}
        elif x["type"] == "noul":
            out[k] = {"answer": bool(x["noul"] > 0.5), "p": round(x["noul"], 2)}
        else:
            out[k] = {"choice": x["choice"], "confidence": round(x["confidence"], 2)}
    return out


def cat_value(d, k):
    """The categorical value of a slot, for agree/disagree comparison and for display."""
    v = d[k]
    if "level" in v:
        return v["level"]
    if "answer" in v:
        return "YES" if v["answer"] else "NO"
    return v["choice"]


def ui_label(k, d):
    t = UI[k]
    v = cat_value(d, k)
    if isinstance(t, dict):
        return t[d[k]["answer"]]
    if k == "subtraction_scope":
        return t.format(v_lc=SCOPE_WORDS[v])
    return t.format(v=v, v_lc=(v[0].lower() + v[1:]) if v else v)


def routing_rules(slots):
    """The extracted routing, as STRUCTURED DATA. Every value came out of a slot above."""
    return {
        "by_situation": [{"when": SLOTS[k]["situation"],
                          "reach_for": slots[k]["choice"],
                          "confidence": slots[k]["confidence"]} for k in ROUTE_SLOTS],
        "by_category": {"never_leave_out": slots["defended_category"]["choice"],
                        "any_decent_one_will_do": slots["interchangeable_category"]["choice"],
                        "first_to_drop_when_money_is_tight": slots["skippable_category"]["choice"]},
        "when_they_say_buy_less": slots["subtraction_scope"]["choice"],
        "how_many_from_a_standing_start": slots["starting_from_zero"]["level"],
        "_provenance": "Every value in this object was produced by a typed extraction slot run against "
                       "this judge's own source corpus. No value here was written by hand.",
    }


def judge_from_slots(name, slots):
    """The ENTIRE judge state. Derived, not authored. Same keys on both sides."""
    return {
        "name": name,
        "extracted_standard": slots,
        "her_written_routing_rules": routing_rules(slots),
        "shelf": SHELF_FOR_STATE,
        "instruction": "Apply `extracted_standard` and `her_written_routing_rules` exactly. Both were "
                       "extracted from this person's own source material and are their measured "
                       "decision profile. Where a rule in `her_written_routing_rules.by_situation` "
                       "matches this shopper's conditions, it is what this person actually does.",
    }


def routed_products(slots, shopper, threshold=0.6):
    """Products this judge's OWN extracted routing names for conditions this shopper actually has."""
    out = []
    for cond, slot in CONDITION_TO_ROUTE.items():
        if shopper.get("conditions", {}).get(cond, 0.0) > threshold:
            pick = slots[slot]["choice"]
            if pick != "none" and pick not in out:
                out.append(pick)
    return out


def feasible(budget, owns, max_items, defended=None, must=()):
    pool = [p["product"] for p in SHELF if p["product"] not in owns]

    def isdef(x):
        return bool(defended) and defended != "none" and BY[x]["type"].lower().startswith(defended[:3])

    owns_def = any(isdef(o) for o in owns if o in BY)
    cheap = [BY[x]["gbp"] for x in pool if isdef(x)]
    must = [m for m in must if m in pool]
    out = []
    for k in range(1, max_items + 1):
        for c in itertools.combinations(pool, k):
            if sum(BY[x]["gbp"] for x in c) > budget:
                continue
            # her non-negotiable category is a HARD CONSTRAINT, enforced in code, taken from
            # the extracted standard - skipped only if she already owns one or cannot afford one
            if cheap and not owns_def and budget >= min(cheap) and not any(isdef(x) for x in c):
                continue
            if must and not all(m in c for m in must):
                continue
            out.append(c)
    return out


def score_payload(judge, shopper, combos):
    return {"model": "jev-latest",
            "state": {"judge": judge, "shopper": shopper,
                      "baskets": {"b%d" % i: {"items": [{"product": x, "gbp": BY[x]["gbp"], "type": BY[x]["type"],
                                                         "skin": BY[x]["skin"]} for x in c],
                                              "total_gbp": sum(BY[x]["gbp"] for x in c)} for i, c in enumerate(combos)}},
            "questions": {"b%d" % i: {"type": "score",
                                      "instructions": "Would `judge` send `baskets.b%d` to `shopper`? Apply "
                                                      "`judge.extracted_standard` and "
                                                      "`judge.her_written_routing_rules`." % i,
                                      "criteria": ["Wrong for this person", "Defensible but not their pick",
                                                   "Reasonable", "Good", "Exactly what they would send"]}
                          for i in range(len(combos))}}


async def post(client, payload, tries=4):
    for a in range(tries):
        r = await client.post(URL, headers=H, json=payload, timeout=120)
        if r.status_code in (429, 500, 502, 503, 529):
            await asyncio.sleep(1.5 * (a + 1))
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()
    return r.json()


async def decide(client, judge, shopper, slots, hard_route):
    """Two-stage: score every feasible basket, take the top 8, then ONE choice."""
    defended = slots["defended_category"]["choice"]
    must = routed_products(slots, shopper) if hard_route else ()
    combos = feasible(shopper["budget_gbp"], shopper["owns"], shopper["max_items"], defended, must)
    relaxed = False
    if not combos and must:
        combos = feasible(shopper["budget_gbp"], shopper["owns"], shopper["max_items"], defended)
        relaxed = True
    if not combos:
        combos = feasible(shopper["budget_gbp"], shopper["owns"], shopper["max_items"])
        relaxed = True
    if not combos:
        return None, relaxed
    CH = 70
    chunks = [combos[i:i + CH] for i in range(0, len(combos), CH)]
    rs = await asyncio.gather(*[post(client, score_payload(judge, shopper, ch)) for ch in chunks])
    sc = {}
    for ch, js in zip(chunks, rs):
        a = js["answers"]
        for i, x in enumerate(ch):
            sc[x] = a["b%d" % i]["score"]
    fin = sorted(sc, key=lambda k: -sc[k])[:8]
    js2 = await post(client, {"model": "jev-latest",
                              "state": {"judge": judge, "shopper": shopper,
                                        "finalists": {"b%d" % i: {"items": list(x),
                                                                  "total_gbp": sum(BY[y]["gbp"] for y in x)}
                                                      for i, x in enumerate(fin)}},
                              "questions": {"pick": {"type": "choice",
                                                     "instructions": "Which one of `finalists` would `judge` "
                                                                     "actually send to `shopper`?",
                                                     "criteria": {"b%d" % i: " + ".join(x) for i, x in enumerate(fin)}}}})
    return fin[int(js2["answers"]["pick"]["choice"][1:])], relaxed


SHOPPERS = [
    ("@gracelee", {"says": "dry skin + redness, GBP60", "skin": "dry with redness", "budget_gbp": 60, "owns": [], "max_items": 4}),
    ("@joanna", {"says": "only 2 products, will not do 8 steps", "skin": "normal", "budget_gbp": 120, "owns": [], "max_items": 2}),
    ("@jessica", {"says": "already have the night serum, do i need more", "skin": "normal", "budget_gbp": 80, "owns": ["Night Serum"], "max_items": 3}),
    ("Priya", {"says": "my face freaks out with everything", "skin": "very sensitive", "budget_gbp": 80, "owns": [], "max_items": 3}),
    ("Emily", {"says": "not spending 100 on serum", "skin": "combination", "budget_gbp": 40, "owns": [], "max_items": 3}),
    ("@kate", {"says": "first date Friday HELP", "skin": "normal", "budget_gbp": 70, "owns": [], "max_items": 3}),
    ("owns SPF", {"says": "i already use an spf", "skin": "combination", "budget_gbp": 60, "owns": ["SPF 50"], "max_items": 3}),
    ("tiny", {"says": "i only have 20 quid", "skin": "oily", "budget_gbp": 20, "owns": [], "max_items": 2}),
]


def cost(c):
    return sum(BY[x]["gbp"] for x in c)


def condition_payload():
    """BUG 1: skin type is MULTI-LABEL. One noul per condition, extracted, not typed by us."""
    qs = {}
    for i, (lab, s) in enumerate(SHOPPERS):
        for c in CONDITIONS:
            qs["s%d__%s" % (i, c)] = {"type": "noul",
                "instructions": "Reading `shoppers.s%d`, is %s true of this person's skin right now?" % (i, c),
                "criteria": {"true": "Their own words indicate %s skin" % c,
                             "false": "Their own words do not indicate %s skin" % c}}
    return {"model": "jev-latest",
            "state": {"shoppers": {"s%d" % i: dict(s, who=lab) for i, (lab, s) in enumerate(SHOPPERS)}},
            "questions": qs}


def evidence_payload(corpus_key, items, findings):
    """Ask WHICH line of the corpus each finding came from. We do not hand-map it."""
    return {"model": "jev-latest",
            "state": {corpus_key: {it["id"]: it["text"] for it in items}, "findings": findings},
            "questions": {k: {"type": "choice",
                              "instructions": "Which single entry of `%s` is the strongest evidence for "
                                              "`findings.%s`?" % (corpus_key, k),
                              "criteria": {it["id"]: it["text"] for it in items}} for k in findings}}


async def one_run(client, JM, JD, M, D, shoppers, hard_route):
    async def pair(lab, s):
        (a, ra), (b, rb) = await asyncio.gather(decide(client, JM, s, M, hard_route),
                                                decide(client, JD, s, D, hard_route))
        return lab, s, list(a), list(b), ra, rb
    return await asyncio.gather(*[pair(lab, s) for lab, s in shoppers])


def modal(seq):
    """The most frequent basket across repeats; ties broken by first appearance."""
    keys = [tuple(x) for x in seq]
    best = max(set(keys), key=lambda k: (keys.count(k), -keys.index(k)))
    return list(best), keys.count(best) / len(keys)


async def run_mode(client, JM, JD, M, D, shoppers, hard_route, repeats=REPEATS):
    """Repeat the whole shopper sweep N times. One run is not a measurement."""
    runs = await asyncio.gather(*[one_run(client, JM, JD, M, D, shoppers, hard_route)
                                  for _ in range(repeats)])
    per_run_div = [sum(1 for (_, _, a, b, _, _) in r if a != b) for r in runs]
    rows, mi, di, mg, dg, div = [], [], [], [], [], 0
    for j, (lab, s) in enumerate(shoppers):
        ma, mstab = modal([runs[k][j][2] for k in range(repeats)])
        da, dstab = modal([runs[k][j][3] for k in range(repeats)])
        rows.append({"shopper": lab, "says": s["says"], "budget_gbp": s["budget_gbp"],
                     "owns": s["owns"], "max_items": s["max_items"],
                     "conditions": s.get("conditions", {}),
                     "maya_basket": ma, "maya_total_gbp": cost(ma),
                     "derm_basket": da, "derm_total_gbp": cost(da),
                     "diverged": ma != da,
                     "stability": {"maya": round(mstab, 2), "derm": round(dstab, 2), "repeats": repeats},
                     "all_runs": {"maya": [runs[k][j][2] for k in range(repeats)],
                                  "derm": [runs[k][j][3] for k in range(repeats)]},
                     "constraint_relaxed": {"maya": runs[0][j][4], "derm": runs[0][j][5]}})
        mi.append(len(ma)); di.append(len(da)); mg.append(cost(ma)); dg.append(cost(da))
        div += (ma != da)
    agg = {"shoppers": len(shoppers), "repeats": repeats, "divergence": div,
           "divergence_per_run": per_run_div,
           "maya_avg_products": round(statistics.mean(mi), 2), "maya_avg_gbp": round(statistics.mean(mg), 2),
           "derm_avg_products": round(statistics.mean(di), 2), "derm_avg_gbp": round(statistics.mean(dg), 2),
           "fewer_products": round(statistics.mean(di) - statistics.mean(mi), 2),
           "less_gbp": round(statistics.mean(dg) - statistics.mean(mg), 2),
           "mean_basket_stability": round(statistics.mean([r["stability"]["maya"] for r in rows]
                                                          + [r["stability"]["derm"] for r in rows]), 2)}
    return rows, agg


def print_table(title, rows, agg):
    print("\n%s" % title)
    print("%-12s %-40s %-40s" % ("SHOPPER", "MAYA", "DERMATOLOGIST"))
    for r in rows:
        print("%-12s %-40s %-40s%s" % (r["shopper"],
                                       " + ".join(r["maya_basket"]) + " (GBP%d)" % r["maya_total_gbp"],
                                       " + ".join(r["derm_basket"]) + " (GBP%d)" % r["derm_total_gbp"],
                                       "  <- diverge" if r["diverged"] else
                                       ("  (unstable %.2f/%.2f)" % (r["stability"]["maya"], r["stability"]["derm"])
                                        if min(r["stability"]["maya"], r["stability"]["derm"]) < 1.0 else "")))
    print("DIVERGENCE %d/%d (modal basket over %d repeats; per-run %s) | MAYA %.2f products GBP%.0f | "
          "DERM %.2f products GBP%.0f | delta %+.2f products, GBP%+.0f | basket stability %.2f"
          % (agg["divergence"], agg["shoppers"], agg["repeats"], agg["divergence_per_run"],
             agg["maya_avg_products"], agg["maya_avg_gbp"], agg["derm_avg_products"], agg["derm_avg_gbp"],
             agg["fewer_products"], agg["less_gbp"], agg["mean_basket_stability"]))


async def main():
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=60)) as c:
        # ---------------- STAGE 1: both standards, same 14 slots ----------------
        t0 = time.time()
        jm, jd, jc = await asyncio.gather(
            post(c, {"model": "jev-latest", "state": {"public_profile": SCRAPED, "shelf": SHELF_FOR_STATE}, "questions": API_SLOTS}),
            post(c, {"model": "jev-latest", "state": {"public_profile": DERM_SOURCE, "shelf": SHELF_FOR_STATE}, "questions": API_SLOTS}),
            post(c, condition_payload()))
        extraction_seconds = round(time.time() - t0, 2)

        # The extraction is one API call, so repeat it and keep the MODAL value per slot. A slot
        # that flips between runs is reported as unstable rather than quietly published.
        extra = await asyncio.gather(*(
            [post(c, {"model": "jev-latest", "state": {"public_profile": SCRAPED, "shelf": SHELF_FOR_STATE}, "questions": API_SLOTS})
             for _ in range(REPEATS - 1)] +
            [post(c, {"model": "jev-latest", "state": {"public_profile": DERM_SOURCE, "shelf": SHELF_FOR_STATE}, "questions": API_SLOTS})
             for _ in range(REPEATS - 1)]))
        mruns = [slot_summary(jm["answers"])] + [slot_summary(x["answers"]) for x in extra[:REPEATS - 1]]
        druns = [slot_summary(jd["answers"])] + [slot_summary(x["answers"]) for x in extra[REPEATS - 1:]]

        def consolidate(runs):
            out, stab = {}, {}
            for k in SLOTS:
                vals = [cat_value(r, k) for r in runs]
                win = max(set(vals), key=lambda v: (vals.count(v), -vals.index(v)))
                stab[k] = round(vals.count(win) / float(len(vals)), 2)
                out[k] = runs[vals.index(win)][k]
            return out, stab

        M, mstab = consolidate(mruns)
        D, dstab = consolidate(druns)
        slot_stability = {k: {"maya": mstab[k], "derm": dstab[k]} for k in SLOTS}

        print("shelf mode: %s" % ("OBJECTIVE (no creator ratings/notes in either judge state)"
                                  if OBJECTIVE_SHELF else "v1 (creator ratings/notes in BOTH judge states)"))
        print("STAGE 1 - BOTH STANDARDS EXTRACTED THROUGH THE SAME %d SLOTS (%.2fs)\n" % (len(SLOTS), extraction_seconds))
        print("%-26s %-42s %-30s %s" % ("SLOT", "MAYA (from her public posts)", "DERMATOLOGIST (clinical guidance)", ""))
        agree = 0
        for k in SLOTS:
            same = cat_value(M, k) == cat_value(D, k)
            agree += same
            flag = "agree" if same else "DISAGREE"
            if min(mstab[k], dstab[k]) < 1.0:
                flag += "  (UNSTABLE %.1f/%.1f over %d extractions)" % (mstab[k], dstab[k], REPEATS)
            print("%-26s %-42s %-30s %s" % (k, str(cat_value(M, k))[:41], str(cat_value(D, k))[:29], flag))
        dis_live = len(SLOTS) - agree
        print("\n%d agree / %d disagree, out of %d slots." % (agree, dis_live, len(SLOTS)))

        # ---------------- STAGE 1b: which line of the corpus each finding came from ------------
        findM = {k: cat_value(M, k) for k in SLOTS}
        findD = {k: cat_value(D, k) for k in SLOTS}
        guide_items = [{"id": "g%d" % i, "text": t} for i, t in enumerate(DERM_SOURCE["guidance"])]
        em, ed = await asyncio.gather(
            post(c, evidence_payload("captions", CAPTIONS, findM)),
            post(c, evidence_payload("guidance", guide_items, findD)))
        capby = {x["id"]: x for x in CAPTIONS}
        gby = {x["id"]: x for x in guide_items}

        # ---------------- STAGE 1c: the shopper conditions (multi-label) ------------------------
        ca = jc["answers"]
        shoppers = []
        for i, (lab, s) in enumerate(SHOPPERS):
            s2 = dict(s)
            s2["conditions"] = {cnd: round(ca["s%d__%s" % (i, cnd)]["noul"], 2) for cnd in CONDITIONS}
            shoppers.append((lab, s2))
        print("\nSTAGE 1c - SHOPPER SKIN, EXTRACTED AS ONE NOUL PER CONDITION (multi-label, bug #1)\n")
        print("%-12s %s" % ("SHOPPER", "  ".join("%-12s" % cnd for cnd in CONDITIONS)))
        for lab, s in shoppers:
            print("%-12s %s" % (lab, "  ".join("%-12.2f" % s["conditions"][cnd] for cnd in CONDITIONS)))

        # ---------------- write data/standard-extracted.json -------------------------------------
        out = {"maya": {}, "derm": {}}
        dis = 0
        for k in SLOTS:
            same = cat_value(M, k) == cat_value(D, k)
            dis += (not same)
            cap = capby[em["answers"][k]["choice"]]
            out["maya"][k] = dict(M[k], label=ui_label(k, M), source_caption=cap["text"],
                                  evidence_ref=cap["ref"], agrees=same, toggleable=True)
            out["derm"][k] = dict(D[k], label=ui_label(k, D),
                                  derm_source=gby[ed["answers"][k]["choice"]]["text"],
                                  evidence_ref="clinical-guidance", agrees=same, toggleable=True)
        out["meta"] = {"extraction_seconds": extraction_seconds, "slot_count": len(SLOTS),
                       "agree_count": len(SLOTS) - dis, "disagree_count": dis,
                       "model": jm.get("model", "jev-latest"),
                       "generated_by": "scripts/engine_decontaminated_v2.py",
                       "objective_shelf": OBJECTIVE_SHELF,
                       "slot_stability": slot_stability,
                       "note": "Every value was produced by a typed extraction slot. The same 14 slots, "
                               "word for word, were asked of Maya's public captions and of clinical "
                               "guidance. No judgement rule in this file was written by hand."}
        json.dump(out, open(os.path.join(REPO, "data", "standard-extracted.json"), "w", encoding="utf-8"),
                  indent=1, ensure_ascii=False)

        JM = judge_from_slots("Maya Rao", M)
        JD = judge_from_slots("A dermatologist", D)

        # ---------------- STAGE 2: the shoppers, both modes --------------------------------------
        print("\nSTAGE 2 - BASKETS. Both judges built ONLY from the table above.")
        t1 = time.time()
        rows_soft, agg_soft = await run_mode(c, JM, JD, M, D, shoppers, hard_route=False)
        print_table("MODE A - extracted routing present in `state` as structured data, nothing forced:",
                    rows_soft, agg_soft)
        rows_hard, agg_hard = await run_mode(c, JM, JD, M, D, shoppers, hard_route=True)
        print_table("MODE B - + each judge's OWN extracted routing as a feasibility filter "
                    "(condition noul > 0.6), per GO section 6:", rows_hard, agg_hard)
        basket_seconds = round(time.time() - t1, 2)

        # ---------------- ABLATION: was the convergence caused by OUR richer derm corpus? --------
        jdn = await post(c, {"model": "jev-latest",
                             "state": {"public_profile": DERM_SOURCE_NARROW, "shelf": SHELF_FOR_STATE},
                             "questions": API_SLOTS})
        DN = slot_summary(jdn["answers"])
        JDN = judge_from_slots("A dermatologist", DN)
        rows_abl, agg_abl = await run_mode(c, JM, JDN, M, DN, shoppers, hard_route=False)
        print("\nABLATION - same 14 slots, but the dermatologist gets ONLY the 6 guidance lines the")
        print("v1 script used. This isolates our own corpus expansion from the slot expansion.")
        n_dis_abl = sum(1 for k in SLOTS if cat_value(M, k) != cat_value(DN, k))
        print("  slot disagreement: %d/%d (vs %d/%d with the matched corpus)" % (n_dis_abl, len(SLOTS), dis_live, len(SLOTS)))
        print_table("ABLATION baskets (narrow derm corpus, mode A):", rows_abl, agg_abl)

        # ---------------- STAGE 3: held-out check against her private routing sheet (E-02.2) -----
        priv = {"DRY": "route_dry", "OILY": "route_oily", "REDNESS": "route_redness"}
        print("\nSTAGE 3 - HELD-OUT CHECK. E-02.2 (her private routing sheet) was NEVER shown to the")
        print("extractor. Comparing it to what we discovered from her PUBLIC posts alone:\n")
        hits = 0
        held = []
        for r in HELD_OUT_PRIVATE_ROUTING:
            if r["if"] in priv:
                got = M[priv[r["if"]]]["choice"]
                ok = got in r["then"]
                hits += ok
                held.append({"condition": r["if"], "her_private_sheet": r["then"], "discovered": got, "match": bool(ok)})
                print("  %-8s private sheet says %-28s we discovered %-14s %s"
                      % (r["if"], "/".join(r["then"]), got, "MATCH" if ok else "miss"))
        print("\n  %d/%d conditions recovered from public posts alone." % (hits, len(held)))

        # ---------------- results file -----------------------------------------------------------
        priya_soft = next(r for r in rows_soft if r["shopper"] == "Priya")
        priya_hard = next(r for r in rows_hard if r["shopper"] == "Priya")
        res = {
            "generated_by": "scripts/engine_decontaminated_v2.py",
            "model": jm.get("model", "jev-latest"),
            "timing": {"extraction_seconds": extraction_seconds, "basket_seconds": basket_seconds},
            "slot_count": len(SLOTS),
            "objective_shelf": OBJECTIVE_SHELF,
            "slot_stability_over_%d_extractions" % REPEATS: slot_stability,
            "extracted_standard": {"maya": M, "derm": D},
            "routing_rules": {"maya": routing_rules(M), "derm": routing_rules(D)},
            "shopper_conditions": {lab: s["conditions"] for lab, s in shoppers},
            "mode_a_soft_routing_in_state": {"rows": rows_soft, "aggregate": agg_soft},
            "mode_b_routing_as_feasibility_filter": {"rows": rows_hard, "aggregate": agg_hard},
            "fidelity_test_priya_red_reset": {
                "mode_a": "Red Reset" in priya_soft["maya_basket"],
                "mode_b": "Red Reset" in priya_hard["maya_basket"],
                "mode_a_basket": priya_soft["maya_basket"], "mode_b_basket": priya_hard["maya_basket"],
                "mode_a_hit_rate_over_repeats": round(sum("Red Reset" in r for r in priya_soft["all_runs"]["maya"])
                                                      / float(len(priya_soft["all_runs"]["maya"])), 2),
                "mode_b_hit_rate_over_repeats": round(sum("Red Reset" in r for r in priya_hard["all_runs"]["maya"])
                                                      / float(len(priya_hard["all_runs"]["maya"])), 2)},
            "held_out_private_routing_check": {"source": "E-02.2, never shown to the extractor",
                                               "matched": hits, "of": len(held), "detail": held},
            "ablation_narrow_derm_corpus": {
                "what": "The same 14 slots, but the dermatologist gets only the 6 guidance lines the v1 "
                        "script used. Isolates our corpus expansion from the slot expansion.",
                "derm_extracted_standard": DN,
                "slot_disagreement": n_dis_abl, "of_slots": len(SLOTS),
                "rows": rows_abl, "aggregate": agg_abl},
            "baseline_six_slot_run": {"divergence": "3/8", "fewer_products": 0.2, "less_gbp": 7,
                                      "source": "scripts/engine_decontaminated.py"},
        }
        json.dump(res, open(os.path.join(REPO, "data", "decontaminated-results.json"), "w", encoding="utf-8"),
                  indent=1, ensure_ascii=False)

        print("\n" + "=" * 90)
        print("FIDELITY TEST  Priya (%s): mode A -> %s | mode B -> %s"
              % (", ".join("%s %.2f" % (k, v) for k, v in priya_soft["conditions"].items() if v > 0.5),
                 " + ".join(priya_soft["maya_basket"]), " + ".join(priya_hard["maya_basket"])))
        print("  Red Reset present?  mode A %s (%.0f%% of repeats) | mode B %s (%.0f%% of repeats)"
              % (res["fidelity_test_priya_red_reset"]["mode_a"],
                 100 * res["fidelity_test_priya_red_reset"]["mode_a_hit_rate_over_repeats"],
                 res["fidelity_test_priya_red_reset"]["mode_b"],
                 100 * res["fidelity_test_priya_red_reset"]["mode_b_hit_rate_over_repeats"]))
        print("BASELINE (6 slots)   3/8 divergence, 0.2 fewer products, GBP7 less")
        print("MODE A  (14 slots)   %d/8 divergence, %+.2f products, GBP%+.0f  (per-run %s)"
              % (agg_soft["divergence"], agg_soft["fewer_products"], agg_soft["less_gbp"],
                 agg_soft["divergence_per_run"]))
        print("MODE B  (14 slots)   %d/8 divergence, %+.2f products, GBP%+.0f  (per-run %s)"
              % (agg_hard["divergence"], agg_hard["fewer_products"], agg_hard["less_gbp"],
                 agg_hard["divergence_per_run"]))
        print("ABLATION narrow derm %d/8 divergence, %+.2f products, GBP%+.0f  (per-run %s)  <- rigged, do not publish"
              % (agg_abl["divergence"], agg_abl["fewer_products"], agg_abl["less_gbp"],
                 agg_abl["divergence_per_run"]))
        print("SLOT DISAGREEMENT   %d/%d matched corpus | %d/%d narrow corpus" % (dis_live, len(SLOTS), n_dis_abl, len(SLOTS)))
        print("wrote data/standard-extracted.json and data/decontaminated-results.json")

        # ---------------- STAGE 4: adversarial self-review ---------------------------------------
        print("\n" + "=" * 90)
        print("ADVERSARIAL SELF-REVIEW - the complete judge states, printed for a hostile reader\n")
        for nm, J in (("MAYA", JM), ("DERM", JD)):
            print("--- %s judge state keys: %s" % (nm, sorted(J.keys())))
        print("\nSTRUCTURAL SYMMETRY: keys identical = %s" % (sorted(JM.keys()) == sorted(JD.keys())))
        print("extracted_standard keys identical = %s" % (sorted(JM["extracted_standard"].keys()) ==
                                                          sorted(JD["extracted_standard"].keys())))
        print("her_written_routing_rules keys identical = %s" % (sorted(JM["her_written_routing_rules"].keys()) ==
                                                                 sorted(JD["her_written_routing_rules"].keys())))
        print("shelf identical object = %s" % (JM["shelf"] == JD["shelf"]))
        print("instruction identical string = %s" % (JM["instruction"] == JD["instruction"]))
        print("\nMAYA state:\n" + json.dumps(JM, indent=1, ensure_ascii=False))
        print("\nDERM state:\n" + json.dumps(JD, indent=1, ensure_ascii=False))
        json.dump({"maya": JM, "derm": JD},
                  open(os.path.join(REPO, "data", "decontaminated-judge-states.json"), "w", encoding="utf-8"),
                  indent=1, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())
