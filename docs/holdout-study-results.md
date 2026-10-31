# Fresh holdout study — results (LIVE, 31 Oct 2026)

Protocol: `docs/holdout-study-protocol.md` (frozen; `fixtures/holdout/FROZEN.sha256` verified by the runner before
the first call). Session `ses_63033bcece24`. Raw scorer output: `eval/results/holdout-study.json`.
This is the **fresh holdout** result set. It is separate from the historical pre-registered 26-photo study and from
the post-hoc re-scoring (`docs/muse-study-results.md`), and is never pooled with them.
Independent verification: see the last section.

## Run

- 14 photos, 12 concept runs, full-frame regions (SAM not called), 12/12 runs succeeded, 0 provider errors.
- **19 Muse Spark calls**: 14 first reads ($0.0844) + 5 second reads ($0.0356) = **$0.1200**.
  Mean cost per inspection $0.0086; median latency per inspection (both reads) 7.6 s.
- Spend against the shared $0.30 ceiling: Phase 3 proof $0.0068 + holdout $0.1200 = **$0.1268**. No retries.

## Pre-registered metrics (n is small; Wilson 95% CIs)

| # | Metric | Result |
|---|---|---|
| H1 | Unsafe automatic verifications | **0** (0 by design: whole-photo regions cannot verify under D-17) |
| H2 | Exact serial on positives (first read) | **5/6** (83%, CI 44–97%) — h14 read `3554`, truth `8534` |
| H3 | Verification precision | n.a. (no VERIFIED) |
| H4 | Correct automatic verification yield | 0/6 (by design) |
| H4b | Correct single-candidate suggestion | **5/6** (CI 44–97%) |
| H4c | "Wrong" single-candidate suggestions (pre-registered definition) | 6: h04, h07, h08, h09, h12, h13 — see note |
| H5 | Abstention on verifiable positives | 1/6 (h14) |
| H6 | Unsafe verification rate | 0/14 (CI 0–21.5%) |
| H7 | Two-read: second reads / agree / disagree-or-failed | **5 / 5 / 0** |
| H8 | Serial emitted on negatives | 1 (h04 — a printed distractor number, read with uncertainty) |
| C | Calls / errors / cost | 19 / 0 / $0.1200 |

Confusion matrix (ground truth × outcome): positive → 5 suggest_correct, 1 abstained; negative → 5 suggest_wrong,
2 abstained; disputed → 1 suggest_wrong. No `correct` or `unsafe` outcomes (no VERIFIED at all).
Decision mix: WEAK 7, MISMATCHED 4, PROBABLE 3.

## What the numbers do and do not show

- **Muse transcription held up on new photos:** 5 of 6 agreed serials read exactly, no prompt or rule tuning after
  any holdout output. One clean misread (h14) — the second read was not triggered there because the first read's
  serial did not reach the certainty bar.
- **The second read ran live for the first time:** 5 second reads, all agreeing with the first read. So on this set
  the gate *did not catch anything*; its live disagreement rate is 0/5. It remains an experimental safeguard, untested
  against a real disagreement.
- **Safety came from the rules, not from luck:** the D-17 whole-photo rule means no plate photo can auto-verify;
  the only `R2e_*` block observed was h11 (whole-photo). The baseline without Muse gives 0 suggestions; Muse +
  rules gave the reviewer the correct single candidate on 5 of 6 readable plates.
- **H4c note (definition, not re-scored):** the pre-registered definition counts any single candidate that is an
  `N-` row as "wrong". For h07/h08/h09/h13 the single candidate is `N-hNN`, the registered unit of that type whose
  serial is not visible — by construction the unit pictured, offered as a type-only WEAK suggestion. Genuinely
  misleading suggestions are **h04** (Muse read a printed distractor, `ZF1P4000`, as an uncertain serial → suggests
  distractor row `X-h04-4`) and **h12** (disputed item; both reads gave `1S7P205`, matching reader 1's register row
  `U-h12-1`, held as MISMATCHED for review). Neither reached VERIFIED.
