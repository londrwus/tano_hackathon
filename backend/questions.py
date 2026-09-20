"""Every Jev question lives here and nowhere else.

Two rules from the measured runs, both load-bearing:

  * BUG 1 - skin type is MULTI-LABEL. One `noul` per condition, never one `choice`.
    A single choice loses "dry + redness" and never fires REDNESS -> Red Reset.
  * BUG 4 - criteria describe concrete SITUATIONS, never bare labels. Rewriting
    `later` from "already decided" to "waiting for money or time - payday, next
    month, when it restocks" moved its confidence from 0.65 to 0.96.
"""
from __future__ import annotations

SKIN_CONDITIONS = ["dry", "oily", "combination", "sensitive", "redness"]

# ---------------------------------------------------------------- skin (bug 1)
_SKIN_SITUATION = {
    "dry": ("Their skin is tight, flaky or thirsty - it drinks product and still feels papery, "
            "worse in winter or after cleansing"),
    "oily": ("They shine through by lunchtime, their T-zone is slick, makeup slides off and they "
             "blot or powder during the day"),
    "combination": ("Oily down the middle of the face and dry or normal on the cheeks - one "
                    "product never suits both halves"),
    "sensitive": ("Their face reacts to new things - stinging, itching, tightness or breakouts "
                  "whenever they introduce a product"),
    "redness": ("Visible redness, flushing, rosacea or angry-looking patches they want calmed "
                "down rather than covered up"),
}


def skin_multilabel(subject: str = "message") -> dict:
    """One noul per condition. NEVER one choice - that is bug #1."""
    return {
        "skin__" + c: {
            "type": "noul",
            "instructions": "Does `" + subject + "` state or clearly imply that this person has "
                            + c + " skin?",
            "criteria": {"true": _SKIN_SITUATION[c],
                         "false": "Nothing in `" + subject + "` points at " + c + " skin"},
        }
        for c in SKIN_CONDITIONS
    }


def read_skin(answers: dict, gate: float = 0.55) -> list:
    """Pull the multi-label skin array back out of a triage answer set."""
    out = []
    for c in SKIN_CONDITIONS:
        try:
            if float(answers["skin__" + c]["noul"]) >= gate:
                out.append(c)
        except Exception:
            continue
    return out


# ---------------------------------------------------------------- the fan-out
BUDGET_BANDS = {"under_30": 30, "30_to_60": 60, "60_to_100": 100, "over_100": 150, "not_stated": 80}
ITEM_BANDS = {"one": 1, "two": 2, "three_or_four": 4, "not_stated": 3}

_JOBS = {
    "pick_for_me": "They want her to choose specific products for them, possibly under a budget or a product count",
    "is_it_worth_it": "They name one product and want to know whether it justifies its price",
    "do_i_need_it": "They already own something and want to know whether they need another thing on top",
    "what_is_it": "They want her to identify a specific item she wore or used in a post",
    "diagnose_me": "They do not know their own skin type or what is going wrong with their face",
    "occasion": "They have a date, a wedding, an interview or a holiday coming and need to look good for it",
    "buying_for_someone_else": "They are choosing on behalf of another person - a mum, a partner, a friend",
    "not_a_question": "Trust, praise or affection with nothing to decide and no purchase pending",
    "later": ("They have ALREADY decided to buy and are only waiting for money or time - payday, "
              "next month, when it restocks, when it goes on sale"),
}

_REFER_TO = {
    "a dermatologist": "A skin condition, a reaction or a prescription question that needs a doctor who can see the skin",
    "their prescribing doctor": "They are already on a prescription - tretinoin, accutane, a medicated cream - and are asking what to add",
    "a pharmacist or their GP": "Pregnancy, breastfeeding or a medication-safety question",
    "a parent and their GP": "The person being asked about is a child",
    "nobody - this is safely hers to answer": "An ordinary beauty question a creator can answer",
}

_REFUSAL_REASON = {
    "prescription_interaction": "They are on a prescribed treatment and are asking what to layer on top of it",
    "pregnancy_or_nursing": "They are pregnant or nursing and asking what is safe",
    "active_skin_condition": "They describe a diagnosed or diagnosable condition - dermatitis, eczema, a rosacea flare",
    "adverse_reaction": "Their skin is reacting badly right now - red, peeling, burning - and needs looking at",
    "a_child": "The person the advice is for is a child",
    "none": "Nothing medical here at all",
}


