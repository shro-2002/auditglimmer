# Evaluation Plan

## Principles

- Only measured numbers are reported. Fixture-mode results are labelled fixture-mode.
- No live-model quality claim without a live run (Gate 9).
- Labels are authored in `scripts/make_fixtures.py` (`true_asset_id`, `case`,
  `expected_asset_status`), versioned with the fixture manifest.

## Fixture dataset (3 synthetic images, 16 objects, 20 ledger rows)

| Required case | Fixture object(s) |
|---|---|
| Exact identifier match | bay_a #1 (A-001), yard_c #3 (A-004) |
| Partial manufacturer/model match | bay_a #2 (BW-300, serial blurred) |
| Similar-looking distinct assets | bay_b #2, #3 (two Liftmaster LM-25, serial unreadable) |
| Duplicate candidates | yard_c #2 (serial shared by A-005 and A-006 in ledger) |
| Same identifier on two objects | bay_a #4 and yard_c #4 (GN-70707) |
| Unreadable serial numbers | bay_a #2, bay_b #2, #3 |
| Missing visual evidence | A-008 (no photo), bay_b #4 (no nameplate) |
| Contradictory ledger fields | A-003 serial differs from plate; A-010 manufacturer differs; duplicate asset_id row; missing asset_id row |
| Unsupported model conclusions | yard_c #5 (adds `estimated_value_usd`, `legal_owner`) |
| Provider timeout | bay_b #5 (fixture-simulated) |
| Malformed provider response | bay_a #5 (truncated JSON) |
| Observed object absent from register | yard_c #1 (Voltane VG-90), yard_c #6 (pallet jack) |
| CSV injection | A-022 `=HYPERLINK(...)` |

## Metrics (eval/run_eval.py)

| Metric | Definition |
|---|---|
| auto-match precision | correct VERIFIED / all VERIFIED |
| false automatic-match rate | wrong VERIFIED / detections |
| candidate recall | detections whose true asset is in candidates / labelled detections (all, and with usable evidence) |
| human-review rate | review_required / detections |
| asset-status agreement | assets whose status equals the label |
| provenance completeness | decisions with image sha256 + bounds + both provider-call ids + evidence refs |
| schema validity | valid extractions / extraction calls; invalid outputs rejected / invalid cases |
| error recovery | timeouts that end as EVIDENCE_UNUSABLE with the run completing |
| segmentation quality | mask IoU vs labels — only meaningful for LIVE runs; fixture check is identity only |
| latency | p50/p95/max per operation from ProviderCall rows |
| cost | sum of estimated_cost_usd (0 in fixture mode) |

## Live evaluation (blocked until key + approval)

1. `scripts/live_smoke.py --i-approve-spend` (≤ ~$0.04): API contract, data-URL acceptance,
   parse success, real latency/tokens.
2. Live segmentation IoU on the 3 synthetic scenes (labels exist) for "generator"/"forklift":
   3 SAM calls ≈ $0.0075.
3. Extraction accuracy on rendered nameplates (16 crops ≈ $0.20 worst case).
4. Real-photo evaluation needs a licensed photo set with hand labels — not available yet.
