# Model Evaluation (live + fixture), 2026-10-31

> **Update (2026-10-31, real-photo study):** 26 further `muse-spark-1.3` calls ($0.158) ran in the pre-registered real-photo study (`docs/muse-study-results.md`). Verified live footprint now: **6 SAM + 31 Muse calls ≈ $0.197**. Pre-registered outcome: exact serial reads 11/16 (69%), 0 invented serials on 8 negatives, 0 wrong-asset auto-verifications among agreed items, but 1 auto-verification on a disputed item (safety gate failed as pre-registered).

> **Correction (2026-10-31, independent judge audit):** stored artifacts substantiate **6 SAM + 5 Muse calls ≈ $0.0388** (SQLite: 5 SAM + 4 Muse = $0.0306; `eval/results/live-smoke.json`: 1 SAM; `eval/results/live-muse-nameplate.json`: 1 Muse $0.0057). The 7th SAM call (first smoke call) was console-only and has no persisted artifact. The nameplate call ran via a direct script, not through the app pipeline. Treat "7 SAM / ≈$0.041" as claimed, "6 SAM / ≈$0.039" as verified.


**Label source:** assistant visual inspection of the photos (`fixtures/real/LICENSES.md`). These are
**not independent human ground truth**; an owner review of the labels is the first open action.
Sample sizes are tiny; nothing here supports a general accuracy claim.

## SAM 3.1 (live)

| Case | n images | Expected | Returned | Outcome |
|---|---|---|---|---|
| Single machine (generator) | 1 | 1 | 1 | TP |
| Multiple similar (forklifts) | 1 | 2 | 2 | 2 TP |
| Absent object (forklift in generator photo) | 1 | 0 | 0 | correct empty |
| Ambiguous concept ("machine") | 1 | ≥1 (forklift) | 0 | miss (prompting limitation) |
| Small / top-down / mixed lighting (forklift) | 1 | 1 | 1 | TP |
| Synthetic flat cartoons ("generator") | 1 (2 calls) | 4 | 0 | miss ×2 |

- Specific-concept detection on real photos: **precision 4/4, recall 4/4** (n = 4 instances across 3 distinct photos; the generator photo was used for two cases).
- Including the ambiguous prompt: recall 4/5.
- **Mask IoU: INSUFFICIENT EVIDENCE** — no human pixel-level masks exist; boxes were judged visually.
- Latency (n = 5 app calls): p50 3.5 s, max 4.0 s (p95 not meaningful at n = 5).

## Muse Spark 1.3 (live, n = 5 extractions)

| Measure | Result |
|---|---|
| Structured-output validity (Pydantic, extra fields forbidden) | 5/5 |
| Object type correct | 5/5 |
| Visible manufacturer correct when legible (CAT, HYSTER) | 2/2 |
| Abstained (null + uncertainty) when not legible | 3/3 |
| Serial reading agrees with the label ("5735") | 1/1 — the label is also an assistant reading and the third digit is worn, so this is agreement, not independent confirmation |
| Possible missed identifiers | 2 — a rear plate on the warehouse forklift (digits uncertain; two readers disagree) and a front-panel number on the left army forklift; Muse reported neither |
| Fabricated serials (images with no serial) | 0/4 |
| Photo caption mistaken for asset serial ("BC-260") | 0/1 |
| Unsupported claims (ownership, value, unseen damage) | 0/5 |
| Evidence references attached server-side to the right crop | 4/4 in-app (the direct nameplate call bypasses the app) |
| Latency p50 / max | 5.4 s / 7.3 s |

## Reconciliation (live sessions)

- Decisions: 4 in-app (generator, warehouse forklift, 2 army forklifts). **Automatic matches: 0;
  false automatic matches: 0.** All four are Tier 3 (type only; manufacturer narrowing where a brand was read) → human review.
- Misleading register entry (R-001 serial = photo caption) was **not** auto-verified.
- Look-alike Hysters (R-002/R-003) remain ambiguous: the region where Muse read "HYSTER" is still pending review. A scripted
  test confirmation (non-Hyster unit → R-002) exercised the override control and was then voided by an append-only reject
  with an explanatory note; both entries stay in the audit trail. Duplicate assignment is blocked (409, covered by tests).
- Coverage: in the eval session R-001–R-006 are UNVERIFIED (types inspected, no adequate evidence) and R-007 is
  NOT_OBSERVABLE (racking never inspected). Fixture regression also includes 13/16 schema-valid extractions, by design
  (3 deliberate failure cases).

## Fixture-mode regression metrics (engine only)

`eval/results/fixture-eval.json`: 18/18 asset statuses, auto-match precision 2/2, 0 false
automatic matches over 16 detections, invalid outputs rejected 2/2, provenance completeness 100%.

## System

- Live end-to-end UI journey: **1/1 completed** (create → ledger → upload real photo → live SAM →
  select regions → live Muse ×2 → reconcile → review → download report → trace).
- Provider errors: 0/12 live calls; error-recovery paths are covered offline (timeouts,
  malformed and forbidden-field outputs, 429/5xx retries, budget exhaustion).
- Provenance: every in-app decision links image SHA-256 → detection bounds → SAM call → Muse call.
- Observed cost: ≈ $0.041 for all live work.

## Impact (assistance, not certification)

**Manual baseline time: INSUFFICIENT EVIDENCE** (not observed). What the live run shows: for a
7-asset register and one photo, the system located 2 forklifts, read a manufacturer on one,
narrowed 4 forklift candidates to 2, and escalated everything ambiguous to a human with the
evidence attached. It made no automatic matches, and therefore no incorrect ones.
