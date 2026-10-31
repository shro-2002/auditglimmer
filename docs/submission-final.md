# Submission — AuditGlimmer (final draft for the owner; not submitted)

AuditGlimmer is a hackathon prototype. It is **not production-certified** and makes no regulatory or audit-standard claim.

**Track:** Indie developer (owner to confirm) · **Built:** started Oct 31, 2026, inside the event window (Oct 26 – Nov 4).

## Tagline

Photo evidence in, auditable collateral reconciliation out — SAM 3.1 finds the equipment, Muse Spark
reads what is really printed on it, deterministic rules match it to the books, and a human signs off.

## Problem

Lenders and insurers hold registers of physical collateral. Verifying them means site walks,
reading nameplates and hand-reconciling spreadsheets. AI can help — but an audit tool that
overclaims (guessing serials, "verifying" from a brand logo, calling unphotographed assets
missing) is worse than none.

## What it does

1. Upload an asset register (CSV, validated, formula-injection safe) and site photos.
2. **SAM 3.1** (`sam-3.1`) segments a named concept; real pixel masks are overlaid in source coordinates. It
   supplies geometry only — it reads nothing. For a close-up of a nameplate the auditor can skip SAM; the UI then
   says "SAM skipped — whole photo declared as one region".
3. **Muse Spark 1.3** (`muse-spark-1.3`) reads the crop into a closed JSON schema (manufacturer, model, serial,
   identifiers, visible condition, uncertainties). It never sees the register.
4. A **deterministic engine** matches evidence to the register. Automatic verification (Tier 1) needs all of:
   a unique serial match; a second, independently constructed Muse read that agrees; a corroborating manufacturer
   or model; no contradictory evidence; and a region segmented on the equipment (a whole-photo plate cannot prove
   which unit carries it). Everything else goes to a named human reviewer. The two-read check is an
   **experimental safeguard**: two agreeing reads are supporting evidence, not proof.
5. Export an HTML/CSV/JSON report; the audit trail lists every Meta call (model, latency, tokens, estimated cost).

## Verified live footprint (single source of truth)

**7 SAM 3.1 + 51 Muse Spark calls ≈ $0.3235 estimated**, all persisted: SQLite `provider_calls` (6 SAM + 50 Muse,
$0.3153), `eval/results/live-smoke.json` (1 SAM) and `eval/results/live-muse-nameplate.json` (1 Muse via a direct
script). Independently recomputed 31 Oct. Older figures ("7 SAM + 5 Muse", "6 + 5", "6 + 31", "7 + 32") are superseded.

## Results — three separate sets, never mixed

1. **Historical, pre-registered (26 photos, `docs/muse-study-results.md`, frozen):** exact serial reads 11/16 (69%,
   below the 70% bar); 0 invented serials on 8 negatives; **1 unsafe automatic verification on a disputed item
   (s14) — the pre-registered safety gate FAILED.** This failure motivated the two-read gate and the whole-photo rule.
2. **Post-hoc development (same 26 photos, engine changes after seeing outputs; not pre-registered):** correct
   automatic verifications 3/14 → 7/14. Optimistic by construction. Under the current rules these whole-photo
   items can no longer auto-verify at all.
3. **Fresh holdout (14 new photos, frozen before the run; `docs/holdout-study-results.md`, independently
   verified):** exact serial 5/6 (CI 44–97%); 0 automatic verifications and 0 unsafe (by design: whole-photo plates
   cannot auto-verify); correct single suggestion to the reviewer 5/6; 1 distractor number read on a negative (h04,
   flagged uncertain); 19 Muse calls, $0.12. AI-only labels, one source site, n = 14.

End-to-end live proof (31 Oct): a real equipment photo went SAM 3.1 → Muse → rules → UI. Muse found no legible
serial, so the result was WEAK (type only) and no second read was needed. In the holdout the second read ran live
5 times and agreed every time, so it has **not yet been seen catching a real disagreement** — it remains an
experimental safeguard, not validated.

Engineering: 143 backend tests (incl. 39 for the Tier 1 gate), 16 browser tests + 1 paid live journey, axe 0
serious issues, independent adversarial reviews. Labels in all studies are AI-made, not independent human ground truth.

## Judging criteria

The official event page (cerebralvalley.ai/e/meta-ai-developer-hackathon) describes judging on creativity, technical
ambition and whether it works, **without published weights**. Weightings seen elsewhere are not official and are
not used here.

- **Creativity** — evidence-first collateral audit: the model reads, rules decide, humans own ambiguity.
- **Technical ambition** — two Meta models with distinct jobs (SAM geometry, Muse structured reading), provenance
  graph, pre-registered evaluation, spend caps, failure-mode handling.
- **Whether it works** — DEMO runs end to end offline; live calls are recorded and replayable; limits stated above.

## Built with

Meta Model API (SAM 3.1, Muse Spark 1.3), FastAPI, Pydantic v2, SQLAlchemy/SQLite, Next.js 16,
TypeScript, Tailwind 4, TanStack Query, Recharts, Playwright, axe-core. Development used an AI
coding assistant (Claude Code) — disclosed for transparency.

## Credits

Photos via Wikimedia Commons: US Army Corps of Engineers; FEMA (Casey Deshong, Eliud Echevarria);
US Army (SSG Alfred Batungbacal) — public domain. Generator nameplate: Haweroth, CC BY-SA 4.0.

## Links (owner to fill)

Video: … · Repository: … · Hosted demo: not deployed (no authentication yet; localhost only)
