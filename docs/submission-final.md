# Submission — AuditGlimmer (final draft for the owner; not submitted)

> **Update (2026-10-31, real-photo study):** 26 further `muse-spark-1.3` calls ($0.158) ran in the pre-registered real-photo study (`docs/muse-study-results.md`). Verified live footprint now: **6 SAM + 31 Muse calls ≈ $0.197**. Pre-registered outcome: exact serial reads 11/16 (69%), 0 invented serials on 8 negatives, 0 wrong-asset auto-verifications among agreed items, but 1 auto-verification on a disputed item (safety gate failed as pre-registered).

> **Correction (2026-10-31, independent judge audit):** stored artifacts substantiate **6 SAM + 5 Muse calls ≈ $0.0388** (SQLite: 5 SAM + 4 Muse = $0.0306; `eval/results/live-smoke.json`: 1 SAM; `eval/results/live-muse-nameplate.json`: 1 Muse $0.0057). The 7th SAM call (first smoke call) was console-only and has no persisted artifact. The nameplate call ran via a direct script, not through the app pipeline. Treat "7 SAM / ≈$0.041" as claimed, "6 SAM / ≈$0.039" as verified.


**Track:** Indie developer (owner to confirm) · **Built:** started Oct 31, 2026, inside the event window (Oct 26 – Nov 4).

## Tagline

Photo evidence in, auditable collateral reconciliation out — SAM 3.1 finds the equipment, Muse Spark
reads what is really printed on it, deterministic rules match it to the books, and a human signs off.

## Problem

Lenders and insurers hold registers of physical collateral. Verifying them means site walks,
reading nameplates and hand-reconciling spreadsheets. AI can help — but an audit tool that
overclaims (guessing serials, "verifying" from a brand logo, calling unphotographed assets
missing) is worse than none.

## What it does (verified live on Meta Model API)

1. Upload an asset register (CSV, validated, formula-injection safe) and site photos.
2. **SAM 3.1** (`sam-3.1`) segments a named concept; real pixel masks are overlaid in source
   coordinates. In LIVE mode the inspector then **chooses regions** to extract — each paid call is deliberate.
3. **Muse Spark 1.3** (`muse-spark-1.3`) reads the selected crop into a closed JSON schema
   (manufacturer, model, serial, identifiers, visible condition, uncertainties). Extra fields such
   as ownership or value are rejected; no ledger data is sent to the model.
4. A **deterministic engine** matches evidence to the register: unique readable serial → verified;
   brand/model only, uncertain or duplicated identifiers → human review; conflicts → mismatched.
5. Inspectors confirm or reject; one asset can never be assigned to two physical objects.
6. Export an HTML/CSV/JSON report; the audit trail lists the exact Meta calls (model, latency,
   tokens, estimated cost) behind each decision.

## Evidence (measured; small samples, labelled honestly)

- Live: 7 SAM + 5 Muse calls, 0 errors, ≈ $0.041 estimated.
- SAM on real photos, specific concepts: 4/4 objects found, 0 false detections (4 cases, 3 distinct photos);
  correct empty result for an absent object; the vague prompt "machine" returned nothing.
- Muse: 5/5 schema-valid; read "HYSTER" and "CAT" correctly and a serial matching our reading ("5735"); 0 invented serials,
  0 ownership/value claims; ignored a photo caption the register falsely lists as a serial;
  two possible missed plate numbers.
- Reconciliation: 0 automatic matches on the real set (all ambiguous → review), therefore 0 false
  matches; fixture regression 18/18 statuses, 0 false automatic matches in 16 detections.
- Engineering: 81 backend tests, 8 browser tests + 1 paid live browser journey, axe 0 serious issues,
  independent adversarial review (16 defects fixed with regression tests).
- Labels are assistant-made (not independent human ground truth); mask IoU not measured.

## How it maps to the judging criteria (official weights)

- **Impact (30%)** — assists a real, expensive inspection workflow; honest about what a photo proves.
- **Use of Meta AI Tooling (25%)** — SAM 3.1 geometry + Muse Spark structured vision, each doing
  what it is best at, official `meta-sam-parser`, per-call telemetry.
- **Technical Depth & Execution (20%)** — provenance graph, deterministic rules, spend caps,
  failure-mode handling, independent verification.
- **Demo (25%)** — 3-minute live walkthrough (`docs/final-demo-script.md`).

## Built with

Meta Model API (SAM 3.1, Muse Spark 1.3), FastAPI, Pydantic v2, SQLAlchemy/SQLite, Next.js 16,
TypeScript, Tailwind 4, TanStack Query, Recharts, Playwright, axe-core. Development used an AI
coding assistant (Claude Code) — disclosed for transparency.

## Credits

Photos via Wikimedia Commons: US Army Corps of Engineers; FEMA (Casey Deshong, Eliud Echevarria);
US Army (SSG Alfred Batungbacal) — public domain. Generator nameplate: Haweroth, CC BY-SA 4.0.

## Links (owner to fill)

Video: … · Repository: … · Hosted demo: not deployed (no authentication yet; localhost only)
