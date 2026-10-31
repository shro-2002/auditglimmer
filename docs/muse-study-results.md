# Real-photo Muse Spark effectiveness study — results (2026-10-31)

Protocol: `docs/muse-study-protocol.md` (frozen before the run; hashes in `fixtures/study/PROTOCOL.sha256`).
Raw data: session `ses_8cde3ee6a3bb` in `backend/data/auditglimmer.db` (26 `muse-spark-1.3` calls, raw bodies
under `backend/data/raw/`). Pre-registered scoring: `eval/results/muse-study-preregistered.json`
(sha256 `8eedf5dd…52bd8`). Post-hoc engine analysis: `eval/results/muse-study-posthoc-engine.json`.

> Engineer corrections applied after independent verification (s02 length, 4-not-5 engine losses, source of
> misses, S1 caveat). Numbers in the tables were confirmed unchanged.

## Headline (pre-registered)

| # | Metric | Result | Threshold | Verdict |
|---|---|---|---|---|
| S1 | Unsafe automatic verifications | **1** (s14, an item whose ground truth is *disputed*: reader 1 read 5735, reader 2 read 5765; Muse read 5735 and matched the reader-1 row) | must be 0 | **FAIL** |
| — | …of which verifications to a *wrong* asset among agreed items | **0** | — | — |
| M1 | Exact serial transcription on positives | **11/16 = 68.8%** (Wilson 95% CI 44–86%) | ≥ 70% | **just below — not met** |
| M2 | Serial invented on negatives | **0/8** | ≤ 1 | **PASS** |
| M3 | Distractor number reported as the serial (order no., catalogue no., archive caption, contract no.) | **0** of 4 distractor-bearing photos (s04, s06, s10, s23) | reported | none |
| U1 | Correct automatic verifications | **3/14** verifiable positives (CI 8–48%) | reported | low |
| C1 | Calls / errors / cost / median latency | 26 / 1 schema failure / **$0.158** / 6.2 s | cap $0.30 | within cap |

Decision mix (26 images): VERIFIED 4, MISMATCHED 5, PROBABLE 2, WEAK 13, NOT_IN_REGISTER 1, UNUSABLE 1.

**Caveat on S1 (raised by the independent verifier):** adjudication honoured reader 1's declared alternates
(which made s17 positive) but reader 2 wrote its alternates as free text; for both disputed items reader 2's
text names reader 1's reading (s14: "third char 6 or 3"). Applying the rule symmetrically would make s14
positive (5735) and S1 = 0, with M1 = 12/18 = 66.7% (still below 70%). The frozen result stands — ground truth was
locked before the run and the asymmetry made the test stricter — but s14 is an unconfirmed reading, not a
proven misread. The register rows holding both disputed readings were defined in the pre-run code, not in the
protocol text; without them s14 would have been NOT_IN_REGISTER.

**Pre-registered conclusion: the safety claim ("never auto-verifies unless the identity is certain") is NOT
supported by this study**, because one automatic verification landed on an item that two readers could not
agree on. The model did not mark that reading uncertain, so nothing in the pipeline could have stopped it.
Transcription quality is good but misses the 70% bar by one image.

## What the failures were (all from stored outputs)

| Image | What happened | Classification |
|---|---|---|
| s02 | Muse read the serial correctly (254175 in the raw body) but transcribed a whole plate line (134 chars) into one identifier; the schema's 120-char limit rejected the entire output | fail-closed schema limit (product defect) |
| s03 | read `92233/65` for `92233/58`, **and flagged it uncertain** → no match attempted | honest miss |
| s10 | faint engraved serial: Muse returned null with an uncertainty | honest abstention |
| s17 | dropped one digit (`BP45797`), **flagged uncertain** | honest miss |
| s25 | read `470830 N` — included a suffix letter printed in a separate box; normalised value no longer equals the register serial → NOT_IN_REGISTER (no false match) | transcription convention error, safe outcome |
| s14 | read `5735`; readers disagree (3 vs 6); VERIFIED | **unsafe per protocol** |
| s09 | disputed (5 vs 6); Muse read `264374`, flagged uncertain → WEAK | safe |

