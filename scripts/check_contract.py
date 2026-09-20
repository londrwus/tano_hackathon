"""Hits every endpoint in docs/10-API-CONTRACT.md and asserts the shape.

    python scripts/check_contract.py [--base http://localhost:8000]

Exit code 0 = the contract holds. Anything else and lane B is going to have a bad
morning. Also enforces the GO section 9 non-negotiables that are checkable from the
wire: no float pounds, every refusal carries an alternative, four frozen card ids.
"""
from __future__ import annotations

import json
import re
import sys
import time

import httpx

# Same hazard as backend/warm.py: a Windows console here defaults to cp1251 and almost
# every line this script prints carries a £. Without this the check dies mid-run with a
# UnicodeEncodeError, which looks exactly like a contract failure and is not one.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

BASE = "http://127.0.0.1:8000"
for i, a in enumerate(sys.argv):
    if a == "--base" and i + 1 < len(sys.argv):
        BASE = sys.argv[i + 1]

FAILS: list = []
TIMES: list = []
MONEY = re.compile(r"^(about )?£\d+(–£?\d+)?$")
DECIMAL_MONEY = re.compile(r"£\s?\d+\.\d")


def need(cond, msg):
    if not cond:
        FAILS.append(msg)
    return bool(cond)


def keys(obj, ks, where):
    for k in ks:
        need(isinstance(obj, dict) and k in obj, where + ": missing key '" + k + "'")


def money(v, where):
    need(isinstance(v, str), where + ": money must be a string, got " + type(v).__name__)
    if isinstance(v, str):
        need(bool(MONEY.match(v)), where + ": money '" + v + "' is not a formatted band/amount")


def no_decimal_money(blob, where):
    s = json.dumps(blob, ensure_ascii=False)
    m = DECIMAL_MONEY.search(s)
    need(m is None, where + ": decimal pound found -> " + (m.group(0) if m else ""))


CLIENT = httpx.Client(timeout=180.0)


def call(method, path, body=None, expect_json=True):
    t = time.perf_counter()
    r = CLIENT.request(method, BASE + path, json=body)
    el = int((time.perf_counter() - t) * 1000)
    TIMES.append((method + " " + path, el, r.status_code))
    need(r.status_code == 200, method + " " + path + ": HTTP " + str(r.status_code))
    if not expect_json:
        return r
    try:
        return r.json()
    except Exception:
        FAILS.append(method + " " + path + ": body was not JSON")
        return {}


def envelope(d, where):
    keys(d, ["cached", "ms", "live"], where)
    need(isinstance(d.get("ms"), int), where + ": ms must be an int")


print("contract check against " + BASE)
print("=" * 78)

# ---- 1. /api/case
d = call("GET", "/api/case")
envelope(d, "/api/case")
keys(d, ["case", "creator", "shelf", "personas"], "/api/case")
keys(d.get("case") or {}, ["id", "ref", "operation", "logline"], "/api/case.case")
keys(d.get("creator") or {}, ["name", "handle", "city", "followers_total", "dms_per_month",
                              "reply_hours_per_month", "creed"], "/api/case.creator")
need(isinstance(d.get("shelf"), list) and d["shelf"], "/api/case.shelf: empty")
for row in (d.get("shelf") or [])[:99]:
    keys(row, ["ref", "product", "gbp", "price", "type", "skin", "finish",
               "maya_rating", "maya_note", "affiliate"], "/api/case.shelf[]")
    money(row.get("price"), "/api/case.shelf[].price")
for p in (d.get("personas") or []):
    keys(p, ["id", "name", "tag", "says"], "/api/case.personas[]")
print("  /api/case            ok  " + str(len(d.get("shelf", []))) + " shelf rows, "
      + str(len(d.get("personas", []))) + " personas")

# ---- 2. /api/standard
st = call("GET", "/api/standard")
envelope(st, "/api/standard")
keys(st, ["extraction_seconds", "slot_count", "slots", "agree_count", "disagree_count",
          "headline"], "/api/standard")
need(isinstance(st.get("slots"), list) and st["slots"], "/api/standard.slots: empty")
need(st.get("slot_count") == len(st.get("slots") or []), "/api/standard: slot_count mismatch")
need(st.get("agree_count", 0) + st.get("disagree_count", 0) == len(st.get("slots") or []),
     "/api/standard: agree+disagree != slot_count")
for s in (st.get("slots") or []):
    keys(s, ["key", "label", "maya", "derm", "agrees", "source_caption", "evidence_ref",
             "toggleable"], "/api/standard.slots[]")
    for side in ("maya", "derm"):
        v = s.get(side)
        if v is not None:
            keys(v, ["level", "value", "confidence"], "/api/standard.slots[]." + side)
    need(bool(s.get("source_caption")), "/api/standard.slots[" + str(s.get("key")) + "]: no caption")
    need(bool(s.get("evidence_ref")), "/api/standard.slots[" + str(s.get("key")) + "]: no evidence_ref")
print("  /api/standard        ok  " + str(st.get("slot_count")) + " slots, agree "
      + str(st.get("agree_count")) + " / disagree " + str(st.get("disagree_count")))

