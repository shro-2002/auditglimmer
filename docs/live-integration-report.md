# Live Integration Report — Meta Model API (2026-10-31)

> **Update (2026-10-31, real-photo study):** 26 further `muse-spark-1.3` calls ($0.158) ran in the pre-registered real-photo study (`docs/muse-study-results.md`). Verified live footprint now: **6 SAM + 31 Muse calls ≈ $0.197**. Pre-registered outcome: exact serial reads 11/16 (69%), 0 invented serials on 8 negatives, 0 wrong-asset auto-verifications among agreed items, but 1 auto-verification on a disputed item (safety gate failed as pre-registered).

> **Correction (2026-10-31, independent judge audit):** stored artifacts substantiate **6 SAM + 5 Muse calls ≈ $0.0388** (SQLite: 5 SAM + 4 Muse = $0.0306; `eval/results/live-smoke.json`: 1 SAM; `eval/results/live-muse-nameplate.json`: 1 Muse $0.0057). The 7th SAM call (first smoke call) was console-only and has no persisted artifact. The nameplate call ran via a direct script, not through the app pipeline. Treat "7 SAM / ≈$0.041" as claimed, "6 SAM / ≈$0.039" as verified.


Calls 1–2 were the owner-run smoke test; calls 3–12 were made under the owner's sprint approval
(download of 5 Commons photos; ≤ 5 SAM + 5 Muse calls, $1.00 cap) — 5 SAM + 5 Muse used. Raw results: `eval/results/live-eval.json`,
`eval/results/live-muse-nameplate.json`, live journey session `ses_936bef692a74`
(trace, screenshots and video under `eval/results/live-journey/` and `e2e/test-results/`).
No API key or provider response body containing credentials is stored in any artifact.

## Calls made

| # | When | Path | Model | Input | Result | Latency | Est. cost |
|---|---|---|---|---|---|---|---|
| 1–2 | smoke | `scripts/live_smoke.py` | sam-3.1 | synthetic fixture scene, "generator" | 0 matches (both); `images_processed: 1` | 3.2 s (console only), 2.9 s (stored) | $0.005 |
| 3 | eval | app API | sam-3.1 | USACE generator photo, "generator" | 1 instance, box correct | 4.0 s | $0.0025 |
| 4 | eval | app API | sam-3.1 | same photo, "forklift" (absent) | 0 matches (correct) | 3.9 s | $0.0025 |
| 5 | eval | app API | sam-3.1 | FEMA airfield photo, "machine" (ambiguous) | 0 matches | 3.5 s | $0.0025 |
| 6 | eval | app API | sam-3.1 | FEMA warehouse (small, top-down forklift), "forklift" | 1 instance, box correct | 3.2 s | $0.0025 |
| 7 | eval | app API, selected region | muse-spark-1.3 | generator crop | valid; type generator; mfr/model/serial null with uncertainties; did not treat "BC-260" photo caption as a serial | 5.0 s | $0.0045 |
| 8 | eval | app API, selected region | muse-spark-1.3 | warehouse forklift crop | valid; manufacturer "CAT" | 5.2 s | $0.0042 |
| 9 | eval | direct (`eval/live_muse_nameplate.py`) | muse-spark-1.3 | nameplate close-up (CC BY-SA) | valid; serial "5735" + AMP 16 / VOLT 70 / GIRI 1000; manufacturer null | 7.3 s | $0.0057 |
| 10 | UI journey | browser → app | sam-3.1 | US Army forklift photo, "forklift" | 2 instances, both correct | 2.4 s | $0.0025 |
| 11–12 | UI journey | browser → selected regions | muse-spark-1.3 | 2 forklift crops | valid; right unit "HYSTER" + "U.S. ARMY" (partially readable); left unit no manufacturer | 5.4 s, 5.6 s | $0.0094 |

Totals: **7 SAM calls, 5 Muse calls, 0 provider errors, 0 schema failures, ≈ $0.041 estimated**
(published prices; actual billing is whatever Meta's console shows). A request ID was confirmed for the
nameplate call (`request_id_present: true`); in-app call records are in the SQLite trace, not in docs.

## Integration facts verified live

- SAM 3.1 accepts a base64 `data:` URL in `input_image.image_url`.
- SAM streams no `output_text.delta` for zero matches; text arrives in `output_text.done` /
  `content_part.done`. The adapter originally read only deltas — fixed and regression-tested
  before any real detection was missed.
- Real masks are `one_bit` encoded and decode via the official `meta-sam-parser`; overlays align
  pixel-exactly with the source image in the UI (screenshot `demo-inspect-evidence.png`).
- Muse Spark 1.3 Chat Completions `json_schema` output passed Pydantic validation 5/5,
  `reasoning_effort: low`; `finish_reason: stop` is stored for the nameplate call (the app rejects `length`, and none of the 5 was rejected).

## Failures and limitations observed

- SAM returned **no detections on flat-shaded synthetic cartoons** — the demo fixtures are
  useless for live evaluation; real photos are required.
- The ambiguous concept "machine" returned 0 instances although an all-terrain forklift is in
  frame. Consistent with Meta's guidance to prompt with a specific noun phrase; the UI help text
  already asks for one.
- Muse reported "CAT" while the register says "Caterpillar": the engine had no alias table, so
  candidates were not narrowed. Fixed (deterministic `MANUFACTURER_ALIASES`) with a test; the
  stored decision for call 8 predates the fix (recomputed on read, it now narrows to R-004/R-005).
- The first live UI test asserted too early (matched the detection label before Muse returned);
  backend trace proves both extractions completed, test strengthened afterwards. Screenshots for
  the demo were re-captured from the stored session without new calls.
- The UI journey's scripted review confirmed the first candidate of the first queue item
  (left forklift → R-002) to exercise the override path. It was voided afterwards by an append-only
  reject (reviewer `release-coordinator`, with note); `eval/results/live-journey/live-audit-report.html`
  was regenerated after the void; screenshot `05-review.png` shows the scripted step.