**Where the misses came from (corrected after verification).** Of 11 verifiable positives not auto-verified,
4 were lost to the rule engine and 7 to the extraction side (s02 schema overflow; s03/s17 misreads; s10 no
serial; s25 suffix letter; s16/s21 correct but self-flagged uncertain). The 4 engine losses (s05, s07, s08, s20)
ended MISMATCHED only because the plate prints the full maker line ("ANTON PILLER KG", "PRATT & WHITNEY AIRCRAFT",
"LIEBHERR-HYDRAULIKBAGGER GMBH") while the register holds the short name — the engine required exact equality.
Two short serials (692, 604) are below the 4-character Tier-1 minimum by design.

## Post-hoc engine analysis (NOT pre-registered; same stored evidence, no new calls)

Two product fixes were made **after** seeing these results, with regression tests:
1. `same_manufacturer`: the register name matches if its words start the plate's maker line (legal suffixes such
   as GmbH/KG/AG ignored; one direction only; short names must be distinctive).
2. Identifier value limit raised 120 → 300 chars (the s02 failure, 134 chars; the stored s02 output stays a failure because it
   was rejected at the time).

Re-scoring the same stored evidence with the new engine:

| Metric | Pre-registered | Post-hoc |
|---|---|---|
| Correct automatic verifications | 3/14 | **7/14** (CI 27–73%) |
| Verifications to a wrong asset (agreed items) | 0 | **0** |
| Unsafe verification on a disputed item (s14) | 1 | 1 |

**Caveat:** the matching rule was designed after looking at these 26 images, so the post-hoc numbers are
optimistic and need confirmation on fresh photos. They are reported to show where the remaining work is, not as
a validated result.

## What this means for the product (honest reading)

- Muse Spark is genuinely useful on real plates: it transcribed most serials exactly, flagged most of its own
  misreads as uncertain, never invented a serial on 8 negatives, and never confused order/catalogue/caption numbers
  for serials. Without Muse the tool could verify nothing automatically.
- It is **not yet safe enough to auto-verify without a second check**: one confident reading of an ambiguous digit
  produced a VERIFIED. The recommended fix is a double-read gate (two independent reads, or a zoomed re-read of the
  serial region, must agree before Tier 1) — not implemented or tested here.
- Limits: 26 images, AI readers (not independent humans), synthetic register, one run, no retries.

## Independent verification

_Filled in by the independent verifier (separate agent) below. The engineer did not edit this section._

Verifier: a separate agent that did not run the study, 2026-10-31. Method: read-only SQLite
(`sqlite3 -readonly` / `mode=ro`), the raw provider bodies, the fixture files, and GET-only API calls
(`/api/sessions/ses_8cde3ee6a3bb/reconciliation`, `/detections`; API confirmed in `demo` mode). No POSTs and no
live calls were made. Every number was recomputed with a separate script
(`scratchpad/verifier2/verify.py`) that does not import `eval/muse_study.py`.

### Integrity

| Check | Finding |
|---|---|
| `PROTOCOL.sha256` (protocol, ground_truth.json, ledger_study.csv, eval/muse_study.py) | All 4 hashes **match** the files on disk now. |
| `eval/muse_study.py` edited before the run? | Yes, and that is allowed: last modified 18:15:33 IST, after the protocol (18:13:49) but **before** the hash file was written (18:15:45) and before the first paid call (18:17:49). The hash still matches, so it has **not been edited since it was hashed**. The scoring code was therefore fixed before the run. |
| `labels_reader1.json` sha256 `1cfa66bb…3a23` | Matches. `labels_reader2.json` matches the `reader2_sha256` value in ground_truth.json. |
| `muse-study-preregistered.json` sha256 `8eedf5dd…52bd8` | Matches (`8eedf5dd…a52bd8`). `muse-study.json` is byte-identical to it. Both files are read-only. |
| Time order | All 26 provider calls ran 12:47:49.727Z–12:50:35.692Z (18:17:49–18:20:35 IST). That is after the newest frozen-file mtime (18:15:45 IST). The engine fix (`backend/app/reconcile.py`, 18:22:55) came **after** the pre-registered JSON (18:21:46). `schemas.py` (the 300-character limit) came after that, at 18:25:32. The order matches the report's account. |
| Calls / statuses / cost | 26 calls, all `meta-muse` / `muse-spark-1.3` / `live` / `extract`: 25 `ok`, 1 `invalid_output` (s02, `visible_identifiers.2.value` > 120 chars). Summed estimated cost **$0.157861**. True median latency is 6.201 s; the JSON reports 6.204 s because it takes the upper middle value. Both round to 6.2 s. |
| SAM | **No SAM call.** The session has no segmentation call, and the only calls in the whole DB during 12:47–12:51Z are these 26 Muse calls. |
| Stored images | All 26 stored image sha256 values equal the files in `fixtures/study/images/`. The session holds 49 ledger records, the same as the CSV. |
| Not verifiable | That reader 1 was sealed before reader 2 started: all three label/GT files share the mtime 18:15:04. That reader 2 was blind. That the live caps (≤30 calls, +$0.30) were set as stated (spend is under $0.30). The protocol also says the protocol sha256 is recorded in `muse-study.json → protocol`. That field holds only the file path, not a hash. |

