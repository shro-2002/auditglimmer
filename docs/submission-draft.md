# Hackathon Submission Draft — AuditGlimmer

> DRAFT for the owner to edit. Not submitted. Claims below are limited to what was measured.

## One-liner

AuditGlimmer turns warehouse inspection photos into an auditable reconciliation of an asset
register: SAM 3.1 finds the equipment, Muse Spark records what is visibly printed on it, and a
deterministic engine decides what matches — sending every ambiguous case to a human.

## Problem

Lenders, insurers and asset managers hold registers of physical collateral (generators, forklifts,
machinery). Field inspections mean walking a site, finding each item, reading nameplates and
reconciling by hand. The hard part is not seeing objects; it is being honest about what a photo
proves.

## What it does

1. Create an audit session, upload the asset register (CSV) — validated, formula-injection safe.
2. Upload site photos; type a concept ("forklift").
3. **SAM 3.1** (`sam-3.1`, Meta Model API) returns a mask per instance; masks are drawn on the
   photo in exact source-pixel alignment.
4. **Muse Spark** (`muse-spark-1.3`) reads each crop into a closed JSON schema (manufacturer, model,
   serial, identifiers, visible condition, uncertainties) using constrained `json_schema` decoding,
   then re-validated with Pydantic. Fields like ownership or value are rejected outright.
5. A **deterministic, explainable** engine matches evidence to the register (unique serial → verified;
   model-only, uncertain or duplicated identifiers → human review; conflicts → mismatched).
6. Reviewers confirm or reject; the system refuses to assign one asset to two physical objects.
7. Export an HTML/CSV/JSON audit report where every decision cites image SHA-256, mask bounds and
   provider call; inspect latency, tokens and estimated cost per call.

## Why it is trustworthy by design

- Absence from a photo is **UNVERIFIED**, never "missing".
- The model never sees ledger values; visible text is treated as data, not instructions.
- LIVE mode never falls back to canned output; DEMO mode only answers for bundled demo images.
- Spend is zero by default; live runs need an explicit approval flag and are capped per run.

## Built with

Meta Model API (SAM 3.1 via Responses API + official `meta-sam-parser`; Muse Spark 1.3 via Chat
Completions structured output), FastAPI, Pydantic v2, SQLAlchemy/SQLite, Next.js 16, TypeScript,
Tailwind 4, React Query, Recharts, Playwright, axe-core.

## Measured results (fixture mode — synthetic scenes, authored labels)

| Measure | Result |
|---|---|
| Backend tests | 76 passed (incl. 17 regression tests from an adversarial review) |
| Browser E2E (real UI + API) | 8 passed |
| axe serious/critical violations (overview, inspect, reconciliation) | 0 |
| Asset-status agreement with labels | 18/18 |
| False automatic matches | 0 of 16 detections (2 auto-matches, both correct) |
| Invalid model outputs rejected (malformed, forbidden fields) | 2/2 |
| Provenance completeness of decisions | 100% |

These numbers test the engine, validation and provenance — **not** SAM 3.1 or Muse Spark accuracy.
Live integration is implemented and contract-tested offline but has **not** been run against the
real API at the time of writing (owner to run `scripts/live_smoke.py` with approval, ≈ $0.04).

## What's next

Live evaluation on licensed real photos; video walkthrough tracking (SAM 3.1 supports it);
asset-identity graph across audits; authentication for multi-user deployment.

## Links (to fill)

Repository: … · Demo video: … · Live demo: not deployed