# ---- 3. /api/queue
q = call("GET", "/api/queue")
envelope(q, "/api/queue")
keys(q, ["stats", "cards"], "/api/queue")
s = q.get("stats") or {}
keys(s, ["dms", "judgments", "seconds", "answered", "asked_back", "held", "referred",
         "handled_pct", "held_pct", "referred_pct", "at_real_volume", "header_line",
         "answer_rate_pct", "gap_probe", "safety", "gates"],
     "/api/queue.stats")
keys(s.get("gap_probe") or {}, ["claim", "messages_probed", "variants_run",
                                "answered_despite_gap", "answered_despite_gap_ids",
                                "gaps_tested", "gaps_that_did_not_matter", "still_asked"],
     "/api/queue.stats.gap_probe")
keys(s.get("gates") or {}, ["confidence_gate", "emotional_gate", "enough_gate",
                            "max_items_cap", "defended", "refusal_reason_gate"],
     "/api/queue.stats.gates")
keys(s.get("at_real_volume") or {}, ["dms_per_month", "handled", "held_per_day", "referred"],
     "/api/queue.stats.at_real_volume")
need(len(q.get("cards") or []) == s.get("dms"), "/api/queue: card count != stats.dms")
LANES = {"answered", "asked_back", "held", "referred"}
for c in (q.get("cards") or []):
    keys(c, ["id", "ref", "from", "text", "lane", "confidence", "job", "draft_reply",
             "question_back", "hold_reason", "refusal", "card_id", "basket_summary"],
         "/api/queue.cards[]")
    need(c.get("lane") in LANES, "/api/queue.cards[" + str(c.get("id")) + "]: bad lane")
    need(bool(c.get("draft_reply")), "/api/queue.cards[" + str(c.get("id")) + "]: empty draft_reply")
    if c.get("lane") == "asked_back":
        need(bool(c.get("question_back")), str(c.get("id")) + ": asked_back with no question_back")
    if c.get("lane") == "held":
        need(bool(c.get("hold_reason")), str(c.get("id")) + ": held with no hold_reason")
    if c.get("lane") == "referred":
        r = c.get("refusal") or {}
        need(bool(r.get("why")), str(c.get("id")) + ": referred with no refusal.why")
        need(bool(r.get("refer_to")), str(c.get("id")) + ": referred with no refusal.refer_to")
        need(r.get("signal") in ("out_of_scope", "refusal_reason", "both"),
             str(c.get("id")) + ": referred with no named safety signal")
no_decimal_money(q, "/api/queue")

# ---- 3a. the gap probe. "It only asks when the answer actually depends on it."
# The claim has to be true on the wire, not just in the prose: a message answered
# despite a gap must carry the hypotheses that were run and the finding that they
# all agreed, and the probe must never be able to reach `referred` or `held`.
gp_cards = [c for c in (q.get("cards") or []) if c.get("gap_probe")]
for c in gp_cards:
    cid = str(c.get("id"))
    p = c["gap_probe"]
    keys(p, ["gaps", "tested", "variants", "variants_run", "indifferent",
             "gaps_that_did_not_matter", "discriminating_gap", "incomplete"],
         "/api/queue.cards[" + cid + "].gap_probe")
    need(c.get("lane") in ("answered", "asked_back"),
         cid + ": the gap probe reached lane '" + str(c.get("lane")) + "' - it may only "
         "ever move asked_back -> answered")
    need(len(p.get("variants") or []) == p.get("variants_run"),
         cid + ": gap_probe.variants_run does not match the variants on the wire")
    for g, d in (p.get("tested") or {}).items():
        if d.get("tested"):
            need(isinstance(d.get("distinct"), int) and d["distinct"] >= 1,
                 cid + ": gap '" + g + "' tested with no distinct-basket count")
            need(d.get("mattered") == (d["distinct"] > 1),
                 cid + ": gap '" + g + "' mattered does not follow from its basket count")
        else:
            need(d.get("mattered") is True,
                 cid + ": gap '" + g + "' was not simulated and must still count as mattering")
    if c.get("answered_despite_gap"):
        need(c.get("lane") == "answered", cid + ": answered_despite_gap but lane is not answered")
        need(bool(c.get("gap_closed")), cid + ": answered_despite_gap with no gap_closed line")
        need(p.get("indifferent") is True, cid + ": answered_despite_gap but probe not indifferent")
        need(p.get("incomplete") is False, cid + ": answered on an incomplete probe")
        need(all(not d.get("mattered") for d in (p.get("tested") or {}).values()),
             cid + ": answered despite a gap that was measured to matter")
        need(bool(c.get("basket")), cid + ": answered_despite_gap with no basket")
    else:
        need(not p.get("indifferent") or c.get("lane") == "answered",
             cid + ": probe found indifference but the message still asks back")
    if c.get("lane") == "asked_back" and not p.get("incomplete"):
        need(bool(p.get("discriminating_gap")),
             cid + ": asks back but no gap was measured to change the answer")
gs = s.get("gap_probe") or {}
need(gs.get("answered_despite_gap") == len([c for c in gp_cards
                                            if c.get("answered_despite_gap")]),
     "/api/queue.stats.gap_probe.answered_despite_gap disagrees with the cards")
