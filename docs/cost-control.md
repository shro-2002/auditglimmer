# Cost Control

Default spend: **$0**. DEMO mode makes no network calls to any model provider.

## Prices used (dev.meta.ai/docs/pricing-rate-limits, read 2026-10-31, Standard mode)

| Item | Price | Code constant |
|---|---|---|
| SAM 3.1 image segmentation | $2.50 / 1,000 images | `SAM_USD_PER_IMAGE` |
| Muse Spark 1.3 input | $1.25 / 1M tokens | `MUSE_USD_PER_INPUT_TOKEN` |
| Muse Spark 1.3 output (incl. reasoning) | $4.25 / 1M tokens | `MUSE_USD_PER_OUTPUT_TOKEN` |

Promotional or hackathon credits are **not assumed** to apply to Meta Model API usage; check
your account before enabling live mode.

## Gates before any paid request

1. `AUDITGLIMMER_MODE=live` — otherwise fixtures only.
2. `MODEL_API_KEY` present — detected as a boolean, never displayed (`/api/config` shows
   `credentials_present: true|false`).
3. `AUDITGLIMMER_LIVE_APPROVED=1` — explicit human approval; without it every live run is `403`.
4. Per-run caps enforced *before* each request (`pipeline.Budget`):
   `AUDITGLIMMER_MAX_LIVE_REQUESTS_PER_RUN` (default 40) and `AUDITGLIMMER_MAX_LIVE_USD_PER_RUN`
   (default $0.50). Each extraction reserves a conservative $0.0123 (3k in + 2k out tokens).
   When a cap is hit the run stops with `BUDGET_EXCEEDED` and keeps what it has.
5. Concurrency: max 2 runs, max 2 extraction requests in flight per run. Rate limits per team are
   far higher (3,000 RPM for both models).
6. The smoke script additionally needs `--i-approve-spend` on the command line.

## Estimates

| Action | Requests | Worst-case estimate |
|---|---|---|
| Live smoke (`scripts/live_smoke.py`, defaults) | 1 SAM + 3 Muse | ≈ $0.039 |
| One concept over the 3 demo scenes | 3 SAM + ~10 Muse | ≈ $0.13 |
| A 20-image session, 5 objects/image | 20 SAM + 100 Muse | ≈ $1.28 (exceeds default $0.50 cap: raise deliberately) |

## Usage recording

Every provider request writes a `ProviderCall` row: latency, `prompt_tokens`/`completion_tokens`
from the response `usage`, images, estimated USD, status, error, and a pointer to the raw output
file. Totals appear on the Observability screen and in the JSON report.
Estimates are computed from published prices; actual billing is whatever Meta's console reports.
