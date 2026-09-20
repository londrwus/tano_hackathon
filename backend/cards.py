"""Card store: mint ids, parent_card_id lineage, re-decide on open.

A card is a SPEC (who asked, what they said, their constraints) plus the last
payload we computed for it. Opening a card re-runs the spec - no scheduler, no
fake clock. If Jev is unreachable, the last payload is served with live=false.
"""
from __future__ import annotations

import json
import re
import uuid

from . import cache

ID_RE = re.compile(r"^c-[a-z0-9_-]{1,32}$")

# The four frozen demo cards. These must exist and must never 404 (contract section 9).
FROZEN = {
    "c-jessica": {
        "card_id": "c-jessica", "name": "@jessica", "parent_card_id": None,
        "said": "I already have the night serum. Do I need the barrier cream too?",
        "skin": [], "budget": 80, "owns": ["Night Serum"], "how_many": 3,
        "named_product": "Cloud Cream",
        "note": "Beat 1 - the cold-open refusal.",
    },
    "c-sister": {
        "card_id": "c-sister", "name": "her sister", "parent_card_id": "c-jessica",
        "said": "sent by a friend. oily skin, breakouts, student budget",
        "skin": ["oily"], "budget": 40, "owns": [], "how_many": 3,
        "note": "Beat 7 - the forward. Child of c-jessica.",
    },
    "c-mum": {
        "card_id": "c-mum", "name": "her mum", "parent_card_id": "c-jessica",
        "said": "sent by my daughter. dry, mature skin",
        "skin": ["dry"], "budget": 100, "owns": [], "how_many": 3,
        "note": "Beat 7 - keeps money unspent. Child of c-jessica.",
    },
    "c-priya": {
        "card_id": "c-priya", "name": "Priya", "parent_card_id": None,
        "said": "Every time I try something new my face freaks out. It is red most days.",
        "skin": ["sensitive", "redness"], "budget": 80, "owns": [], "how_many": 3,
        "note": "Fidelity proof - she must get Red Reset.",
    },
}


def valid(card_id: str) -> bool:
    return bool(card_id and ID_RE.match(card_id))


def mint() -> str:
    return "c-" + uuid.uuid4().hex[:6]


def _rel(card_id: str) -> str:
    return "cards/" + card_id


def save(payload: dict) -> None:
    cid = payload["card_id"]
    cache.put(_rel(cid), payload)


def load(card_id: str) -> dict | None:
    return cache.get(_rel(card_id))


def spec_for(card_id: str) -> dict | None:
    """The inputs a card re-decides from. Frozen ids have a spec even with no file."""
    if card_id in FROZEN:
        base = dict(FROZEN[card_id])
        saved = load(card_id)
        if saved and isinstance(saved.get("spec"), dict):
            s = dict(saved["spec"])
            s["card_id"] = card_id
            s.setdefault("name", base["name"])
            s["parent_card_id"] = base["parent_card_id"]
            s.setdefault("named_product", base.get("named_product"))
            return s
        return base
    saved = load(card_id)
    if not saved:
        return None
    s = dict(saved.get("spec") or {})
    s["card_id"] = card_id
    s.setdefault("name", (saved.get("asker") or {}).get("name") or "someone")
    s.setdefault("parent_card_id", saved.get("parent_card_id"))
    return s


def children(card_id: str) -> list:
    out = []
    for p in sorted(cache.CARDS.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("parent_card_id") == card_id:
            out.append(d["card_id"])
    return out


def all_ids() -> list:
    return sorted(p.stem for p in cache.CARDS.glob("*.json"))
