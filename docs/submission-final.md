# Submission — AuditGlimmer (final draft for the owner; not submitted)

AuditGlimmer is a hackathon prototype. It is **not production-certified** and makes no regulatory or audit-standard claim.

**Track:** Indie developer (owner to confirm) · **Built:** started Oct 31, 2026, inside the event window (Oct 26 – Nov 4).
**Demo video:** `submission/AuditGlimmer_Meta_Final.mp4` (174.9 s, includes 4 live Meta API calls recorded 1 Nov 2026), described in [demo-video.md](demo-video.md).

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
   a unique serial match; a second Muse extraction (an enhanced re-cut of the same photo, own prompt) that agrees; a corroborating manufacturer
   or model; no contradictory evidence; and a region segmented on the equipment (a whole-photo plate cannot prove
   which unit carries it). Everything else goes to a named human reviewer. The two-read check is an
   **experimental safeguard**: two agreeing reads are supporting evidence, not proof.
5. Export an HTML/CSV/JSON report; the audit trail lists every Meta call (model, latency, tokens, estimated cost).

## Verified live footprint (single source of truth)

**8 SAM 3.1 + 54 Muse Spark calls ≈ $0.3455 estimated**, all persisted: SQLite `provider_calls` (7 SAM + 53 Muse,
$0.3373), `eval/results/live-smoke.json` (1 SAM, local only) and `eval/results/live-muse-nameplate.json` (1 Muse via a
direct script). Includes the filmed live take of 1 Nov 2026 (1 SAM + 3 Muse, $0.0220;
`eval/results/live-film-2026-11-01/`). Older figures ("7 SAM + 51 Muse", "7 + 5", "6 + 31") are superseded.

## Results — three separate sets, never mixed

1. **Historical, pre-registered (26 photos, `docs/muse-study-results.md`, frozen):** exact serial reads 11/16 (69%,
   below the 70% bar); 0 invented serials on 8 negatives; **1 unsafe automatic verification on a disputed item
   (s14) — the pre-registered safety gate FAILED.** This failure motivated the two-read gate and the whole-photo rule.
2. **Post-hoc development (same 26 photos, engine changes after seeing outputs; not pre-registered):** correct
   automatic verifications 3/14 → 7/14, while still auto-verifying the disputed s14. Optimistic by construction. Under the current rules these whole-photo
   items can no longer auto-verify at all.
3. **Fresh holdout (14 new photos, frozen before the run; `docs/holdout-study-results.md`, independently
   verified):** exact serial 5/6 (CI 44–97%); 0 automatic verifications and 0 unsafe (by design: whole-photo plates
   cannot auto-verify); correct single suggestion to the reviewer 5/6 (3 of those 5 labelled MISMATCHED because the synthetic register's long maker names conflict); 1 distractor number read on a negative (h04,
   flagged uncertain); 19 Muse calls, $0.12. AI-only labels, one source site, n = 14.

**Holdout arms (post-hoc, same stored outputs):** rules without Muse give 0/6 correct single suggestions; with Muse
5/6; with Muse + the two-read gate 5/6 at +42% cost — on this set the gate caught nothing. Muse's measured value is
turning "check every asset" into the right single candidate; no arm auto-verified anything on whole-photo plates.

**Evidence challenge page (`/challenge`):** one recorded-live case (SAM 3.1 masks on a real forklift photo; Muse read
"HYSTER", no serial; rules narrowed the register to two Hyster rows and sent it to review) beside one labelled DEMO
Tier 1 match. No live photo has produced a Tier 1 match yet, and the page says so.

End-to-end live proof (31 Oct): a real equipment photo went SAM 3.1 → Muse → rules → UI. Muse found no legible
serial, so the result was WEAK (type only) and no second read was needed. In the holdout the second read ran live
5 times and agreed every time, so it has **not yet been seen catching a real disagreement** — it remains an
experimental safeguard, not validated.

Engineering: 144 backend tests (incl. 40 for the Tier 1 gate), 17 browser tests + 1 paid live journey, axe 0
serious issues, independent adversarial reviews. Labels in all studies are AI-made, not independent human ground truth.

## Judging criteria (Impact 30% · Use of Meta AI Tooling 25% · Technical Depth & Execution 20% · Demo 25%)

- **Impact** — collateral inspection for asset-based lending: turns "search every photo against every row" into
  reviewing one evidence-linked candidate, without claiming title, ownership or physical identity.
- **Use of Meta AI tooling** — SAM 3.1 for per-machine geometry and Muse Spark 1.3 for structured identifier reading with
  stated uncertainty; retrospective holdout comparison: rules alone 0/6 correct candidates, with Muse 5/6.
- **Technical depth & execution** — deterministic rules with a Tier 1 gate, provenance graph, pre-registered
  evaluation, spend caps, 144 backend tests, recorded provider calls.
- **Demo** — 174.9 s video with live SAM and Muse calls captured once, every result labelled live, replay or synthetic.

## Built with

Meta Model API (SAM 3.1, Muse Spark 1.3), FastAPI, Pydantic v2, SQLAlchemy/SQLite, Next.js 16,
TypeScript, Tailwind 4, TanStack Query, Recharts, Playwright, axe-core. Development used an AI
coding assistant (Claude Code) — disclosed for transparency. Demo video produced with Ultrademo (Apache-2.0)
and a local Kokoro TTS voice.

## Credits

Photos via Wikimedia Commons: US Army Corps of Engineers; FEMA (Casey Deshong, Eliud Echevarria);
US Army (SSG Alfred Batungbacal) — public domain. Generator nameplate: Haweroth, CC BY-SA 4.0. Henschel builder's
plate (holdout h11, used in the video): Franciscus3668, CC BY-SA 4.0. Full lists: `fixtures/*/LICENSES.md`.

## Links (owner to fill)

Video: https://youtu.be/xvGoop1LOUE (YouTube, unlisted, 2:55) · Repository: https://github.com/shro-2002/auditglimmer (public, Apache-2.0) · Hosted demo: not deployed (localhost only; a shared access code exists, no per-user accounts)