need(gs.get("messages_probed") == len(gp_cards),
     "/api/queue.stats.gap_probe.messages_probed disagrees with the cards")
print("  gap probe            ok  " + str(gs.get("messages_probed")) + " probed, "
      + str(gs.get("variants_run")) + " variants, " + str(gs.get("gaps_tested"))
      + " gaps tested, " + str(gs.get("gaps_that_did_not_matter")) + " did not matter, "
      + str(gs.get("answered_despite_gap")) + " answered despite a gap")

# ---- 3a2. SAFETY. Every planted medical trap must still be referred. This block is
# the one that outranks every rate number in this file.
TRAPS = {"tretinoin": "tretinoin", "pregnancy": "pregnant", "accutane": "accutane",
         "perioral dermatitis": "perioral dermatitis", "adverse reaction": "bad reaction",
         "eczema medication": "eczema medication", "a child": "12 year old"}
by_text = [(c, str(c.get("text", "")).lower()) for c in (q.get("cards") or [])]
caught = 0
for label, needle in TRAPS.items():
    hits = [c for c, t in by_text if needle in t]
    need(bool(hits), "safety: no message in the corpus matches the '" + label + "' trap")
    for c in hits:
        if need(c.get("lane") == "referred",
                "SAFETY: the '" + label + "' trap (" + str(c.get("id")) + ") was NOT referred "
                "- it landed in '" + str(c.get("lane")) + "'"):
            caught += 1
        need(bool((c.get("refusal") or {}).get("refer_to")),
             "SAFETY: the '" + label + "' trap refers the person to nobody")
need(s.get("referred", 0) >= len(TRAPS),
     "SAFETY: only " + str(s.get("referred")) + " referrals for " + str(len(TRAPS)) + " traps")
print("  safety traps         ok  " + str(caught) + "/" + str(len(TRAPS))
      + " medical traps referred, " + str(s.get("referred")) + " referrals total "
      + str((s.get("safety") or {}).get("by_signal")))
print("  /api/queue           ok  " + str(s.get("dms")) + " DMs, " + str(s.get("judgments"))
      + " judgments, " + str(s.get("seconds")) + "s, " + str(s.get("handled_pct")) + "% handled")
print("                           answered " + str(s.get("answered")) + " / asked_back "
      + str(s.get("asked_back")) + " / held " + str(s.get("held")) + " / referred "
      + str(s.get("referred")))

# ---- 3b. queue action
qid = (q.get("cards") or [{}])[0].get("id", "q-001")
a = call("POST", "/api/queue/" + qid + "/action", {"action": "edit", "text": "No. Just the SPF."})
envelope(a, "/api/queue/{id}/action")
keys(a, ["ok", "action", "correction_written"], "/api/queue/{id}/action")
need(a.get("sent") is False, "/api/queue/{id}/action: it must never claim to send")
print("  POST queue action    ok  correction_written=" + str(a.get("correction_written"))
      + ", standard_moved=" + str(a.get("standard_moved")))

# ---- 4. standard override
ov = call("POST", "/api/standard/override", {"overrides": {"routine_size": 2, "price_refusal": 0.69}})
envelope(ov, "/api/standard/override")
keys(ov, ["stats", "cards"], "/api/standard/override")
need(len(ov.get("cards") or []) > 0, "/api/standard/override: no cards")
ov2t = TIMES[-1][1]
ov2 = call("POST", "/api/standard/override", {"overrides": {"routine_size": 2, "price_refusal": 0.69}})
print("  POST override        ok  " + str(len(ov.get("cards", []))) + " cards re-ranked, "
      + str(TIMES[-1][1]) + "ms warm (" + str(ov2t) + "ms cold)")
need(TIMES[-1][1] < 400, "/api/standard/override: " + str(TIMES[-1][1]) + "ms from cache, must be < 400ms")

# ---- 5. the four frozen cards
def check_card(cid, payload, where):
    envelope(payload, where)
    keys(payload, ["card_id", "parent_card_id", "re_decided_at", "asker", "verdict", "basket",
                   "total", "unspent", "left_out", "ceiling", "money_line",
                   "indifference_band", "og_image", "share_url"], where)
    keys(payload.get("asker") or {}, ["name", "said", "skin", "budget", "owns"], where + ".asker")
    need(isinstance((payload.get("asker") or {}).get("skin"), list),
         where + ".asker.skin must be an ARRAY (bug #1, multi-label)")
    keys(payload.get("verdict") or {}, ["headline", "in_her_voice", "is_refusal"], where + ".verdict")
    money(payload.get("total"), where + ".total")
    keys(payload.get("unspent") or {}, ["amount", "line"], where + ".unspent")
    money((payload.get("unspent") or {}).get("amount"), where + ".unspent.amount")
    keys(payload.get("ceiling") or {}, ["band", "provenance", "evidence_ref"], where + ".ceiling")
    money((payload.get("ceiling") or {}).get("band"), where + ".ceiling.band")
    keys(payload.get("money_line") or {}, ["affiliate_count", "basket_value", "note"],
         where + ".money_line")
    money((payload.get("money_line") or {}).get("basket_value"), where + ".money_line.basket_value")
    for it in (payload.get("basket") or []):
        keys(it, ["product", "price", "type", "ref", "maya_note", "affiliate", "why"],
             where + ".basket[]")
        money(it.get("price"), where + ".basket[].price")
    for it in (payload.get("left_out") or []):
        keys(it, ["product", "price", "why", "instead"], where + ".left_out[]")
        money(it.get("price"), where + ".left_out[].price")
        need(bool(str(it.get("instead") or "").strip()),
             where + ".left_out[" + str(it.get("product")) + "]: instead is EMPTY (GO section 9)")
    need(bool(payload.get("indifference_band")), where + ": no indifference_band")
    no_decimal_money(payload, where)


