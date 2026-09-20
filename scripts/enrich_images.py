"""Read the PICTURES in a fetched corpus, not just the words.

    python scripts/enrich_images.py labmuffin
    python scripts/enrich_images.py labmuffin --dry-run      # find images, call nothing
    python scripts/enrich_images.py labmuffin --force        # re-read every image
    python scripts/enrich_images.py labmuffin --max 8 --per-post 1

WHAT THIS IS, AND WHO DID WHAT
------------------------------
`scripts/fetch_corpus.py` gives us a real creator's real WORDS. That is only half of
what is on her page. This script re-opens each post she wrote, pulls the images that
were already in that page's HTML, and has **GPT-4o-mini** look at each one and return
**typed attributes** under a strict `json_schema` - the same technique as
`scripts/vision_to_jev.py`.

  * **GPT-4o-mini does the SEEING.** Every attribute in a `vision` block came out of
    that model. It is written into the file as `vision_model` so nothing downstream
    can imply otherwise.
  * **Jev does the JUDGING.** The typed attributes land in `state.public_profile`
    under `what_her_pictures_show` (backend/corpora.py) and Jev answers the same
    fourteen questions over them. Jev never sees a pixel.

That is the documented "an LLM writes, Jev decides, code acts" split, and we say it
rather than blur it.

RULES THIS SCRIPT HOLDS ITSELF TO
---------------------------------
1. **Prefetch only.** Nothing in `backend/` calls this. It runs by hand before the
   demo, exactly like `fetch_corpus.py`. A vision call on stage is a beat that can
   fail in front of judges.
2. **Never fabricate.** A fetch or a vision call that fails is written back as
   `"vision": null` with an `error` string. It is never filled in with a guess.
3. **Her images stay hers.** We keep the original `url` and reference it. Nothing is
   downloaded to disk and re-hosted; the bytes we fetch go to the model and are
   dropped.
4. **Idempotent and resumable.** An image that already has a `vision` block is
   skipped, and a post whose images are all done is not even re-fetched. Raw model
   responses are cached under `cache/vision/<sha1 of image url>.json`, so even
   `--force` re-reads from disk and costs nothing unless the cache is cold.
"""
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import pathlib
import re
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit

import httpx

try:
    from dotenv import load_dotenv
except ImportError:                                              # noqa: BLE001
    load_dotenv = None

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

REPO = pathlib.Path(__file__).resolve().parent.parent
DATA = REPO / "data"
VISION_CACHE = REPO / "cache" / "vision"

MODEL = "gpt-4o-mini"
UA = {"User-Agent": "tano-hackathon/1.0 (corpus image enrichment)"}

# Published list price for gpt-4o-mini at the time of writing, USD per 1M tokens.
# Only ever multiplied by usage numbers the API actually returned - we do not
# estimate token counts, we read them off the response.
USD_PER_M_IN = 0.15
USD_PER_M_OUT = 0.60

MIN_PX = 200            # anything smaller is furniture, not content
PER_POST = 2
MAX_TOTAL = 15
MAX_BYTES = 12 * 1024 * 1024

# Things that are on a page but are not the author's photographs.
JUNK = re.compile(
    r"(avatar|gravatar|logo|favicon|sprite|emoji|spacer|pixel|tracking|1x1|blank\."
    r"|placeholder|/ad[s]?[-_/]|share|button|badge|icon|feed-?burner|amazon-adsystem)",
    re.I)
RESIZE = re.compile(r"-\d{2,4}x\d{2,4}(?=\.[A-Za-z0-9]+$)")
IMG_EXT = re.compile(r"\.(jpe?g|png|webp|gif|avif)(\?|$)", re.I)
MIME = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
        "webp": "image/webp", "gif": "image/gif", "avif": "image/avif"}

