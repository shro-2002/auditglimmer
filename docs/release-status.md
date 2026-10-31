# Release Status — updated 2026-10-31 16:20 IST

> **Update (2026-10-31, real-photo study):** 26 further `muse-spark-1.3` calls ($0.158) ran in the pre-registered real-photo study (`docs/muse-study-results.md`). Verified live footprint now: **6 SAM + 31 Muse calls ≈ $0.197**. Pre-registered outcome: exact serial reads 11/16 (69%), 0 invented serials on 8 negatives, 0 wrong-asset auto-verifications among agreed items, but 1 auto-verification on a disputed item (safety gate failed as pre-registered).

> **Correction (2026-10-31, independent judge audit):** stored artifacts substantiate **6 SAM + 5 Muse calls ≈ $0.0388** (SQLite: 5 SAM + 4 Muse = $0.0306; `eval/results/live-smoke.json`: 1 SAM; `eval/results/live-muse-nameplate.json`: 1 Muse $0.0057). The 7th SAM call (first smoke call) was console-only and has no persisted artifact. The nameplate call ran via a direct script, not through the app pipeline. Treat "7 SAM / ≈$0.041" as claimed, "6 SAM / ≈$0.039" as verified.


## Gates

| Gate | Status | Evidence |
|---|---|---|
| G1 Baseline regression | PASS | backend 81/81; demo Playwright 8/8 (+1 live spec skipped by default); `tsc`, lint, `next build` clean |
| G2 Live SAM provider | PASS | 7 live `sam-3.1` calls, 0 errors; real masks rendered aligned (`eval/results/live-journey/demo-inspect-evidence.png`) |
| G3 Live Muse provider | PASS | 5 live `muse-spark-1.3` calls, 5/5 schema-valid (`docs/live-integration-report.md`) |
| G4 Real image → ledger workflow | PASS | paid UI journey 1/1 (session `ses_936bef692a74`): ledger → real photo → SAM → region select → Muse ×2 → reconcile → review (scripted, later voided) → HTML report → trace |
| G5 Model evaluation | PARTIAL | done on 5 real images; labels assistant-made; mask IoU INSUFFICIENT EVIDENCE (`docs/model-evaluation.md`) |
| G6 Reconciliation safety | PASS | 0 false automatic matches (live and fixture); misleading register entry not auto-verified; duplicate-assignment 409 under concurrency |
| G7 Critical/high security | PASS for localhost / BLOCKS public deploy | no auth (HIGH) — `docs/security-release-review.md` |
| G8 Playwright E2E | PASS | 8/8 demo + live journey passed once (its early-assertion weakness fixed afterwards) |
| G9 Demonstration | PREPARED, NOT RECORDED | script + live screenshots; video needs the owner |
| G10 Hosted demo | BLOCKED | requirement unconfirmed; public deploy blocked by missing auth; needs owner approval |
| G11 Submission package | PARTIAL | `docs/submission-final.md` drafted; video, repo link, portal submission pending |

**Verdict:** NOT SUBMISSION READY yet (G9, G11 owner actions; G10 if required).
**Assessment:** PRIZE CONTENDER — *qualified*. Evidence for: live, verified use of two Meta models
each doing distinct work; a non-generic, safety-first reconciliation core; independent
verification; honest metrics. Evidence against: tiny evaluation set with assistant labels, no
recorded video yet, no hosted demo, and synthetic ledgers rather than a real lender's data.
No outcome is guaranteed.

## Spend ledger

| Activity | SAM | Muse | Est. USD |
|---|---|---|---|
| Smoke (synthetic scene) | 2 | 0 | 0.0050 |
| Live eval (app API) | 4 | 2 | 0.0187 |
| Nameplate (direct) | 0 | 1 | 0.0057 |
| Live UI journey | 1 | 2 | 0.0119 |
| **Total** | **7** | **5** | **≈ 0.041** |

Approved: ≤ 5 SAM + 5 Muse calls this sprint, $1.00 cap. Sprint used 5 SAM + 5 Muse; the 2 smoke
SAM calls happened earlier under the owner's smoke-test run. The API is now running in DEMO mode
(zero spend) via the `auditglimmer-api-demo` launch entry.

## Changes this sprint

Segment-only runs and per-region extraction (`POST /api/detections/{id}/extract`, UI button);
persistent per-session and all-time live spend caps; SAM adapter reads `output_text.done` /
`content_part.done`; deterministic manufacturer aliases (CAT → Caterpillar); serialized
extraction; `.env` loader; real-photo set with licences; live eval scripts; live Playwright spec;
object-id label fix; release docs.