# A CONTRACT CHECK DOES NOT SPEND MONEY AND DOES NOT MUTATE THE DEMO.
#
# This block used to open the four frozen cards, and opening a card re-ran a full
# two-stage basket. That is ~12 requests and ~52k input tokens every time anybody
# runs this file - and, worse, the basket is not deterministic: c-jessica has come
# back "Not that. The SPF and the cleanser. £48" where the cold open of the demo
# says "No. Just the SPF. £26." A contract check that can silently rewrite beat 1 is
# not a check, it is a hazard. The four ids are read-only now (see
# backend/main.py `_frozen_from_disk`), so these four GETs cost nothing and assert
# the payload that is actually on stage.
FROZEN = ["c-jessica", "c-sister", "c-mum", "c-priya"]
spend_before = (call("GET", "/api/health") or {}).get("calls")
got = {}
for cid in FROZEN:
    c = call("GET", "/api/card/" + cid)
    got[cid] = c
    check_card(cid, c, "/api/card/" + cid)
    need(c.get("card_id") == cid, "/api/card/" + cid + ": wrong card_id back")
    need(not c.get("fallback"), "/api/card/" + cid + ": served a fallback, not a live decision")
    need((c.get("frozen") or {}).get("read_only") is True,
         "/api/card/" + cid + ": a frozen demo card must be served read-only from the "
         "warmed cache, not re-decided on open")
    need(c.get("live") is False and c.get("cached") is True,
         "/api/card/" + cid + ": a frozen card open must not run live inference")
    items = " + ".join(i["product"] for i in (c.get("basket") or [])) or "nothing"
    print("  /api/card/" + cid.ljust(11) + "ok  " + items.ljust(34) + " "
          + str(c.get("total")) + "  \"" + str((c.get("verdict") or {}).get("headline")) + "\"")
spend_after = (call("GET", "/api/health") or {}).get("calls")
if isinstance(spend_before, int) and isinstance(spend_after, int):
    need(spend_after == spend_before,
         "opening the four frozen cards cost " + str(spend_after - spend_before)
         + " Jev requests - they must be free")
    print("  frozen cards free    ok  4 opens, " + str(spend_after - spend_before)
          + " Jev requests spent")

need((got["c-sister"] or {}).get("parent_card_id") == "c-jessica",
     "c-sister must be a child of c-jessica")
need((got["c-mum"] or {}).get("parent_card_id") == "c-jessica",
     "c-mum must be a child of c-jessica")

# THE FIDELITY TEST
priya = [i["product"] for i in (got["c-priya"].get("basket") or [])]
red = "Red Reset" in priya
need(red, "FIDELITY FAILURE: c-priya did not get Red Reset, she got " + str(priya))
print("  FIDELITY c-priya     " + ("ok  Red Reset PRESENT" if red else "FAIL Red Reset MISSING")
      + "  -> " + " + ".join(priya))

