# Evaluation Report — 2026-10-31

**Mode: FIXTURE (DEMO).** Segmentation and extraction outputs are authored fixture labels on 3
synthetic scenes. These results measure the reconciliation engine, validation, provenance, error
handling and UI — **not** SAM 3.1 or Muse Spark quality. LIVE mode: **PARTIALLY VERIFIED** — SAM 3.1 transport verified
live; segmentation of synthetic cartoons returns zero matches; Muse Spark not yet called live.

Reproduce: `uv run --project backend python eval/run_eval.py` → `eval/results/fixture-eval.json`.

## Engine and pipeline metrics (16 detections, 18 accepted ledger assets)

| Metric | Value |
|---|---|
| Automatic matches | 2 |
| Auto-match precision | 1.00 (2/2) |
| False automatic-match rate | 0.00 (0/16) |
| Candidate recall, all labelled detections | 0.79 (11/14; misses are the 3 deliberately failed extractions) |
| Candidate recall, usable evidence | 1.00 |
| Human-review rate | 0.69 (11/16) — by design: fixtures are mostly hard cases |
| Unregistered objects flagged NOT_IN_REGISTER | 2/2 |
| Asset-status agreement with labels | 18/18 |
| Provenance completeness | 1.00 |
| Schema-valid extractions | 13/16 |
| Invalid outputs rejected (malformed JSON, forbidden `legal_owner`/`estimated_value_usd`) | 2/2 |
| Timeouts recovered as EVIDENCE_UNUSABLE, run completes | 1/1 |
| Overlay bounds = labelled bounds | 16/16 (identity check of the overlay path; not SAM IoU) |
| End-to-end runs completed | 2/2 (status `partial`, as designed) |
| Fixture latency p50 / p95 (extract) | 0.01 / 0.03 ms — local lookup, meaningless for live |
| Estimated provider cost | $0.00 |

## Verification gates

| Gate | Result | Evidence |
|---|---|---|
| 1 Architecture + contracts | PASS | `docs/` |
| 2 Frontend + backend boot | PASS | both served on :3000 / :8000; `next build` compiled |
| 3 Demo full journey | PASS | `tests/test_journey.py`, Playwright journey test |
| 4 Overlay alignment | PASS | SVG box == img box (950×593 at same origin), viewBox == natural 1280×800; Playwright assertion within 1 px; bounds equal labels 16/16 |
| 5 Deterministic explainable decisions | PASS | `tests/test_reconcile.py` incl. shuffled-input determinism |
| 6 Report with evidence + uncertainty | PASS | JSON/HTML/CSV tests; HTML contains disclaimer + DEMO notice |
| 7 Backend tests | PASS | 76 passed |
| 8 Browser E2E | PASS | 8 passed; axe serious/critical: 0 on overview, inspect, reconciliation |
| 9 Live Meta API smoke | PARTIAL | 2 approved SAM calls (auth, endpoint, data-URL image, stream parsing verified); both returned 0 matches for "generator" on the synthetic flat-shaded scene, so Muse extraction was not exercised. Needs a real photo. Est. spend $0.005 |
| 10 Docs/claims audit | PASS | claims limited to measured fixture results; live labelled UNVERIFIED |

## Independent verification (separate contexts)

- **Browser verifier** wrote `e2e/` (8 tests). First run: 7/8 — found a 375 px horizontal
  overflow on the inspect page and an axe `aria-hidden-focus` violation (focusable Recharts layer
  inside a hidden chart). Both fixed; rerun 8/8, axe 0.
- **Adversarial reviewer** (read-only) reported 16 confirmed defects. Fixed with regression tests
  (`tests/test_regressions.py`, 17 tests):
  - CRITICAL concurrent confirms assigned one asset to several objects → process-wide review lock
    spanning validation and commit. Mutation check: test fails 3/3 with the lock removed.
  - Re-run on a subset wiped other images' evidence and reviews → supersession per (concept, image),
    based on successful segmentation events.
  - Duplicate-identifier exemption keyed on flags instead of serials; auto-verified assets could be
    human-confirmed to another object → serial-equality check, auto claims included.
  - One bad mask crashed the whole run → bounds clamped at parse, per-detection exception isolation.
  - Live `explain` was untraced and uncapped → recorded as a ProviderCall, per-process cap.
  - Failed images counted as inspected; SSE hang on deleted runs; orphaned runs after restart;
    malformed CSV → 500; 500s lost the correlation id; ledger re-upload kept stale reviews; second
    visible serial ignored; uncertain misread produced confident NOT_IN_REGISTER; reject ignored its
    asset; report preview mutated state; raw outputs survived deletion; budget never trued-up;
    unbounded run queue; phone JPEGs (MPO, EXIF rotation) → all fixed.

## Not measured

SAM 3.1 segmentation quality, Muse Spark transcription accuracy, live latency, real billed cost,
behaviour on real (non-synthetic) photographs. See `docs/evaluation-plan.md` for the live protocol.
