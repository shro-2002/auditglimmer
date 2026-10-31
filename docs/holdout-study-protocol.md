# Fresh holdout study — two-read Tier 1 gate — pre-registered protocol

Status: **draft until `fixtures/holdout/FROZEN.sha256` exists.** `eval/holdout_study.py freeze` hashes this file,
both label files, the adjudicated ground truth, the ledger, provenance, the runner/scorer, the rule engine,
the Muse prompts and the pipeline. `run` refuses if any frozen file changed. No paid call is made without the
owner's explicit approval.

## Separation of results (never mixed in any report)

| Result set | Source | Status |
|---|---|---|
| Original pre-registered | 26 photos, `docs/muse-study-protocol.md`, `eval/results/muse-study.json` | frozen, immutable; S1 FAILED (s14) |
| Post-hoc development | same 26 photos re-scored after engine changes, `eval/results/muse-study-posthoc-engine.json` | not pre-registered; optimistic by construction |
| Fresh holdout (this file) | 10–15 new photos, `fixtures/holdout/`, `eval/results/holdout-study.json` | pending owner approval |

## Question

With the two-read confirmation gate in front of Tier 1, on photos the system has never been tuned on, does
AuditGlimmer (Muse Spark 1.3 + deterministic rules) auto-verify **only** correct register assets, and how much
field-check work does it still remove compared with the no-Muse baseline (0 automatic verifications)?

## Data

- 10–15 licensed photographs (CC0 / public domain / CC BY / CC BY-SA), none of the 26 earlier images or another
  photo of the same physical plate. Provenance and attribution in `fixtures/holdout/LICENSES.md` and
  `provenance.json`. Re-encoded (EXIF/GPS stripped, ≤ 2048 px), neutral names h01…hNN shuffled with seed 20261101.
- Includes negatives (no legible serial), distractor numbers and, where available, look-alike plates.
- No photo is chosen, excluded or relabelled after any model output exists.
- **As built (2026-10-31, before freezing):** 14 photos, 0 excluded, all from Wikimedia Commons (h10 is a US
  federal HAER/NPS work hosted there) — *a single source site, disclosed*. Families: tractor, wheel loader,
  telehandler, 2 locomotive builder's plates, current transformer, 2 generators, steam roller, crane badge,
  elevator, pumping engine, marine DC motor, hand pump. No look-alike pair was found.
  Adjudicated: **6 positive, 7 negative, 1 disputed (h12)**; all 6 positive serials are ≥ 4 characters, so
  n_verifiable = 6. **n is small: every rate below has a wide CI.**
- Offline check before freezing found that six holdout families were not accepted run concepts (the API would
  have rejected those runs mid-study). The concept vocabulary (`TYPE_SYNONYMS`) was extended with locomotive,
  wheel loader, telehandler, roller, elevator, pump and electrical equipment. No matching rule changed.

## Ground truth

- Reader 1 (sourcing agent) labels from pixels and seals `labels_reader1.json` (sha256 file) before reader 2 starts.
- Reader 2 (separate agent) labels blind: sees only h01…hNN images — not reader 1's labels, Commons titles,
  provenance or any model output.
- **Both readers are AI assistants of the same model family. These are AI-only labels, not independent human
  ground truth.** If a human verifies labels before the run, that is recorded here before freezing.
- Mechanical adjudication (`adjudicate`): both readers give the same normalised serial → `positive`;
  neither gives a readable serial → `negative`; anything else → `disputed` (excluded from accuracy
  denominators, still counted for safety — a VERIFIED on a disputed item is unsafe). Unlike the original
  protocol there are **no alternate-character allowances**, so the rule is symmetric between readers
  (this removes the s14 adjudication asymmetry).

## Register (synthetic, disclosed)

Built mechanically by `ledger`: a true row `T-hNN` and a one-transposition look-alike `D-hNN` per positive;
a row `X-hNN-k` per distractor number (≥ 4 chars); both readings `U-hNN-1/2` per disputed item; an unseen-serial
unit `N-hNN` per negative. Same structure as the original study.

## Procedure

- All offline checks first: backend tests, `dry-run` against the DEMO API (must show $0 and no model call).
- LIVE only after owner approval, API restarted with `AUDITGLIMMER_MODE=live`, `AUDITGLIMMER_LIVE_APPROVED=1`
  and `AUDITGLIMMER_MAX_LIVE_USD_TOTAL` = current recorded all-time live spend **+ $0.30** (hard stop).