### Claims → verdict

| Claim in report | Verdict |
|---|---|
| S1 = 1 unsafe verification (s14, disputed; r1 5735 / r2 5765; Muse 5735 → VERIFIED to the reader-1 row `U-s14-1`) | **CONFIRMED** against the frozen ground truth. Muse's s14 evidence has no uncertainty on the serial (model_confidence 0.9), so "did not mark that reading uncertain" is confirmed. See the adjudication caveat below. |
| Wrong-asset verifications among agreed items = 0 | **CONFIRMED** (pre-registered and post-hoc). |
| M1 = 11/16 = 68.8%, Wilson 44–86% | **CONFIRMED** (0.444–0.858). The misses are s02, s03, s10, s17, s25. s16 (`8.253 379`) counts as exact after normalisation. |
| M2 = 0/8 serials on negatives | **CONFIRMED**. No negative image got any non-empty serial, under any length threshold. |
| M3 = 0 distractors read as the serial, on 4 distractor photos s04/s06/s10/s23 | **CONFIRMED**. |
| U1 = 3/14 (CI 8–48%) | **CONFIRMED**: s15, s19, s22 (0.076–0.476). 14 = 16 positives minus the short serials 692 and 604. |
| C1 = 26 calls / 1 schema failure / $0.158 / 6.2 s | **CONFIRMED**. |
| Decision mix VERIFIED 4, MISMATCHED 5, PROBABLE 2, WEAK 13, NOT_IN_REGISTER 1, UNUSABLE 1 | **CONFIRMED** (from the pre-registered JSON). |
| Pre-registered JSON matches the DB | **CONFIRMED**: its `muse_serial` agrees with the stored evidence for all 26 images. |
| s02: correct serial (254175) in the raw body; one identifier of **170 chars** broke the 120-char limit | **CORRECTED**: 254175 is in the raw body, both as `visible_serial_number` and as its own `serial` identifier. The offending identifier (`kind: other`, the whole plate text) is **134 characters**, not 170. The raw body is 764 characters in total. |
| s03 read `92233/65`, flagged uncertain → no match | **CONFIRMED** (WEAK). |
| s10 null serial with uncertainty | **CONFIRMED**. The decision was PROBABLE: manufacturer and model matched T/D/X rows. |
| s17 read `BP45797`, flagged uncertain | **CONFIRMED** (WEAK). |
| s25 read `470830 N` → NOT_IN_REGISTER | **CONFIRMED**. |
| s09 disputed (5 vs 6), Muse `264374`, uncertain → WEAK | **CONFIRMED**. |
| "Five correct reads (s05, s07, s08, s16, s20) ended MISMATCHED only because of the maker line" | **CORRECTED**: all five were MISMATCHED with `CONFLICTING_MANUFACTURER`. But s16's serial was also self-flagged uncertain, so the fixed engine gives PROBABLE, not VERIFIED. "Only because" holds for **four** (s05, s07, s08, s20). |
| "The bottleneck was the rule engine, not Muse" | **CORRECTED (overstated)**. 11 of the 14 verifiable positives were not auto-verified. The engine's manufacturer rule cost **4** (s05, s07, s08, s20). The Muse/extraction side cost **7**: s02 schema overflow, s03 and s17 misreads, s10 abstention, the s25 suffix, and s16 and s21, which were read correctly but self-flagged uncertain. After the post-hoc fix, all 7 remaining misses are on the Muse side. The engine was *a* bottleneck, not *the* bottleneck. |
| Post-hoc: 7/14 correct (CI 27–73%), 0 wrong-asset, s14 still unsafe | **CONFIRMED** from the current API: s05, s07, s08, s15, s19, s20, s22 (0.268–0.732). Post-hoc decision mix: VERIFIED 8, PROBABLE 4, WEAK 12, NOT_IN_REGISTER 1, UNUSABLE 1. The report does not mention that s01 changed from WEAK to PROBABLE; this has no effect on the metrics. |
| "Muse flagged most of its own misreads as uncertain" | **CONFIRMED, narrowly**: 2 of the 3 wrong transcriptions on positives were flagged (s03, s17). s25 was not. |