#: Asked on every one of the fifty DMs until we went looking for who read the answer.
#: Nobody did. Grepped across backend/, scripts/ and frontend/src: neither id appeared
#: outside this file, so neither ever reached a lane, a gate, a draft or a screen.
#:
#:   wants_verdict_not_facts  - zero references anywhere. `job` already separates
#:                              "what shade is that" (what_is_it) from "you pick"
#:                              (pick_for_me), and `job` is the one that routes.
#:   urgency                  - written onto /api/queue.cards[].urgency and read by
#:                              nothing. Not in docs/10-API-CONTRACT.md, not asserted
#:                              by scripts/check_contract.py, not rendered anywhere in
#:                              frontend/src. The `later` job and the fourth rung of
#:                              `emotional_weight` already carry what it was for.
#:
#: 2 of 20 questions x 50 DMs = 100 judgments we were buying and throwing away, and
#: 141 input tokens per message because the criteria travel in every request.
#: Listed, not deleted from history, so the removal is auditable.
REMOVED_UNUSED = ("wants_verdict_not_facts", "urgency")


def triage(products: list, intake_questions: list) -> dict:
    """ONE speculative fan-out per DM. Every question asked at once; CODE routes
    on the answers. This is the signature pattern and it is why it is fast.

    Eighteen questions, not twenty: see REMOVED_UNUSED above. Every id below is
    read by name somewhere in backend/engine.py - lane_for, has_enough, refers_out,
    draft_for, shopper_from_triage or detect_gaps.
    """
    q = {
        "job": {"type": "choice",
                "instructions": "What is `message` actually asking Maya to do?",
                "criteria": dict(_JOBS)},
        "out_of_scope": {
            "type": "noul",
            "instructions": ("Is `message` asking for something outside `creator.her_scope` - medical "
                             "advice, a prescription interaction, pregnancy safety, a skin condition "
                             "that needs a doctor, or a routine for a child?"),
            "criteria": {"true": "Maya must not answer this herself; it needs a clinician",
                         "false": "This is an ordinary beauty question a creator answers every day"}},
        "refusal_reason": {"type": "choice",
                           "instructions": "If `message` is outside Maya's scope, what makes it so?",
                           "criteria": dict(_REFUSAL_REASON)},
        "refer_to": {"type": "choice",
                     "instructions": "If Maya cannot answer `message` herself, who should this person be sent to?",
                     "criteria": dict(_REFER_TO)},
        "needs_question_back": {
            "type": "noul",
            "instructions": "Would Maya have to ask something back before she could answer `message` responsibly?",
            "criteria": {"true": "She would ask one thing first - she never adds product blind",
                         "false": "There is enough here for her to just answer"}},
        "which_question_back": {
            "type": "choice",
            "instructions": "If Maya asked ONE question back, which of `creator.her_intake_questions` would it be?",
            "criteria": {qq: None for qq in intake_questions}},
        # wording below is the MEASURED one from engine_overnight_queue.py (50 DMs, 78%
        # handled). Sharpening it to "she would be guessing" collapsed answered 30 -> 5.
        "enough_to_answer": {
            "type": "noul",
            "instructions": ("Is there enough in `message` for Maya's standard to produce an answer "
                             "she would stand behind?"),
            "criteria": {"true": "Enough to answer", "false": "Too little to be responsible"}},
        "emotional_weight": {
            "type": "score",
            "instructions": "How much does `message` need Maya herself rather than a useful answer?",
            "criteria": ["Purely practical - any correct answer will do",
                         "Mostly practical, a little personal",
                         "Personal - warmth matters as much as the answer",
                         "This person wants Maya specifically and nobody else"]},
        "budget": {"type": "choice",
                   "instructions": "What budget does `message` state or imply?",
                   "criteria": {"under_30": "Thirty pounds or less - a student, a tight month, 'only 20 quid'",
                                "30_to_60": "Somewhere between thirty and sixty pounds",
                                "60_to_100": "Somewhere between sixty and a hundred pounds",
                                "over_100": "Over a hundred pounds, or no ceiling mentioned at all",
                                "not_stated": "No money signal anywhere in the message"}},
        "max_items": {"type": "choice",
                      "instructions": "How many products would this person tolerate being told to buy?",
                      "criteria": {"one": "They want one answer and one only - 'if you had to pick ONE'",
                                   "two": "Explicitly a minimal routine - 'only 2 products', 'I will not do 8 steps'",
                                   "three_or_four": "Open to a small set of three or four",
                                   "not_stated": "No signal about how many"}},
        "already_owns": {"type": "noul",
                         "instructions": "Does `message` say they already own one of `creator.her_shelf`?",
                         "criteria": {"true": "They name something they already have",
                                      "false": "They do not mention owning anything"}},
        "which_owned": {"type": "choice",
                        "instructions": "Which product from `creator.her_shelf` does `message` say they already own?",
                        "criteria": dict([(p, None) for p in products] + [("none", "They do not name one")])},
        "named_product": {"type": "choice",
                          "instructions": "Which product from `creator.her_shelf` is `message` asking about specifically?",
                          "criteria": dict([(p, None) for p in products] + [("none", "No specific product named")])},
    }
    q.update(skin_multilabel("message"))
    return q