- Full-frame regions (auditor-declared whole photo, SAM not called). One run per declared asset type.
- First read: one Muse call per image. Second read: one Muse call only when the first read has a certain,
  readable serial (enhanced view: ×2 upscale capped at 1536 px, autocontrast, unsharp mask; identifier-only prompt).
- **Retry policy:** no study-level retries, no re-runs, no prompt changes. The HTTP transport retries
  429/500/502/503 up to 2 times inside one logical call (existing behaviour); a failed call is reported as a
  failure and, for a second read, makes the item abstain.
- Tier 1 policy: `two_read` (default).

## Metrics and pre-registered thresholds

**Design rule D-17 (approved by the owner before the run):** a whole-photo region cannot establish which physical
unit a plate belongs to, and Tier 1 also needs a corroborating manufacturer or model. Every holdout item is a
whole-photo region, so **automatic verification is impossible by design** and H1/H3/H4 are expected to be 0/n.a.
The useful output is a **single-candidate suggestion** to the human reviewer; that is what H4b/H4c measure.

| # | Metric | Threshold |
|---|---|---|
| H1 | Unsafe automatic verifications (VERIFIED to anything but `T-hNN`, or on a negative/disputed item) | **must be 0** (0 by design here) |
| H2 | Exact serial transcription (first read) on positives, Wilson 95% CI | reported; "effective" if ≥ 70% |
| H3 | Automatic verification precision | n.a. if no VERIFIED |
| H4 | Correct automatic verification yield | 0 by design (D-17) |
| H4b | Correct single-candidate suggestions (only candidate = `T-hNN`) / verifiable positives, Wilson 95% CI | reported (benefit vs baseline 0) |
| H4c | Wrong single-candidate suggestions (only candidate is a decoy, distractor, disputed or N- row) | reported; each case is a finding |
| H5 | Abstention (no single candidate) on verifiable positives | reported |
| H6 | Unsafe verification rate over all items, Wilson 95% CI | reported |
| H7 | Two-read agreement / disagreement / failure; gate blocks by rule | reported (first live test of the second read) |
| H8 | Serial emitted on negatives | "effective" if ≤ 1 |
| C | Calls, errors, cost per inspection, median latency per inspection (both reads) | reported |

Confusion matrix: ground-truth status (positive / negative / disputed) × outcome (correct / unsafe /
suggest_correct / suggest_wrong / abstained). n is small (6 verifiable positives): a 0/14 unsafe result has a Wilson
upper bound near 22%. **The two-read gate stays an experimental safeguard, not a validated safety guarantee.**

## Paid-call proposal (requires explicit owner approval)

Already spent under the owner's earlier approval (31 Oct, 19:39 IST, before D-17): Phase 3 end-to-end proof,
`fixtures/real/usace_cat_generator.jpg` → SAM 3.1 (1 call, $0.0025) → Muse (1 call, $0.00434) → rules: WEAK
(Muse saw no legible serial, so no second read was triggered). **$0.00684 of the $0.30 ceiling is used.**

Measured Muse cost (31 recorded calls): mean $0.00587, max $0.00805. The second read's larger view is unmeasured;
the worst case assumes 1.5 × the max ($0.0121).

| Item | Requests (exact bound) | Projected | Worst case |
|---|---|---|---|
| Phase 3 proof (done) | 2 | $0.00684 (actual) | — |
| Holdout first reads: 14 images, 12 concept runs, full-frame (no SAM) | **14** | $0.082 | $0.113 |
| Holdout second reads: only when the first read has one certain serial (expected ≈ 6–8) | **0–14** | ≈ $0.06 | $0.169 |
| **Total under the shared ceiling** | **16–30** | **≈ $0.15** | **$0.289 ≤ $0.30** |

Hard stop: API restarted with `AUDITGLIMMER_MAX_LIVE_USD_TOTAL=0.4884` (recorded all-time live spend before this
work $0.188462 + $0.30), per-session request cap 30, per-run $0.30. The pipeline reserves $0.0123 before each Muse
call and refuses a call that could cross the cap; the runner also stops if session spend exceeds $0.30.
No retries beyond the transport's 2 retries inside one logical call. API returns to DEMO immediately after.

## Independent verification

A separate agent recomputes every metric from stored raw outputs and ground truth and checks every claim in
`docs/holdout-study-results.md` before it is cited.
