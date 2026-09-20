"""Disk cache under cache/. sha256 content keys. ?live=1 bypasses it.

Nothing here knows what a card or a queue is - it stores bytes and JSON
against a content hash, and it never raises on a miss.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
ROOT = REPO / "cache"
CARDS = ROOT / "cards"
OG = ROOT / "og"
for _d in (ROOT, CARDS, OG):
    _d.mkdir(parents=True, exist_ok=True)


def key(name: str, payload) -> str:
    """sha256 content key. Same inputs -> same file, always."""
    blob = name + "|" + json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _p(name: str) -> pathlib.Path:
    return ROOT / f"{name}.json"


def get(name: str):
    """Read cache/<name>.json. Returns None on any miss or corruption."""
    p = _p(name)
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    return None


def put(name: str, obj) -> None:
    p = _p(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


def get_bytes(rel: str) -> bytes | None:
    p = ROOT / rel
    try:
        if p.exists():
            return p.read_bytes()
    except Exception:
        return None
    return None


def put_bytes(rel: str, data: bytes) -> None:
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def age_seconds(name: str) -> float | None:
    p = _p(name)
    return (time.time() - p.stat().st_mtime) if p.exists() else None


def exists(name: str) -> bool:
    return _p(name).exists()
