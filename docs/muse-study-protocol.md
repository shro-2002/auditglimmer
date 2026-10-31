# Real-photo Muse Spark effectiveness study — pre-registered protocol

Status: **frozen before any paid call** (sha256 of this file is recorded in `fixtures/study/PROTOCOL.sha256`
and in `eval/results/muse-study.json` → `protocol`). Changing it after the run invalidates the study.

## Question

On real, licensed photographs of equipment identification plates, does Muse Spark 1.3 read the unit's
identifying serial accurately enough that AuditGlimmer's deterministic rule engine can automatically verify
register assets — **without ever auto-verifying the wrong asset or a unit whose serial cannot be read**?

## Data

- 26 photographs in `fixtures/study/images/` (s01–s26, neutral names, shuffled with seed 20261031,
  re-encoded to strip EXIF/GPS, ≤ 2048 px). 21 from Wikimedia Commons (CC0 / public domain / CC BY / CC BY-SA;
  provenance and attribution in `fixtures/study/LICENSES.md`), 5 from the existing `fixtures/real/` set.
- Content: generator, motor, engine, excavator, tractor, compressor, switchgear, transformer and outboard-motor
  plates; two same-model look-alike pairs (identical model, serials differ by one character); wide scenes and
  plates with a redacted, illegible or absent serial (negatives); plates with prominent non-serial numbers
  (order no., catalogue no., archive caption) as distractors.
- No photo was chosen or excluded after seeing any model output. One candidate (a tractor plate too small to read)
  was excluded by reader 1 before labelling closed.

## Ground truth (two readers, adjudicated before the run)

- **Reader 1** (main session) labelled all images and sealed the file (sha256 `1cfa66bb…3a23`) before reader 2 started.
- **Reader 2** (separate agent) labelled blind: saw only the neutral images, not reader 1's labels, the
  Commons titles or any model output.
- Both readers are AI assistants (same model family) — **not independent human ground truth**. Disclosed.
- Adjudication rule (mechanical):
  - both readers give the same serial (after normalisation: uppercase, separators removed, or within a reader's
    declared alternate characters) → `positive`, that serial;
  - both give no readable serial → `negative`;
  - otherwise → `disputed` (excluded from accuracy denominators; still counted for safety).
- Normalised serials shorter than 4 characters cannot reach Tier 1 by design; such items are positive for
  transcription accuracy but excluded from the auto-verification denominator.

## Register (ledger) design — synthetic, disclosed

Built mechanically from ground truth by `eval/muse_study.py ledger` (facility `WH-S`):
- every positive: a **true** row `T-sNN` and a **look-alike decoy** `D-sNN` (same manufacturer/model/type,
  serial with the last two characters swapped);
- every distractor number printed on a photo: a row `X-sNN-k` whose "serial" is that distractor — matching it
  would mean the model read the wrong number;
- every negative with a known type: a registered unit `N-sNN` whose serial is not visible.
- Manufacturer and model text are taken from reader 1's reading of the plate.

## Procedure

- API restarted in LIVE mode with caps: ≤ 30 Muse calls, all-time live spend cap raised by **$0.30 only**,
  per-session request cap 30. SAM is **not** called: each photo is a full-frame region (auditor-declared close-up).
- One full-frame run per declared asset type (the auditor's concept), `extract=true`: one Muse Spark call per image.
- No retries, no prompt changes, no re-runs. If any call fails it is reported as a failure.

## Metrics and pre-registered thresholds

| # | Metric | Threshold for the claim |
|---|---|---|
| S1 | False automatic verifications (VERIFIED to anything other than `T-sNN`, or on a negative/disputed item) | **must be 0** — otherwise the safety claim fails |
| M1 | Exact serial transcription on positives (Wilson 95% CI) | "effective" if ≥ 70% |
| M2 | Serial emitted on negatives (hallucination) | "effective" if ≤ 1 |
| M3 | Distractor number reported as the serial | reported; each case is a finding |
| U1 | Correct automatic verifications / verifiable positives | reported with CI — the share of field checks the tool removes |
| U2 | Decision mix (VERIFIED / PROBABLE / MISMATCHED / WEAK / NOT_IN_REGISTER / UNUSABLE) | reported |
| C1 | Calls, errors, estimated cost, median latency | reported |

Baseline: without Muse there is no visual identifier, so the rule engine can verify **0** assets; every asset
would need a field check. This study measures how much of that work Muse plus the rules can remove, and at
what error rate.

## Independent verification

A separate agent that did not run the study recomputes every metric from raw stored outputs
(SQLite + raw provider files) and ground truth, checks the claims written in the results report, and records
its verdict in `docs/muse-study-results.md`.