# ---------------------------------------------------------------- the schema
# Strict json_schema, same shape as scripts/vision_to_jev.py. Every field is
# something a human can settle by looking at the picture: that is the whole point.
# There is no "vibe" field and no free prose beyond text that is literally printed
# in the image.
SCHEMA = {
    "name": "post_image",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "shows": {
                "type": "string",
                "enum": ["product", "demo", "diagram", "chart", "person",
                         "packaging", "screenshot", "other"],
                "description": "The single best description of what the picture IS. "
                               "product = a product sitting there; demo = something "
                               "being done or applied; diagram = a drawn explanation; "
                               "chart = axes and data; person = a face or body is the "
                               "subject; packaging = a close read of a label or box; "
                               "screenshot = a capture of a screen or a document.",
            },
            "readable_text": {
                "type": "string",
                "description": "Text that is actually legible in the image, transcribed "
                               "verbatim. Empty string if there is none. Do not "
                               "summarise and do not invent text you cannot read.",
            },
            "products_named": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Brand or product names visible in the image. Empty array "
                               "if none are legible. Do not guess a brand from a shape.",
            },
            "is_instructional": {
                "type": "string",
                "enum": ["yes", "no", "unclear"],
                "description": "Does the image show someone HOW to do something - a step, "
                               "a hand applying, an arrow, a numbered stage?",
            },
            "is_comparison": {
                "type": "string",
                "enum": ["yes", "no", "unclear"],
                "description": "Does the image put two or more things side by side to be "
                               "compared - two products, two halves of a face, before "
                               "and after, two bars on a chart?",
            },
            "shows_a_result": {
                "type": "string",
                "enum": ["yes", "no", "unclear"],
                "description": "Does the image show the OUTCOME of a test or experiment - "
                               "a UV camera shot, a measurement, a stained or marked "
                               "surface, a graph of a result?",
            },
        },
        "required": ["shows", "readable_text", "products_named",
                     "is_instructional", "is_comparison", "shows_a_result"],
    },
}

PROMPT = ("This image was published inside a blog post by a cosmetic chemist. Fill in the "
          "schema from what is VISIBLE in the picture. Transcribe only text you can "
          "actually read; if you cannot read it, leave it out. Name only brands you can "
          "actually see written. Where the picture does not settle a yes/no field, answer "
          "'unclear' rather than guessing.")


# ---------------------------------------------------------------- image discovery
def _attrs(tag: str) -> dict:
    out = {}
    for m in re.finditer(r'([a-zA-Z_:][-\w:.]*)\s*=\s*("([^"]*)"|\'([^\']*)\'|([^\s"\'>]+))', tag):
        out[m.group(1).lower()] = html.unescape(m.group(3) or m.group(4) or m.group(5) or "")
    return out


def _int(v) -> int | None:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def dedupe_key(url: str) -> str:
    """WordPress serves the same photograph at a dozen sizes: `foo-600x337.jpg` and
    `foo.jpg` are one picture, and og:image is usually the full-size twin of the first
    in-article image. Strip the `-WxH` suffix so we do not pay to look at it twice."""
    p = urlsplit(url)
    return (p.netloc + RESIZE.sub("", p.path)).lower()


