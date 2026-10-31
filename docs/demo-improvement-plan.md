# Demo Improvement Plan — AuditGlimmer (2026-10-31)

Driven by the blind judge's Scenario F and competitive-weakness findings (`judge-review-initial.md`).
Do not record the final video until items marked **before recording** are done and re-judged.

## What the judge said a 3-minute viewer misses

1. Value proposition unclear on arrival → fixed in remediation (landing explanation + guided demo CTA, test sessions collapsed).
2. Visual moment (numbered SAM masks colour-coded by decision) hidden behind a thumbnail click → fixed (auto-select image with detections).
3. Muse contribution invisible in demo (fixture-authored evidence) → **not fixable without a real live run** (see §3).
4. Rule engine (rule IDs, flags) is the strongest asset but takes ~5 min to discover → script §2 leads with it.
5. Business decision ("which collateral needs a field visit") implied, never stated → narrate it; candidate feature in §4.

## 1. Truthfulness rules for footage

- Every DEMO-mode frame must show the DEMO badge; say aloud "fixture providers, no model call".
- Live evidence shown from `ses_34ab4ba56b1b` / `ses_936bef692a74` is a **replay of genuine live calls** — say "recorded live earlier today", show the trace page with "evidence produced in LIVE mode".
- Never show the nameplate serial result as an in-app result unless it was produced in-app (it was produced by a direct script).
- Quote verified numbers only: 6 SAM + 5 Muse calls ≈ $0.039 (or whatever the trace shows after any approved run).

## 2. Recommended 3-minute structure (before recording)

| t | Shot | Point |
|---|---|---|
| 0:00–0:20 | Landing explanation | Lender's collateral auditor: ledger vs site photos; field exams are slow and costly |
| 0:20–1:00 | Guided demo → forklift bay: SAM masks, two lookalike LM-25s | Lookalikes are never auto-verified: `AMBIGUOUS_CANDIDATES`, `COMPETING_FOR_ASSET` |
| 1:00–1:40 | Reconciliation: VERIFIED only on unique serial; misleading ledger rows flagged (duplicate serial, wrong manufacturer, facility mismatch) | Deterministic rules, not a chatbot |
| 1:40–2:15 | Human review: confirm requires a note; result is `HUMAN_CONFIRMED`, not VERIFIED; conflicting second review is flagged and kept | Audit trail integrity |
| 2:15–2:45 | Trace of a real live session (replay): SAM masks on a real US Army forklift photo, Muse reading "HYSTER" | Meta models doing distinct jobs on real photos |
| 2:45–3:00 | Report: DRAFT until every decision reviewed; field-visit list = UNVERIFIED + MISMATCHED + review items | Business decision |

## 3. Highest-value improvement needing owner approval (spend)

The judge's top improvement: one real in-app success where Muse reads a legible identifier and the rule
engine produces a serial-backed VERIFIED match. Constraint found while planning: the nameplate photo is a
close-up of a plate, so SAM with concept "generator" will probably return 0 instances and there is then no
region to extract. Two honest options:

- **Option 3a (no code, ≈ $0.013–0.02):** run SAM "generator" + up to 2 Muse crops on `usace_cat_generator.jpg` /
  `fema_forklift_generators.jpg` with `ledger_real.csv`. Likely outcome: type/manufacturer evidence only → WEAK/PROBABLE. Shows live pipeline, not a serial match.
- **Option 3b (small feature + ≈ $0.008):** add "extract from whole image" for close-up identifier photos
  (1 Muse call, no SAM), add a synthetic ledger row `R-008 Generator, serial 5735` (disclosed as synthetic),
  and show Tier-1 VERIFIED driven by a live Muse transcription. Needs a code change + tests + re-judge.

Recommendation: 3b if the owner accepts ~1 h of work; otherwise 3a. Neither has been run.

## 4. Product gaps the judge named (not built; post-hackathon or if time allows)

- Count roll-up per make/model ("ledger says 3 LM-25, observed 2").
- Field-exam action list: auto-generated "request nameplate photo / schedule revisit" per unresolved asset.
- Borrowing-base impact view (sum of ledger value by status) — must stay labelled "ledger value as stated", never an appraisal.
