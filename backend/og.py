"""1080x1350 PNG share image. Dark dossier look.

page #0a0a08 / sheet #131311 / cream #f4f2e9 / stamp red #d03b3b.
Monospace ref code top-left, letter-spaced uppercase chrome, the verdict headline
large in a plain sans. It has to read as a thumbnail in an iMessage bubble, so the
headline is the only thing allowed to be big.
"""
from __future__ import annotations

import io
import pathlib

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
PAGE = (10, 10, 8)
SHEET = (19, 19, 17)
CREAM = (244, 242, 233)
DIM = (150, 147, 136)
FAINT = (74, 72, 66)
RED = (208, 59, 59)
RULE = (48, 47, 43)

_FONT_DIRS = [pathlib.Path("C:/Windows/Fonts"), pathlib.Path("/usr/share/fonts")]
_SANS = ["segoeui.ttf", "SegoeUI.ttf", "arial.ttf", "DejaVuSans.ttf"]
_SANS_B = ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"]
_MONO = ["consola.ttf", "cour.ttf", "DejaVuSansMono.ttf"]
_cache: dict = {}


def _find(names):
    for d in _FONT_DIRS:
        for n in names:
            p = d / n
            if p.exists():
                return str(p)
    return None


def font(kind: str, size: int):
    k = (kind, size)
    if k in _cache:
        return _cache[k]
    path = _find({"sans": _SANS, "bold": _SANS_B, "mono": _MONO}[kind])
    try:
        f = ImageFont.truetype(path, size) if path else ImageFont.load_default()
    except Exception:
        f = ImageFont.load_default()
    _cache[k] = f
    return f


def _tracked(d: ImageDraw.ImageDraw, xy, text: str, f, fill, track: int = 4):
    """Letter-spaced uppercase chrome. Pillow has no tracking, so we walk it."""
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + track
    return x


def _wrap(d, text: str, f, max_w: int, max_lines: int = 4) -> list:
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
            if len(lines) == max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and words:
        joined = " ".join(lines)
        if len(joined) < len(text) - 1:
            while lines and d.textlength(lines[-1] + " ...", font=f) > max_w:
                lines[-1] = lines[-1].rsplit(" ", 1)[0]
            lines[-1] = lines[-1] + " ..."
    return lines