def find_images(page_url: str, timeout: float = 40.0) -> tuple[list, str | None]:
    """-> (candidates, error). Every candidate is an image ALREADY in that page's HTML.

    og:image first (it is the picture she chose to represent the post), then in-article
    `<img>` tags in document order. Skips lazy-load `data:` placeholders, anything
    under MIN_PX in either dimension, and anything whose URL says it is furniture.
    """
    try:
        r = httpx.get(page_url, timeout=timeout, follow_redirects=True, headers=UA)
        r.raise_for_status()
    except Exception as e:                                       # noqa: BLE001
        return [], "%s: %s" % (type(e).__name__, str(e)[:160])

    doc = r.text
    # script/style only. NOT <noscript>: a lazy-loading plugin (perfmatters, here)
    # puts an inline SVG placeholder in the real <img> and the ACTUAL photograph in
    # the <noscript> twin. Strip it and the article looks like it has one picture.
    doc = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", doc)
    out: list[dict] = []
    seen: set = set()

    def add(url, w, h, alt, where):
        if not url or url.startswith("data:"):
            return
        url = urljoin(page_url, html.unescape(url).strip())
        if not url.startswith(("http://", "https://")) or not IMG_EXT.search(url):
            return
        if JUNK.search(url):
            return
        if (w is not None and w < MIN_PX) or (h is not None and h < MIN_PX):
            return
        k = dedupe_key(url)
        if k in seen:
            return
        seen.add(k)
        out.append({"url": url, "width_hint": w, "height_hint": h,
                    "alt": (alt or "").strip()[:200] or None, "found_in": where})

    # --- og:image (+ its declared size, when the page states one)
    def meta_of(prop):
        m = re.search(r'<meta[^>]+(?:property|name)=["\']%s["\'][^>]*>' % re.escape(prop), doc, re.I)
        if not m:
            m = re.search(r'<meta[^>]+content=["\'][^"\']*["\'][^>]*(?:property|name)=["\']%s["\'][^>]*>'
                          % re.escape(prop), doc, re.I)
        return _attrs(m.group(0)).get("content") if m else None

    og = meta_of("og:image")
    if og:
        add(og, _int(meta_of("og:image:width")), _int(meta_of("og:image:height")),
            meta_of("og:image:alt"), "og:image")

    # --- in-article <img>. Same body-finding heuristic as fetch_corpus.fetch_body,
    #     so the pictures we read come from the same region as the text we read.
    body = re.search(r"(?is)<(article|main)[^>]*>(.*?)</\1>", doc)
    seg = body.group(2) if body else doc
    for m in re.finditer(r"(?is)<img[^>]*>", seg):
        a = _attrs(m.group(0))
        add(a.get("src") or a.get("data-src") or a.get("data-lazy-src"),
            _int(a.get("width")), _int(a.get("height")), a.get("alt"), "article")
    return out, None


def select(per_post: list[list], per_post_cap: int, total_cap: int) -> list[list]:
    """Round-robin, so every post contributes a picture before any post contributes two.

    Taking the first `per_post_cap` of each post in order would starve the last posts
    once the total cap bites, and the corpus would silently become "the first seven
    posts have pictures". This way the coverage is even and reportable.
    """
    picked: list[list] = [[] for _ in per_post]
    n = 0
    for rank in range(per_post_cap):
        for i, cands in enumerate(per_post):
            if n >= total_cap:
                return picked
            if rank < len(cands):
                picked[i].append(cands[rank])
                n += 1
    return picked


# ---------------------------------------------------------------- the vision call
def cache_path(url: str) -> pathlib.Path:
    return VISION_CACHE / (hashlib.sha1(url.encode("utf-8")).hexdigest() + ".json")


