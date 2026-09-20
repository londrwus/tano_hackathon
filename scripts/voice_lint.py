"""Scan our copy for the tells that make writing read as machine-written.

    python scripts/voice_lint.py            # everything that ships
    python scripts/voice_lint.py --fix      # auto-fix only the safe ones (dashes, spacing)
    python scripts/voice_lint.py --docs     # include docs/ and README

Rules come from .claude/skills/maya-voice/SKILL.md, which is grounded in her real
sentences in data/case-001-maya.json: "Non-negotiable." / "Easy. No drama." /
"Good. Not GBP62 good." Two to five words. Full stops where a machine writes commas.
Not one em-dash anywhere.

Exit code is the number of BLOCKING hits, so it works as a pre-commit gate.
Her pet peeve in the case file is "generic automation" - a reply that reads as
machine-written fails the product no matter how good the recommendation inside it is.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

REPO = pathlib.Path(__file__).resolve().parent.parent

# (id, regex, message, blocking, auto-fixable)
RULES: list[tuple[str, str, str, bool, bool]] = [
    ("em-dash",    r"—",                       "em-dash. Use a full stop.",                       True,  True),
    ("en-dash",    r"(?<=\s)–(?=\s)",          "en-dash used as an aside. Use a full stop.",       True,  True),
    ("semicolon",  r";",                            "semicolon. She has never written one.",            True,  False),
    ("bang",       r"!",                            "exclamation mark. Dry, not perky.",                True,  False),
    ("ellipsis",   r"\.\.\.|…",                "trailing off. Finish the sentence or stop.",       False, False),
    ("not-just",   r"\bnot just\b[^.?!]{0,60}\bbut\b", "'not just X but Y'. Instant machine.",          True,  False),
    ("not-about",  r"\bit'?s not about\b",          "'it's not about X, it's about Y'.",                True,  False),
    ("whether",    r"\bwhether you'?re\b",          "'whether you're X or Y' opener.",                  True,  False),
    ("today",      r"\bin today'?s world\b|\bin a world where\b", "'in today's world'.",                True,  False),
    ("dive",       r"\b(let'?s )?dive in(to)?\b",   "'dive into'.",                                     True,  False),
    ("looking-to", r"^\s*looking to\b",             "'Looking to...' opener.",                          True,  False),
    ("hedge",      r"\b(can help|may help|tends to|might be worth|generally speaking|it'?s worth noting|that being said|at the end of the day)\b",
                   "hedging. She decides.",                                                             True,  False),
    ("llm-words",  r"\b(delve|seamless|robust|elevate|unlock|curated|bespoke|holistic|empower|transformative|game-?changer|nourish(ing)?|glow-boosting)\b",
                   "LLM vocabulary.",                                                                   True,  False),
    ("banned-product", r"\b(autonomous|chatbot|AI clone|judgments|confidence gate|fan-?out)\b",
                   "banned product word. Say her standard / calibrated / leverage.",                     True,  False),
    ("gbp-decimal", r"£\d+\.\d",               "decimal price. Never a decimal pound on screen.",  True,  False),
]

# Files whose *content* we ship to a human.
UI_GLOBS = ["frontend/src/**/*.tsx", "frontend/src/**/*.ts"]
DATA_FILES = ["cache/queue.json"] + [str(p.relative_to(REPO)) for p in sorted((REPO / "cache" / "cards").glob("*.json"))]
DOC_GLOBS = ["docs/07-demo-script.md", "docs/09-GO.md", "README.md"]

# Strings in code that are not user-facing.
CODE_NOISE = re.compile(
    r"^\s*(//|/\*|\*)|"                       # comments
    r"(import|export|from)\s|"                # module lines
    r"(className|classname|href|src|key|id|data-|aria-|type|role)=|"
    r"console\.|useEffect|useState|=>|\?\?|&&"
)
# JSON keys we grade; everything else in a card is machinery.
CARD_TEXT_KEYS = {"headline", "in_her_voice", "why", "instead", "line", "note", "band",
                  "provenance", "draft_reply", "question_back", "hold_reason", "text",
                  "basket_summary", "maya_note", "statement", "label"}


def hits(text: str) -> list[tuple[str, str]]:
    out = []
    for rid, pat, msg, blocking, _fix in RULES:
        if re.search(pat, text, re.I):
            out.append((rid, msg if blocking else "(warn) " + msg))
    return out


def walk_json(node, keys=CARD_TEXT_KEYS):
    """Yield (path, string) for every value under a text-bearing key."""
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str) and k in keys:
                yield k, v
            else:
                yield from walk_json(v, keys)
    elif isinstance(node, list):
        for i in node:
            yield from walk_json(i, keys)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="auto-fix dashes only")
    ap.add_argument("--docs", action="store_true", help="also scan docs and README")
    a = ap.parse_args(argv)

    blocking = warn = 0
    fixed_files = 0

    def report(where: str, line: str, found: list[tuple[str, str]]):
        nonlocal blocking, warn
        for rid, msg in found:
            if msg.startswith("(warn)"):
                warn += 1
            else:
                blocking += 1
            print("  %-22s %-13s %s" % (where[-22:], rid, msg))
            print("      %s" % line.strip()[:110])

    print("scanning UI strings")
    for g in UI_GLOBS:
        for p in sorted(REPO.glob(g)):
            src = p.read_text(encoding="utf-8", errors="replace")
            if a.fix:
                new = src.replace("—", ". ").replace(" – ", ". ")
                new = re.sub(r"\.\s+\.", ".", new)
                if new != src:
                    p.write_text(new, encoding="utf-8")
                    fixed_files += 1
                    src = new
            for n, line in enumerate(src.splitlines(), 1):
                if CODE_NOISE.search(line):
                    continue
                quoted = re.findall(r"['\"`]([^'\"`]{12,})['\"`]", line)
                for q in quoted:
                    found = hits(q)
                    if found:
                        report("%s:%d" % (p.name, n), q, found)

    print("scanning what the engine actually wrote")
    for rel in DATA_FILES:
        p = REPO / rel
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:                                        # noqa: BLE001
            continue
        for k, v in walk_json(data):
            found = hits(v)
            if found:
                report("%s[%s]" % (p.name, k), v, found)

    if a.docs:
        print("scanning docs")
        for g in DOC_GLOBS:
            for p in sorted(REPO.glob(g)):
                for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                    if line.lstrip().startswith(("|", ">", "`", "#")):
                        continue
                    found = [h for h in hits(line) if h[0] not in ("banned-product",)]
                    if found:
                        report("%s:%d" % (p.name, n), line, found)

    print()
    if a.fix:
        print("auto-fixed dashes in %d file(s)" % fixed_files)
    print("%d blocking, %d warning" % (blocking, warn))
    if blocking == 0:
        print("clean. It reads like her.")
    return min(blocking, 125)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
