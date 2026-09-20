"""The subjects the engine can extract a standard from.

A "subject" is anything that can be put in front of the SAME fourteen questions:

  * `maya`  - the case-pack creator. Her post *titles* are verbatim from the case
              pack; the caption bodies and the bio are OUR reconstruction. Not real.
  * `derm`  - the control. Twelve statements, every word written by us. Not real.
  * any `data/corpus-<slug>.json` - a REAL person's public writing, fetched once,
              by hand, before the demo (`scripts/fetch_corpus.py`). Verbatim.

Nothing in here talks to the network. `scripts/fetch_corpus.py` writes the files
and the backend only ever reads them: a live fetch on stage is a beat that can
fail in front of judges, and Instagram will fail (see scripts/probe_modal_ip.py).
The EXTRACTION is the part that runs live, and it is the part that is fast.

The point of this module is that a judge can tell, from the payload alone and
without reading any documentation, which subject is a real human being and which
is ours. That is what `provenance` and the per-item `verbatim` flag are for.

HER PICTURES, AND WHO READ THEM
-------------------------------
A corpus may also carry images, written in by `scripts/enrich_images.py` before the
demo. They are the pictures that were already in her own posts, referenced at their
original URLs - nothing is downloaded or re-hosted here or there.

**GPT-4o-mini did the seeing.** Every `vision` block is typed output from that model
under a strict `json_schema`. **Jev does the judging**, over those attributes, and it
never sees a pixel. `vision_model` rides along on the meta row, on every wire image
and inside `public_profile`, so no payload can imply otherwise.

They reach Jev as STRUCTURED DATA under `public_profile.what_her_pictures_show`, not
as prose. Prose measurably does not fire - docs/09-GO.md section 5, bug #3. Set
`CORPUS_IMAGES=0` in the environment to run the extraction without them, which is how
the with/without comparison is reproduced.
"""
from __future__ import annotations

import json
import os
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parent.parent
DATA = REPO / "data"

_CACHE: dict = {}

# The six typed fields scripts/enrich_images.py asks GPT-4o-mini for. Listed here so
# that whatever else ends up in a vision block, exactly these go to Jev - the judge
# state must not drift because the enrichment schema grew a field.
VISION_FIELDS = ("shows", "readable_text", "products_named",
                 "is_instructional", "is_comparison", "shows_a_result")


def images_enabled() -> bool:
    """False only if someone explicitly turned the pictures off, for the A/B."""
    return str(os.environ.get("CORPUS_IMAGES", "1")).strip().lower() not in ("0", "false", "no")


def slug_of(path: pathlib.Path) -> str:
    return re.sub(r"^corpus-", "", path.stem)


def paths() -> list:
    return sorted(DATA.glob("corpus-*.json"))


def slugs() -> list:
    return [slug_of(p) for p in paths()]


def load(slug: str) -> dict | None:
    """Read data/corpus-<slug>.json. None on any miss or corruption - never raises."""
    slug = re.sub(r"[^a-z0-9\-]+", "", str(slug or "").lower())
    if not slug:
        return None
    if slug in _CACHE:
        return _CACHE[slug]
    p = DATA / ("corpus-%s.json" % slug)
    if not p.exists():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except Exception:                                            # noqa: BLE001
        return None
    if not isinstance(raw, dict) or not isinstance(raw.get("items"), list):
        return None
    raw = dict(raw)
    raw["slug"] = slug
    raw["path"] = "data/" + p.name
    _CACHE[slug] = raw
    return raw


def char_count(c: dict) -> int:
    return sum(len(str(i.get("text") or "")) for i in (c.get("items") or []))


def all_images(c: dict) -> list:
    """Every image on the corpus, read or not, paired with the post it was in.

    An image whose fetch or vision call failed is still here, with `vision` None and
    an `error`. It is not hidden: "we found fourteen pictures and could read twelve"
    is the truth, and it is a more interesting sentence than a silent twelve.
    """
    out = []
    for it in (c.get("items") or []):
        for im in (it.get("images") or []):
            if not isinstance(im, dict) or not im.get("url"):
                continue
            row = dict(im)
            row.setdefault("source_page", it.get("url"))
            out.append(row)
    return out


def image_count(c: dict) -> int:
    """How many of her pictures we actually READ. Not how many we found."""
    return sum(1 for im in all_images(c) if im.get("vision"))


def wire_images(it: dict, c: dict) -> list:
    """One post's images as they go on the wire.

    The original URL, never a copy: these are a real person's photographs on her own
    server and we reference them where they live. `vision_model` is on every row so a
    thumbnail in the UI can say who read it without the frontend having to know.
    """
    out = []
    for im in (it.get("images") or []):
        if not isinstance(im, dict) or not im.get("url"):
            continue
        v = im.get("vision")
        row = {
            "url": im.get("url"),
            "width_hint": im.get("width_hint"),
            "height_hint": im.get("height_hint"),
            "alt": im.get("alt"),
            "found_in": im.get("found_in"),
            "source_page": im.get("source_page") or it.get("url"),
            "vision_model": im.get("vision_model") or c.get("vision_model"),
            "read_by": "gpt-4o-mini vision, under a strict json_schema. Not Jev - Jev "
                       "judges these attributes, it does not see the picture.",
            "seen_at": im.get("seen_at"),
            "vision": {k: v.get(k) for k in VISION_FIELDS} if isinstance(v, dict) else None,
        }
        if not row["vision"]:
            row["error"] = im.get("error") or "not read"
        out.append(row)
    return out