### Adjudication and ledger

- **Ledger: built per the hashed code.** 49 rows = 14 positives' T+D (28) + 5 distractor rows + 8 negative rows +
  4 disputed rows + 2 short-serial positives' T+D (4). Every T row's serial normalises to the ground-truth serial.
  No decoy normalises to the true serial or to an accepted alternate. Every normalised serial is unique.
  Manufacturer and model come from reader 1. Two deviations from the protocol text (both are in the
  pre-run hashed code, so neither is post-hoc):
  - When the last two characters are equal (s17 `BP457977`), the decoy bumps the last digit (`BP457978`)
    instead of swapping.
  - The **disputed `U-sNN-k` rows are not described in the protocol's register section**. s14 could only be
    VERIFIED because both readers' readings were registered. Without those rows it would have been
    NOT_IN_REGISTER.
- **Adjudication: mostly mechanical, but not symmetric.** The 8 negatives and 16 positives follow from the
  two label files. For s17, reader 1's structured `serial_alternates` (BP457977) was used to make the item
  positive. Reader 2 recorded its alternates only as free text in `ambiguous_characters`, and for both disputed
  items that text names reader 1's reading:
  - s09: "second char 6 or 5 (264174 vs 254174)"
  - s14: "third char 6 or 3 (5765 vs 5735)"

  The protocol's rule ("same serial … or within a reader's declared alternate characters"), applied to both
  readers equally, would make **s14 positive with 5735** and s09 positive with 254174. Under that reading,
  S1 = 0 (Muse's 5735 would be a correct verification), U1 = 4/16 and M1 = 12/18 = 66.7%; M1 still fails.
  The frozen ground truth is the pre-registered truth, so the pre-registered verdicts stand. The direction of the
  asymmetry is conservative (it made the safety claim harder to pass). But the report should say
  that the S1 FAIL depends on this adjudication call. It should also say that Muse's 5735 agrees with reader 1
  (who rated the plate "clear"), so the case is an *unconfirmed* reading, not a demonstrated misread.

### Honesty assessment

- The pre-registered and post-hoc sections are clearly separated. The post-hoc caveat (rule designed after
  seeing the images, so the numbers are optimistic) is present and adequate.
- The headline numbers are accurate. Nothing is inflated in the study's favour; the failures (S1, M1)
  are reported as failures.
- Overstated or inaccurate: "the bottleneck was the rule engine, not Muse" (see above), "five … only
  because" (four), and "170 chars" (134).
- Missing caveats: the S1 result depends on the asymmetric adjudication of s14; the disputed register rows are
  not in the protocol text; the claimed protocol hash inside `muse-study.json` does not exist; reader sealing
  order and blindness cannot be verified from the files.

### Overall verdict

**Substantially CONFIRMED, with three corrections and one material caveat.** Every pre-registered metric
(S1 = 1, M1 = 11/16, M2 = 0/8, M3 = 0, U1 = 3/14, the decision mix, and C1) reproduces exactly from the raw stored
data. The integrity hashes hold, the calls happened after the freeze, and no SAM call was made. The corrections:
- the s02 identifier was 134 characters, not 170;
- the maker-line failures that the engine fix recovers are four, not five (s16 stays PROBABLE);
- "the bottleneck was the rule engine, not Muse" is overstated: the Muse side accounts for 7 of the 11 missed
  verifications, the engine for 4.

The caveat: the S1 FAIL holds under the frozen ground truth, but it rests on an adjudication that honoured
reader 1's alternates (s17) and not reader 2's (s14). Applied symmetrically, the protocol rule would make s14
positive and S1 pass. The report's overall conclusion ("not yet safe enough to auto-verify without a second
check") stays reasonable either way: on 26 images, S1 is not a strong safety guarantee in either direction.