def look(url: str, api_key: str, force: bool = False) -> dict:
    """GPT-4o-mini reads ONE image. -> a cache record, never an exception.

    {"url", "model", "seen_at", "ok", "vision"|None, "error"|None, "usage", "bytes",
     "seconds", "from_cache"}

    A failure returns ok=False with the reason. It NEVER returns a guessed vision
    block: an image we could not read is an image we say we could not read.
    """
    p = cache_path(url)
    if p.exists() and not force:
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
            if rec.get("ok"):
                rec["from_cache"] = True
                return rec
        except Exception:                                        # noqa: BLE001
            pass

    t0 = time.perf_counter()
    rec = {"url": url, "model": MODEL,
           "seen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "ok": False, "vision": None, "error": None, "usage": None,
           "bytes": None, "seconds": None, "from_cache": False}
    try:
        ir = httpx.get(url, headers=UA, follow_redirects=True, timeout=60)
        ir.raise_for_status()
        blob = ir.content
        if not blob:
            raise ValueError("empty image body")
        if len(blob) > MAX_BYTES:
            raise ValueError("image is %dKB, over the %dKB cap" % (len(blob) // 1024,
                                                                   MAX_BYTES // 1024))
        rec["bytes"] = len(blob)
        ext = (urlsplit(url).path.rsplit(".", 1)[-1] or "jpeg").lower()
        mime = (ir.headers.get("content-type") or "").split(";")[0].strip()
        if not mime.startswith("image/"):
            mime = MIME.get(ext, "image/jpeg")
        data_url = "data:%s;base64,%s" % (mime, base64.b64encode(blob).decode())

        r = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": "Bearer " + api_key},
            timeout=120,
            json={"model": MODEL,
                  "messages": [{"role": "user", "content": [
                      {"type": "text", "text": PROMPT},
                      {"type": "image_url", "image_url": {"url": data_url}}]}],
                  "response_format": {"type": "json_schema", "json_schema": SCHEMA}})
        r.raise_for_status()
        body = r.json()
        rec["usage"] = body.get("usage")
        rec["vision"] = json.loads(body["choices"][0]["message"]["content"])
        rec["ok"] = True
    except Exception as e:                                       # noqa: BLE001
        rec["error"] = "%s: %s" % (type(e).__name__, str(e)[:200])
        rec["vision"] = None
        rec["ok"] = False
    rec["seconds"] = round(time.perf_counter() - t0, 2)

    VISION_CACHE.mkdir(parents=True, exist_ok=True)
    try:
        p.write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
    except Exception:                                            # noqa: BLE001
        pass
    return rec


def cost_usd(usage: dict | None) -> float:
    u = usage or {}
    return ((u.get("prompt_tokens") or 0) * USD_PER_M_IN
            + (u.get("completion_tokens") or 0) * USD_PER_M_OUT) / 1_000_000.0


# ---------------------------------------------------------------- main
def enrich(slug: str, force: bool = False, dry: bool = False,
           per_post_cap: int = PER_POST, total_cap: int = MAX_TOTAL) -> int:
    path = DATA / ("corpus-%s.json" % re.sub(r"[^a-z0-9\-]+", "", slug.lower()))
    if not path.exists():
        print("no such corpus: %s" % path)
        return 2
    corpus = json.loads(path.read_text(encoding="utf-8"))
    items = corpus.get("items") or []
    print("corpus %s  -  %d items, %d characters"
          % (path.name, len(items), sum(len(i.get("text") or "") for i in items)))
    print("vision model: %s   (it does the SEEING; Jev does the JUDGING, over these attributes)"
          % MODEL)
    print("-" * 78)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key and not dry:
        print("OPENAI_API_KEY is not set (put it in .env). Nothing was called.")
        return 2

    wall0 = time.perf_counter()

    # --- 1. discovery. A post whose images are all already read is not re-fetched:
    #        that is what makes a second run free AND fast, not just free.
    per_post: list[list] = []
    fetch_fail = 0
    reused_posts = 0
    for it in items:
        have = it.get("images") or []
        if have and not force and all(im.get("vision") for im in have):
            per_post.append([])          # nothing to discover, nothing to pay for
            reused_posts += 1
            print("  = %-62s %d image(s) already read" % ((it.get("url") or "?")[-62:], len(have)))
            continue
        url = it.get("url")
        if not url:
            per_post.append([])
            continue
        cands, err = find_images(url)
        if err:
            fetch_fail += 1
            print("  ! %-62s page fetch failed: %s" % (url[-62:], err))
            it["image_fetch_error"] = err
        else:
            it.pop("image_fetch_error", None)
            print("  + %-62s %2d candidate(s)" % (url[-62:], len(cands)))
        per_post.append(cands)

    chosen = select(per_post, per_post_cap, total_cap)
    found = sum(len(c) for c in per_post)
    picked = sum(len(c) for c in chosen)
    print("-" * 78)
    print("found %d candidate image(s) across %d post(s); selected %d (cap %d/post, %d total)"
          % (found, sum(1 for c in per_post if c), picked, per_post_cap, total_cap))
    if reused_posts:
        print("%d post(s) skipped entirely - every image already has a vision block" % reused_posts)
    if dry:
        for i, cands in enumerate(chosen):
            for c in cands:
                print("  would read  %s  (%sx%s, %s)"
                      % (c["url"], c["width_hint"], c["height_hint"], c["found_in"]))
        print("--dry-run: no vision calls made, nothing written.")
        return 0

    # --- 2. the vision pass
    enriched = failed = cached = 0
    usd = 0.0
    tin = tout = 0
    for idx, (it, cands) in enumerate(zip(items, chosen)):
        old = {im.get("url"): im for im in (it.get("images") or [])}
        keep: list = []
        # anything already read stays exactly as it is
        if not force:
            for im in (it.get("images") or []):
                if im.get("vision"):
                    keep.append(im)
        kept_urls = {im.get("url") for im in keep}
        for c in cands:
            if c["url"] in kept_urls:
                continue
            rec = look(c["url"], api_key, force=force)
            row = {"url": c["url"],
                   "width_hint": c.get("width_hint"),
                   "height_hint": c.get("height_hint"),
                   "alt": c.get("alt"),
                   "found_in": c.get("found_in"),
                   "source_page": it.get("url"),
                   "vision_model": MODEL,
                   "seen_at": rec.get("seen_at"),
                   "vision": rec.get("vision") if rec.get("ok") else None}
            if not rec.get("ok"):
                row["error"] = rec.get("error") or "unknown vision failure"
                failed += 1
                print("  x [%2d] %-56s %s" % (idx + 1, c["url"][-56:], row["error"][:60]))
            else:
                enriched += 1
                if rec.get("from_cache"):
                    cached += 1
                else:
                    usd += cost_usd(rec.get("usage"))
                    u = rec.get("usage") or {}
                    tin += u.get("prompt_tokens") or 0
                    tout += u.get("completion_tokens") or 0
                v = row["vision"] or {}
                print("  %s [%2d] %-52s %-10s text=%-4s products=%s"
                      % ("~" if rec.get("from_cache") else "*", idx + 1,
                         c["url"].rsplit("/", 1)[-1][:52], v.get("shows", "?"),
                         len(v.get("readable_text") or ""),
                         (v.get("products_named") or [])[:2]))
            keep.append(row)
        # an image that was there before and is not a candidate now is kept, not dropped
        for u_, im in old.items():
            if u_ not in {x.get("url") for x in keep}:
                keep.append(im)
        if keep:
            it["images"] = keep
        elif "images" in it:
            del it["images"]

    # --- 3. write back
    total_imgs = sum(len(it.get("images") or []) for it in items)
    with_vision = sum(1 for it in items for im in (it.get("images") or []) if im.get("vision"))
    corpus["image_count"] = with_vision
    corpus["image_candidate_count"] = total_imgs
    corpus["vision_model"] = MODEL
    # Only moves when a picture was actually read. A no-op re-run must leave the file
    # byte-identical, otherwise "it costs nothing" is true but "it did nothing" is not.
    if enriched - cached or failed or not corpus.get("vision_enriched_at"):
        corpus["vision_enriched_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    corpus["vision_note"] = (
        "The images are read by %s under a strict json_schema, not by Jev. Jev judges the "
        "extracted attributes. The pictures are %s's own, published on the site they were "
        "fetched from; we reference the original URL and do not re-host them. An image we "
        "could not read carries vision: null and an error, never a guess."
        % (MODEL, corpus.get("display_name") or corpus.get("handle") or "the author")
        if with_vision else
        "No image on this corpus carries a vision block.")
    corpus["vision_script"] = "scripts/enrich_images.py"
    path.write_text(json.dumps(corpus, indent=1, ensure_ascii=False), encoding="utf-8")

    wall = time.perf_counter() - wall0
    print("-" * 78)
    print("images found      : %d candidate(s) in this run" % found)
    print("images selected   : %d" % picked)
    print("images enriched   : %d  (%d fresh vision calls, %d served from cache/vision/)"
          % (enriched, enriched - cached, cached))
    print("images failed     : %d" % failed)
    print("pages unreachable : %d" % fetch_fail)
    print("tokens (fresh)    : %d in / %d out" % (tin, tout))
    print("cost estimate     : $%.4f  (%s list price, from the usage the API returned)"
          % (usd, MODEL))
    print("wall time         : %.1fs" % wall)
    print("corpus now        : image_count=%d, vision_model=%s"
          % (corpus["image_count"], corpus["vision_model"]))
    print("wrote %s" % path)
    return 0


def main(argv: list[str]) -> int:
    if load_dotenv:
        load_dotenv(REPO / ".env")
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2

    def opt(name, default):
        for i, a in enumerate(argv):
            if a == "--" + name and i + 1 < len(argv):
                return int(argv[i + 1])
            if a.startswith("--" + name + "="):
                return int(a.split("=", 1)[1])
        return default

    return enrich(args[0], force="--force" in argv, dry="--dry-run" in argv,
                  per_post_cap=opt("per-post", PER_POST), total_cap=opt("max", MAX_TOTAL))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
