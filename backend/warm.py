"""python -m backend.warm

Regenerates the whole frozen demo cache: the standard, the queue (raw judgments
and the assembled payload), the four frozen cards and their share images.
Run it before the demo. If the venue wifi dies at 19:44 the demo still runs, and
it is still honest, because these are real judgments we really computed.
"""
from __future__ import annotations

import asyncio
import sys
import time

from . import cache, cards, engine as E, og
from .jev import JEV, JevUnavailable

# A Windows console defaults to a legacy codepage (cp1251 on this machine) and every
# line we print carries a £. Without this the warm crashes half way through, after the
# standard and the queue have been written but before the cards - which looks like a
# cache that warmed fine and is not. Do this before anything prints.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


async def main(argv=None) -> int:
    argv = argv or []
    only = set(a for a in argv if not a.startswith("-"))
    t_all = time.perf_counter()
    print("warming cache at", cache.ROOT)
    if not JEV.configured:
        print("  !! JEV_API_KEY is not set. Nothing live can be computed.")
        return 2

    # 1 + 1b. ONE extraction of Maya, read twice -------------------------
    # The standard and the extraction replay are the same measurement: the same
    # fourteen typed slots, the same two judges, the same two requests. This used to
    # run twice - `extract_standard_live()` against the legacy six slots for the
    # standard, then `extract_live()` against the fourteen for the replay - and the
    # six-slot pair was discarded in full, because data/standard-extracted.json is
    # the source of truth for every slot it carries and it carries all fourteen.
    # Two requests, ~8k input tokens, every byte thrown away. Now: one extraction.
    #
    # The replay keeps the per-REQUEST timings and token counts so the frontend can
    # draw the fan-out honestly. There is no per-slot arrival time in here and there
    # must never be one: Jev answers all fourteen in one response, and the reveal in
    # the browser is a replay.
    st = None
    if not only or "standard" in only or "extract" in only:
        t = time.perf_counter()
        try:
            ex = await E.extract_live()
            if not only or "extract" in only:
                cache.put("extract", ex)
            tt = ex["totals"]
            print("  extract    %5.2fs  %d questions, %d requests, %d input tokens, agree %d / disagree %d"
                  " (step took %.2fs incl. client setup)"
                  % (tt["seconds"], tt["questions"], tt["requests"], tt["input_tokens"],
                     tt["agree"], tt["disagree"], time.perf_counter() - t))
            for r in ex["requests"]:
                print("             %-5s fired at +%dms, back in %dms, %d questions, %d input tokens"
                      % (r["judge"], r["at_ms"], r["ms"], r["question_count"], r["input_tokens"]))
            if not only or "standard" in only:
                maya, derm, secs = E.standard_sides_from_extract(ex)
                st = E.build_standard(maya, derm, secs, True, E.load_standard_file())
                cache.put("standard", st)
                print("  standard   %5.2fs  %d slots, agree %d / disagree %d  (no extra "
                      "requests - read off the extraction above)"
                      % (time.perf_counter() - t, st["slot_count"], st["agree_count"],
                         st["disagree_count"]))
        except JevUnavailable as e:
            print("  extract    FAILED:", e)
    if st is None:
        st = cache.get("standard") or E.build_standard({}, {}, 0.0, False, E.load_standard_file())

    # 1c. the other subjects -- the proof this is not hardcoded to Maya ----
    # Their corpora were fetched BEFORE today by scripts/fetch_corpus.py and committed.
    # Nothing here touches the network except Jev. Same fourteen questions, same control,
    # a real person's own words: cache/extract-<slug>.json.
    if not only or "extract" in only or "creators" in only:
        for meta in E.corpora.all_meta():
            slug = meta["slug"]
            t = time.perf_counter()
            try:
                ex = await E.extract_live(slug)
                cache.put(E.extract_cache_name(slug), ex)
                tt = ex["totals"]
                print("  %-10s %5.2fs  %s, %d items / %d chars %s"
                      % (slug, tt["seconds"], meta.get("display_name") or slug,
                         meta.get("item_count") or 0, meta.get("char_count") or 0,
                         "(REAL, verbatim)" if meta.get("real") else "(not verbatim)"))
                print("             %d questions, %d requests, %s input tokens, agree %d / "
                      "disagree %d vs the same dermatologist (step %.2fs)"
                      % (tt["questions"], tt["requests"], tt["input_tokens"], tt["agree"],
                         tt["disagree"], time.perf_counter() - t))
                for r in ex["requests"]:
                    print("             %-10s fired at +%dms, back in %dms, %d questions, "
                          "%d input tokens" % (r["judge"], r["at_ms"], r["ms"],
                                               r["question_count"], r["input_tokens"]))
            except JevUnavailable as e:
                print("  %-10s FAILED: %s" % (slug, e))
            except Exception as e:                            # noqa: BLE001
                print("  %-10s FAILED: %s: %s" % (slug, type(e).__name__, str(e)[:160]))

    pol = E.policy_from(st)
    print("             policy:", {k: v for k, v in pol.items() if k != "routing"})
    print("             routing enforced from slots:",
          {k: (v["product"], v["confidence"]) for k, v in (pol.get("routing") or {}).items()})

    # 2. the queue -------------------------------------------------------
    if not only or "queue" in only:
        t = time.perf_counter()
        try:
            raw = await E.build_queue_raw(st, pol)
            cache.put("queue-judgments", raw)
            out = E.assemble_queue(raw, pol)
            cache.put("queue", out)
            s = out["stats"]
            print("  queue      %5.2fs  %d DMs, %d judgments (triage %.2fs + baskets %.2fs)"
                  % (time.perf_counter() - t, s["dms"], s["judgments"],
                     s["triage_seconds"], s["basket_seconds"]))
            print("             answered %d  asked_back %d  held %d  referred %d  -> %d%% handled"
                  % (s["answered"], s["asked_back"], s["held"], s["referred"], s["handled_pct"]))
        except JevUnavailable as e:
            print("  queue      FAILED:", e)

    # 3. the four frozen cards ------------------------------------------
    if not only or "cards" in only:
        for cid, spec in cards.FROZEN.items():
            t = time.perf_counter()
            try:
                card = await E.build_card(dict(spec), st, pol)
                cards.save(card)
                og.render_to_cache(card)
                items = " + ".join(i["product"] for i in card["basket"]) or "nothing"
                print("  %-10s %5.2fs  %-34s %-6s  %s"
                      % (cid, time.perf_counter() - t, items, card["total"],
                         card["verdict"]["headline"]))
            except JevUnavailable as e:
                print("  %-10s FAILED: %s" % (cid, e))

    # 4. the fidelity check ---------------------------------------------
    pri = cards.load("c-priya")
    if pri:
        got = [i["product"] for i in pri.get("basket", [])]
        print("\nFIDELITY  c-priya (sensitive + redness, GBP80) -> %s  [Red Reset %s]"
              % (" + ".join(got) or "nothing", "PRESENT" if "Red Reset" in got else "MISSING"))

    files = (["cache/standard.json", "cache/extract.json", "cache/queue.json",
              "cache/queue-judgments.json"]
             + ["cache/extract-%s.json" % m["slug"] for m in E.corpora.all_meta()
                if cache.exists(E.extract_cache_name(m["slug"]))]
             + ["cache/cards/%s.json" % c for c in cards.all_ids()]
             + ["cache/og/%s.png" % p.stem for p in sorted(cache.OG.glob("*.png"))])
    print("\nwrote %d files in %.2fs" % (len(files), time.perf_counter() - t_all))
    for f in files:
        print("   ", f)
    await JEV.aclose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
