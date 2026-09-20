# docs

Thirteen numbered files, written over one build, in the order they were written. They do not all
still agree with each other. This index says which one wins.

**If you read three, read these.**

1. [`11-honest-headline.md`](11-honest-headline.md). The source of truth for every measured number.
   It retracts earlier claims by name and reviews our own work adversarially. Where it disagrees
   with any other file here, it wins.
2. [`10-API-CONTRACT.md`](10-API-CONTRACT.md). The frozen contract. Every endpoint, every field.
3. [`09-GO.md`](09-GO.md). The build spec, which is what actually got built.

---

## Current

| File | What it is |
|---|---|
| [`03-build-plan.md`](03-build-plan.md) | How and when it was built. Historical now, accurate then |
| [`05-backend-architecture.md`](05-backend-architecture.md) | The machinery. FastAPI, the cache, the model client. Still describes the code |
| [`08-persona-stress-test.md`](08-persona-stress-test.md) | Five adversarial reads of the product, including a tired judge at 19:50 |
| [`09-GO.md`](09-GO.md) | The definitive build spec. **Two known holes**: section 2's divergence table and section 7's opening beat were both disproved by `11`. Read `11` alongside it |
| [`10-API-CONTRACT.md`](10-API-CONTRACT.md) | Frozen API contract. Backend and frontend both build against this |
| [`11-honest-headline.md`](11-honest-headline.md) | What is measured, what is retired, what is still our own handwriting |
| [`12-DESIGN-LIGHT.md`](12-DESIGN-LIGHT.md) | The frozen light design system. This is what the app looks like |
| [`13-PIPELINE-ANIMATION.md`](13-PIPELINE-ANIMATION.md) | Spec for `/how-it-works`, the fifteen-second pipeline animation |

## Superseded

| File | Status |
|---|---|
| [`04-visual-language.md`](04-visual-language.md) | **Superseded by [`12-DESIGN-LIGHT.md`](12-DESIGN-LIGHT.md).** The dark dossier direction was cut for being hard to read. Kept only as the audit trail. Do not build from it |
| [`07-demo-script.md`](07-demo-script.md) | Mostly current, but its cold open rests on a dermatologist price comparison that `11` section 3 item 6 disproved. That beat must change before anyone performs this |

## v1 leftovers

Written before the product settled. Kept for the record, not for reference.

| File | Status |
|---|---|
| [`01-constraints-and-stack-status.md`](01-constraints-and-stack-status.md) | v1. The stack survey from the day before the build. The verified-versus-assumed table is still useful, the spend figures are stale |
| [`02-the-pick.md`](02-the-pick.md) | v1. Why this case and this build were chosen out of three. Superseded as a spec by `09-GO.md` |
| [`06-demo-day-runbook.md`](06-demo-day-runbook.md) | v1. The operational plan. Superseded by `03-build-plan.md` and `07-demo-script.md` |

---

## Subdirectories

| Directory | What is in it |
|---|---|
| `evidence/` | The issued case files, as text and as PDF. **Tano's, not ours.** See [`../NOTICE`](../NOTICE) |
| `personas/` | Five persona reviews, the raw material behind `08` |
| `research/` | Background compiled during the build. Mixed provenance, see below |

### A warning about `research/`

`research/` is working material from the first day and it was never written to be read by
strangers.

- **`tano-and-judges-intel.md` should be deleted before this repository is made public.** It is a
  briefing on named real people, the event's hosts and judges, including social handles, follower
  counts, unverified claims about their funding and careers, and notes on how to appeal to them
  personally. Several entries are marked as low confidence or unverified by their own author.
  Publishing it is not defensible, whatever its accuracy.
- `typesafe-http-api.md` is a copy of TypeSafe's own published API reference, snapshotted so the
  build could work offline. Prefer https://docs.typesafe.ai. See [`../NOTICE`](../NOTICE).
- `jev-engineering-playbook.md` and `jev-measured-benchmarks.md` are ours, compiled from those
  docs plus our own measured calls. The benchmarks file carries the same retraction as `11`.
- `market-and-prior-art.md` and `concepts-raw.json` are ours, and are opinion written fast.
