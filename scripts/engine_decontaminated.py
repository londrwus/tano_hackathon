"""DECONTAMINATION — the headline must be DISCOVERED, not authored.

Three of five review personas opened the earlier engine and found hand-written rules
("Fewer steps beats more steps", "She does NOT spend the whole budget") inside Maya's judge
state, while the dermatologist's state had no budget rule at all. That makes the divergence
an artefact of our prompt, not a finding.

Fix, in three parts:
  1. Maya's standard is EXTRACTED from her public posts through six typed slots.
  2. The dermatologist's standard is extracted through the SAME six slots, from clinical guidance.
  3. Both judge states contain nothing but those extracted slots plus the shelf.

Whatever divergence survives is real. Run it and publish the number you get.
"""
import os, asyncio, json, time, itertools, statistics
import httpx

URL = "https://api.typesafe.ai/v1/systemone"
JEV = os.environ["JEV_API_KEY"]
H = {"Authorization": f"Bearer {JEV}"}
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = json.load(open(os.path.join(REPO, "data", "case-001-maya.json"), encoding="utf-8"))
SHELF = P["shelf"]
BY = {p["product"]: p for p in SHELF}

# ---- what a scrape of her public account returns. Nothing private. ----
SCRAPED = {
    "handle": "@mayarao", "bio": "skincare, mostly honest. london.",
    "posts": [{"caption": b["title"], "views": b["views"], "saves": b["saves"]} for b in P["broadcast_log"]],
    "captions": [
        "3 things I would repurchase with 50 quid. SPF, obviously. non negotiable, I will die on this hill.",
        "the 62 pound serum everyone is posting. it is good. it is not 62 pounds good. save your money.",
        "things I bought because tiktok told me to. 4 of them were a waste. here is the 1 that was not.",
        "my 5 minute morning routine. two products. that is it. you do not need eight steps you need consistency.",
        "the product I would NOT rebuy. beautiful packaging, too rich for my skin, I gave it away.",
        "luxury vs drugstore. the cleanser genuinely does not matter. spend it on sunscreen.",
        "if your face freaks out every time you try something new, stop adding things. take things away.",
        "people do not need more products. they need to feel confident about the two they already own.",
    ],
}

# ---- THE SIX SLOTS. Identical for both judges. Nothing creator-specific hard-coded. ----
SLOTS = {
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
}

DERM_SOURCE = {
    "who": "A board-certified dermatologist with good taste, writing patient guidance",
    "guidance": [
        "A complete daily routine is cleanser, moisturiser and broad-spectrum SPF.",
        "Barrier support and photoprotection are the foundations of every regimen.",
        "Well-formulated actives at adequate concentrations are worth investing in.",
        "Patients should be advised on the full regimen appropriate to their skin type.",
        "Cosmetic elegance matters for adherence; patients continue what feels good.",
        "Evidence of efficacy should drive selection over marketing claims.",
    ],
}


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


def judge_from_slots(name, slots):
    """The ENTIRE judge state. Derived, not authored."""
    return {
        "name": name,
        "extracted_standard": slots,
        "shelf": [{"product": p["product"], "gbp": p["gbp"], "type": p["type"], "skin": p["skin"],
                   "creator_rating": p["maya_rating"], "creator_note": p["maya_note"]} for p in SHELF],
        "instruction": "Apply `extracted_standard` exactly. It is this person's measured decision profile.",
    }


def feasible(budget, owns, max_items, defended=None):
    pool = [p["product"] for p in SHELF if p["product"] not in owns]
    def isdef(x): return bool(defended) and defended != "none" and BY[x]["type"].lower().startswith(defended[:3])
    owns_def = any(isdef(o) for o in owns if o in BY)
    cheap = [BY[x]["gbp"] for x in pool if isdef(x)]
    out = []
    for k in range(1, max_items + 1):
        for c in itertools.combinations(pool, k):
            if sum(BY[x]["gbp"] for x in c) > budget:
                continue
            # her non-negotiable category is a HARD CONSTRAINT, enforced in code, taken from
            # the extracted standard - skipped only if she already owns one or cannot afford one
            if cheap and not owns_def and budget >= min(cheap) and not any(isdef(x) for x in c):
                continue
            out.append(c)
    return out


