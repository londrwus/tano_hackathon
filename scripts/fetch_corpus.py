"""Fetch a real creator's public writing into a corpus file the engine can read.

    python scripts/fetch_corpus.py instagram <handle>
    python scripts/fetch_corpus.py rss https://someone.substack.com/feed
    python scripts/fetch_corpus.py paste <handle> < captions.txt

Every source writes the SAME shape to data/corpus-<slug>.json, so the extraction
pipeline does not know or care where the text came from:

    {"handle": "...", "source": "instagram|rss|paste", "fetched_at": "...",
     "verbatim": true, "items": [{"text": "...", "kind": "caption|post|bio",
                                  "date": "...", "url": "..."}]}

WHY THIS EXISTS, AND WHY IT IS NOT CALLED AT REQUEST TIME
---------------------------------------------------------
This runs BEFORE the demo, by hand, and writes a file. Nothing in backend/ ever
calls it. A live fetch on stage is a beat that can fail in front of judges, and
Instagram in particular will fail: measured on this machine 2026-09-20, a
logged-out profile lookup returned HTTP 429 on the FIRST request, with an
11-minute backoff. Assume it will not work and treat a success as a bonus.

`rss` and `paste` have no such problem and are the reliable paths.

THE SECOND HALF: HER PICTURES
-----------------------------
This script fetches WORDS only. The images that were in the same posts are read by a
separate prefetch, `scripts/enrich_images.py`, which re-opens each item's `url`, pulls
the images already in that page's HTML, and has **GPT-4o-mini** return typed attributes
under a strict `json_schema`:

    python scripts/fetch_corpus.py rss https://labmuffin.com/feed/ --full
    python scripts/enrich_images.py labmuffin

It writes `images` back onto each item plus `image_count` / `vision_model` /
`vision_enriched_at` on the corpus, and `backend/corpora.py` puts those attributes into
`state.public_profile` as structured data. GPT-4o-mini does the SEEING; Jev does the
JUDGING and never sees a pixel. Both scripts are prefetch: nothing in `backend/` calls
either of them. `docs/10-API-CONTRACT.md` section 15.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

REPO = pathlib.Path(__file__).resolve().parent.parent
OUT = REPO / "data"
MAX_ITEMS = 40

# How much of one post we keep, and it was MEASURED, not guessed. It was 6,000, which
# put Michelle Wong's ten posts at 57,015 characters and 22,832 input tokens for one
# extraction - three times what Maya's whole corpus costs, for the same fourteen
# answers. Her standard comes out of HOW she writes, so the question is how much of a
# post that takes. Four live extractions, same fourteen questions, same control:
#
#   cap     chars   input_tokens   price_refusal (subject side)
#   full    57,015     22,832      0.72 / 0.66  "Mentions price occasionally"
#   4,000   38,888     18,683      0.52         "Mentions price occasionally"
#   3,000   29,137     16,473      0.55         "Mentions price occasionally"
#   1,500   14,972     13,212      0.45         "Never talks about price"   <-- FLIPPED
#
# 1,500 was too far. `price_refusal` is the one slot anybody would quote about her -
# "science-led rather than price-led, which is the interesting part" is why she is in
# this repo at all - and at 1,500 it crosses the 0.5 line and changes level. At 3,000
# every one of the fourteen slots comes back at the same level as the full corpus.
#
# The two slots that DO differ from the frozen file at 3,000 (interchangeable_category,
# skippable_category) differ from it in the full-corpus control run as well, so that is
# Jev's own run-to-run variation on a short-corpus subject and not the cap. Only compare
# a capped run against a full run made the same day; the frozen file is not a control.
#
# Raise it if a future corpus needs it, and re-extract and diff the slots before you do.
MAX_CHARS_PER_ITEM = 3000


def cap_text(t: str, cap: int = MAX_CHARS_PER_ITEM) -> str:
    """First `cap` characters, cut at a sentence end so a post never stops
    mid-word. See MAX_CHARS_PER_ITEM for why the cap is where it is."""
    t = (t or "").strip()
    if len(t) <= cap:
        return t
    cut = t[:cap]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    if end > cap * 0.7:
        return cut[:end + 1].rstrip()
    sp = cut.rfind(" ")
    return (cut[:sp] if sp > cap * 0.7 else cut).rstrip()


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60] or "corpus"


def write(handle: str, source: str, items: list[dict], verbatim: bool = True) -> pathlib.Path:
    items = [i for i in items if (i.get("text") or "").strip()][:MAX_ITEMS]
    for i in items:
        i["text"] = cap_text(i["text"])
    if not items:
        raise SystemExit("nothing to write - no non-empty items")
    path = OUT / ("corpus-%s.json" % slugify(handle))
    path.write_text(json.dumps({
        "handle": handle,
        "source": source,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "verbatim": verbatim,
        "item_count": len(items),
        "items": items,
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    chars = sum(len(i["text"]) for i in items)
    print("wrote %s  -  %d items, %d characters, source=%s" % (path, len(items), chars, source))
    return path


# ------------------------------------------------------------------ instagram
def from_instagram(handle: str, want: int = 15, patience_s: int = 2400) -> list[dict]:
    """Logged-out, best effort, patient. Expect 429. Do NOT run this twice in a row."""
    import instaloader

    L = instaloader.Instaloader(quiet=True, download_pictures=False, download_videos=False,
                               download_comments=False, save_metadata=False,
                               max_connection_attempts=1)
    handle = handle.lstrip("@")
    deadline = time.time() + patience_s
    delay = 60
    while True:
        try:
            profile = instaloader.Profile.from_username(L.context, handle)
            items = [{"text": profile.biography or "", "kind": "bio", "date": None, "url": None}]
            for post in profile.get_posts():
                if len(items) > want:
                    break
                items.append({"text": post.caption or "", "kind": "caption",
                              "date": post.date_utc.date().isoformat(),
                              "url": "https://www.instagram.com/p/%s/" % post.shortcode})
            return items
        except Exception as e:                                   # noqa: BLE001
            name = type(e).__name__
            if time.time() > deadline:
                raise SystemExit(
                    "instagram fetch gave up after %ds: %s: %s\n"
                    "This is expected. Use `rss` or `paste` instead." % (patience_s, name, str(e)[:200]))
            print("  %s - retrying in %ds (%ds of patience left)"
                  % (name, delay, int(deadline - time.time())), flush=True)
            time.sleep(delay)
            delay = min(delay * 2, 600)


# ------------------------------------------------------------------ rss / atom
class _Strip(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out: list[str] = []

    def handle_data(self, d):
        self.out.append(d)


def _text(html: str) -> str:
    p = _Strip()
    p.feed(html or "")
    return re.sub(r"\s+", " ", "".join(p.out)).strip()


def fetch_body(url: str) -> str:
    """Follow an item's link and pull the readable article text.

    Feeds usually carry a one-paragraph summary, which is far too thin to extract a
    standard from - Maya's corpus is ~30k characters and a summary-only feed gives ~4k.
    This is a deliberately dumb extractor: strip script/style, take the text, collapse
    whitespace. It does not need to be clever, it needs to be reliable and offline-safe.
    """
    import httpx

    try:
        r = httpx.get(url, timeout=30, follow_redirects=True,
                      headers={"User-Agent": "tano-hackathon/1.0 (corpus fetch)"})
        r.raise_for_status()
    except Exception:                                            # noqa: BLE001
        return ""
    html = r.text
    html = re.sub(r"(?is)<(script|style|nav|footer|header|aside)[^>]*>.*?</\1>", " ", html)
    body = re.search(r"(?is)<(article|main)[^>]*>(.*?)</\1>", html)
    return _text(body.group(2) if body else html)[:MAX_CHARS_PER_ITEM]


def from_rss(url: str, want: int = 25, full: bool = False) -> list[dict]:
    """Any RSS or Atom feed. Substack, Ghost, Medium, WordPress, a blog. Never rate-limited."""
    import xml.etree.ElementTree as ET

    import httpx

    r = httpx.get(url, timeout=45, follow_redirects=True,
                  headers={"User-Agent": "tano-hackathon/1.0 (corpus fetch)"})
    r.raise_for_status()
    root = ET.fromstring(r.content)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    items: list[dict] = []
    for node in root.iter():
        tag = node.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        def pick(*names):
            for n in names:
                el = node.find(n) if "}" not in n else node.find(n, ns)
                if el is None:
                    el = node.find("a:" + n, ns)
                if el is not None and (el.text or "").strip():
                    return el.text
            return ""
        title = _text(pick("title"))
        body = _text(pick("description", "summary", "content"))
        link = _text(pick("link")) or None
        if not link:
            el = node.find("a:link", ns)
            link = el.get("href") if el is not None else None
        if full and link:
            deep = fetch_body(link)
            if len(deep) > len(body):
                body = deep
            print("  + %-58s %5d chars" % (title[:58], len(body)), flush=True)
        blob = (title + ". " + body).strip(". ").strip()
        if blob:
            items.append({"text": cap_text(blob), "kind": "post",
                          "date": _text(pick("pubDate", "updated", "published"))[:32] or None,
                          "url": link})
        if len(items) >= want:
            break
    return items


# ------------------------------------------------------------------ paste
def from_paste(handle: str) -> list[dict]:
    """Read captions from stdin, one per line (blank lines ignored). Always works."""
    print("paste captions, one per line, then Ctrl-Z + Enter (Windows) / Ctrl-D (unix):",
          file=sys.stderr)
    return [{"text": ln.strip(), "kind": "caption", "date": None, "url": None}
            for ln in sys.stdin.read().splitlines() if ln.strip()]


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    mode, target = argv[0], argv[1]
    if mode == "instagram":
        items = from_instagram(target, patience_s=int(argv[2]) if len(argv) > 2 else 2400)
    elif mode == "rss":
        items = from_rss(target, full="--full" in argv)
    elif mode == "paste":
        items = from_paste(target)
    else:
        print("unknown mode %r - use instagram | rss | paste" % mode)
        return 2
    write(target, mode, items)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