# ---------------------------------------------------------------- the basket
def basket_scores(baskets: dict) -> dict:
    """Stage 1 of the two-stage basket (bug #2): score every feasible set."""
    return {
        bid: {"type": "score",
              "instructions": "Would `judge` send `baskets." + bid + "` to `shopper`? Judge the SET, not the items.",
              "criteria": ["Wrong for this person - she would not send this",
                           "Defensible, but not the set she would pick",
                           "Reasonable",
                           "Good - close to her answer",
                           "Exactly the set she would send"]}
        for bid in baskets
    }


def basket_choice(finalists: dict) -> dict:
    """Stage 2: ONE choice over the finalists. The single-stage version gave a
    different winner between runs; two-stage was stable."""
    return {"pick": {"type": "choice",
                     "instructions": "Which one of `finalists` would `judge` actually send to `shopper`?",
                     "criteria": {bid: " + ".join(v["items"]) for bid, v in finalists.items()}}}


_LEFT_OUT = {
    "already_covered": "Something they already own, or something already in the basket, does this job",
    "over_her_price_line": "She likes it but it costs more than she thinks it is worth",
    "wrong_for_their_skin": "It is the wrong texture or the wrong formula for this person's skin",
    "not_needed_yet": "A fine product, but this person does not need it yet - it is a fourth step, not a first",
    "does_not_fit_budget": "It simply does not fit inside what they said they have to spend",
}
LEFT_OUT_REASONS = _LEFT_OUT


def left_out_reasons(candidates: list) -> dict:
    """Why each near-miss was left out. Always paired with an alternative in code."""
    return {
        "why__" + str(i): {
            "type": "choice",
            "instructions": "`judge` did not put `considered.p" + str(i) + "` in `chosen_basket` for `shopper`. Why not?",
            "criteria": dict(_LEFT_OUT)}
        for i in range(len(candidates))
    }


# ---------------------------------------------------------------- the standard
STANDARD_SLOTS = {
    "routine_size": {"type": "score",
                     "instructions": "Does this person favour the fewest possible products, or a complete multi-step routine?",
                     "criteria": ["The fewest possible products", "A small routine",
                                  "A moderate routine", "A complete multi-step routine"]},
    "budget_behaviour": {"type": "noul",
                         "instructions": "Given a budget, would this person spend all of it, or deliberately leave money unspent?",
                         "criteria": {"true": "They would spend the whole budget because it is there",
                                      "false": "They are happy to hand money back and send someone away with less"}},
    "price_refusal": {"type": "score",
                      "instructions": "How willing is this person to say something is good but not worth its price?",
                      "criteria": ["Never talks about price", "Mentions price occasionally",
                                   "Will call something overpriced", "Price is central to their judgement"]},
    "subtraction": {"type": "noul",
                    "instructions": "Does this person tell people to REMOVE products as often as add them?",
                    "criteria": {"true": "Taking things away is half of their advice",
                                 "false": "Their advice is almost always to add something"}},
    "hype": {"type": "score",
             "instructions": "How does this person treat trending or heavily marketed products?",
             "criteria": ["Actively sceptical of hype", "Cautious", "Neutral", "Follows trends"]},
    "defended_category": {"type": "choice",
                          "instructions": "Which single category does this person treat as non-negotiable, bought before anything else?",
                          "criteria": {"spf": None, "cleanser": None, "moisturiser": None,
                                       "serum": None, "makeup": None, "none": "No clear priority"}},
}


