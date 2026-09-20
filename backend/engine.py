"""Composition: triage, basket, card, standard.

This is the policy layer. `jev.py` returns calibrated probabilities and knows
nothing about what "recommended" means; every threshold, every gate and every
sentence of English lives here.

Ports scripts/engine_dm_router.py, engine_basket.py, engine_overnight_queue.py,
engine_onboarding.py, engine_sharecard.py and engine_end_to_end.py.
"""
from __future__ import annotations

import asyncio
import hashlib
import itertools
import json
import math
import os
import pathlib
import time
from datetime import datetime, timezone

from . import corpora
from . import questions as Q
from .jev import JEV, MODEL as JEV_MODEL, JevUnavailable, choice, conf, level, noul, score

REPO = pathlib.Path(__file__).resolve().parent.parent
DATA = REPO / "data"

CASE = json.loads((DATA / "case-001-maya.json").read_text(encoding="utf-8"))
SHELF = CASE["shelf"]
BY = {p["product"]: p for p in SHELF}
PRODUCTS = [p["product"] for p in SHELF]
VOICE = CASE["voice"]
RULES = CASE["decision_rules"]
INTAKE = RULES["intake_questions"]

_FENCE_PATH = DATA / "fence-curves-verified.json"
FENCE = json.loads(_FENCE_PATH.read_text(encoding="utf-8")) if _FENCE_PATH.exists() else {}

# Her business is affiliate + brand deals (sheet 03) and her shelf is her storefront.
# The two products she publicly refuses are the two that are NOT linked. Rule stated
# on the wire so nobody has to guess where the flag came from.
NOT_AFFILIATE = {"Glass Drop", "Oil Balm"}
AFFILIATE_RULE = ("Everything on her own shelf is affiliate-linked except the two she "
                  "publicly refuses - Glass Drop (E-04.6) and Oil Balm (E-04.8).")

# Her favourite moisturiser. Her audience calls it 'the good one' because she does.
HER_NAMES = {"Cloud Cream": "the good one", "SPF 50": "the SPF", "Red Reset": "the Red Reset",
             "Soft Clean": "the cleanser", "Daily Gel": "the gel", "Clear Wash": "the wash",
             "Night Serum": "the night serum", "Tint Veil": "the tint", "Oil Balm": "the balm",
             "Glass Drop": "the £62 one"}

CATEGORY_TO_TYPE = {"spf": "SPF", "cleanser": "Cleanser", "moisturiser": "Moisturiser",
                    "serum": "Serum", "makeup": "Base"}

# ---------------------------------------------------------------- money, never a float
_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
         "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
         "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def _words(n: int) -> str:
    n = int(n)
    if n < 20:
        return _ONES[n]
    if n < 100:
        t, r = divmod(n, 10)
        return _TENS[t] + ("-" + _ONES[r] if r else "")
    h, r = divmod(n, 100)
    return _ONES[h] + " hundred" + (" and " + _words(r) if r else "")


def gbp(n) -> str:
    """The ONLY way money leaves this process. Never a float, never a decimal."""
    return "£" + str(int(round(float(n))))


def in_words_gbp(n) -> str:
    n = int(round(float(n)))
    return _words(n).capitalize() + (" pound" if n == 1 else " pounds")


def band(lo, hi) -> str:
    return "about £" + str(int(lo)) + "–" + str(int(hi))


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


# ---------------------------------------------------------------- the shelf
def affiliate(product: str) -> bool:
    return product not in NOT_AFFILIATE


def touched(product: str) -> bool:
    """She has used everything on her own shelf; each row carries her own note."""
    return bool(BY.get(product, {}).get("maya_note"))


def shelf_row(p: dict) -> dict:
    return {"ref": p["ref"], "product": p["product"], "gbp": p["gbp"], "price": gbp(p["gbp"]),
            "type": p["type"], "skin": p["skin"], "finish": p["finish"],
            "maya_rating": p["maya_rating"], "maya_note": p["maya_note"],
            "affiliate": affiliate(p["product"]), "touched": True,
            "is_contradiction": bool(p.get("is_contradiction"))}


# ---------------------------------------------------------------- bug 3: routing as DATA
_ALIAS = {"Barrier Oil": "Oil Balm"}


def routing_rules() -> list:
    """Her notebook (E-02.2) as STRUCTURED DATA, never prose. As prose it did not fire."""
    out = []
    for r in RULES["routing"]:
        cond = str(r["if"]).upper()
        products, prose = [], []
        for t in r["then"]:
            name = _ALIAS.get(t, t)
            (products if name in BY else prose).append(name)
        row = {"condition": cond, "as_written": list(r["then"]), "source": "E-02.2"}
        if products:
            row["she_reaches_for"] = products
        if prose:
            row["rule"] = "; ".join(prose)
        out.append(row)
    return out


ROUTING = routing_rules()
ROUTING_BY_COND = {r["condition"]: r for r in ROUTING}


def routed_products(skin: list) -> list:
    out = []
    for c in skin or []:
        r = ROUTING_BY_COND.get(str(c).upper())
        if r:
            out += r.get("she_reaches_for", [])
    return [p for p in dict.fromkeys(out) if p in BY]


# ---------------------------------------------------------------- judge states
def maya_state(slots_by_key: dict | None = None) -> dict:
    """The judge state. Her standard is EXTRACTED (slots), her routing is her own
    handwriting as structured data, and the shelf carries her own notes verbatim."""
    st = {
        "name": "Maya Rao",
        "creed": VOICE["creed"],
        "voice": VOICE["style_rules"],
        "her_shelf": [{"product": p["product"], "gbp": p["gbp"], "type": p["type"],
                       "skin": p["skin"], "finish": p["finish"],
                       "maya_rating": p["maya_rating"], "maya_note": p["maya_note"]}
                      for p in SHELF],
        "her_written_routing_rules": ROUTING,          # BUG 3 - data, not prose
        "her_intake_questions": INTAKE,
        "her_scope": ("She is a beauty creator, not a doctor. She does not give medical advice, "
                      "does not advise on prescriptions or pregnancy, and does not advise children."),
    }
    if slots_by_key:
        st["her_extracted_standard"] = slots_by_key
        st["instruction"] = ("Apply `her_written_routing_rules` first - they are her own handwriting. "
                             "Then apply `her_extracted_standard`, which is her measured decision "
                             "profile taken from her public posts.")
    return st


