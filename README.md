# AuditGlimmer

Visual-financial reconciliation for physical collateral audits: segment equipment in inspection
photos with **SAM 3.1**, record visible identifiers with **Muse Spark** as validated JSON, and
reconcile them against an asset register with a **deterministic, explainable** matching engine.
Humans review every ambiguous match; the audit report links each decision to its raw evidence.

> AuditGlimmer records visual evidence. A photo does not prove ownership, authenticity, condition
> or value, and an asset that was not photographed is **UNVERIFIED — not missing**.

| Status | |
|---|---|
| DEMO mode (fixture providers, synthetic images, $0) | working end to end, tested |
| LIVE mode (Meta Model API: `sam-3.1`, `muse-spark-1.3`) | implemented and contract-tested offline; **UNVERIFIED against the real API** (no key / no spend approval) |

## Quick start (macOS, Apple Silicon)

Requirements: [uv](https://docs.astral.sh/uv/) (Python 3.13 is fetched automatically), Node 20.17+ / 22.9+.

```bash
cd auditglimmer/backend && uv sync
```

```bash
cd auditglimmer/frontend && npm ci
```

Start the API (DEMO mode, port 8000):

```bash
cd auditglimmer && uv run --project backend uvicorn app.main:create_app --factory --app-dir backend --host 127.0.0.1 --port 8000
```

Start the UI (port 3000) in a second terminal:

```bash
cd auditglimmer/frontend && npm run dev
```

Open http://localhost:3000 → **New session** (facility `WH-01`) → **Load demo dataset** →
**Visual inspection**: run `industrial generator`, then `forklift` → **Reconciliation** →
**Review queue** → **Report** → **Observability**. Walkthrough: [docs/demo-script.md](docs/demo-script.md).

## Tests and evaluation

```bash
cd auditglimmer/backend && uv run pytest -q -p no:logging
```

```bash
cd auditglimmer && uv run --project backend python eval/run_eval.py
```

```bash
cd auditglimmer/e2e && npm ci && npx playwright install chromium && npx playwright test
```

(The browser suite expects both servers running.) Regenerate fixtures:
`uv run --project backend python scripts/make_fixtures.py`.

## LIVE mode (paid — read [docs/cost-control.md](docs/cost-control.md) first)

```bash
export AUDITGLIMMER_MODE=live MODEL_API_KEY=... AUDITGLIMMER_LIVE_APPROVED=1
```

Without the key or approval, live runs return `403 LIVE_NOT_APPROVED`; there is never a silent
fallback to fixtures. Smoke test (≈ $0.04 worst case, refuses without `--i-approve-spend`):

```bash
cd auditglimmer && uv run --project backend python scripts/live_smoke.py --i-approve-spend
```

## How matching works

| Outcome | Rule | Auto? |
|---|---|---|
| VERIFIED (Tier 1) | readable serial uniquely equals one ledger serial; no conflicting mfr/model/type/facility | yes |
| PROBABLE (Tier 2) | mfr+model match, or serial uncertain / duplicated in ledger / seen on 2+ objects | review |
| WEAK (Tier 3) | asset type only | review |
| MISMATCHED | identifiers conflict (serial vs model, manufacturer, facility) | review |
| NOT_IN_REGISTER (Tier 4) | observed object with no supported register match | review |
| EVIDENCE_UNUSABLE | extraction failed validation / timed out | — |

Asset statuses: VERIFIED, PROBABLE, MISMATCHED, UNVERIFIED (inspected, no adequate evidence),
NOT_OBSERVABLE (not covered by any inspection).

## Repository map

| Path | Contents |
|---|---|
| `backend/app/` | FastAPI app: `main.py` routes, `pipeline.py` run worker, `reconcile.py` engine, `providers/` (Meta + fixture adapters), `ledger.py`, `security.py`, `report.py`, `services.py`, `db.py`, `schemas.py` |
| `backend/tests/` | pytest: journey, reconciliation rules, provider contracts and failure modes, input security |
| `frontend/` | Next.js 16 + TypeScript + Tailwind 4 + React Query + Recharts |
| `e2e/` | Playwright browser tests (independent verifier) |
| `fixtures/` | synthetic CC0 images, ledger CSV, labelled manifest |
| `eval/` | evaluation harness and results |
| `scripts/` | fixture generator, gated live smoke test |
| `docs/` | [task graph](docs/task-graph.md), [architecture](docs/architecture.md), [ontology](docs/ontology.md), [decisions](docs/decisions.md), [contracts](docs/integration-contracts.md), [evaluation plan](docs/evaluation-plan.md) / [report](docs/evaluation-report.md), [cost control](docs/cost-control.md), [security](docs/security.md), [demo script](docs/demo-script.md), [submission draft](docs/submission-draft.md) |

## Configuration

See [.env.example](.env.example). Data (SQLite + uploads + raw provider outputs) lives in
`backend/data/` (git-ignored). Delete a session from the API to remove its rows and images.

## Licence notes

Fixtures: CC0 (generated). `meta-sam-parser` is distributed under the SAM License.