- **Register artefact:** h03, h05, h06 and h12 are MISMATCHED (`CONFLICTING_MANUFACTURER`) because the synthetic
  register copied reader 1's long maker lines and the engine only accepts the register name as a prefix of the read
  text: place names for h03 ("…, Glasgow") and h06 ("…, Edinburgh"), a suffix "(ZH)" for h05, and for h12 Muse read
  only "Westinghouse" against "Westinghouse Electric & Manufacturing Company, East Pittsburgh" (corrected after
  independent verification). This sends items to review (the safe
  direction) and would not occur with the short names real registers usually hold. Not corrected after the fact.
- Labels are AI-only (two AI readers, sealed before the run); single source site (Wikimedia Commons); n = 14.

## Post-hoc 3-arm comparison (not pre-registered; same stored outputs, no new calls)

`eval/holdout_arms.py` → `eval/results/holdout-arms.json`. Arms differ only in the rules applied to the same photos,
register, ground truth and stored Muse outputs. Arm 2 uses the rule engine exactly as committed at `c7d6206`
(before the gate).

| Arm | Correct auto-verifications | Unsafe | Correct single suggestion | Abstained (of 6) | Muse calls | Cost | Median latency / inspection |
|---|---|---|---|---|---|---|---|
| 1 Rules, no Muse identifiers | 0/6 | 0 | 0/6 | 6 | 0 | $0 | — |
| 2 Rules + Muse single read (c7d6206) | 0/6 | 0 | 5/6 | 1 | 14 | $0.0844 | 6.5 s |
| 3 Rules + Muse + two-read gate (current) | 0/6 | 0 | 5/6 | 1 | 19 | $0.1200 | 7.6 s |

Reading: Muse is what turns "check every asset" into a correct single candidate for 5 of 6 readable plates. On this
set **no arm auto-verified anything**: the old engine was already held back by register conflicts (the long maker
names noted above) and uncertainty flags. The gate changed one decision (h11 → `R2e_WHOLE_PHOTO_ASSOCIATION_UNSUPPORTED`)
and added 5 calls (+42% cost, +1.1 s median). **This set gives no evidence that the gate prevents errors**; its value
here is architectural (whole-photo plates can never auto-verify), not measured.

Note: after this run the engine changed again (near-full-frame SAM masks are treated as whole-photo; a missing second
read is retried in place). The executed run's code is commit `5b26076`, hashed in `fixtures/holdout/FROZEN.sha256`;
`holdout_study.py run` now refuses to re-run against changed code, by design.

## Live footprint after this run

SQLite now records 6 SAM + 50 Muse live calls ($0.3153); with the two persisted off-pipeline calls
(`live-smoke.json` 1 SAM, `live-muse-nameplate.json` 1 Muse $0.0057): **7 SAM + 51 Muse ≈ $0.3235**.

## Independent verification

**31 Oct 2026, separate agent, API in DEMO, no paid calls.** Verdict: **CONFIRMED, with one wording correction.**

Checked: both label seals and all 25 `FROZEN.sha256` lines match. Every frozen file's mtime (latest 19:43:39 IST) is
before the first session call (14:27:18Z = 19:57:18 IST). Adjudication follows the mechanical rule (6 positive,
7 negative, h12 disputed). I recomputed every number from SQLite, the 19 raw files and the ground truth, without
the scorer. H1–H8, the confusion matrix, the decision mix, calls (14 extract $0.084413 + 5 confirm $0.035556 =
$0.119969), mean $0.008569 and median latency 7.62 s all equal `holdout-study.json`.

CONFIRMED:
- The h14 first read carried a `visible_serial_number` uncertainty, so `needs_confirmation` was false.
- h04 and h12 are as described.
- No R2e block other than h11.
- 12/12 runs; 19/19 calls `ok`.
- Live SQLite 6 SAM + 50 Muse = $0.315271 (one is a $0 `invalid_output` row in an earlier session). Total ≈ $0.3235.
- Kept separate from the 26-photo study.

CORRECTED (register artefact): only h03 (Glasgow) and h06 (Edinburgh) are place names. For h05 the extra register
token is "(ZH)". For h12 Muse read only "Westinghouse", and the register adds "Electric & Manufacturing Company,
East Pittsburgh". Without the place name, h12 would still be MISMATCHED. All four still pass with a short register
name, so the conclusion holds.

Caveats: transport-level retries are not logged. "No retries" is verified only at study level (one call per read,
latencies 4.6–10.2 s). Labels are AI-only. n = 14.