# ---------------------------------------------------------------- the standard
SCRAPED = {
    "handle": "@mayarao", "bio": "skincare, mostly honest. london.",
    "posts": [{"caption": b["title"], "views": b["views"], "saves": b["saves"]}
              for b in CASE["broadcast_log"]],
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

SLOT_META = {
    "routine_size": ("How many products",
                     "my 5 minute morning routine. two products. that is it.", "E-03.5"),
    "budget_behaviour": ("Spending the whole budget",
                         "people do not need more products. they need to feel confident about the two they already own.",
                         "E-07.4"),
    "price_refusal": ("Price",
                      "the 62 pound serum everyone is posting. it is good. it is not 62 pounds good.",
                      "E-04.6"),
    "subtraction": ("Adding vs taking away",
                    "if your face freaks out every time you try something new, stop adding things. take things away.",
                    "E-03.6"),
    "hype": ("Hype", "things I bought because tiktok told me to. 4 of them were a waste.", "E-03.2"),
    "defended_category": ("The one she defends",
                          "SPF, obviously. non negotiable, I will die on this hill.", "E-04.5"),
    "asks_before_advising": ("Asks before advising", "what are you using now?", "E-02.1"),
    "tone": ("How she talks", "skincare, mostly honest. london.", "E-06.1"),
    "sells_hard": ("How hard she sells", "the product I would NOT rebuy.", "E-03.6"),
    "irritation_response": ("When skin reacts",
                            "if your face freaks out every time you try something new, stop adding things.",
                            "E-03.6"),
    "category_priority": ("Where the money goes",
                          "luxury vs drugstore. the cleanser genuinely does not matter. spend it on sunscreen.",
                          "E-03.4"),
    "cleanser_matters": ("Does the cleanser matter",
                         "the cleanser genuinely does not matter. spend it on sunscreen.", "E-03.4"),
}
_LABEL_FALLBACK_CAPTION = "people do not need more products. they need confidence."


def _caption_for(key: str) -> tuple:
    if key in SLOT_META:
        m = SLOT_META[key]
        return m[1], m[2]
    words = set(key.replace("_", " ").split())
    best, hits = _LABEL_FALLBACK_CAPTION, 0
    for cap in SCRAPED["captions"]:
        h = len(words & set(cap.lower().replace(".", " ").replace(",", " ").split()))
        if h > hits:
            best, hits = cap, h
    return best, "E-03"


def _label_for(key: str) -> str:
    if key in SLOT_META:
        return SLOT_META[key][0]
    return key.replace("_", " ").strip().capitalize()


def _side(x):
    """Normalise one side of a slot to {level, value, confidence}. Tolerates every
    shape LANE C might write: {level,value} {answer,p} {choice,confidence} or a scalar."""
    if x is None:
        return None
    if not isinstance(x, dict):
        return {"level": str(x), "value": None, "confidence": None, "confidence_known": False}
    if "level" in x:
        c = x.get("confidence")
        return {"level": str(x["level"]),
                "value": round(float(x["value"]), 2) if x.get("value") is not None else None,
                "confidence": round(float(c), 2) if c is not None else None,
                "confidence_known": c is not None}
    if "answer" in x:
        p = float(x.get("p", x.get("value", 0.0)))
        return {"level": "YES" if x["answer"] else "NO", "value": round(p, 2),
                "confidence": round(max(p, 1.0 - p), 2), "confidence_known": True}
    if "choice" in x:
        c = x.get("confidence")
        return {"level": str(x["choice"]), "value": round(float(c), 2) if c is not None else None,
                "confidence": round(float(c), 2) if c is not None else None,
                "confidence_known": c is not None}
    if "noul" in x:
        p = float(x["noul"])
        return {"level": "YES" if p > 0.5 else "NO", "value": round(p, 2),
                "confidence": round(max(p, 1.0 - p), 2), "confidence_known": True}
    return {"level": json.dumps(x)[:40], "value": None, "confidence": None, "confidence_known": False}


def load_standard_file() -> dict:
    """Read data/standard-extracted.json DEFENSIVELY. LANE C is rewriting it with
    MORE slots; tolerate extra slots, never assume six, never crash on a new shape."""
    p = DATA / "standard-extracted.json"
    if not p.exists():
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: dict = {}
    out["__meta__"] = raw.get("meta") if isinstance(raw, dict) and isinstance(raw.get("meta"), dict) else {}

    def _extras(d):
        if not isinstance(d, dict):
            return {}
        return {k: d[k] for k in ("label", "source_caption", "evidence_ref", "toggleable",
                                  "agrees", "derm_source") if k in d}

    def absorb_pairs(maya: dict, derm: dict):
        for k in list(maya.keys()) + [k for k in derm if k not in maya]:
            row = {"maya": _side(maya.get(k)), "derm": _side(derm.get(k))}
            row.update(_extras(derm.get(k)))
            row.update(_extras(maya.get(k)))     # her side wins for captions
            out[k] = row

    if isinstance(raw, dict) and isinstance(raw.get("slots"), list):
        for s in raw["slots"]:
            if not isinstance(s, dict):
                continue
            k = s.get("key") or s.get("slot") or s.get("slot_key")
            if not k:
                continue
            out[k] = {"maya": _side(s.get("maya")), "derm": _side(s.get("derm")),
                      "label": s.get("label"), "source_caption": s.get("source_caption") or s.get("caption"),
                      "evidence_ref": s.get("evidence_ref") or s.get("ref"),
                      "toggleable": s.get("toggleable")}
    elif isinstance(raw, list):
        for s in raw:
            if isinstance(s, dict) and (s.get("key") or s.get("slot")):
                k = s.get("key") or s.get("slot")
                out[k] = {"maya": _side(s.get("maya")), "derm": _side(s.get("derm")),
                          "label": s.get("label"), "source_caption": s.get("source_caption") or s.get("caption"),
                          "evidence_ref": s.get("evidence_ref") or s.get("ref"),
                          "toggleable": s.get("toggleable")}
    elif isinstance(raw, dict) and ("maya" in raw or "derm" in raw):
        absorb_pairs(raw.get("maya") or {}, raw.get("derm") or {})
    elif isinstance(raw, dict):
        # slot_key -> {maya: ..., derm: ...}
        for k, v in raw.items():
            if isinstance(v, dict) and ("maya" in v or "derm" in v):
                out[k] = {"maya": _side(v.get("maya")), "derm": _side(v.get("derm")),
                          "label": v.get("label"), "source_caption": v.get("source_caption"),
                          "evidence_ref": v.get("evidence_ref"), "toggleable": v.get("toggleable")}
    return out


def standard_sides_from_extract(ex: dict) -> tuple:
    """(maya, derm, seconds) read out of an /api/extract payload.

    The extraction and the standard are the same measurement of the same person by
    the same fourteen questions, so they are one run, not two. `build_standard`
    takes exactly this tuple.
    """
    slots = ex.get("slots") or []
    maya = {s["key"]: s["maya"] for s in slots if isinstance(s, dict) and s.get("maya")}
    derm = {s["key"]: s["derm"] for s in slots if isinstance(s, dict) and s.get("derm")}
    return maya, derm, float((ex.get("totals") or {}).get("seconds") or 0.0)


async def extract_standard_live() -> tuple:
    """The standard, extracted live. Two requests - one per judge - and they are the
    SAME two requests /api/extract makes.

    It used to be its own pair of requests against `Q.STANDARD_SLOTS`, the legacy six
    slots, while `extract_live()` separately asked the fourteen. So one `python -m
    backend.warm` extracted Maya twice, four requests, and then threw one extraction
    away: `build_standard` treats data/standard-extracted.json as the source of truth
    (`m = fm.get("maya") or maya.get(k)`) and that file carries all fourteen slots with
    both sides filled, so not one value from the six-slot run could ever reach the
    payload. Two requests bought nothing at all.

    Now there is one extraction and both callers read it. `Q.STANDARD_SLOTS` stays in
    questions.py untouched so the v1-to-v14 diff is still auditable; nothing sends it.
    Callers that already hold an extraction should use `standard_sides_from_extract`
    and not call this at all - backend/warm.py does.
    """
    ex = await extract_live(MAYA_SLUG)
    return standard_sides_from_extract(ex)


def build_standard(maya: dict, derm: dict, extraction_seconds: float, live: bool,
                   file_slots: dict | None = None) -> dict:
    file_slots = dict(file_slots or {})
    meta = file_slots.pop("__meta__", {}) or {}
    # the file is the source of truth (LANE C owns it); a live run only fills gaps
    keys = list(dict.fromkeys(list(file_slots.keys()) + list(maya.keys()) + list(derm.keys())))
    slots = []
    for k in keys:
        fm = file_slots.get(k, {})
        m = fm.get("maya") or maya.get(k)
        d = fm.get("derm") or derm.get(k)
        if m is None and d is None:
            continue
        cap, ref = _caption_for(k)
        if fm.get("agrees") is not None:
            agrees = bool(fm["agrees"])
        else:
            agrees = bool(m and d and str(m["level"]).strip().lower() == str(d["level"]).strip().lower())
        toggle = fm.get("toggleable")
        if toggle is None:
            toggle = k != "defended_category"
        row = {
            "key": k,
            "label": _label_for(k),
            "maya": m, "derm": d,
            "agrees": agrees,
            "source_caption": fm.get("source_caption") or cap,
            "evidence_ref": fm.get("evidence_ref") or ref,
            "toggleable": bool(toggle),
        }
        if fm.get("label"):
            row["statement"] = fm["label"]          # LANE C's rendered sentence
        if fm.get("derm_source"):
            row["derm_source"] = fm["derm_source"]
        st = (meta.get("slot_stability") or {}).get(k)
        if st:
            row["stability"] = st
        slots.append(row)
    agree = sum(1 for s in slots if s["agrees"])
    dis = len(slots) - agree
    n = len(slots)
    headline = ("Same " + _words(n) + " questions. They agree on " + _words(agree)
                + " and disagree on " + _words(dis) + ".")
    secs = extraction_seconds if live else (meta.get("extraction_seconds") or extraction_seconds)
    out = {"extraction_seconds": secs, "slot_count": n, "slots": slots,
           "agree_count": agree, "disagree_count": dis, "headline": headline,
           "live": live,
           "routing": extracted_routing({"slots": slots}),
           "provenance": ("Extracted from her public posts and from clinical guidance, "
                          "through the same typed slots."),
           "extraction_note": meta.get("note"),
           "generated_by": meta.get("generated_by")}
    return out


# --- routing, EXTRACTED (not authored). LANE C's route_<condition> slots ------
_ROUTE_COND_ALIAS = {"reacting": "SENSITIVE"}
ROUTE_CONSTRAINT_CONF = 0.9     # the only number we chose; applied to every condition alike


def extracted_routing(standard: dict) -> dict:
    """{CONDITION: {product, confidence}} from any slot named route_<condition>
    whose extracted value is a product on her shelf."""
    out = {}
    for s in standard.get("slots", []):
        k = str(s.get("key", ""))
        if not k.startswith("route_"):
            continue
        m = s.get("maya") or {}
        prod = str(m.get("level") or "")
        if prod not in BY:
            continue
        cond = k[len("route_"):].lower()
        cond = _ROUTE_COND_ALIAS.get(cond, cond.upper())
        c = m.get("confidence")
        out[cond] = {"product": prod, "confidence": float(c) if c is not None else 0.0,
                     "slot_key": k, "evidence_ref": s.get("evidence_ref")}
    return out


def required_products(skin: list, budget: int, owns: list, def_type: str | None,
                      routing: dict, cap: int) -> list:
    """Her extracted routing as a HARD constraint, exactly like the defended
    category - and relaxed, cheapest-confidence-first, when it cannot be afforded."""
    owns = owns or []
    cands = []
    for c in skin or []:
        r = (routing or {}).get(str(c).upper())
        if r and r["confidence"] >= ROUTE_CONSTRAINT_CONF and r["product"] not in owns:
            cands.append((r["confidence"], -BY[r["product"]]["gbp"], r["product"]))
    cands.sort(reverse=True)
    owns_def = any(BY[o]["type"] == def_type for o in owns if o in BY)
    def_cost = 0
    if def_type and not owns_def:
        prices = [BY[x]["gbp"] for x in PRODUCTS if BY[x]["type"] == def_type and x not in owns]
        def_cost = min(prices) if prices else 0
    chosen = []
    for _, _, prod in cands:
        trial = list(dict.fromkeys(chosen + [prod]))
        extra = 0 if (def_type and BY[prod]["type"] == def_type) else def_cost
        if sum(BY[x]["gbp"] for x in trial) + extra <= budget and len(trial) <= cap:
            chosen = trial
    return chosen


def slots_by_key(standard: dict) -> dict:
    return {s["key"]: s["maya"] for s in standard.get("slots", []) if s.get("maya")}


# ---------------------------------------------------------------- policy knobs
# ---------------------------------------------------------------- the safety net
# `out_of_scope` is ONE prior, and on the most urgent message in the corpus it is a
# coin flip. Measured over five identical triage runs, q-046 ("i had a bad reaction
# to something, red and peeling, what do i do") came back 0.48 / 0.48 / 0.51 / 0.50 /
# 0.50: referred once, answered four times. `refusal_reason` is the same judgement
# asked a different way and it is not marginal at all - `adverse_reaction` at 0.96 in
# every run, while every message that is safely hers comes back `none` at 0.94+.
#
# So a message is out of scope if EITHER signal says so. This is an OR and it is one
# way only: it can ADD a referral, it can never remove one, and no existing threshold
# was moved to get it. `refers_out()` is the single place that decides.
REFUSAL_REASON_GATE = 0.90

DEFAULT_POLICY = {"confidence_gate": 0.55, "emotional_gate": 2.6, "enough_gate": 0.30,
                  "max_items_cap": 4, "defended": "spf", "price_weight": 0.0, "routing": {},
                  # the second safety signal; see refers_out(). Not derived from her
                  # standard and not touched by any override - safety is not a slider.
                  "refusal_reason_gate": 0.90}


def policy_from(standard: dict, overrides: dict | None = None) -> dict:
    vals = {}
    for s in standard.get("slots", []):
        m = s.get("maya") or {}
        vals[s["key"]] = m.get("value")
        if s["key"] == "defended_category":
            vals["defended_choice"] = m.get("level")
    vals.update({k: v for k, v in (overrides or {}).items()})
    p = dict(DEFAULT_POLICY)
    p["refusal_reason_gate"] = REFUSAL_REASON_GATE      # never overridable
    # how many products she starts someone on. `starting_from_zero` asks exactly that
    # ("Three - a short but complete routine"); `routine_size` is the fallback.
    zero = vals.get("starting_from_zero")
    routine = vals.get("routine_size")
    if isinstance(zero, (int, float)):
        p["max_items_cap"] = int(clamp(round(float(zero)) + 1, 1, 4))
    elif isinstance(routine, (int, float)):
        p["max_items_cap"] = int(clamp(round(float(routine)) + 2, 1, 4))
    price = vals.get("price_refusal")
    if isinstance(price, (int, float)):
        # the more price is central to her judgement, the more decisive she is and the
        # fewer messages have to wait for her
        p["confidence_gate"] = round(clamp(0.55 + (2.8 - float(price)) * 0.05, 0.35, 0.80), 3)
        p["price_weight"] = round(clamp(float(price) / 3.0, 0.0, 1.0), 3)
    sub = vals.get("subtraction")
    if isinstance(sub, (int, float)):
        p["enough_gate"] = round(clamp(0.30 + (float(sub) - 0.62) * 0.15, 0.15, 0.60), 3)
    dc = overrides.get("defended_category") if overrides else None
    p["defended"] = str(dc or vals.get("defended_choice") or "spf").lower()
    p["routing"] = standard.get("routing") or extracted_routing(standard)
    return p


def defended_type(pol: dict) -> str | None:
    return CATEGORY_TO_TYPE.get(str(pol.get("defended", "spf")).lower())


# ---------------------------------------------------------------- the basket
def feasible(budget: int, owns: list, max_items: int, def_type: str | None,
             enforce: bool = True, required: list | None = None) -> list:
    """Every feasible set. Her non-negotiable category and her extracted routing
    are HARD CONSTRAINTS here in code, not preferences for Jev to weigh."""
    owns = [o for o in (owns or [])]
    required = [r for r in (required or []) if r in BY and r not in owns]
    pool = [p["product"] for p in SHELF if p["product"] not in owns]
    def_items = [x for x in pool if def_type and BY[x]["type"] == def_type]
    cheapest_def = min((BY[x]["gbp"] for x in def_items), default=None)
    owns_def = any(BY[o]["type"] == def_type for o in owns if o in BY)
    out = []
    for k in range(1, max(1, int(max_items)) + 1):
        for c in itertools.combinations(pool, k):
            if sum(BY[x]["gbp"] for x in c) > budget:
                continue
            if enforce and required and not all(r in c for r in required):
                continue
            if (enforce and cheapest_def is not None and not owns_def
                    and budget >= cheapest_def
                    and not any(BY[x]["type"] == def_type for x in c)):
                continue
            out.append(c)
    return out


def _baskets_state(combos: list) -> dict:
    return {"b" + str(i): {"items": [{"product": x, "gbp": BY[x]["gbp"], "type": BY[x]["type"],
                                      "skin": BY[x]["skin"], "finish": BY[x]["finish"],
                                      "maya_note": BY[x]["maya_note"]} for x in c],
                           "total_gbp": sum(BY[x]["gbp"] for x in c)}
            for i, c in enumerate(combos)}


CHUNK = 70


async def score_baskets(judge: dict, shopper: dict, combos: list) -> dict:
    """Stage 1. Every feasible set scored, packed ~70 questions per request."""
    chunks = [combos[i:i + CHUNK] for i in range(0, len(combos), CHUNK)]
    jobs = []
    for ch in chunks:
        st = {"judge": judge, "shopper": shopper, "baskets": _baskets_state(ch)}
        jobs.append((st, Q.basket_scores(st["baskets"])))
    results = await JEV.batch(jobs)
    scored = {}
    for ch, r in zip(chunks, results):
        a = r["answers"]
        for i, cb in enumerate(ch):
            k = "b" + str(i)
            if k in a:
                scored[cb] = round(float(a[k]["score"]), 4)
    return scored


async def pick_finalist(judge: dict, shopper: dict, finalists: list) -> tuple:
    """Stage 2 (bug #2). ONE choice over the top 8."""
    fin = {"b" + str(i): {"items": list(c), "total_gbp": sum(BY[x]["gbp"] for x in c)}
           for i, c in enumerate(finalists)}
    st = {"judge": judge, "shopper": shopper, "finalists": fin}
    r = await JEV.ask(st, Q.basket_choice(fin))
    a = r["answers"]["pick"]
    idx = int(str(a["choice"])[1:]) if str(a["choice"])[1:].isdigit() else 0
    idx = min(idx, len(finalists) - 1)
    return finalists[idx], round(float(a.get("confidence", 0.0)), 3)


async def decide_basket(shopper: dict, pol: dict, sweep: bool = False) -> dict:
    """The two-stage basket. Score all feasible -> top 8 -> one choice."""
    judge = maya_state(shopper.get("_slots"))
    budget = int(shopper["budget_gbp"])
    cap = int(min(int(shopper.get("max_items", 3)), pol["max_items_cap"]))
    dt = defended_type(pol)
    ceiling_budget = max(budget, 100) if sweep else budget
    skin = shopper.get("skin_conditions") or []
    req = required_products([s for s in skin if s != "not stated"], budget,
                            shopper.get("owns", []), dt, pol.get("routing") or {}, cap)
    combos = feasible(ceiling_budget, shopper.get("owns", []), cap, dt,
                      enforce=True, required=req)
    if not combos and req:
        combos = feasible(ceiling_budget, shopper.get("owns", []), cap, dt, enforce=True)
    if not combos:
        combos = feasible(ceiling_budget, shopper.get("owns", []), cap, dt, enforce=False)
    if not combos:
        return {"basket": [], "scored": [], "confidence": 0.0, "considered": 0,
                "judgments": 0, "cap": cap, "required": req}
    shop_for_jev = {k: v for k, v in shopper.items() if not k.startswith("_")}
    scored = await score_baskets(judge, shop_for_jev, combos)
    in_budget = {c: s for c, s in scored.items() if sum(BY[x]["gbp"] for x in c) <= budget}
    if not in_budget:
        in_budget = scored
    finalists = sorted(in_budget, key=lambda c: (-in_budget[c], sum(BY[x]["gbp"] for x in c)))[:8]
    winner, c2 = await pick_finalist(judge, shop_for_jev, finalists)
    ranked = sorted(scored, key=lambda c: (-scored[c], sum(BY[x]["gbp"] for x in c)))[:14]
    return {"basket": list(winner), "confidence": c2, "considered": len(combos),
            "cap": cap, "required": req,
            "scored": [{"items": list(c), "total": sum(BY[x]["gbp"] for x in c),
                        "score": scored[c]} for c in ranked],
            "all_scores": {"|".join(c): s for c, s in scored.items()}}


RUNGS = [30, 40, 50, 60, 80, 100]


def indifference(all_scores: dict, budget: int, winner: list) -> str:
    """Where the winning basket stops changing. Zero inference - re-reads the
    stage-1 scores we already paid for."""
    if not all_scores:
        return "One budget, one answer."
    def best_at(b):
        cands = [(s, k) for k, s in all_scores.items()
                 if sum(BY[x]["gbp"] for x in k.split("|")) <= b]
        if not cands:
            return None
        return max(cands, key=lambda t: (t[0], -sum(BY[x]["gbp"] for x in t[1].split("|"))))[1]
    # anchor on the top-scoring feasible set at the asked budget, so the band and the
    # sweep are measured on the same quantity
    target = best_at(budget) or "|".join(winner)
    rungs = sorted(set(RUNGS + [budget]))
    same = [b for b in rungs if best_at(b) == target]
    if not same:
        return "Her answer moves with the budget."
    lo, hi = min(same), max(same)
    # only claim a contiguous band
    for b in rungs:
        if lo < b < hi and best_at(b) != target:
            hi = b - 1
            break
    if hi <= lo:
        return "Her answer changes as soon as the budget moves off " + gbp(budget) + "."
    return "Between " + gbp(lo) + " and " + gbp(hi) + " her answer does not change."


# ---------------------------------------------------------------- the ceiling
def ceiling_for(product: str) -> dict | None:
    curve = FENCE.get(product)
    if not curve:
        return None
    pts = sorted((int(k), float(v)) for k, v in curve.items())
    x = None
    for i in range(1, len(pts)):
        (a_x, a_y), (b_x, b_y) = pts[i - 1], pts[i]
        if a_y >= 0.5 > b_y:
            t = (a_y - 0.5) / (a_y - b_y) if a_y != b_y else 0.0
            x = a_x + t * (b_x - a_x)
            break
    if x is None:
        return None
    lo = int(math.floor(x / 5.0) * 5)
    return {"band": band(lo, lo + 5),
            "provenance": "Estimated from Maya's own posts. She sets the line",
            "evidence_ref": BY.get(product, {}).get("ref", "E-04"),
            "product": product,
            "over_sticker": bool(x >= BY.get(product, {}).get("gbp", 0))}


DEFAULT_CEILING = {"band": band(50, 55),
                   "provenance": "Estimated from Maya's own posts. She sets the line",
                   "evidence_ref": "E-04.6", "product": "Glass Drop", "over_sticker": False}


# ---------------------------------------------------------------- the words
def _short(product: str) -> str:
    return HER_NAMES.get(product, product)


def basket_why(product: str, skin: list, pol: dict, owns: list) -> str:
    dt = defended_type(pol)
    if dt and BY[product]["type"] == dt:
        return "Her defended category."
    for c in skin or []:
        er = (pol.get("routing") or {}).get(str(c).upper())
        if er and er["product"] == product:
            return "Her rule for " + str(c).upper() + ", extracted from her own captions."
        r = ROUTING_BY_COND.get(str(c).upper())
        if r and product in r.get("she_reaches_for", []):
            return "Her own rule for " + str(c).upper() + "."
    if BY[product]["skin"].lower().startswith(tuple(str(s).lower()[:3] for s in (skin or []) if s)):
        return "Made for this skin."
    return "It fits the budget and it does a job nothing else in the basket does."


_WHY_TEXT = {
    "already_covered": "You already have something doing that job.",
    "over_her_price_line": "She likes it. Not at that price.",
    "wrong_for_their_skin": "Wrong texture for your skin.",
    "not_needed_yet": "A fourth step you do not need yet.",
    "does_not_fit_budget": "It does not fit in what you said you had.",
}


def compose_left_out(excluded: list, reasons: dict, basket: list, owns: list,
                     skin: list, budget: int, total: int) -> list:
    """Every refusal carries an alternative. `instead` is NEVER empty."""
    out = []
    remaining = max(0, budget - total)
    for i, prod in enumerate(excluded):
        reason = reasons.get(i, "not_needed_yet")
        p = BY[prod]
        why = _WHY_TEXT.get(reason, _WHY_TEXT["not_needed_yet"])
        instead = ""
        same_type_in_basket = [b for b in basket if BY[b]["type"] == p["type"]]
        same_type_owned = [o for o in owns if o in BY and BY[o]["type"] == p["type"]]
        if reason == "already_covered":
            if same_type_owned:
                why = "The " + same_type_owned[0] + " you already have is doing that job."
                instead = "Nothing. Save it."
            elif same_type_in_basket:
                why = same_type_in_basket[0] + " in the basket already does this."
                instead = same_type_in_basket[0] + ", " + gbp(BY[same_type_in_basket[0]]["gbp"]) + "."
            else:
                instead = "Nothing. Save it."
        elif reason == "over_her_price_line":
            if touched(prod) and p.get("maya_note"):
                why = p["maya_note"]
            cheaper = sorted([x for x in PRODUCTS
                              if BY[x]["type"] == p["type"] and BY[x]["gbp"] < p["gbp"]
                              and x not in owns],
                             key=lambda x: BY[x]["gbp"])
            instead = (cheaper[0] + " at " + gbp(BY[cheaper[0]]["gbp"]) + " does the same job."
                       if cheaper else "Nothing. Save it.")
        elif reason == "wrong_for_their_skin":
            routed = [x for x in routed_products(skin) if x != prod]
            instead = (routed[0] + ", " + gbp(BY[routed[0]]["gbp"]) + "." if routed
                       else "Nothing. Save it.")
        elif reason == "does_not_fit_budget":
            afford = sorted([x for x in PRODUCTS
                             if BY[x]["type"] == p["type"] and BY[x]["gbp"] <= remaining
                             and x not in owns and x not in basket],
                            key=lambda x: -BY[x]["maya_rating"])
            instead = (afford[0] + " at " + gbp(BY[afford[0]]["gbp"]) + " instead."
                       if afford else "Nothing. Save the " + gbp(remaining) + ".")
        else:
            instead = ("Nothing yet. Come back when " + _short(basket[0]) + " runs out."
                       if basket else "Nothing. Save it.")
        if not instead.strip():
            instead = "Nothing. Save it."
        out.append({"product": prod, "price": gbp(p["gbp"]), "ref": p["ref"],
                    "why": why, "instead": instead, "reason_code": reason,
                    "affiliate": affiliate(prod)})
    return out


def compose_verdict(basket: list, named: str | None, owns: list, budget: int,
                    requested_items: int) -> dict:
    total = sum(BY[x]["gbp"] for x in basket)
    refused_named = bool(named and named in BY and named not in basket)
    fewer_than_asked = len(basket) < max(1, int(requested_items))
    # a refusal is declining something they were considering, or handing back a
    # serious slice of the budget - not merely rounding down by a tenner
    held_back = bool(budget) and (budget - total) >= 0.35 * budget
    is_refusal = bool(refused_named or (fewer_than_asked and held_back) or not basket)
    names = [_short(x) for x in basket]

    def _join(ns):
        s = (" and ".join([", ".join(ns[:-1]), ns[-1]]) if len(ns) > 2 else " and ".join(ns))
        return s[:1].upper() + s[1:] if s else s

    if not basket:
        head = "Nothing. Save your money."
    elif refused_named and len(basket) == 1:
        head = "No. Just " + names[0] + "."
    elif refused_named:
        head = "Not that. " + _join(names) + "."
    elif len(basket) == 1:
        head = "One thing. " + basket[0] + "."
    else:
        head = _words(len(basket)).capitalize() + " things. " + _join(names) + "."
    voice = head + (" " + in_words_gbp(total) + "." if basket else "")
    if len(basket) == 1 and touched(basket[0]):
        note = BY[basket[0]]["maya_note"]
        if note and len(voice) + len(note) < 120:
            voice = voice + " " + note
    return {"headline": head, "in_her_voice": voice, "is_refusal": is_refusal}


def money_line(basket: list) -> dict:
    n = len(basket)
    aff = sum(1 for x in basket if affiliate(x))
    total = sum(BY[x]["gbp"] for x in basket)
    if n == 0:
        note = "Nothing in the basket. Maya earns nothing here."
    elif aff == 0:
        note = "Maya earns nothing on this one."
    else:
        note = (str(aff) + " of " + str(n) + " product" + ("s" if n != 1 else "")
                + " is affiliate-linked." if n == 1 or aff == 1 else
                str(aff) + " of " + str(n) + " products are affiliate-linked.")
    return {"affiliate_count": aff, "basket_value": gbp(total), "note": note,
            "rule": AFFILIATE_RULE}


def unspent_line(budget: int, total: int) -> dict:
    left = max(0, int(budget) - int(total))
    if left <= 0:
        return {"amount": gbp(0), "line": "She spent the whole " + gbp(budget) + "."}
    return {"amount": gbp(left),
            "line": "She left " + gbp(left) + " of your " + gbp(budget) + " on the table."}


# ================================================================ the card
async def build_card(spec: dict, standard: dict, pol: dict) -> dict:
    """One asker -> one verdict card. Re-decides every time it is called."""
    t0 = time.perf_counter()
    skin = [str(s).lower() for s in (spec.get("skin") or [])]
    budget = int(spec.get("budget") or 80)
    owns = [o for o in (spec.get("owns") or []) if o in BY]
    how_many = int(spec.get("how_many") or 3)
    said = spec.get("said") or ""
    shopper = {
        "says": said or "chose their skin, their budget and how many products they want",
        "skin_conditions": skin or ["not stated"],
        "budget_gbp": budget,
        "owns": owns,
        "max_items": how_many,
        "how_many_they_want": how_many,
        "_slots": slots_by_key(standard),
    }
    res = await decide_basket(shopper, pol, sweep=True)
    basket = res["basket"]
    total = sum(BY[x]["gbp"] for x in basket)

    # near-misses: the products she considered hardest and still left out
    best_with = {}
    for k, s in (res.get("all_scores") or {}).items():
        for x in k.split("|"):
            if x and s > best_with.get(x, -1):
                best_with[x] = s
    excluded = [x for x in sorted(best_with, key=lambda x: -best_with[x])
                if x not in basket and x not in owns][:3]
    named = spec.get("named_product") if spec.get("named_product") in BY else None
    if named and named not in basket and named not in excluded:
        excluded = ([named] + excluded)[:3]

    # Her most valuable refusal is the one she RATES and still declines on price.
    # `is_contradiction` marks it in the case pack (Glass Drop, 8.1/10, "Good. Not £62 good.",
    # E-04.6). Scored on basket fit alone it never surfaces - it is expensive, so it loses to
    # three cheap products she is merely neutral about, and the card ends up refusing nothing
    # interesting. Promote it when she could have afforded it and still did not pick it.
    contradiction = next((x for x in PRODUCTS
                          if BY[x].get("is_contradiction")
                          and x not in basket and x not in owns
                          and BY[x]["gbp"] <= budget), None)
    if contradiction and contradiction not in excluded:
        head = [named] if (named and named in excluded) else []
        rest = [x for x in excluded if x not in head and x != contradiction]
        excluded = (head + [contradiction] + rest)[:3]

    reasons = {}
    if excluded:
        try:
            st = {"judge": maya_state(shopper["_slots"]),
                  "shopper": {k: v for k, v in shopper.items() if not k.startswith("_")},
                  "chosen_basket": {"items": basket, "total_gbp": total},
                  "considered": {"p" + str(i): {"product": x, "gbp": BY[x]["gbp"],
                                                "type": BY[x]["type"], "skin": BY[x]["skin"],
                                                "maya_note": BY[x]["maya_note"]}
                                 for i, x in enumerate(excluded)}}
            r = await JEV.ask(st, Q.left_out_reasons(excluded))
            for i in range(len(excluded)):
                reasons[i] = choice(r["answers"], "why__" + str(i), "not_needed_yet")
        except JevUnavailable:
            reasons = {}

    left_out = compose_left_out(excluded, reasons, basket, owns, skin, budget, total)
    verdict = compose_verdict(basket, named, owns, budget, how_many)
    head_product = max(basket, key=lambda x: BY[x]["gbp"]) if basket else (named or "Glass Drop")
    ceiling = ceiling_for(head_product) or DEFAULT_CEILING
    card_id = spec.get("card_id") or new_card_id()
    payload = {
        "card_id": card_id,
        "parent_card_id": spec.get("parent_card_id"),
        "re_decided_at": now_iso(),
        "asker": {"name": spec.get("name") or "someone", "said": said,
                  "skin": skin, "budget": budget, "owns": owns, "how_many": how_many},
        "verdict": verdict,
        "basket": [{"product": x, "price": gbp(BY[x]["gbp"]), "type": BY[x]["type"],
                    "ref": BY[x]["ref"], "maya_note": BY[x]["maya_note"],
                    "affiliate": affiliate(x), "touched": touched(x),
                    "why": basket_why(x, skin, pol, owns)} for x in basket],
        "total": gbp(total),
        "unspent": unspent_line(budget, total),
        "left_out": left_out,
        "ceiling": ceiling,
        "money_line": money_line(basket),
        "indifference_band": indifference(res.get("all_scores") or {}, budget, basket),
        "og_image": "/api/card/" + card_id + "/og.png",
        "share_url": "/c/" + card_id,
        "baskets_considered": res["considered"],
        "basket_confidence": res["confidence"],
        "defended_category": pol.get("defended"),
        "routing_fired": [{"condition": c.upper(), "product": (pol.get("routing") or {})[c.upper()]["product"]}
                          for c in skin if c.upper() in (pol.get("routing") or {})],
        "routing_enforced": res.get("required") or [],
        "seconds": round(time.perf_counter() - t0, 2),
        "live": True,
        "spec": {"name": spec.get("name"), "said": said, "skin": skin, "budget": budget,
                 "owns": owns, "how_many": how_many,
                 "parent_card_id": spec.get("parent_card_id"),
                 "named_product": named},
    }
    return payload


def new_card_id() -> str:
    import uuid
    return "c-" + uuid.uuid4().hex[:6]


# ================================================================ the queue
_VARIANTS = [
    "what lipstick is that in the reel", "which foundation do u use for filming",
    "where is the jumper from lol", "i have oily skin and £35, what should i get",
    "combo skin, breakouts on chin, £50 help", "dry flaky skin in winter, budget 70",
    "sensitive + rosacea, £45, what's safe", "if you had to pick one serum forever which",
    "only ONE product for the rest of your life go", "is the night serum worth 42 honestly",
    "would you pay 62 for the glass drop", "is the tint veil worth it or is there a cheaper dupe",
    "i already use the daily gel, do i need a serum too", "i have the spf already what else",
    "got the soft clean last month, what next", "i own like 6 products should i stop buying",
    "i genuinely cannot tell if im oily or combo", "my skin is weird lately idk what changed",
    "wedding next month what do i start now", "interview tomorrow morning help",
    "holiday in 2 weeks what do i pack", "you're the only person i trust on this stuff",
    "obsessed with your account", "literally changed my routine because of you",
    "ordering next week when i get paid", "saving up for the cloud cream",
    "gonna buy it in the sale", "my mum wants to know what you'd get her, she's 60 dry skin",
    "buying for my boyfriend, he uses nothing, where does he start",
    "what would you buy if you only had 25 quid", "if it was your money what would you do",
    "i've been using tretinoin from my derm, can i add anything",
    "im pregnant, is any of this safe",
    "i had a bad reaction to something, red and peeling, what do i do",
    "i have perioral dermatitis, which of these is ok", "im on accutane currently",
    "my 12 year old wants a routine", "is this safe with my eczema medication",
]
_SYNTH_HANDLES = [
    "@bea", "@tashk", "@nadia.h", "@ellalou", "@meghanp", "@rosiej", "@aimee", "@dani",
    "@cleo", "@fiona", "@harriet", "@izzy", "@jaz", "@kiran", "@leila", "@mollyb",
    "@nell", "@orla", "@pippa", "@quinn", "@romy", "@sadie", "@tilly", "@una",
    "@verity", "@wren", "@xanthe", "@yas", "@zara", "@anya", "@bridie", "@cerys",
    "@delphi", "@esme", "@freya", "@greta", "@hollie", "@indy",
]


# ---- voice notes. Her audience sends them (case pack: voice._source, "E-06.1 voice
# note (00:52)"), so the queue has to carry them. A voice note is a MESSAGE WHOSE TEXT
# ARRIVED DIFFERENTLY and nothing below this line treats it as anything else: the
# transcript goes into `state.message` in the same field a typed DM occupies, through
# the same triage questions, the same safety gate and the same confidence gate.
#
# The audio is SYNTHETIC and says so everywhere - OpenAI tts-1 speaking a script we
# wrote, then OpenAI whisper-1 transcribing it. Written by scripts/transcribe_voice.py
# BEFORE the demo; nothing here calls OpenAI at request time. OpenAI hears it, Jev
# decides what to do about it, exactly like the images.
_VOICE_FILE = DATA / "voice-notes.json"


def voice_manifest() -> dict:
    """data/voice-notes.json, or an empty manifest. Never raises, never blocks a queue."""
    try:
        if _VOICE_FILE.exists():
            return json.loads(_VOICE_FILE.read_text(encoding="utf-8"))
    except Exception:                                            # noqa: BLE001
        return {}
    return {}


def voice_dms() -> list:
    """The transcribed voice notes, shaped exactly like a text DM plus a `voice` block.

    A note with no transcript (the TTS or the transcription failed) is dropped rather
    than guessed at - we never route the script we asked the TTS to read as if it were
    what came back.
    """
    man = voice_manifest()
    out = []
    for n in (man.get("notes") or []):
        t = (n.get("transcript") or "").strip()
        if not t:
            continue
        out.append({
            "id": n["id"], "ref": n["ref"], "from": n["from"],
            "text": t,                       # <- the ONLY thing triage sees
            "synthetic": True,
            "source": "voice",
            "voice": {
                "audio_url": n.get("audio_url") or ("/api/voice/" + str(n.get("file"))),
                "file": n.get("file"), "seconds": n.get("seconds"),
                "transcript": t,
                "stt_model": n.get("model") or man.get("stt_model"),
                "transcribe_ms": n.get("transcribe_ms"),
                "tts_model": n.get("tts_model") or man.get("tts_model"),
                "tts_voice": n.get("voice"),
                "tts_script": n.get("tts_script"),
                "verbatim_match": n.get("verbatim_match"),
                "synthetic": True,
                "disclosure": n.get("disclosure") or man.get("_comment"),
                "who_did_what": man.get("who_did_what"),
            },
        })
    return out


def dm_corpus() -> list:
    out = []
    for i, d in enumerate(CASE["inbox"]):
        out.append({"id": "q-%03d" % (i + 1), "ref": d["ref"], "from": d["handle"],
                    "text": d["text"], "synthetic": False})
    for j, t in enumerate(_VARIANTS):
        i = len(CASE["inbox"]) + j
        out.append({"id": "q-%03d" % (i + 1),
                    "ref": "E-05." + str(j + 1),
                    "from": _SYNTH_HANDLES[j % len(_SYNTH_HANDLES)],
                    "text": t, "synthetic": True})
    out += voice_dms()
    return out


FROZEN_CARD_FOR_HANDLE = {"@jessica": "c-jessica"}


def queue_card_id(dm: dict) -> str:
    if dm["from"] in FROZEN_CARD_FOR_HANDLE:
        return FROZEN_CARD_FOR_HANDLE[dm["from"]]
    return "c-" + hashlib.sha1((dm["ref"] + dm["from"]).encode()).hexdigest()[:6]


async def run_triage(texts: list, standard: dict) -> list:
    """ONE speculative fan-out per DM, all fired at once."""
    st = maya_state(slots_by_key(standard))
    qs = Q.triage(PRODUCTS, INTAKE)
    jobs = [({"creator": st, "message": t}, qs) for t in texts]
    results = await JEV.batch(jobs)
    return [r["answers"] for r in results]


_HOLD = {
    "unclear": "She has not said enough here for her standard to be sure. Maya decides.",
    "personal": "This person wants Maya specifically, not a good answer. Maya decides.",
}

_REFER_DISPLAY = {
    "a dermatologist": "a dermatologist",
    "their prescribing doctor": "the doctor who prescribed it",
    "a pharmacist or their GP": "a pharmacist or your GP",
    "a parent and their GP": "their parent and a GP",
}

_REFUSAL_WHY = {
    "prescription_interaction": "They are on a prescription and asking what to layer on top of it. That is their doctor's call.",
    "pregnancy_or_nursing": "They are pregnant or nursing and asking what is safe. Maya is not the person to answer that.",
    "active_skin_condition": "They describe a skin condition that needs someone who can actually look at it.",
    "adverse_reaction": "Their skin is reacting right now. That needs a clinician, not a shopping list.",
    "a_child": "The advice is for a child. Maya does not write routines for children.",
    "none": "This sits outside what a beauty creator should answer.",
}


#: jobs she can answer with nothing further, and jobs her own notebook says she
#: always asks back on ("shade question -> ask what foundation they currently wear")
_ALWAYS_ANSWERABLE = {"not_a_question", "later"}
_ALWAYS_ASKS_BACK = {"what_is_it", "diagnose_me"}


def _intake_like(*words: str) -> str | None:
    """Her own intake question containing these words, so a question back is always
    in her handwriting and never in ours."""
    for qq in INTAKE:
        low = str(qq).lower()
        if all(w in low for w in words):
            return qq
    return None


# ========================================================= which question back
# GRADED BUG. Reading all fifty drafted replies next to the message that produced
# them, the single largest failure was not the lane and not the basket. It was the
# question we bounced back:
#
#   "i dont even know what my skin type is lol"        -> `Skin type?`
#   "i genuinely cannot tell if im oily or combo"      -> `Budget?`
#   "what lipstick is that in the reel"                -> `Do you actually care
#                                                         about skincare or do you
#                                                         just want to look hot
#                                                         tomorrow?`
#
# All three came out of `which_question_back`, a six-way choice Jev returned at
# 0.31-0.48 confidence, taken by code at any confidence with no check against what
# the message had already said. Her case pack already answers two of the three in
# `decision_rules.routing`, so the fix is to put that routing in CODE as a hard
# constraint - exactly how feasible() treats her product routing - and to strike
# off any intake question the message has already answered.

#: decision_rules.routing, verbatim: "shade question -> ask what foundation they
#: currently wear". `diagnose_me` is the same shape: someone who has just told us
#: they cannot tell what their skin is cannot be asked `Skin type?`, so the honest
#: next step is the one she actually uses to work it out.
_JOB_QUESTION = {
    "what_is_it": _intake_like("using", "now"),
    "diagnose_me": _intake_like("using", "now"),
}


def _already_answered(q: str, a: dict) -> bool:
    """True when `message` has already told us the thing this intake question asks.
    Asking it anyway is not a question, it is a sign nobody read the message."""
    low = str(q).lower()
    if "skin type" in low:
        # they stated it, or they opened by saying they do not know it
        return bool(Q.read_skin(a)) or choice(a, "job", "") == "diagnose_me"
    if "budget" in low:
        return choice(a, "budget", "not_stated") != "not_stated"
    if "using now" in low:
        return noul(a, "already_owns") > 0.5 and choice(a, "which_owned", "none") in BY
    return False


def question_back_for(a: dict, override: str | None = None) -> str:
    """Which ONE of her intake questions to ask back. Four sources, in this order,
    and only the third is Jev's:

      1. Her own routing (`_JOB_QUESTION`). A hard constraint from her case pack.
      2. `override` - the gap the indifference probe MEASURED to change her answer -
         unless the message has already answered it.
      3. Jev's `which_question_back`, unless the message has already answered it.
      4. The first of her intake questions the message has not already answered.

    This can only change WHICH question is asked. It never decides whether to ask,
    so no lane, gate or referral is reachable from here.
    """
    routed = _JOB_QUESTION.get(choice(a, "job", "pick_for_me"))
    if routed:
        return routed
    if override and not _already_answered(override, a):
        return override
    pick = choice(a, "which_question_back", "") or ""
    if pick in INTAKE and not _already_answered(pick, a):
        return pick
    for qq in INTAKE:
        if not _already_answered(qq, a):
            return qq
    return INTAKE[0]


def has_enough(a: dict, pol: dict) -> bool:
    """Composite over calibrated judgments, not one prior.

    `enough_to_answer` alone is a poor gate once her state carries her intake
    questions - it reads "would she ask something first", and the honest answer for
    a creator whose fourth style rule is "asks what you already own" is almost
    always yes. So we ask the question her intake questions actually ask: does the
    message carry skin, money, a count, a named product or something they own?
    """
    job = choice(a, "job", "pick_for_me")
    if job in _ALWAYS_ANSWERABLE:
        return True
    if job in _ALWAYS_ASKS_BACK:
        return False
    if job == "is_it_worth_it":
        return choice(a, "named_product", "none") in BY
    # GRADED BUG. `do_i_need_it` is a yes/no about adding to what they ALREADY have,
    # so if we cannot name what they have we are not answering their question, we are
    # writing a shopping list. "i own like 6 products should i stop buying" came back
    # as "Two things. The SPF and the cleanser. Forty-eight pounds." Her fourth style
    # rule, verbatim: "Asks what you already own before adding anything." So when the
    # owned product does not resolve to her shelf, she asks. This tightens the test -
    # it moves messages OUT of answered, never into it.
    if job == "do_i_need_it":
        return (noul(a, "already_owns") > 0.5
                and choice(a, "which_owned", "none") in BY
                and noul(a, "enough_to_answer") >= pol["enough_gate"])
    signal = (bool(Q.read_skin(a))
              or choice(a, "budget", "not_stated") != "not_stated"
              or choice(a, "max_items", "not_stated") != "not_stated"
              or (noul(a, "already_owns") > 0.5 and choice(a, "which_owned", "none") in BY)
              or choice(a, "named_product", "none") in BY)
    return bool(signal) and noul(a, "enough_to_answer") >= pol["enough_gate"]


def refers_out(a: dict, pol: dict) -> tuple:
    """(out_of_scope, which signal fired, its strength). Two independent readings of
    the same question, OR-ed. See REFUSAL_REASON_GATE for why there are two."""
    oos = noul(a, "out_of_scope")
    reason = choice(a, "refusal_reason", "none")
    rc = conf(a, "refusal_reason")
    named = (reason != "none" and reason in _REFUSAL_WHY
             and rc >= float(pol.get("refusal_reason_gate", REFUSAL_REASON_GATE)))
    if oos > 0.5:
        return True, ("both" if named else "out_of_scope"), round(max(oos, rc if named else 0.0), 2)
    if named:
        return True, "refusal_reason", round(rc, 2)
    return False, None, round(oos, 2)


def lane_for(a: dict, pol: dict) -> tuple:
    out, _signal, strength = refers_out(a, pol)
    jc = conf(a, "job")
    emo = score(a, "emotional_weight")
    if out:
        return "referred", strength
    if jc < pol["confidence_gate"]:
        return "held", round(jc, 2)
    if emo >= pol["emotional_gate"]:
        return "held", round(jc, 2)
    if not has_enough(a, pol):
        return "asked_back", round(jc, 2)
    return "answered", round(jc, 2)


def hold_reason_for(a: dict, pol: dict) -> str:
    if conf(a, "job") < pol["confidence_gate"]:
        return _HOLD["unclear"]
    return _HOLD["personal"]


def draft_for(dm: dict, a: dict, lane: str, basket: list, pol: dict,
              question_override: str | None = None) -> dict:
    """Her voice. Third person about anything she has not touched - and she has
    touched everything on her own shelf, so first person is only ever her own note."""
    job = choice(a, "job", "pick_for_me")
    named = choice(a, "named_product", "none")
    named = named if named in BY else None
    owned = choice(a, "which_owned", "none")
    owned = owned if owned in BY else None
    # her routing first, then the gap the indifference probe MEASURED to change her
    # answer, then Jev - and never a question this message has already answered.
    qback = question_back_for(a, question_override)
    total = sum(BY[x]["gbp"] for x in basket)

    if lane == "referred":
        why = _REFUSAL_WHY.get(choice(a, "refusal_reason", "none"), _REFUSAL_WHY["none"])
        code = choice(a, "refer_to", "a dermatologist")
        if code.startswith("nobody"):
            code = "a dermatologist"
        who = _REFER_DISPLAY.get(code, code)
        draft = ("I am not the right person for this one. Please ask " + who
                 + ". I would rather send you there than guess with your skin.")
        _out, signal, strength = refers_out(a, pol)
        return {"draft_reply": draft, "question_back": None, "hold_reason": None,
                "refusal": {"why": why, "refer_to": who, "refer_to_code": code,
                            "reason_code": choice(a, "refusal_reason", "none"),
                            "signal": signal, "signal_strength": strength}}

    if lane == "asked_back":
        # GRADED BUG. A `what_is_it` whose product Jev DID resolve to her shelf was
        # still getting a bare intake question back. "which foundation do u use for
        # filming" (named_product = Tint Veil at 0.85) came out as "What are you
        # using now?" and nothing else. Name the thing first, then ask her routing
        # question. It stays an ask-back, so no gate and no lane moves.
        if job == "what_is_it" and named:
            head = named + ". " + in_words_gbp(BY[named]["gbp"]) + "."
            note = BY[named]["maya_note"] if touched(named) else ""
            if note and len(head) + len(note) + len(qback) < 90:
                head = head + " " + note
            return {"draft_reply": head + " " + qback, "question_back": qback,
                    "hold_reason": None, "refusal": None}
        return {"draft_reply": qback, "question_back": qback, "hold_reason": None,
                "refusal": None}

    if lane == "held":
        reason = hold_reason_for(a, pol)
        if job == "not_a_question":
            draft = "Thank you. Genuinely. Nothing to buy today."
        elif noul(a, "needs_question_back") > 0.5:
            draft = qback
        else:
            draft = "Held for you. Say the word and I will draft it."
        return {"draft_reply": draft, "question_back": None, "hold_reason": reason,
                "refusal": None}

    # answered
    if job == "what_is_it":
        q = "What are you using now?"
        return {"draft_reply": q, "question_back": q, "hold_reason": None, "refusal": None}
    if job == "not_a_question":
        return {"draft_reply": "Thank you. Genuinely. Nothing to buy today.",
                "question_back": None, "hold_reason": None, "refusal": None}
    if job == "is_it_worth_it" and named:
        p = BY[named]
        cl = ceiling_for(named)
        if cl and not cl["over_sticker"]:
            line = (p["maya_note"] if touched(named) and "not" in p["maya_note"].lower()
                    else "Good. Not " + gbp(p["gbp"]) + " good.")
            draft = line + " Her line on it is " + cl["band"] + "."
        else:
            draft = ("Yes. " + gbp(p["gbp"]) + ". " + (p["maya_note"] if touched(named) else ""))
        return {"draft_reply": draft.strip(), "question_back": None, "hold_reason": None,
                "refusal": None}
    if job == "later":
        # GRADED BUG. The template asserted "payday" on every one of these. The job's
        # own criteria list four triggers - payday, next month, a restock, a sale -
        # and nothing downstream knows which one this message gave. "gonna buy it in
        # the sale" came back as "Buy it on payday, not before.", which reads as
        # nobody having read it. Say only the part that is true for all four.
        prod = named or (basket[0] if basket else None)
        if prod:
            draft = "It is worth the " + gbp(BY[prod]["gbp"]) + ". It will still be there."
        else:
            draft = "Good. Buy it when you are ready. It will still be there."
        return {"draft_reply": draft, "question_back": None, "hold_reason": None, "refusal": None}
    if basket:
        v = compose_verdict(basket, named, [owned] if owned else [], 0, len(basket))
        draft = v["in_her_voice"]
        if owned and job == "do_i_need_it":
            # GRADED BUG. This named basket[0] and then priced the WHOLE basket. "i
            # already use the daily gel, do i need a serum too" came out as "No. Just
            # the SPF. Forty-six pounds." - one product, two products' worth of money.
            # A yes/no question gets a yes/no, and the price covers what it names.
            names = [_short(x) for x in basket]
            if len(names) == 1:
                head = "No. Just " + names[0] + "."
            else:
                body = ", ".join(names[:-1]) + " and " + names[-1]
                head = "No. " + body[:1].upper() + body[1:] + "."
            draft = head + " " + in_words_gbp(total) + "."
        return {"draft_reply": draft, "question_back": None, "hold_reason": None, "refusal": None}
    return {"draft_reply": qback, "question_back": qback, "hold_reason": None, "refusal": None}


def shopper_from_triage(a: dict) -> dict:
    owned = choice(a, "which_owned", "none")
    owns = [owned] if (noul(a, "already_owns") > 0.5 and owned in BY) else []
    return {"skin": Q.read_skin(a),
            "budget": Q.BUDGET_BANDS.get(choice(a, "budget", "not_stated"), 80),
            "max_items": Q.ITEM_BANDS.get(choice(a, "max_items", "not_stated"), 3),
            "owns": owns}


BASKET_JOBS = {"pick_for_me", "do_i_need_it", "occasion", "buying_for_someone_else"}


# ================================================================ the gap probe
# "It only asks when the answer actually depends on it."
#
# The old test for bouncing a question back was "is something missing from the
# message". That is the wrong test. What matters is whether the missing thing
# CHANGES WHAT SHE WOULD SEND. So for every gap we enumerate its plausible values,
# run the SAME two-stage basket once per value, and compare the winners:
#
#   same winning basket for every value -> the question is pointless. Answer.
#   different winners                   -> ask, and ask the gap that discriminates.
#
# This is `indifference()` - the "between £40 and £80 her answer does not change"
# band already printed on every card - moved off money and onto intake. It invents
# no new opinion about the person: it re-runs the basket she already knows how to
# build, once per hypothesis, and every run goes out in ONE fan-out.
#
# Three rules keep it honest, and they all point the same way (towards asking):
#   * A gap we could not afford to test IN FULL is never called indifferent. A
#     capped probe can only ever conclude "ask"; it can never conclude "answer".
#   * A probe whose baseline run failed is never called indifferent.
#   * It only ever moves asked_back -> answered. `referred` and `held` are not
#     reachable from here, so no safety refusal can be argued away by an
#     indifference result and no confidence gate is touched.

GAP_PROBE_JOBS = BASKET_JOBS | {"diagnose_me"}
GAP_MAX_VARIANTS = 8        # per message, on top of the one baseline run

# MEASURED, AND THEN TURNED OFF. The probe is correct and it is honest, and on this
# corpus it bought nothing: 9 messages probed, 78 extra basket runs, 157 extra HTTP
# requests, and `answered_despite_gap` came back 0. It moved no message into the
# answered lane. All it changed was WHICH of her intake questions 9 of the ask-backs
# used. Priced against the rest of the system that is the single most expensive thing
# we run (971k -> 304k input tokens on one queue warm, a 3.2x cut), so the default is
# OFF and the finding stays reproducible:
#
#   GAP_PROBE_MESSAGES=20 python -m backend.warm queue
#   E.build_queue_raw(st, pol, gap_cap=20)
#
# Nothing else changed: the code, the contract fields, `gap_stats` and every honesty
# rule below are exactly as they were. With the probe off every card carries
# `gap_probe: null` and `answered_despite_gap: false`, which is what they already
# carried for the 41 messages that were never probed.
GAP_MAX_MESSAGES = int(os.environ.get("GAP_PROBE_MESSAGES", "0") or 0)
GAP_BUDGETS = (30, 60, 100)
GAP_COUNTS = (1, 2, 4)

# A skin condition is a PLAUSIBLE value of an unstated skin type when the triage
# fan-out WE ALREADY PAID FOR gives it more than a trace of probability. This is a
# hypothesis filter, not a decision gate: on its own it decides nothing, it only
# says which worlds are worth simulating. `Q.read_skin`'s 0.55 means "she says she
# is oily"; this means "oily cannot be ruled out". If nothing clears it, the message
# says nothing whatsoever about skin and ALL FIVE conditions stay on the table -
# which is the conservative direction, because more hypotheses means more chance
# they disagree and more chance we ask.
GAP_SKIN_PLAUSIBLE = 0.15


#: gap -> the one of HER intake questions that closes it. `count` maps to nothing:
#: she has no intake question about how many products, so for that gap we leave
#: Jev's own `which_question_back` pick alone rather than inventing her a question.
GAP_QUESTION = {
    "skin": _intake_like("skin", "type"),
    "budget": _intake_like("budget"),
    "owns": _intake_like("using", "now"),
    "count": None,
}

GAP_LABEL = {"skin": "skin type", "budget": "budget",
             "count": "how many products", "owns": "what they already own"}


def plausible_skin(a: dict) -> list:
    """The skin conditions this message has not ruled out."""
    live = [c for c in Q.SKIN_CONDITIONS if noul(a, "skin__" + c) >= GAP_SKIN_PLAUSIBLE]
    return live or list(Q.SKIN_CONDITIONS)


def detect_gaps(a: dict) -> list:
    """The intake facts this message does not carry, in the order her own intake
    questions ask for them."""
    gaps = []
    if not Q.read_skin(a):
        gaps.append({"gap": "skin", "values": plausible_skin(a), "probeable": True})
    if choice(a, "budget", "not_stated") == "not_stated":
        gaps.append({"gap": "budget", "values": list(GAP_BUDGETS), "probeable": True})
    if choice(a, "max_items", "not_stated") == "not_stated":
        gaps.append({"gap": "count", "values": list(GAP_COUNTS), "probeable": True})
    if noul(a, "already_owns") > 0.5 and choice(a, "which_owned", "none") not in BY:
        # They say they own something and did not say what. Nothing in the answers we
        # hold is a distribution over her ten products, so there is no honest set of
        # values to enumerate. Detected, never simulated, and therefore - by the rule
        # above - never indifferent.
        gaps.append({"gap": "owns", "values": [], "probeable": False})
    return gaps


def gap_variants(a: dict) -> tuple:
    """(gaps, variants). One variant per plausible value, ONE GAP VARIED AT A TIME
    with everything else held at what the message actually said. Varying one at a
    time is what makes "which question would actually help" answerable at the end -
    a cross product tells you the answer moved, not what moved it."""
    base = shopper_from_triage(a)
    gaps = detect_gaps(a)
    variants = [{"gap": None, "value": None, "shopper": dict(base)}]
    left = GAP_MAX_VARIANTS
    for g in gaps:
        vals = list(g.get("values") or [])
        if not g.get("probeable") or not vals or len(vals) > left:
            g["tested"] = False
            continue
        g["tested"] = True
        left -= len(vals)
        for v in vals:
            sh = dict(base)
            if g["gap"] == "skin":
                sh["skin"] = [v]
            elif g["gap"] == "budget":
                sh["budget"] = int(v)
            elif g["gap"] == "count":
                sh["max_items"] = int(v)
            variants.append({"gap": g["gap"], "value": v, "shopper": sh})
    return gaps, variants


def _join_labels(items: list) -> str:
    if len(items) > 2:
        return ", ".join(items[:-1]) + " and " + items[-1]
    return " and ".join(items)


def gap_verdict(gaps: list, variants: list, baskets: list, pol: dict) -> dict:
    """Same winner everywhere -> the gaps did not matter, so answer. Otherwise name
    the gap whose hypotheses produced the MOST different baskets: that is the one
    question worth her asker's time.

    The comparison is over the HYPOTHESES only, never against the baseline. "Not
    stated" is the absence of a value, not a plausible value of it, and the baseline
    basket is the engine's best guess in the dark - counting it would let one noisy
    guess invent a disagreement that none of the real worlds have. If every plausible
    world agrees, the answer we send is the one they agree on, not the guess.
    """
    base = list(baskets[0] or [])
    seen_by_gap: dict = {}
    for v, b in zip(variants[1:], baskets[1:]):
        row = seen_by_gap.setdefault(v["gap"], {"values": [], "baskets": [], "seen": set()})
        row["values"].append(v["value"])
        row["baskets"].append(list(b or []))
        row["seen"].add(tuple(sorted(b or [])))

    detail: dict = {}
    for g in gaps:
        name = g["gap"]
        row = seen_by_gap.get(name)
        if not g.get("tested") or not row:
            detail[name] = {"tested": False, "distinct": None, "mattered": True,
                            "values": list(g.get("values") or []), "baskets": [],
                            "why": "not simulated, so it is treated as mattering"}
            continue
        detail[name] = {"tested": True, "distinct": len(row["seen"]),
                        "mattered": len(row["seen"]) > 1,
                        "values": row["values"], "baskets": row["baskets"]}

    # every gap moot on its own is not enough: two gaps can each be internally
    # consistent and still disagree with each other, so the whole hypothesis set has
    # to land on ONE basket.
    everything = {tuple(sorted(b or [])) for b in baskets[1:]}
    indifferent = all(not d["mattered"] for d in detail.values()) and len(everything) <= 1
    agreed = sorted(everything)[0] if (indifferent and everything) else None
    did_not_matter = [k for k, d in detail.items() if d["tested"] and not d["mattered"]]
    mattered = [k for k, d in detail.items() if d["mattered"]]

    disc = None
    if mattered:
        # most different baskets wins; an untested gap counts as the weakest evidence
        # (2) so a gap we actually measured always outranks one we only assumed.
        order = [g["gap"] for g in gaps]
        disc = sorted(mattered, key=lambda k: (-(detail[k]["distinct"] or 2),
                                               order.index(k)))[0]

    gap_closed = None
    if did_not_matter:
        gap_closed = _join_labels([GAP_LABEL[k] for k in did_not_matter]) + " didn't matter here"
    elif indifferent:
        gap_closed = "nothing missing here would have changed her answer"

    return {
        "gaps": [g["gap"] for g in gaps],
        "gap_detail": detail,
        "baseline_basket": base,
        # what every plausible world agreed on; the baseline only when there was
        # nothing to disagree about
        "agreed_basket": list(agreed) if agreed is not None else (base if indifferent else None),
        "indifferent": bool(indifferent),
        "gaps_that_did_not_matter": did_not_matter,
        "discriminating_gap": disc,
        "question": GAP_QUESTION.get(disc) if disc else None,
        "gap_closed": gap_closed,
        "variants_run": len(variants),
        "rule": ("Every plausible value of the gap was run through the same two-stage "
                 "basket. She asks only when the winning basket actually changed."),
        "policy": {"max_items_cap": pol.get("max_items_cap"),
                   "enough_gate": pol.get("enough_gate"),
                   "confidence_gate": pol.get("confidence_gate"),
                   "defended": pol.get("defended")},
    }


async def build_queue_raw(standard: dict, pol: dict, basket_cap: int = 26,
                          gap_cap: int = GAP_MAX_MESSAGES) -> dict:
    """50 DMs, one fan-out each, then real baskets for the answered ones AND every
    gap hypothesis of the ones that wanted to bounce a question back - all in one
    second fan-out, so the probe costs wall time only once."""
    dms = dm_corpus()
    t0 = time.perf_counter()
    answers = await run_triage([d["text"] for d in dms], standard)
    triage_seconds = round(time.perf_counter() - t0, 2)
    judgments = sum(len(a) for a in answers)
    slots = slots_by_key(standard)

    recs = []
    for d, a in zip(dms, answers):
        lane, c = lane_for(a, pol)
        recs.append({**d, "answers": a, "lane0": lane, "confidence": c,
                     "shopper": shopper_from_triage(a), "basket": None, "scored": [],
                     "gap_probe": None})

    wants = [r for r in recs
             if r["lane0"] == "answered" and choice(r["answers"], "job", "") in BASKET_JOBS]
    wants = wants[:basket_cap]

    # everything that wanted to ask a question back and could have had a basket
    probes = [r for r in recs
              if r["lane0"] == "asked_back"
              and choice(r["answers"], "job", "") in GAP_PROBE_JOBS][:gap_cap]
    plans = []
    for r in probes:
        gaps, variants = gap_variants(r["answers"])
        plans.append((r, gaps, variants))

    def one(rec, shopper):
        sh = {"says": rec["text"], "skin_conditions": shopper["skin"] or ["not stated"],
              "budget_gbp": shopper["budget"], "owns": shopper["owns"],
              "max_items": shopper["max_items"], "_slots": slots}
        return decide_basket(sh, pol, sweep=False)

    tasks = [one(r, r["shopper"]) for r in wants]
    for r, _g, variants in plans:
        tasks += [one(r, v["shopper"]) for v in variants]

    t1 = time.perf_counter()
    # ONE fan-out. Jev is flat in question count and 100-way concurrent, so the
    # hypotheses cost roughly what one of them would cost on its own.
    outs = await asyncio.gather(*tasks, return_exceptions=True) if tasks else []
    basket_seconds = round(time.perf_counter() - t1, 2)

    def unwrap(o):
        return o if isinstance(o, dict) else None

    cur = 0
    for r in wants:
        o = unwrap(outs[cur]); cur += 1
        if o:
            r["basket"] = o["basket"]
            r["scored"] = o["scored"]
    gap_variants_run = 0
    for r, gaps, variants in plans:
        res = [unwrap(o) for o in outs[cur:cur + len(variants)]]
        cur += len(variants)
        gap_variants_run += len(variants)
        if res[0] is None or any(x is None for x in res):
            # a hypothesis we could not run is a hypothesis we cannot rule out
            r["gap_probe"] = {"gaps": [g["gap"] for g in gaps], "gap_detail": {},
                              "indifferent": False, "gaps_that_did_not_matter": [],
                              "discriminating_gap": None, "question": None,
                              "gap_closed": None, "baseline_basket": [],
                              "variants_run": len(variants), "incomplete": True,
                              "rule": "One or more hypotheses did not come back, so "
                                      "nothing here is called indifferent."}
            continue
        v = gap_verdict(gaps, variants, [x["basket"] for x in res], pol)
        v["baseline"] = {"basket": res[0]["basket"], "scored": res[0]["scored"]}
        # the reply we would send if the gaps turn out not to matter: the basket every
        # plausible world agreed on, carrying THAT run's scores so an override re-ranks
        # it against the same numbers it was chosen from.
        src = next((x for x in res[1:]
                    if sorted(x["basket"]) == sorted(v["agreed_basket"] or [])), res[0]) \
            if v["indifferent"] else None
        v["answer"] = ({"basket": list(v["agreed_basket"] or []), "scored": src["scored"]}
                       if v["indifferent"] and src else None)
        v["variants"] = [{"gap": vr["gap"], "value": vr["value"], "basket": x["basket"]}
                         for vr, x in zip(variants, res)]
        v["incomplete"] = False
        r["gap_probe"] = v

    return {"dms": recs, "triage_seconds": triage_seconds, "basket_seconds": basket_seconds,
            "judgments": judgments, "baskets_computed": len([r for r in recs if r["basket"]]),
            "gap_probes": len(plans), "gap_variants_run": gap_variants_run,
            "built_at": now_iso()}


GAP_CLAIM = "It only asks when the answer actually depends on it."


def gap_stats(cards: list, raw: dict) -> dict:
    """What the probe actually bought, counted rather than claimed."""
    probed = [c for c in cards if c.get("gap_probe")]
    answered = [c for c in probed if c.get("answered_despite_gap")]
    pairs_tested = pairs_moot = 0
    for c in probed:
        for _k, d in ((c["gap_probe"].get("tested")) or {}).items():
            if d.get("tested"):
                pairs_tested += 1
                if not d.get("mattered"):
                    pairs_moot += 1
    asks = [c for c in probed if c["lane"] == "asked_back"]
    return {
        "claim": GAP_CLAIM,
        "messages_probed": len(probed),
        "variants_run": raw.get("gap_variants_run", 0),
        "answered_despite_gap": len(answered),
        "answered_despite_gap_ids": [c["id"] for c in answered],
        "gaps_tested": pairs_tested,
        "gaps_that_did_not_matter": pairs_moot,
        "still_asked": len(asks),
        # the probe measured a discriminating gap AND that gap's question is the one
        # actually on the card. Since question_back_for() puts her own routing above
        # the probe for `what_is_it` and `diagnose_me`, "a gap was measured" and "the
        # probe chose the words" are no longer the same count, and claiming the
        # bigger one would be claiming credit the probe did not earn.
        "question_chosen_by_probe": sum(
            1 for c in asks
            if (c["gap_probe"] or {}).get("discriminating_gap")
            and c.get("question_back") == GAP_QUESTION.get(
                (c["gap_probe"] or {}).get("discriminating_gap"))),
        "note": ("A gap is only called moot when every plausible value of it was run "
                 "through the same two-stage basket and the winning basket never "
                 "changed. Untested, uncapped or failed hypotheses always count as "
                 "mattering, and the probe can only move asked_back -> answered - it "
                 "can never reach `referred` or `held`."),
    }


def assemble_queue(raw: dict, pol: dict) -> dict:
    """Pure function over cached judgments. NO inference. This is what makes the
    override switch instant."""
    cards = []
    for r in raw["dms"]:
        a = r["answers"]
        lane, c = lane_for(a, pol)
        basket = r.get("basket") or []
        scored = r.get("scored") or []
        gp = r.get("gap_probe") or None
        answered_despite_gap = False
        gap_closed = None
        qoverride = None
        if lane == "asked_back" and gp:
            if gp.get("indifferent"):
                # every plausible value of every gap produced the SAME basket, so the
                # question would not have changed the reply. Answer it.
                lane = "answered"
                answered_despite_gap = True
                gap_closed = gp.get("gap_closed")
                src = gp.get("answer") or gp.get("baseline") or {}
                basket = list(src.get("basket") or [])
                scored = list(src.get("scored") or [])
            else:
                qoverride = gp.get("question")
        if scored:
            ok = [s for s in scored if len(s["items"]) <= pol["max_items_cap"]]
            if ok:
                basket = max(ok, key=lambda s: (s["score"], -s["total"]))["items"]
        # Only an answered card carries a basket. A basket was computed at build
        # time from that message's lane THEN; if a tightened test or an override has
        # since moved it to asked_back or held, the shopping list is not the reply
        # and must not reach the screen or mint a share card.
        if lane != "answered":
            basket, scored = [], []
        parts = draft_for(r, a, lane, basket, pol, qoverride)
        total = sum(BY[x]["gbp"] for x in basket if x in BY)
        cards.append({
            "id": r["id"], "ref": r["ref"], "from": r["from"], "text": r["text"],
            "lane": lane, "confidence": c, "job": choice(a, "job", "pick_for_me"),
            "draft_reply": parts["draft_reply"], "question_back": parts["question_back"],
            "hold_reason": parts["hold_reason"], "refusal": parts["refusal"],
            "card_id": queue_card_id(r) if basket else None,
            "basket_summary": ((" · ".join([x + " " + gbp(BY[x]["gbp"]) for x in basket])
                                + (" · " + gbp(total) if len(basket) > 1 else ""))
                               if basket else None),
            "basket": basket or None,
            "skin": Q.read_skin(a),
            "synthetic": r.get("synthetic", False),
            # ---- how the message arrived. "text" for a typed DM, "voice" for a
            # transcribed voice note. It is a label on the card, never an input to a
            # gate: every lane above was decided from `text` alone, and for a voice
            # note `text` IS the transcript. `voice` is null unless source == "voice".
            "source": r.get("source", "text"),
            "voice": r.get("voice"),
            # `urgency` used to be written here. It was a Jev question on all fifty
            # DMs and nothing - no gate, no draft, no contract assertion, no pixel -
            # ever read it. See questions.REMOVED_UNUSED.
            # ---- the gap probe. null when this message was never probed.
            "answered_despite_gap": answered_despite_gap,
            "gap_closed": gap_closed,
            "gap_probe": ({
                "gaps": gp.get("gaps") or [],
                "tested": {k: {"tested": d.get("tested"), "distinct": d.get("distinct"),
                               "mattered": d.get("mattered"),
                               "values": d.get("values") or []}
                           for k, d in (gp.get("gap_detail") or {}).items()},
                "variants": gp.get("variants") or [],
                "variants_run": gp.get("variants_run"),
                "indifferent": bool(gp.get("indifferent")),
                "gaps_that_did_not_matter": gp.get("gaps_that_did_not_matter") or [],
                "discriminating_gap": gp.get("discriminating_gap"),
                "incomplete": bool(gp.get("incomplete")),
                "rule": gp.get("rule"),
            } if gp else None),
        })
    order = {"answered": 0, "asked_back": 1, "held": 2, "referred": 3}
    pw = pol.get("price_weight", 0.0)

    def rank(c):
        cheap = 0.0
        if c.get("basket"):
            cheap = sum(BY[x]["gbp"] for x in c["basket"] if x in BY) / 100.0
        return (order[c["lane"]], -(c["confidence"] - pw * cheap))
    cards.sort(key=rank)

    n = len(cards)
    counts = {k: sum(1 for c in cards if c["lane"] == k)
              for k in ("answered", "asked_back", "held", "referred")}
    handled = counts["answered"] + counts["asked_back"]
    secs = round(float(raw.get("triage_seconds", 0)) + float(raw.get("basket_seconds", 0)), 2)
    mo = CASE["creator"]["load"]["dms_per_month"]
    stats = {
        "dms": n, "judgments": raw.get("judgments", 0), "seconds": secs,
        "triage_seconds": raw.get("triage_seconds", 0),
        "basket_seconds": raw.get("basket_seconds", 0),
        "answered": counts["answered"], "asked_back": counts["asked_back"],
        "held": counts["held"], "referred": counts["referred"],
        "handled_pct": int(round(100 * handled / n)) if n else 0,
        "held_pct": int(round(100 * counts["held"] / n)) if n else 0,
        "referred_pct": int(round(100 * counts["referred"] / n)) if n else 0,
        "at_real_volume": {
            "dms_per_month": mo,
            "handled": int(mo * handled / n) if n else 0,
            "held_per_day": int(mo * counts["held"] / n / 30) if n else 0,
            "referred": int(mo * counts["referred"] / n) if n else 0,
        },
        "header_line": "you approved " + str(counts["answered"]) + " replies in 4 minutes",
        "answer_rate_pct": int(round(100 * counts["answered"] / n)) if n else 0,
        "gap_probe": gap_stats(cards, raw),
        "gates": {"confidence_gate": pol["confidence_gate"],
                  "emotional_gate": pol["emotional_gate"],
                  "enough_gate": pol["enough_gate"],
                  "max_items_cap": pol["max_items_cap"],
                  "defended": pol["defended"],
                  "refusal_reason_gate": pol.get("refusal_reason_gate",
                                                 REFUSAL_REASON_GATE)},
        "safety": {
            "referred": counts["referred"],
            "by_signal": {k: sum(1 for c in cards if c["lane"] == "referred"
                                 and (c.get("refusal") or {}).get("signal") == k)
                          for k in ("out_of_scope", "refusal_reason", "both")},
            "rule": ("Out of scope if `out_of_scope` > 0.5 OR `refusal_reason` names a "
                     "clinical reason at " + str(pol.get("refusal_reason_gate",
                                                         REFUSAL_REASON_GATE))
                     + " or better. An OR: it can only add a referral, never remove one."),
        },
    }
    return {"stats": stats, "cards": cards, "built_at": raw.get("built_at")}


# ================================================================================
# /api/extract - the replay payload behind the hero visual.
#
# HONESTY CONTRACT, and it is the whole point of this block:
#   Jev returns every answer for a request in ONE response. There is NO genuine
#   per-slot arrival time and this module never invents one. Timings exist at
#   REQUEST granularity only (`ms` per request, `at_ms` when it was fired) and
#   every slot of a request carries that request's id so the frontend can label
#   its own reveal as a replay. Per slot you get confidence, never milliseconds.
# ================================================================================

# The corpus, with the evidence ref of the post each line came from, lifted from
# scripts/engine_decontaminated_v2.py so the wire and the measured run agree.
EXTRACT_CAPTIONS = [
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

EXTRACT_BIO = "skincare, mostly honest. london."

# docs/11-honest-headline.md section 5.1, on the wire so nobody has to read the doc to
# find out which strings are hers and which are ours.
CORPUS_NOTE = ("The six post titles are verbatim from the case pack (E-03.1-E-03.6). The caption "
               "bodies and the bio line are a reconstruction written in the voice of those titles - "
               "her account is login-walled, so say 'reconstructed from her posts', not 'scraped'. "
               "Disclosed in docs/11-honest-headline.md section 5.1.")

EXTRACT_SCRAPED = {
    "handle": "@mayarao",
    "bio": EXTRACT_BIO,
    "posts": [{"caption": b["title"], "views": b["views"], "saves": b["saves"]}
              for b in CASE["broadcast_log"]],
    "captions": [c["text"] for c in EXTRACT_CAPTIONS],
    "her_public_notes_on_products_she_has_used": [
        {"product": p["product"], "rating_out_of_10": p["maya_rating"], "what_she_said": p["maya_note"]}
        for p in SHELF],
}

# The control. Written by us, all twelve statements - docs/11 section 5.2.
DERM_SOURCE_V14 = {
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

DERM_CORPUS_NOTE = ("The dermatologist's corpus is 100% written by us. It is the control, "
                    "not evidence. docs/11-honest-headline.md section 5.2.")

# Identical in both states, and objective: no creator_rating, no creator_note. docs/11 section 4.
EXTRACT_SHELF_STATE = [{"product": p["product"], "gbp": p["gbp"], "type": p["type"],
                        "skin": p["skin"], "finish": p["finish"]} for p in SHELF]

SLOTS_V14 = Q.standard_slots_v14(SHELF)
API_SLOTS_V14 = Q.api_slots(SLOTS_V14)
JUDGES = ("maya", "derm")

# ---------------------------------------------------------------- subjects
# A subject is anything we can put in front of the SAME fourteen questions. Two of
# them are ours (`maya`, `derm`); the rest are real people whose public writing was
# fetched once, by hand, into data/corpus-<slug>.json. See backend/corpora.py.
MAYA_SLUG = "maya"
DERM_SLUG = "derm"

MAYA_PROVENANCE = (
    "Ours, partly. The six post titles are verbatim from the case pack (E-03.1-E-03.6); "
    "the caption bodies and the bio line are a reconstruction written by us in the voice "
    "of those titles. Say 'reconstructed from her posts', never 'scraped'. "
    "docs/11-honest-headline.md section 5.1.")
DERM_PROVENANCE = (
    "Ours, entirely. Twelve statements of clinical guidance, every word written by us. "
    "It is the control, not evidence. docs/11-honest-headline.md section 5.2.")

MAYA_META = {
    "slug": MAYA_SLUG,
    "handle": "@mayarao",
    "display_name": CASE["creator"]["name"],
    "what_she_is": "Beauty creator, London. The case-pack creator this engine was built for.",
    "source": "case-pack",
    "source_url": None,
    "fetched_at": None,
    "why_this_creator": ("The case pack. She is the subject the whole demo is about, and she is "
                         "the reason the other subjects exist: if the engine only works on her, "
                         "it is hardcoded."),
    "cleaning_note": None,
    "verbatim": False,
    "real": False,
    "provenance": MAYA_PROVENANCE,
    "corpus_file": "data/case-001-maya.json",
}


class QuestionDrift(RuntimeError):
    """The fourteen questions stopped being identical across subjects.

    This is not a recoverable condition and it is not caught anywhere. The entire
    methodological claim is 'same questions, different answers'. If the questions
    differ, every comparison downstream is meaningless and it is better for the
    demo to fall over loudly here than to show a comparison that is a lie.
    """


def subject_exists(slug: str) -> bool:
    slug = str(slug or "").strip().lower()
    return slug in (MAYA_SLUG, DERM_SLUG) or corpora.load(slug) is not None


def subject_meta(slug: str) -> dict | None:
    """The identity card for one subject, or None if we have never heard of it."""
    slug = str(slug or "").strip().lower() or MAYA_SLUG
    if slug == MAYA_SLUG:
        m = dict(MAYA_META)
        c = extract_corpus()
        m["item_count"] = len(c)
        m["char_count"] = sum(len(i["text"]) for i in c)
        return m
    if slug == DERM_SLUG:
        return {"slug": DERM_SLUG, "handle": None,
                "display_name": "A board-certified dermatologist",
                "what_she_is": DERM_SOURCE_V14["who"],
                "source": "written-by-us", "source_url": None, "fetched_at": None,
                "item_count": len(DERM_SOURCE_V14["guidance"]),
                "char_count": sum(len(t) for t in DERM_SOURCE_V14["guidance"]),
                "why_this_creator": "The control. Every subject is asked the same fourteen "
                                    "questions against this same yardstick.",
                "cleaning_note": None, "verbatim": False, "real": False,
                "provenance": DERM_PROVENANCE, "corpus_file": "backend/engine.py"}
    c = corpora.load(slug)
    return corpora.meta(c) if c else None


def subject_profile(slug: str) -> dict | None:
    """`state.public_profile` for one subject."""
    slug = str(slug or "").strip().lower() or MAYA_SLUG
    if slug == MAYA_SLUG:
        return EXTRACT_SCRAPED
    if slug == DERM_SLUG:
        return DERM_SOURCE_V14
    c = corpora.load(slug)
    return corpora.profile_state(c) if c else None


def subject_corpus(slug: str) -> list:
    """Every string that goes into that subject's prompt, with its provenance."""
    slug = str(slug or "").strip().lower() or MAYA_SLUG
    if slug == MAYA_SLUG:
        return extract_corpus()
    if slug == DERM_SLUG:
        return derm_corpus()
    c = corpora.load(slug)
    return corpora.wire_items(c) if c else []


def subject_corpus_note(slug: str) -> str | None:
    slug = str(slug or "").strip().lower() or MAYA_SLUG
    if slug == MAYA_SLUG:
        return CORPUS_NOTE
    if slug == DERM_SLUG:
        return DERM_CORPUS_NOTE
    c = corpora.load(slug)
    return (c or {}).get("cleaning_note")


def list_subjects() -> list:
    """Maya first (she is the case), then every fetched corpus. The control is not
    in this list - it is not a subject you choose, it is the yardstick."""
    return [subject_meta(MAYA_SLUG)] + corpora.all_meta()


def extract_corpus() -> list:
    """Every string that goes into Maya's prompt, in the order the state carries it.
    bio, then the six post titles, then the eight captions."""
    out = [{"id": "bio", "text": EXTRACT_BIO, "evidence_ref": None, "kind": "bio",
            "verbatim": False}]
    for b in CASE["broadcast_log"]:
        out.append({"id": "post-" + b["ref"], "text": b["title"], "evidence_ref": b["ref"],
                    "kind": "post", "verbatim": True,
                    "views": b["views"], "saves": b["saves"]})
    for c in EXTRACT_CAPTIONS:
        out.append({"id": c["id"], "text": c["text"], "evidence_ref": c["ref"],
                    "kind": "caption", "verbatim": False})
    return out


def derm_corpus() -> list:
    """The control corpus. Ours, every word of it, and it says so."""
    return [{"id": "d%d" % (i + 1), "text": t, "evidence_ref": None, "kind": "guidance",
             "verbatim": False, "written_by_us": True}
            for i, t in enumerate(DERM_SOURCE_V14["guidance"])]


def question_id(judge: str, slot_key: str) -> str:
    return "q-" + judge + "-" + slot_key


def extract_questions(subject: str = MAYA_SLUG) -> list:
    """The twenty-eight. `text` is the literal `instructions` string sent to Jev.

    Fourteen for the subject, fourteen for the control, and the `text` of question
    i is THE SAME STRING on both sides for every subject we ever ask. Only the `id`
    differs, because an id has to say which request it travelled in.
    """
    out = []
    for judge in (subject, DERM_SLUG):
        for k, spec in SLOTS_V14.items():
            row = {"id": question_id(judge, k), "slot_key": k, "judge": judge,
                   "type": spec["type"], "text": spec["instructions"]}
            if spec.get("situation"):
                row["situation"] = spec["situation"]
            out.append(row)
    return out


def extract_plan(subject: str = MAYA_SLUG) -> list:
    """One entry per real HTTP request. Two, because the fourteen questions of a judge
    travel together - that is what makes it 0.65s instead of fourteen round trips.

    The subject changes. `questions` and `shelf` do not: the same fourteen typed
    questions, the same shelf, against a different `public_profile`. Asserted below,
    not merely intended.
    """
    subject = str(subject or MAYA_SLUG).strip().lower()
    profile = subject_profile(subject)
    if profile is None:
        raise KeyError("unknown subject %r" % subject)
    plan = [
        {"id": "r-" + subject, "judge": subject,
         "state": {"public_profile": profile, "shelf": EXTRACT_SHELF_STATE},
         "questions": API_SLOTS_V14,
         "question_ids": [question_id(subject, k) for k in SLOTS_V14],
         "slot_keys": list(SLOTS_V14),
         "question_count": len(SLOTS_V14)},
        {"id": "r-" + DERM_SLUG, "judge": DERM_SLUG,
         "state": {"public_profile": DERM_SOURCE_V14, "shelf": EXTRACT_SHELF_STATE},
         "questions": API_SLOTS_V14,
         "question_ids": [question_id(DERM_SLUG, k) for k in SLOTS_V14],
         "slot_keys": list(SLOTS_V14),
         "question_count": len(SLOTS_V14)},
    ]
    assert_question_symmetry(plan, subject)
    return plan


# The canonical fourteen, serialised once. Everything is compared against this.
_QUESTIONS_FINGERPRINT = json.dumps(API_SLOTS_V14, sort_keys=True, ensure_ascii=False)


def assert_question_symmetry(plan: list, subject: str = "") -> None:
    """Fail LOUDLY if the fourteen questions are not byte-identical everywhere.

    "Different values, same questions" is the entire claim. A drift here would
    silently turn every side-by-side in this product into a comparison of two
    different tests, so this raises rather than warns, and nothing catches it.
    """
    for req in plan:
        got = json.dumps(req.get("questions"), sort_keys=True, ensure_ascii=False)
        if got != _QUESTIONS_FINGERPRINT:
            raise QuestionDrift(
                "the fourteen questions differ for request %r (subject %r). The whole "
                "comparison rests on them being identical." % (req.get("id"), subject))
        if list(req.get("slot_keys") or []) != list(SLOTS_V14):
            raise QuestionDrift(
                "request %r does not carry the fourteen slots in the canonical order "
                "(subject %r)." % (req.get("id"), subject))
    # and the rendered question TEXT, which is what a judge actually reads on screen
    by_slot: dict = {}
    for row in extract_questions(subject or MAYA_SLUG):
        prev = by_slot.setdefault(row["slot_key"], row["text"])
        if prev != row["text"]:
            raise QuestionDrift("slot %r is asked with different words of different "
                                "judges." % row["slot_key"])


def pack_v14(answers: dict) -> dict:
    """Jev's answers -> the {level, value, confidence} shape /api/standard already uses."""
    out = {}
    for k, spec in SLOTS_V14.items():
        if k not in answers:
            continue
        x = answers[k]
        if x.get("type") == "score" or spec["type"] == "score":
            out[k] = {"level": level(answers, k), "value": round(score(answers, k), 2),
                      "confidence": round(conf(answers, k), 2), "confidence_known": True}
        elif x.get("type") == "noul" or spec["type"] == "noul":
            p = noul(answers, k)
            out[k] = {"level": "YES" if p > 0.5 else "NO", "value": round(p, 2),
                      "confidence": round(max(p, 1 - p), 2), "confidence_known": True}
        else:
            out[k] = {"level": choice(answers, k), "value": round(conf(answers, k), 2),
                      "confidence": round(conf(answers, k), 2), "confidence_known": True}
    return out


async def run_extract_request(req: dict, t0: float) -> dict:
    """Fire ONE request and measure it. `ms` is wall time around the wire call; it is
    the only latency number in this whole payload that was actually observed."""
    fired = round((time.perf_counter() - t0) * 1000)
    t = time.perf_counter()
    data = await JEV.ask(req["state"], req["questions"])
    ms = int((time.perf_counter() - t) * 1000)
    ans = data.get("answers", {}) or {}
    return {"id": req["id"], "judge": req["judge"],
            "question_count": req["question_count"],
            "question_ids": list(req["question_ids"]),
            "at_ms": fired, "ms": ms,
            "input_tokens": int((data.get("usage") or {}).get("input_tokens") or 0),
            "slot_keys": [k for k in req["slot_keys"] if k in ans],
            "answers": ans, "packed": pack_v14(ans)}


def levels_agree(a: dict | None, b: dict | None) -> bool:
    """The ONE definition of 'these two judges gave the same answer'. Used by the
    extraction and by the side-by-side, so the two can never drift apart."""
    if not a or not b:
        return False
    return str(a.get("level")).strip().lower() == str(b.get("level")).strip().lower()


def _extract_slots(by_judge: dict, file_slots: dict, subject: str = MAYA_SLUG) -> list:
    """The resolved slots. Values from wherever they came (live run or the frozen
    extraction), captions and refs from LANE C's file, question_ids from the plan.

    For Maya the subject side is keyed `maya`, because that is the contract lane B
    already builds against. For any other subject it is keyed `subject`, and it
    carries NO source_caption: the per-slot caption for Maya comes from a mapping
    WE wrote by hand (`SLOT_META`), not from the model, and there is no such mapping
    for a fetched corpus. A caption picked by keyword would look like evidence and
    would not be, so the field is null and says nothing.
    """
    is_maya = subject == MAYA_SLUG
    side_key = "maya" if is_maya else "subject"
    left = by_judge.get(subject) or {}
    derm = by_judge.get(DERM_SLUG) or {}
    slots = []
    for k in SLOTS_V14:
        fm = (file_slots.get(k, {}) or {}) if is_maya else {}
        m = left.get(k) or fm.get("maya")
        d = derm.get(k) or fm.get("derm")
        if m is None and d is None:
            continue
        cap, ref = _caption_for(k) if is_maya else (None, None)
        if left.get(k) and derm.get(k):
            agrees = levels_agree(m, d)
        elif fm.get("agrees") is not None:
            agrees = bool(fm["agrees"])
        else:
            agrees = levels_agree(m, d)
        row = {"key": k, "label": _label_for(k), side_key: m, "derm": d, "agrees": bool(agrees),
               "source_caption": fm.get("source_caption") or cap,
               "evidence_ref": fm.get("evidence_ref") or ref,
               "toggleable": bool(fm.get("toggleable") if fm.get("toggleable") is not None
                                  else k != "defended_category"),
               "question_ids": [question_id(subject, k), question_id(DERM_SLUG, k)],
               "request_ids": ["r-" + subject, "r-" + DERM_SLUG],
               "type": SLOTS_V14[k]["type"]}
        if fm.get("label"):
            row["statement"] = fm["label"]
        slots.append(row)
    return slots


def slot_side(row: dict, subject: str) -> dict | None:
    """The subject's own side of a slot row, whichever key it was written under."""
    if subject == DERM_SLUG:
        return row.get("derm")
    return row.get("maya") if subject == MAYA_SLUG else row.get("subject")


REPLAY_NOTE = ("Jev answers all fourteen questions of a judge in ONE response, so there is no "
               "per-slot arrival time and this payload does not contain one. The timings here are "
               "per REQUEST and were measured on the wire. Any per-slot reveal in the UI is a "
               "replay and must say so.")


def _request_rows(results: list, subject: str) -> tuple:
    """-> (requests, total_input_tokens). A number we did not measure is null."""
    if results:
        rows = [{"id": r["id"], "judge": r["judge"], "question_count": r["question_count"],
                 "question_ids": r["question_ids"], "slot_keys": r["slot_keys"],
                 "at_ms": r["at_ms"], "ms": r["ms"], "input_tokens": r["input_tokens"],
                 "measured": True}
                for r in results]
        return rows, sum(r["input_tokens"] for r in rows)
    # No run behind this payload. The shape of the fan-out is still true - two
    # requests, fourteen questions each - but we did not time THIS one, so the
    # numbers we did not measure are null rather than invented.
    rows = [{"id": r["id"], "judge": r["judge"], "question_count": r["question_count"],
             "question_ids": r["question_ids"], "slot_keys": r["slot_keys"],
             "at_ms": None, "ms": None, "input_tokens": None, "measured": False}
            for r in extract_plan(subject)]
    return rows, None


NO_CAPTION_NOTE = (
    "This subject's slots carry no per-slot caption. Maya's do, because the case pack "
    "pins each slot to a post and we wrote that mapping by hand. Jev reads the whole "
    "corpus at once and does not report which sentence moved which slot, so quoting one "
    "here would be our guess dressed up as evidence. The whole corpus is in `corpus`.")


def _build_extract_subject(results: list, seconds: float, live: bool, subject: str) -> dict:
    """The same payload shape for a fetched, real corpus. Same fourteen questions,
    same control, same totals - a different person, and it says whose words they are."""
    meta = subject_meta(subject) or {}
    by_judge = {r["judge"]: r.get("packed") or {} for r in results}
    slots = _extract_slots(by_judge, {}, subject)
    agree = sum(1 for s in slots if s["agrees"])
    requests, tokens = _request_rows(results, subject)
    questions = extract_questions(subject)
    return {
        "subject": subject,
        "handle": meta.get("handle"),
        "display_name": meta.get("display_name"),
        "what_she_is": meta.get("what_she_is"),
        "why_this_creator": meta.get("why_this_creator"),
        "real": bool(meta.get("real")),
        "provenance": meta.get("provenance"),
        "source": meta.get("source"),
        "source_url": meta.get("source_url"),
        "fetched_at": meta.get("fetched_at"),
        "corpus": subject_corpus(subject),
        "corpus_note": subject_corpus_note(subject),
        "caption_note": NO_CAPTION_NOTE,
        "derm_corpus": derm_corpus(),
        "derm_corpus_note": DERM_CORPUS_NOTE,
        "derm_provenance": DERM_PROVENANCE,
        "questions": questions,
        "requests": requests,
        "slots": slots,
        "totals": {
            "questions": len(questions),
            "requests": len(requests),
            "seconds": round(float(seconds or 0.0), 2),
            "input_tokens": tokens,
            "agree": agree,
            "disagree": len(slots) - agree,
            "slot_count": len(slots),
        },
        "model": JEV_MODEL,
        "replay_note": REPLAY_NOTE,
        "measured": bool(live),
        "generated_by": "backend/engine.py extract_live(subject=%r)" % subject,
    }


def build_extract(results: list, seconds: float, live: bool,
                  file_slots: dict | None = None, subject: str = MAYA_SLUG) -> dict:
    """Assemble the replay payload from whatever request results we have (two on a
    live run, none when we are replaying the frozen extraction).

    `subject` defaults to Maya and that path is byte-for-byte what it always was.
    """
    subject = str(subject or MAYA_SLUG).strip().lower()
    if subject != MAYA_SLUG:
        return _build_extract_subject(results, seconds, live, subject)
    file_slots = dict(file_slots or {})
    meta = file_slots.pop("__meta__", {}) or {}
    by_judge = {r["judge"]: r.get("packed") or {} for r in results}
    slots = _extract_slots(by_judge, file_slots)
    agree = sum(1 for s in slots if s["agrees"])
    requests, tokens = _request_rows(results, MAYA_SLUG)
    questions = extract_questions()
    secs = seconds if live else float(meta.get("extraction_seconds") or seconds or 0.0)
    return {
        "handle": "@mayarao",
        "corpus": extract_corpus(),
        "corpus_note": CORPUS_NOTE,
        "derm_corpus": derm_corpus(),
        "derm_corpus_note": ("The dermatologist's corpus is 100% written by us. It is the control, "
                             "not evidence. docs/11-honest-headline.md section 5.2."),
        "questions": questions,
        "requests": requests,
        "slots": slots,
        "totals": {
            "questions": len(questions),
            "requests": len(requests),
            "seconds": round(secs, 2),
            "input_tokens": tokens,
            "agree": agree,
            "disagree": len(slots) - agree,
            "slot_count": len(slots),
        },
        # what was actually sent on a live run; what the frozen file recorded otherwise
        "model": JEV_MODEL if live else (meta.get("model") or JEV_MODEL),
        "replay_note": REPLAY_NOTE,
        "measured": bool(live),
        "generated_by": meta.get("generated_by"),
    }


def build_extract_frozen(subject: str = MAYA_SLUG) -> dict:
    """No network. The frozen extraction, replayable, with everything the hero needs
    except live timings - those come from the measured run in the file."""
    subject = str(subject or MAYA_SLUG).strip().lower()
    if subject == MAYA_SLUG:
        return build_extract([], 0.0, False, load_standard_file())
    # No frozen file for a fetched corpus: the scaffold is true (the corpus, the
    # fourteen questions, the two requests) and every value and timing is null.
    return build_extract([], 0.0, False, None, subject)


async def extract_live(subject: str = MAYA_SLUG) -> dict:
    """Both judges, the same fourteen questions, fired together. Two requests."""
    subject = str(subject or MAYA_SLUG).strip().lower()
    plan = extract_plan(subject)
    # Build the HTTP client before the clock starts. httpx loads the CA bundle in its
    # constructor (~0.5s, once per process) and that is not fan-out latency; leaving it
    # inside the measurement would make the second request look half a second late and
    # misrepresent the parallelism. Nothing is sent here.
    JEV.prepare()
    t0 = time.perf_counter()
    results = await asyncio.gather(*(run_extract_request(r, t0) for r in plan))
    secs = round(time.perf_counter() - t0, 2)
    if subject == MAYA_SLUG:
        return build_extract(list(results), secs, True, load_standard_file())
    return build_extract(list(results), secs, True, None, subject)


def extract_cache_name(subject: str) -> str:
    """cache/extract.json for Maya - the name lane B already reads - and
    cache/extract-<slug>.json for everybody else."""
    subject = str(subject or MAYA_SLUG).strip().lower()
    return "extract" if subject == MAYA_SLUG else "extract-" + subject


# ---------------------------------------------------------------- the side-by-side
def payload_subject(payload: dict) -> str:
    return str(payload.get("subject") or MAYA_SLUG)


def align_subjects(pa: dict, pb: dict) -> dict:
    """Two extraction payloads -> the fourteen slots, aligned, one row each.

    Uses `levels_agree`, the same equality the extraction itself uses, so the
    side-by-side can never disagree with the payloads it was built from.
    """
    a_slug, b_slug = payload_subject(pa), payload_subject(pb)
    rows_a = {s["key"]: s for s in (pa.get("slots") or [])}
    rows_b = {s["key"]: s for s in (pb.get("slots") or [])}
    slots = []
    for k in SLOTS_V14:
        ra, rb = rows_a.get(k) or {}, rows_b.get(k) or {}
        if not ra and not rb:
            continue
        sa = slot_side(ra, a_slug)
        sb = slot_side(rb, b_slug)
        slots.append({
            "key": k,
            "label": _label_for(k),
            "type": SLOTS_V14[k]["type"],
            "a": sa, "b": sb,
            "agrees": levels_agree(sa, sb),
            "a_agrees_with_derm": bool(ra.get("agrees")) if ra else None,
            "b_agrees_with_derm": bool(rb.get("agrees")) if rb else None,
            "a_source_caption": ra.get("source_caption"),
            "b_source_caption": rb.get("source_caption"),
            "question_text": SLOTS_V14[k]["instructions"],
            "question_ids": [question_id(a_slug, k), question_id(b_slug, k)],
        })
    agree = sum(1 for s in slots if s["agrees"])

    def _tot(p, slug):
        t = dict(p.get("totals") or {})
        return {"subject": slug, "seconds": t.get("seconds"),
                "input_tokens": t.get("input_tokens"), "questions": t.get("questions"),
                "requests": t.get("requests"), "slot_count": t.get("slot_count"),
                "measured": bool(p.get("measured")), "live": bool(p.get("live")),
                "cached": bool(p.get("cached"))}

    def _meta(p, slug):
        m = dict(subject_meta(slug) or {})
        m["measured"] = bool(p.get("measured"))
        m["live"] = bool(p.get("live"))
        m["seconds"] = (p.get("totals") or {}).get("seconds")
        m["input_tokens"] = (p.get("totals") or {}).get("input_tokens")
        return m

    toks = [t for t in ((pa.get("totals") or {}).get("input_tokens"),
                        (pb.get("totals") or {}).get("input_tokens")) if t]
    secs = [s for s in ((pa.get("totals") or {}).get("seconds"),
                        (pb.get("totals") or {}).get("seconds")) if s]
    n = len(slots)
    return {
        "subjects": [_meta(pa, a_slug), _meta(pb, b_slug)],
        "a": a_slug, "b": b_slug,
        "slots": slots,
        "agree_count": agree,
        "disagree_count": n - agree,
        "headline": ("Same " + _words(n) + " questions, asked of "
                     + str((subject_meta(a_slug) or {}).get("display_name") or a_slug) + " and "
                     + str((subject_meta(b_slug) or {}).get("display_name") or b_slug)
                     + ". They agree on " + _words(agree) + " and disagree on "
                     + _words(n - agree) + "."),
        "questions_identical": True,        # asserted in extract_plan(), not assumed
        "totals": {
            "slot_count": n,
            "agree": agree,
            "disagree": n - agree,
            "questions": sum((p.get("totals") or {}).get("questions") or 0 for p in (pa, pb)),
            "requests": sum((p.get("totals") or {}).get("requests") or 0 for p in (pa, pb)),
            "input_tokens": sum(toks) if toks else None,
            "seconds": round(max(secs), 2) if secs else None,
            "a": _tot(pa, a_slug),
            "b": _tot(pb, b_slug),
        },
        "note": ("The fourteen questions are byte-identical for both subjects - the same "
                 "`instructions` and the same `criteria` were sent on both wires. Only the "
                 "`public_profile` differs. `seconds` is the slower of the two runs, not "
                 "their sum: they were two separate fan-outs."),
    }