def provenance(c: dict) -> str:
    """One sentence a judge can read off the screen. Real means real."""
    where = c.get("source_url") or c.get("source") or "an unrecorded source"
    when = str(c.get("fetched_at") or "")[:10] or "an unrecorded date"
    if c.get("verbatim"):
        cut = (" Excerpted to a couple of hundred characters a post: her copyright, not ours "
               "to republish. Every character shown is still hers." if c.get("excerpted") else "")
        return ("Real. Her own public writing, verbatim, fetched from %s on %s. "
                "Not written by us.%s" % (where, when, cut))
    return ("Fetched from %s on %s, but not marked verbatim - treat it as "
            "paraphrase, not as her words." % (where, when))


def meta(c: dict) -> dict:
    """The row /api/creators returns for a fetched corpus."""
    return {
        "slug": c.get("slug"),
        "handle": c.get("handle"),
        "display_name": c.get("display_name") or c.get("handle"),
        "what_she_is": c.get("what_she_is"),
        "source": c.get("source"),
        "source_url": c.get("source_url"),
        "fetched_at": c.get("fetched_at"),
        "item_count": int(c.get("item_count") or len(c.get("items") or [])),
        "char_count": char_count(c),
        "why_this_creator": c.get("why_this_creator"),
        "cleaning_note": c.get("cleaning_note"),
        "verbatim": bool(c.get("verbatim")),
        "excerpted": bool(c.get("excerpted")),
        # `real` is about the PERSON and where the words came from, not about how much
        # of the text we are allowed to republish. Truncating her posts for copyright
        # does not turn a real cosmetic chemist into a fictional one. Deriving this from
        # `verbatim` alone once made /api/creators report real_count 0 on the deployed
        # site, which flatly contradicted the thing the page was built to demonstrate.
        "real": bool(c.get("verbatim")) and bool(c.get("source_url")),
        "provenance": provenance(c),
        "corpus_file": c.get("path"),
        # her pictures. `image_count` is the number we READ, which is the number the
        # UI is allowed to say out loud; `image_candidate_count` is what we selected.
        "image_count": image_count(c),
        "image_candidate_count": len(all_images(c)),
        "vision_model": c.get("vision_model"),
        "vision_enriched_at": c.get("vision_enriched_at"),
        "vision_note": c.get("vision_note"),
        "images_in_state": bool(images_enabled() and image_count(c)),
    }


def wire_items(c: dict) -> list:
    """The corpus as it goes on the wire: every item says where it came from.

    `verbatim` is per item and it is the flag that matters. `evidence_ref` is None
    because a fetched post has no case-pack reference - there is no case pack.
    """
    url = c.get("source_url")
    when = c.get("fetched_at")
    out = []
    for i, it in enumerate(c.get("items") or []):
        text = str(it.get("text") or "")
        out.append({
            "id": "%s-%02d" % (c.get("slug") or "item", i + 1),
            "text": text,
            "kind": it.get("kind") or "post",
            "evidence_ref": None,
            "verbatim": bool(c.get("verbatim")),
            "source_url": it.get("url") or url,
            "published": it.get("date"),
            "fetched_at": when,
            "chars": len(text),
            "images": wire_images(it, c),
        })
    return out


def picture_state(c: dict) -> list:
    """`public_profile.what_her_pictures_show` - typed rows, one per picture we read.

    STRUCTURED, not prose, and that is not a style preference: routing written as
    prose measurably did not fire (docs/09-GO.md section 5, bug #3). Every value here
    came out of GPT-4o-mini under a strict schema and every one of them is something a
    human can settle by opening `image_url` and looking.

    Unread images are left out of the judge state - there is nothing typed to judge -
    but they stay on the wire, with their error, in `wire_images`.
    """
    rows = []
    for im in all_images(c):
        v = im.get("vision")
        if not isinstance(v, dict):
            continue
        row = {k: v.get(k) for k in VISION_FIELDS}
        row["image_url"] = im.get("url")
        row["in_post"] = im.get("source_page")
        rows.append(row)
    return rows


def profile_state(c: dict, images: bool | None = None) -> dict:
    """What goes into `state.public_profile`. Her words, once, unpadded.

    Deliberately the same SHAPE as EXTRACT_SCRAPED (handle / bio / posts) so the
    fourteen questions are asked of the same kind of object in both cases. The
    text is not duplicated into a second key - it is ~57k characters and paying
    for it twice would inflate the token count we then put on screen.

    `what_her_pictures_show` is added only when the corpus actually has pictures we
    read. It is additive: her captions are byte-identical with and without it, so the
    with/without comparison isolates the images and nothing else. Pass images=False,
    or set CORPUS_IMAGES=0, to run the without side.
    """
    if images is None:
        images = images_enabled()
    state = {
        "handle": c.get("handle"),
        "bio": c.get("what_she_is") or "",
        "posts": [{"caption": str(it.get("text") or ""),
                   "published": it.get("date"),
                   "url": it.get("url")}
                  for it in (c.get("items") or []) if str(it.get("text") or "").strip()],
    }
    if images:
        pics = picture_state(c)
        if pics:
            state["what_her_pictures_show"] = pics
            # who saw them. A scalar, not a paragraph, and it is here so that nothing
            # in this state can be read as Jev having looked at a photograph.
            state["pictures_read_by"] = (c.get("vision_model") or "an image model") + \
                                        " (vision), not the judge answering these questions"
    return state


def all_meta() -> list:
    out = []
    for p in paths():
        c = load(slug_of(p))
        if c:
            out.append(meta(c))
    return out