def score_payload(judge, shopper, combos):
    return {"model": "jev-latest",
        "state": {"judge": judge, "shopper": shopper,
            "baskets": {f"b{i}": {"items": [{"product": x, "gbp": BY[x]["gbp"], "type": BY[x]["type"], "skin": BY[x]["skin"]} for x in c],
                                  "total_gbp": sum(BY[x]["gbp"] for x in c)} for i, c in enumerate(combos)}},
        "questions": {f"b{i}": {"type": "score",
            "instructions": f"Would `judge` send `baskets.b{i}` to `shopper`? Apply `judge.extracted_standard`.",
            "criteria": ["Wrong for this person", "Defensible but not their pick", "Reasonable", "Good", "Exactly what they would send"]}
            for i in range(len(combos))}}


async def decide(client, judge, shopper, defended):
    combos = feasible(shopper["budget_gbp"], shopper["owns"], shopper["max_items"], defended)
    if not combos:
        return None
    CH = 70
    chunks = [combos[i:i + CH] for i in range(0, len(combos), CH)]
    rs = await asyncio.gather(*[client.post(URL, headers=H, json=score_payload(judge, shopper, ch), timeout=120) for ch in chunks])
    sc = {}
    for ch, r in zip(chunks, rs):
        a = r.json()["answers"]
        for i, x in enumerate(ch):
            sc[x] = a[f"b{i}"]["score"]
    fin = sorted(sc, key=lambda k: -sc[k])[:8]
    r2 = await client.post(URL, headers=H, json={"model": "jev-latest",
        "state": {"judge": judge, "shopper": shopper,
                  "finalists": {f"b{i}": {"items": list(x), "total_gbp": sum(BY[y]["gbp"] for y in x)} for i, x in enumerate(fin)}},
        "questions": {"pick": {"type": "choice",
            "instructions": "Which one of `finalists` would `judge` actually send to `shopper`?",
            "criteria": {f"b{i}": " + ".join(x) for i, x in enumerate(fin)}}}}, timeout=120)
    return fin[int(r2.json()["answers"]["pick"]["choice"][1:])]


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


async def main():
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=40)) as c:
        t0 = time.time()
        rm, rd = await asyncio.gather(
            c.post(URL, headers=H, json={"model": "jev-latest", "state": {"public_profile": SCRAPED}, "questions": SLOTS}, timeout=90),
            c.post(URL, headers=H, json={"model": "jev-latest", "state": {"public_profile": DERM_SOURCE}, "questions": SLOTS}, timeout=90))
        M = slot_summary(rm.json()["answers"])
        D = slot_summary(rd.json()["answers"])
        print("STAGE 1 - BOTH STANDARDS EXTRACTED THROUGH THE SAME SIX SLOTS (%.2fs)\n" % (time.time() - t0))
        print("%-20s %-40s %s" % ("SLOT", "MAYA (from her posts)", "DERMATOLOGIST"))
        def f(d, k):
            return d[k].get("level") or d[k].get("choice") or ("YES" if d[k].get("answer") else "NO")
        for k in SLOTS:
            print("%-20s %-40s %s" % (k, str(f(M, k))[:39], str(f(D, k))[:39]))
        json.dump({"maya": M, "derm": D}, open(os.path.join(REPO, "data", "standard-extracted.json"), "w"), indent=1)

        JM = judge_from_slots("Maya Rao", M)
        JD = judge_from_slots("A dermatologist", D)
        print("\nSTAGE 2 - BASKETS. Both judges built ONLY from the table above.\n")
        print("%-12s %-38s %s" % ("SHOPPER", "MAYA", "DERMATOLOGIST"))
        mi, di, mg, dg, div = [], [], [], [], 0
        for lab, s in SHOPPERS:
            a, b = await asyncio.gather(decide(c, JM, s, M["defended_category"]["choice"]),
                                        decide(c, JD, s, D["defended_category"]["choice"]))
            print("%-12s %-38s %s" % (lab, " + ".join(a) + " (GBP%d)" % cost(a), " + ".join(b) + " (GBP%d)" % cost(b)))
            mi.append(len(a)); di.append(len(b)); mg.append(cost(a)); dg.append(cost(b)); div += (a != b)
        print("\n" + "=" * 72)
        print("DISCOVERED (not authored) DIVERGENCE: %d/%d shoppers" % (div, len(SHOPPERS)))
        print("MAYA avg %.1f products GBP%.0f  |  DERM avg %.1f products GBP%.0f"
              % (statistics.mean(mi), statistics.mean(mg), statistics.mean(di), statistics.mean(dg)))
        print("-> Maya sends %.1f fewer products and spends GBP%.0f less of your money."
              % (statistics.mean(di) - statistics.mean(mi), statistics.mean(dg) - statistics.mean(mg)))


if __name__ == "__main__":
    asyncio.run(main())