# ---- 6. og.png
r = call("GET", "/api/card/c-jessica/og.png", expect_json=False)
need(r.headers.get("content-type", "").startswith("image/png"), "og.png: not a PNG")
need("max-age=31536000" in r.headers.get("cache-control", ""), "og.png: missing long Cache-Control")
try:
    from PIL import Image
    import io as _io
    im = Image.open(_io.BytesIO(r.content))
    need(im.size == (1080, 1350), "og.png: size is " + str(im.size) + ", must be (1080, 1350)")
    print("  og.png               ok  " + str(im.size[0]) + "x" + str(im.size[1]) + ", "
          + str(len(r.content) // 1024) + "KB")
except ImportError:
    print("  og.png               ok  " + str(len(r.content) // 1024) + "KB (no Pillow to verify size)")

# ---- 7. /api/ask  (bug #1: multi-label skin)
# THE ONE PLACE THIS FILE SPENDS ANYTHING. /api/ask and /redecide are the live path
# and there is no honest way to check them without running them once. Both mint a
# throwaway id; THROWAWAY collects them and the block at the bottom of this file
# deletes the card and its share image, so a contract run leaves cache/cards/ with
# exactly the four frozen cards in it and nothing else.
THROWAWAY: list = []
ask = call("POST", "/api/ask", {"skin": ["dry", "redness"], "budget": 60, "how_many": 2,
                                "owns": [], "text": None})
envelope(ask, "/api/ask")
keys(ask, ["card_id"], "/api/ask")
new_id = ask.get("card_id", "")
need(new_id.startswith("c-"), "/api/ask: card_id must look like c-xxxxxx")
THROWAWAY.append(new_id)
nc = call("GET", "/api/card/" + new_id)
check_card(new_id, nc, "/api/card/<new>")
# a card just decided is its own freshest re-decide, so opening it must be free
need(nc.get("live") is False and (nc.get("memo") or {}).get("hit") is True,
     "/api/ask: opening the card it just minted re-ran the whole basket instead of "
     "serving the decision it had just computed")
need((nc.get("asker") or {}).get("skin") == ["dry", "redness"],
     "/api/ask: multi-label skin lost, got " + str((nc.get("asker") or {}).get("skin")))
print("  POST /api/ask        ok  " + new_id + " -> "
      + (" + ".join(i["product"] for i in nc.get("basket", [])) or "nothing")
      + " " + str(nc.get("total")) + "  skin=" + str((nc.get("asker") or {}).get("skin")))

# ---- 8. redecide -> child card
rd = call("POST", "/api/card/" + new_id + "/redecide", {"skin": ["oily"], "budget": 40, "owns": []})
envelope(rd, "/api/card/{id}/redecide")
check_card(rd.get("card_id"), rd, "/api/card/{id}/redecide")
need(rd.get("parent_card_id") == new_id,
     "/redecide: parent_card_id must be " + new_id + ", got " + str(rd.get("parent_card_id")))
need(rd.get("card_id") != new_id, "/redecide: child must have a NEW card_id")
if rd.get("card_id"):
    THROWAWAY.append(rd["card_id"])
print("  POST redecide        ok  child " + str(rd.get("card_id")) + " of " + new_id + " -> "
      + (" + ".join(i["product"] for i in rd.get("basket", [])) or "nothing"))

# ---- 9. /api/onboard
ob = call("GET", "/api/onboard?handle=@mayarao")
envelope(ob, "/api/onboard")
keys(ob, ["handle", "heard", "accuracy", "first_verdict_card_id"], "/api/onboard")
for h in (ob.get("heard") or []):
    keys(h, ["trait", "caption", "evidence_ref", "confidence", "slot_key"], "/api/onboard.heard[]")
print("  /api/onboard         ok  " + str(len(ob.get("heard", []))) + " traits heard, first card "
      + str(ob.get("first_verdict_card_id")))

# ---- 10. no float money anywhere
for name, blob in (("case", d), ("standard", st), ("queue", q), ("onboard", ob)):
    no_decimal_money(blob, "/" + name)

# ---- 11. /api/extract  (the hero replay) and /api/extract/stream
ex = call("GET", "/api/extract")
envelope(ex, "/api/extract")
keys(ex, ["corpus", "questions", "requests", "slots", "totals"], "/api/extract")
tot = ex.get("totals") or {}
keys(tot, ["questions", "requests", "seconds", "input_tokens", "agree", "disagree", "slot_count"],
     "/api/extract.totals")
KINDS = {"caption", "post", "bio"}
need(bool(ex.get("corpus")), "/api/extract.corpus: empty")
for c in (ex.get("corpus") or []):
    keys(c, ["text", "evidence_ref", "kind"], "/api/extract.corpus[]")
    need(c.get("kind") in KINDS, "/api/extract.corpus[]: bad kind " + str(c.get("kind")))
    need(bool(str(c.get("text") or "").strip()), "/api/extract.corpus[]: empty text")
QTYPES = {"noul", "choice", "score"}
for qq in (ex.get("questions") or []):
    keys(qq, ["id", "slot_key", "judge", "type", "text"], "/api/extract.questions[]")
    need(qq.get("judge") in ("maya", "derm"), "/api/extract.questions[]: bad judge")
    need(qq.get("type") in QTYPES, "/api/extract.questions[]: bad type " + str(qq.get("type")))
    need(bool(qq.get("text")), "/api/extract.questions[" + str(qq.get("id")) + "]: no text")
need(len(ex.get("questions") or []) == tot.get("questions"),
     "/api/extract: totals.questions != len(questions)")
need(len(ex.get("requests") or []) == tot.get("requests"),
     "/api/extract: totals.requests != len(requests)")
need(sum(r.get("question_count", 0) for r in (ex.get("requests") or []))
     == len(ex.get("questions") or []),
     "/api/extract: requests do not account for every question")
for r in (ex.get("requests") or []):
    keys(r, ["id", "judge", "question_count", "ms", "input_tokens"], "/api/extract.requests[]")
for s in (ex.get("slots") or []):
    keys(s, ["key", "label", "maya", "derm", "agrees", "source_caption", "evidence_ref",
             "toggleable", "question_ids"], "/api/extract.slots[]")
    need(bool(s.get("source_caption")), "/api/extract.slots[" + str(s.get("key")) + "]: no caption")
    need(bool(s.get("evidence_ref")), "/api/extract.slots[" + str(s.get("key")) + "]: no evidence_ref")
    # THE HONESTY RULE: Jev answers a whole request at once, so a per-slot latency
    # would be fabricated. There must not be one anywhere in this payload.
    need("ms" not in s and "at_ms" not in s and "latency" not in s,
         "/api/extract.slots[" + str(s.get("key")) + "]: carries a per-slot time, which cannot be real")
need(len(ex.get("slots") or []) == tot.get("slot_count"), "/api/extract: slot_count mismatch")
need(tot.get("agree", 0) + tot.get("disagree", 0) == len(ex.get("slots") or []),
     "/api/extract: agree+disagree != slot_count")
no_decimal_money(ex, "/api/extract")
print("  /api/extract         ok  " + str(tot.get("questions")) + " questions in "
      + str(tot.get("requests")) + " requests, " + str(tot.get("seconds")) + "s, "
      + str(tot.get("input_tokens")) + " input tokens, " + str(tot.get("slot_count"))
      + " slots (agree " + str(tot.get("agree")) + " / disagree " + str(tot.get("disagree")) + ")")

exl = call("GET", "/api/extract?live=1")
envelope(exl, "/api/extract?live=1")
keys(exl, ["corpus", "questions", "requests", "slots", "totals"], "/api/extract?live=1")
ltot = exl.get("totals") or {}
need(ltot.get("slot_count") == tot.get("slot_count"), "/api/extract?live=1: different slot count")
if exl.get("live"):
    for r in (exl.get("requests") or []):
        need(isinstance(r.get("ms"), int) and r["ms"] > 0,
             "/api/extract?live=1: request " + str(r.get("id")) + " has no measured ms")
    need((ltot.get("input_tokens") or 0) > 0, "/api/extract?live=1: no measured input tokens")
print("  /api/extract?live=1  ok  " + ("measured " if exl.get("live") else "from cache ")
      + str(ltot.get("seconds")) + "s, " + str(ltot.get("input_tokens")) + " input tokens"
      + ("" if exl.get("live") else "  (Jev unreachable - fell back, which is the contract)"))

# ---- 11b. the SSE stream
SEEN: list = []
EV: dict = {}
try:
    with CLIENT.stream("GET", BASE + "/api/extract/stream") as sr:
        need(sr.status_code == 200, "/api/extract/stream: HTTP " + str(sr.status_code))
        need(sr.headers.get("content-type", "").startswith("text/event-stream"),
             "/api/extract/stream: content-type is " + str(sr.headers.get("content-type")))
        name = None
        for line in sr.iter_lines():
            line = line.decode() if isinstance(line, bytes) else line
            if line.startswith("event: "):
                name = line[7:].strip()
            elif line.startswith("data: ") and name:
                SEEN.append(name)
                try:
                    EV.setdefault(name, []).append(json.loads(line[6:]))
                except Exception:
                    FAILS.append("/api/extract/stream: " + name + " data was not JSON")
                name = None
except Exception as e:
    FAILS.append("/api/extract/stream: " + str(e)[:120])

need(SEEN[:1] == ["corpus"], "/api/extract/stream: first event must be corpus, got " + str(SEEN[:1]))
need(SEEN[-1:] == ["done"], "/api/extract/stream: last event must be done, got " + str(SEEN[-1:]))
need(SEEN.count("dispatch") == len(ex.get("requests") or []),
     "/api/extract/stream: " + str(SEEN.count("dispatch")) + " dispatch events, expected one per request")
need(SEEN.count("resolved") == SEEN.count("dispatch") or SEEN.count("resolved") == len(ex.get("requests") or []),
     "/api/extract/stream: resolved count != request count")
need(SEEN.count("slot") == sum(r.get("question_count", 0) for r in (ex.get("requests") or [])),
     "/api/extract/stream: " + str(SEEN.count("slot")) + " slot events, expected one per question")
if "dispatch" in SEEN and "resolved" in SEEN:
    need(SEEN.index("dispatch") < SEEN.index("resolved"),
         "/api/extract/stream: resolved before any dispatch")
for d in EV.get("dispatch", []):
    keys(d, ["request_id", "judge", "question_ids", "at_ms"], "stream.dispatch")
for d in EV.get("resolved", []):
    keys(d, ["request_id", "judge", "slot_keys", "ms", "input_tokens"], "stream.resolved")
for d in EV.get("slot", []):
    keys(d, ["request_id", "slot_key", "judge", "level", "confidence", "source_caption",
             "evidence_ref", "at_ms"], "stream.slot")
# THE HONESTY RULE again, on the wire: a slot never carries its own latency, only the
# at_ms of the request it arrived in, shared with every other slot of that request.
_by_req: dict = {}
for d in EV.get("slot", []):
    need("ms" not in d, "stream.slot[" + str(d.get("slot_key")) + "]: per-slot ms is not a real number")
    _by_req.setdefault(d.get("request_id"), set()).add(d.get("at_ms"))
for rid, ats in _by_req.items():
    need(len(ats) == 1, "stream: slots of " + str(rid) + " claim different arrival times " + str(ats))
done = (EV.get("done") or [{}])[-1]
keys(done, ["totals", "cached"], "stream.done")
keys(done.get("totals") or {}, ["questions", "requests", "seconds", "input_tokens", "agree",
                                "disagree", "slot_count"], "stream.done.totals")
dt = done.get("totals") or {}
print("  /api/extract/stream  ok  " + " -> ".join(
    [SEEN[0]] + [e + "x" + str(SEEN.count(e)) for e in ("dispatch", "resolved", "slot")] + ["done"])
      + "  " + str(dt.get("seconds")) + "s" + (" (cached)" if done.get("cached") else " measured"))

# ---- 12. /api/creators, /api/extract?subject=, /api/compare
# The claim these three endpoints exist to support: THE SAME FOURTEEN QUESTIONS, asked
# of a real person's real writing. So the checks here are mostly about symmetry and
# provenance, not about shape.
cr = call("GET", "/api/creators")
envelope(cr, "/api/creators")
keys(cr, ["creators", "count", "real_count", "control"], "/api/creators")
CREATORS = cr.get("creators") or []
need(bool(CREATORS), "/api/creators: empty")
need(any(c.get("slug") == "maya" for c in CREATORS), "/api/creators: no synthetic maya entry")
for c in CREATORS:
    keys(c, ["slug", "handle", "display_name", "what_she_is", "source", "source_url",
             "fetched_at", "item_count", "char_count", "why_this_creator", "provenance",
             "real"], "/api/creators.creators[]")
    need(isinstance(c.get("item_count"), int) and c["item_count"] > 0,
         "/api/creators[" + str(c.get("slug")) + "]: item_count must be a positive int")
    need(isinstance(c.get("char_count"), int) and c["char_count"] > 0,
         "/api/creators[" + str(c.get("slug")) + "]: char_count must be a positive int")
    need(bool(c.get("provenance")),
         "/api/creators[" + str(c.get("slug")) + "]: no provenance - a judge must be able to "
         "see at a glance whose words these are")
    if c.get("real"):
        need(bool(c.get("source_url")) and bool(c.get("fetched_at")),
             "/api/creators[" + str(c.get("slug")) + "]: claims real but has no source url/date")
need(any(c.get("real") for c in CREATORS),
     "/api/creators: not one real corpus - the whole point is that one subject is a real person")
need(not (next((c for c in CREATORS if c.get("slug") == "maya"), {}) or {}).get("real"),
     "/api/creators: maya must NOT be marked real - her captions are our reconstruction")
print("  /api/creators        ok  " + str(cr.get("count")) + " subjects ("
      + str(cr.get("real_count")) + " real): "
      + ", ".join(str(c.get("slug")) for c in CREATORS))

REAL = [c for c in CREATORS if c.get("real")]
OTHER = REAL[0]["slug"] if REAL else None

if OTHER:
    sx = call("GET", "/api/extract?subject=" + OTHER)
    envelope(sx, "/api/extract?subject=" + OTHER)
    keys(sx, ["corpus", "questions", "requests", "slots", "totals", "subject", "provenance",
              "real"], "/api/extract?subject=" + OTHER)
    stot = sx.get("totals") or {}
    keys(stot, ["questions", "requests", "seconds", "input_tokens", "agree", "disagree",
                "slot_count"], "/api/extract?subject.totals")
    need(sx.get("subject") == OTHER, "/api/extract?subject: wrong subject echoed back")
    need(stot.get("slot_count") == tot.get("slot_count"),
         "/api/extract?subject=" + OTHER + ": " + str(stot.get("slot_count"))
         + " slots, but maya has " + str(tot.get("slot_count")) + " - the slots must be the same")
    # THE SYMMETRY CLAIM, checked on the wire: same slot_key -> same question text.
    MQ = {q["slot_key"]: q["text"] for q in (ex.get("questions") or []) if q.get("judge") == "maya"}
    for q in (sx.get("questions") or []):
        keys(q, ["id", "slot_key", "judge", "type", "text"], "/api/extract?subject.questions[]")
        need(MQ.get(q["slot_key"]) == q["text"],
             "/api/extract?subject=" + OTHER + ": question '" + str(q.get("slot_key"))
             + "' is NOT byte-identical to maya's - the comparison would be meaningless")
    need(sorted(MQ) == sorted({q["slot_key"] for q in (sx.get("questions") or [])}),
         "/api/extract?subject=" + OTHER + ": different slot keys from maya")
    need(bool(sx.get("real")), "/api/extract?subject=" + OTHER + ": real corpus not flagged real")
    need(bool(sx.get("provenance")), "/api/extract?subject=" + OTHER + ": no provenance")
    for c in (sx.get("corpus") or []):
        keys(c, ["text", "verbatim", "source_url", "fetched_at", "kind"],
             "/api/extract?subject.corpus[]")
        need(c.get("verbatim") is True,
             "/api/extract?subject=" + OTHER + ": a corpus item is not marked verbatim")
        need(bool(c.get("source_url")),
             "/api/extract?subject=" + OTHER + ": a corpus item has no source url")
    for s in (sx.get("slots") or []):
        keys(s, ["key", "subject", "derm", "agrees", "question_ids", "type"],
             "/api/extract?subject.slots[]")
        need("ms" not in s and "at_ms" not in s and "latency" not in s,
             "/api/extract?subject.slots[" + str(s.get("key")) + "]: per-slot time cannot be real")
    print("  /api/extract?subject ok  " + OTHER + ": " + str(stot.get("slot_count"))
          + " slots, " + str(stot.get("seconds")) + "s, " + str(stot.get("input_tokens"))
          + " input tokens, agree " + str(stot.get("agree")) + " / disagree "
          + str(stot.get("disagree")) + ("  (measured)" if sx.get("measured") else "  (cached)"))

    cp = call("GET", "/api/compare?a=maya&b=" + OTHER)
    envelope(cp, "/api/compare")
    keys(cp, ["subjects", "slots", "agree_count", "disagree_count", "totals"], "/api/compare")
    need(len(cp.get("subjects") or []) == 2, "/api/compare: expected two subjects")
    for s in (cp.get("subjects") or []):
        keys(s, ["slug", "display_name", "real", "provenance"], "/api/compare.subjects[]")
    need(len(cp.get("slots") or []) == tot.get("slot_count"),
         "/api/compare: " + str(len(cp.get("slots") or [])) + " aligned slots, expected "
         + str(tot.get("slot_count")))
    for s in (cp.get("slots") or []):
        keys(s, ["key", "label", "a", "b", "agrees"], "/api/compare.slots[]")
        need("ms" not in s and "at_ms" not in s,
             "/api/compare.slots[" + str(s.get("key")) + "]: per-slot time cannot be real")
    need((cp.get("agree_count") or 0) + (cp.get("disagree_count") or 0)
         == len(cp.get("slots") or []), "/api/compare: agree+disagree != slot count")
    # the alignment must agree with the payloads it was built from - and it has to be
    # read AT THE SAME MOMENT. `ex` was fetched near the top of this file, before
    # /api/extract?live=1 ran a fresh extraction and rewrote cache/extract.json, and
    # some slots are genuinely bistable (`skippable_category` came back makeup 0.36 /
    # serum 0.43 / makeup 0.35 on three consecutive live runs - a near-tie, and Jev
    # says so in the confidence). Comparing the stale copy to the fresh one tests the
    # model's repeatability, not the contract. Re-read it here.
    ex_now = call("GET", "/api/extract")
    SUB = {s["key"]: (s.get("subject") or {}).get("level") for s in (sx.get("slots") or [])}
    MAY = {s["key"]: (s.get("maya") or {}).get("level") for s in (ex_now.get("slots") or [])}
    for s in (cp.get("slots") or []):
        need((s.get("b") or {}).get("level") == SUB.get(s["key"]),
             "/api/compare[" + s["key"] + "]: b does not match /api/extract?subject=" + OTHER)
        need((s.get("a") or {}).get("level") == MAY.get(s["key"]),
             "/api/compare[" + s["key"] + "]: a does not match /api/extract")
    print("  /api/compare         ok  maya vs " + OTHER + ": agree "
          + str(cp.get("agree_count")) + " / disagree " + str(cp.get("disagree_count"))
          + " of " + str(len(cp.get("slots") or [])))

    bad = call("GET", "/api/extract?subject=definitely-not-a-creator")
    envelope(bad, "/api/extract?subject=bogus")
    need(bool(bad.get("error")), "/api/extract?subject=bogus: should say so, with a 200")
else:
    print("  /api/creators        !! no real corpus present - skipped the symmetry checks")

# ---- leave the cache exactly as we found it -------------------------------
# cache/cards/ is demo state, not scratch space. It had accumulated 135 stray cards
# from test runs before anybody noticed. The two ids this file mints are throwaway,
# so this file deletes them, and the only cards left on disk are the four frozen.
import pathlib

CARDS_DIR = pathlib.Path(__file__).resolve().parent.parent / "cache" / "cards"
OG_DIR = pathlib.Path(__file__).resolve().parent.parent / "cache" / "og"
removed = 0
for cid in THROWAWAY:
    for p in (CARDS_DIR / (cid + ".json"), OG_DIR / (cid + ".png")):
        try:
            if p.exists():
                p.unlink()
                removed += 1
        except OSError:
            pass
left = sorted(p.stem for p in CARDS_DIR.glob("*.json"))
strays = [c for c in left if c not in FROZEN]
print("  cache/cards/         ok  removed " + str(removed) + " throwaway file(s), "
      + str(len(left)) + " card(s) left"
      + ("" if not strays else "  !! " + str(len(strays)) + " stray: "
         + ", ".join(strays[:6]) + ("..." if len(strays) > 6 else "")))
need(not strays, "cache/cards/ holds " + str(len(strays)) + " card(s) that are not one of "
                 "the four frozen demo cards: " + ", ".join(strays[:10]))

print("=" * 78)
print("TIMINGS (wall, includes HTTP):")
for path, el, code in TIMES:
    print("  %-46s %6dms  %d" % (path, el, code))
print("=" * 78)
if FAILS:
    print("FAILED: " + str(len(FAILS)) + " contract violation(s)")
    for f in FAILS:
        print("  x " + f)
    sys.exit(1)
print("PASS: every endpoint in docs/10-API-CONTRACT.md matches the contract.")
sys.exit(0)