# ---------------------------------------------------------------- the standard, v14
# The FOURTEEN slots that produced docs/11-honest-headline.md, lifted verbatim from
# scripts/engine_decontaminated_v2.py. STANDARD_SLOTS (the six above) is kept untouched
# so the v1 diff stays auditable; this is what /api/extract actually sends.
#
# Identical for both judges. Nothing creator-specific is hard-coded in any of them.
# `situation` is OUR bookkeeping - it is reused verbatim as the `when` clause of the
# structured routing rules so rule text and question text can never drift. The API never
# sees it: `api_slots()` strips it.
CATEGORIES = ["spf", "cleanser", "moisturiser", "serum", "makeup"]

ROUTE_SLOT_KEYS = ["route_reacting", "route_redness", "route_dry", "route_oily"]


def shelf_options(shelf: list, none_text: str) -> dict:
    """Choice criteria generated FROM THE SHELF DATA, not typed out by hand."""
    d = {p["product"]: "%s - a GBP%d %s for %s skin, %s finish"
                       % (p["product"], p["gbp"], str(p["type"]).lower(),
                          str(p["skin"]).lower(), str(p["finish"]).lower())
         for p in shelf}
    d["none"] = none_text
    return d


def standard_slots_v14(shelf: list) -> dict:
    """The fourteen typed slots, with `situation` still attached."""
    cats = CATEGORIES
    return {
        # ---- the original six, byte-for-byte from STANDARD_SLOTS above ----
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

        # ---- category priorities ----
        "interchangeable_category": {"type": "choice",
            "instructions": "Someone asks this person which brand of each category to buy. For which ONE category "
                            "would they say the specific product barely matters and any decent one will do?",
            "criteria": dict([(c, "They would say: any decent %s is fine, do not overthink this one" % c) for c in cats]
                             + [("none", "They think the specific product matters in every category")])},
        "skippable_category": {"type": "choice",
            "instructions": "Someone has less money than a full routine costs and has to leave something out. "
                            "Which ONE category would this person drop first?",
            "criteria": dict([(c, "They would leave the %s out of the basket entirely before dropping anything else" % c) for c in cats]
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

        # ---- routing conditions. Concrete situations, in the asker's own words (bug #4). ----
        "route_reacting": {"type": "choice",
            "situation": "Someone writes 'every time I try something new my face freaks out'. They own no skincare "
                         "yet and are starting from nothing, with money to spend.",
            "instructions": "Someone writes: 'every time I try something new my face freaks out.' They own no "
                            "skincare yet and are starting from nothing, with money to spend. Which ONE item from "
                            "`shelf` does this person reach for first for her?",
            "criteria": shelf_options(shelf, "None of them - they would tell her to buy nothing at all and take products "
                                             "away from whatever she is already using")},
        "route_redness": {"type": "choice",
            "situation": "Someone writes 'my cheeks are red and angry today and nothing calms it down'.",
            "instructions": "Someone writes: 'my cheeks are red and angry today and nothing calms it down.' Which "
                            "ONE item from `shelf` does this person reach for first for her?",
            "criteria": shelf_options(shelf, "None of them - redness is not something they would answer with a product")},
        "route_dry": {"type": "choice",
            "situation": "Someone writes 'my skin is dry and tight all winter and it flakes under makeup'.",
            "instructions": "Someone writes: 'my skin is dry and tight all winter and it flakes under makeup.' "
                            "Which ONE item from `shelf` does this person reach for first for her?",
            "criteria": shelf_options(shelf, "None of them - dryness is not something they would answer with a product")},
        "route_oily": {"type": "choice",
            "situation": "Someone writes 'I am shiny by 11am and my t-zone never stops'.",
            "instructions": "Someone writes: 'I am shiny by 11am and my t-zone never stops.' Which ONE item from "
                            "`shelf` does this person reach for first for her?",
            "criteria": shelf_options(shelf, "None of them - oiliness is not something they would answer with a product")},
    }


def api_slots(slots: dict) -> dict:
    """Strip our bookkeeping. The API sees only type/instructions/criteria."""
    return {k: {kk: vv for kk, vv in v.items() if kk != "situation"} for k, v in slots.items()}
