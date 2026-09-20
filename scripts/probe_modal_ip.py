"""Does running in containers get us different IPs, and does Instagram like them better?

    modal run scripts/probe_modal_ip.py

Answers two separate questions that are easy to conflate:

  1. Do separate containers egress from different IPs?      -> prints one IP per container
  2. Does Instagram serve a cloud IP at all?                 -> tries a logged-out lookup

Context: from this laptop (residential IP) a logged-out Instagram profile lookup
returned HTTP 429 on the FIRST request. The open question is whether cloud egress
is better or worse. Datacenter ranges are usually treated WORSE than residential
by Instagram, so the expected answer is "worse" - but measure, do not assume.

RESULT, measured 2026-09-20, 6 workers
--------------------------------------
    distinct egress IPs:  4 of 6     (AWS, Azure, AWS-Canada, GCP - Modal spreads them)
    instagram lookups OK: 0 of 6     (every one 429, on IPs that had never touched IG)

So: containers DO get different IPs, and it does not help. A brand-new cloud IP is
refused instantly, which means this is IP-reputation blocking of datacenter ranges
wearing a 429 costume - not a rate limit we can wait out or spread around. Cloud
egress is WORSE than the laptop, which at least offered an 11-minute retry.

Conclusion: no amount of horizontal scaling solves this. Use scripts/fetch_corpus.py
in `rss` or `paste` mode instead. Kept in the repo as the record of why.

This is a throwaway probe. It is not part of the product and nothing imports it.
"""
import modal

app = modal.App("tano-ip-probe")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("instaloader==4.15.3", "httpx==0.27.2")
)


@app.function(image=image, timeout=120, retries=0)
def probe(n: int) -> dict:
    import httpx
    import instaloader

    out = {"worker": n, "ip": None, "ig": None}
    try:
        out["ip"] = httpx.get("https://api.ipify.org", timeout=20).text.strip()
    except Exception as e:                                        # noqa: BLE001
        out["ip"] = "ip-lookup-failed: %s" % type(e).__name__

    try:
        L = instaloader.Instaloader(quiet=True, download_pictures=False,
                                    download_videos=False, download_comments=False,
                                    save_metadata=False, max_connection_attempts=1)
        p = instaloader.Profile.from_username(L.context, "nasa")
        out["ig"] = "OK followers=%d posts=%d" % (p.followers, p.mediacount)
    except Exception as e:                                        # noqa: BLE001
        out["ig"] = "%s: %s" % (type(e).__name__, str(e).replace("\n", " ")[:160])
    return out


@app.local_entrypoint()
def main():
    results = list(probe.map(range(6)))
    ips = [r["ip"] for r in results]
    print("\n%-7s %-18s %s" % ("WORKER", "EGRESS IP", "INSTAGRAM"))
    print("-" * 100)
    for r in results:
        print("%-7s %-18s %s" % (r["worker"], r["ip"], r["ig"]))
    print("-" * 100)
    print("distinct egress IPs: %d of %d" % (len(set(ips)), len(ips)))
    ok = sum(1 for r in results if str(r["ig"]).startswith("OK"))
    print("instagram lookups that succeeded: %d of %d" % (ok, len(results)))