def render(card: dict) -> bytes:
    img = Image.new("RGB", (W, H), PAGE)
    d = ImageDraw.Draw(img)

    M = 64
    d.rectangle([M - 24, M - 24, W - M + 24, H - M + 24], fill=SHEET)

    f_mono = font("mono", 26)
    f_chrome = font("mono", 22)
    f_head = font("bold", 92)
    f_head_s = font("bold", 68)
    f_body = font("sans", 34)
    f_small = font("sans", 28)
    f_tiny = font("sans", 24)

    ref = (card.get("asker") or {}).get("name") or "@someone"
    cid = str(card.get("card_id", "c-000000")).upper()
    d.text((M, M), cid, font=f_mono, fill=RED)
    _tracked(d, (M, M + 40), "MAYA RAO / HER STANDARD", f_chrome, DIM, 5)

    y = M + 110
    d.line([M, y, W - M, y], fill=RULE, width=2)

    # who asked
    y += 34
    _tracked(d, (M, y), "ASKED BY", f_chrome, FAINT, 5)
    y += 38
    d.text((M, y), str(ref), font=f_body, fill=CREAM)
    y += 50
    said = (card.get("asker") or {}).get("said") or ""
    if said:
        for ln in _wrap(d, '"' + said + '"', f_small, W - 2 * M, 2):
            d.text((M, y), ln, font=f_small, fill=DIM)
            y += 38

    # the verdict - the only big thing on the sheet
    y += 34
    d.line([M, y, W - M, y], fill=RULE, width=2)
    y += 46
    head = (card.get("verdict") or {}).get("headline") or ""
    fh = f_head if len(head) <= 22 else f_head_s
    lines = _wrap(d, head, fh, W - 2 * M, 3)
    for ln in lines:
        d.text((M, y), ln, font=fh, fill=CREAM)
        y += int(fh.size * 1.12)

    voice = (card.get("verdict") or {}).get("in_her_voice") or ""
    if voice and voice != head:
        y += 12
        for ln in _wrap(d, voice, f_body, W - 2 * M, 2):
            d.text((M, y), ln, font=f_body, fill=DIM)
            y += 44

    if (card.get("verdict") or {}).get("is_refusal"):
        bw, bh = 168, 52
        bx, by = W - M - bw, M
        d.rectangle([bx, by, bx + bw, by + bh], outline=RED, width=3)
        _tracked(d, (bx + 20, by + 14), "REFUSED", font("mono", 22), RED, 4)

    # the basket
    y += 40
    d.line([M, y, W - M, y], fill=RULE, width=2)
    y += 34
    _tracked(d, (M, y), "WHAT SHE SENDS", f_chrome, FAINT, 5)
    y += 46
    for item in (card.get("basket") or [])[:4]:
        d.text((M, y), str(item.get("product", "")), font=f_body, fill=CREAM)
        pr = str(item.get("price", ""))
        d.text((W - M - d.textlength(pr, font=f_body), y), pr, font=f_body, fill=CREAM)
        y += 44
        why = str(item.get("why", ""))
        if why:
            for ln in _wrap(d, why, f_tiny, W - 2 * M - 160, 1):
                d.text((M, y), ln, font=f_tiny, fill=FAINT)
                y += 32
        y += 10
    if not (card.get("basket") or []):
        d.text((M, y), "Nothing.", font=f_body, fill=CREAM)
        y += 54

    total = str(card.get("total", ""))
    y += 14
    _tracked(d, (M, y + 22), "TOTAL", f_chrome, FAINT, 5)
    d.text((W - M - d.textlength(total, font=f_head_s), y), total, font=f_head_s, fill=CREAM)
    y += 92

    # left out - only what fits above the footer; the sheet never overflows
    FOOTER_TOP = H - M - 122
    ROW_H = 36 + 30 + 30 + 8
    lo = card.get("left_out") or []
    room = int((FOOTER_TOP - (y + 72)) // ROW_H)
    lo = lo[:max(0, min(2, room))]
    if lo:
        d.line([M, y, W - M, y], fill=RULE, width=2)
        y += 30
        _tracked(d, (M, y), "LEFT OUT", f_chrome, FAINT, 5)
        y += 42
        for it in lo:
            d.text((M, y), str(it.get("product", "")) + "  " + str(it.get("price", "")),
                   font=f_small, fill=RED)
            y += 36
            for ln in _wrap(d, str(it.get("why", "")), f_tiny, W - 2 * M, 1):
                d.text((M, y), ln, font=f_tiny, fill=DIM)
                y += 30
            for ln in _wrap(d, "Instead: " + str(it.get("instead", "")), f_tiny, W - 2 * M, 1):
                d.text((M, y), ln, font=f_tiny, fill=FAINT)
                y += 30
            y += 8

    # footer chrome: unspent + ceiling
    fy = H - M - 96
    d.line([M, fy - 26, W - M, fy - 26], fill=RULE, width=2)
    uns = (card.get("unspent") or {}).get("line") or ""
    for ln in _wrap(d, uns, f_small, W - 2 * M, 1):
        d.text((M, fy), ln, font=f_small, fill=CREAM)
    cl = (card.get("ceiling") or {}).get("band") or ""
    if cl:
        _tracked(d, (M, fy + 46), ("HER LINE " + cl).upper(), f_chrome, FAINT, 5)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_to_cache(card: dict) -> bytes:
    from . import cache
    data = render(card)
    cache.put_bytes("og/" + str(card["card_id"]) + ".png", data)
    return data
