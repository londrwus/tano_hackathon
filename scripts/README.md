# Verification scripts (session 1)

Run from the repo root with `JEV_API_KEY` exported, or edit the key constant at the top.
These are the scripts that produced every number in `docs/research/jev-measured-benchmarks.md`.

| Script | What it proves |
|---|---|
| `bench_jev_fanout.py` | Latency is flat in question count; 18 questions ≈ 0.6s |
| `bench_jev_concurrency.py` | 100 concurrent requests, 1,800 judgments, 1.57s, zero errors |
| `eval_judgement.py` | **100% recall / 0 violations** vs Maya's documented decision tree. Re-run after ANY prompt change |
| `simulate_audience.py` | 300-person audience x 10 products = 3,000 judgments in 1.18s |

`eval_judgement.py` is the regression gate. If a prompt change drops recall below 100%, revert it.
