# Judge review — round 4 (independent, first-time, blind to earlier reviews)

Date: 2026-11-01 · Mode verified: `GET /api/config` returned `"mode":"demo"`, `live_approved:false`, models `fixture-sam` / `fixture-muse`.
No servers were started, stopped or reconfigured. No live or paid calls were made. Sessions I created are named `judge r4 …`.
Screenshots and scripts: `/private/tmp/claude-501/-Users-shroddhaghosh-Desktop-Hackathons-Meta-Global-AI-Developer-Hackathon/c772fe5e-ae8e-4d44-998c-b12a85b996f6/scratchpad/judge4/`.

## Criteria source

https://cerebralvalley.ai/e/meta-ai-developer-hackathon (fetched 2026-11-01). It says the Indie developer track is "Judged on
creativity, technical ambition, and whether it works", with **no weights**. The only weighting on the page ("both criteria are
weighted equally") applies to application review, not to judging. So each criterion is weighted 1/3 here.

## Scores

| Criterion | Score /10 | Why |
|---|---|---|
| Creativity | 6.5 | A sensible, specific use case: reconciling collateral registers against photo evidence. The best idea is the stance that the model reads, rules decide, and humans own the ambiguity, with "UNVERIFIED ≠ missing" kept explicit. It is a careful idea rather than a surprising one, and the UI is a competent dark dashboard, not a memorable one. |
| Technical ambition | 7.0 | The two models have clearly separate jobs (SAM 3.1 gives masks and geometry, Muse Spark 1.3 gives closed-schema JSON). There is a deterministic tiered engine, a two-read gate, a full provenance graph, spend caps and failure-mode handling. The studies were pre-registered and frozen, and their failure (s14) is reported honestly. 144 backend tests pass (re-run by me). The live footprint is small (56 calls in the DB), and no real photo has ever reached Tier 1. |
| Whether it works | 6.5 | DEMO works end to end in under a second per page with no console errors, and no horizontal overflow at 375 px. I attacked it 18 ways and it never auto-verified anything it should not. But a correct match is labelled MISMATCHED whenever the register uses a legal or longer company name (D1). The guided demo's happy path shows red "Run error" states. The overview counts are polluted by roughly 340 test sessions. A report reads "FINAL" with nothing inspected. Live capability is only shown as replays. |
| **Total (equal weights)** | **66.7 / 100** | (6.5 + 7.0 + 6.5) / 3 × 10 |

## First 30 seconds — verdict: PASS (with noise)

Cold load of `/` took 1.3 s. Above the fold I saw a one-sentence problem statement ("reconcile the equipment ledger against what the site photos
actually show"), a six-step pipeline naming SAM 3.1 and Muse Spark 1.3, and two clear buttons: **Start guided demo** and **See the
evidence challenge**. I understood the problem and knew what to click within about 15 s. "Start guided demo" opened a ready
session in 204 ms with `generator` prefilled.

Noise that costs credibility right away:
- The stat row directly under the buttons says **360 sessions, 2,821 reviews pending, 133 VERIFIED, 5,927 ledger assets**. These come from about 340
  `e2e …`, `verify …` and `judge …` test sessions. A first-time judge reads this as either a busy production system or test litter.
- "Recent sessions" is a list of `judge r3 T1 … T9` and `E2E journey` entries.

## Model-contribution verdict: both models visibly contribute; the claims check out against the trace and raw outputs

- `/challenge` Case A comes from session `ses_936bef692a74`. The DB shows `sam-3.1` segment `call_ab8feee7ee1b` (2,420 ms, $0.0025) followed by two
  `muse-spark-1.3` extract calls. The raw file `backend/data/raw/call_90b3392954ee.txt` matches the panel field for field
  (`visible_manufacturer: "HYSTER"`, no model or serial, confidence 0.85, the same five condition notes). The raw SAM output gives box 2 with
  c=0.68, which matches the panel's "68%". The masks on the photo are real SAM RLE, not boxes. The rules gave WEAK / R3_TYPE_ONLY with two
  Hyster candidates (R-002, R-003), so Muse's read narrowed the register from all forklifts to two rows. That is a real, visible contribution.
- Case B is clearly labelled DEMO fixture, and the page says no live photo has reached Tier 1. That is honest.
- Live footprint: `provider_calls` has 6 `sam-3.1` + 45 `muse-spark-1.3` extract + 5 confirm calls, $0.3153. With `live-smoke.json` (1 SAM,
  0 objects on the synthetic image) and `live-muse-nameplate.json` (1 Muse), that matches the stated **7 SAM + 51 Muse ≈ $0.3235**.
- Holdout claims match `eval/results/holdout-study.json`: serial 5/6 (Wilson 0.44–0.97), 0 unsafe, 5 second reads all agreeing, $0.119969,
  19 raw files. The arms numbers (0/6, 5/6, 5/6) match `holdout-arms.json`.
- Caveat: SAM's live contribution rests on 6 calls and 3 photos. Every holdout item skipped SAM (whole-photo plates), so the headline study
  measures Muse only.

## Is the decision meaningful? Adversarial results (DEMO, fixture reads fixed, register attacked)

Control: the exact row gives VERIFIED Tier 1 (R1_UNIQUE_SERIAL_MATCH).

| # | Attack | Result | Safe? |
|---|---|---|---|
| T1 | Look-alike serial GN-48218 | MISMATCHED (R6) | yes |
| T2 | OCR-confusable GN-4821B | MISMATCHED (R6) | yes |
| T15/T16 | Padded GN-048213 / truncated 48213 | MISMATCHED (R6) | yes |
| T3/T14 | "GN 48213", "gn48213" + lowercase maker/model | VERIFIED (separator and case normalisation) | acceptable, documented normalisation |
| T4 | Serial-only row, no type | row rejected at upload (`asset_type is required`) | yes |
| T5 | Serial + type only, no maker/model | PROBABLE (R2e_NO_CORROBORATING_ATTRIBUTE) | yes |
| T6 | Same serial, different maker | MISMATCHED (R5) | yes |
| T7 | Serial duplicated in register | PROBABLE (R2b) | yes |
| T8 | Register says forklift | MISMATCHED (R5) | yes |
| T9 | Maker matches, model differs | MISMATCHED (R5) | yes |
| T10 | Whole-photo region (SAM skipped), correct row | PROBABLE (R2e_WHOLE_PHOTO_ASSOCIATION_UNSUPPORTED) | yes |
| T11 | Second read disagrees (GN62040 vs GN62046) | PROBABLE (R2e_CONFIRMATION_SERIAL_DISAGREES) | yes |
| T12 | Same serial on objects in two photos | PROBABLE (R2d) for both | yes |
| T13 | Row registered at another facility | MISMATCHED (facility) | yes |
| T17/T18 | Register maker "Cumberland Power Systems, Ltd" / "CPS", everything else correct | **MISMATCHED** | safe, but wrong label (D1) |

Verdict: the gate is meaningful and conservative. I could not trigger an unsafe auto-verification in DEMO. The limit is that DEMO fixes the
model reads, so only the register can be attacked. Real-model failure modes (the s14 class) can only be judged from the stored studies.

## Unsupported or overstated claims

1. **"correct single suggestion to the reviewer 5/6"** (README, submission). 3 of those 5 (h03, h05, h06) reach the reviewer labelled
   **MISMATCHED / "other identifiers conflict"**, even though both reads agree and the unit is correct. The cause is the prefix-only
   manufacturer match against long register names. This is disclosed deep in `docs/holdout-study-results.md` but not where the 5/6 is quoted.
   Telling a reviewer "conflict" on a correct unit is not a clean "correct suggestion".
2. **Session title "Phase 3 end-to-end proof — real photo, SAM + two Muse reads (LIVE)"** (shown on the home page). The DB has only **one** Muse call
   for `ses_bdf8d59682c3`, and no confirm call. The submission text itself says no second read was needed. The title overstates.
3. **README post-hoc row "correct auto-verifications 3/14 → 7/14"** leaves out that the same post-hoc engine still had **1 unsafe
   verification (s14)** (`muse-study-posthoc-engine.json` `false_auto_verifications.k = 1`).
4. **"SAM 3.1 … Segments every instance of an asset type in each photo"** (home page). The evidence is 6 live SAM calls on 4 real photos. The live smoke
   test returned 0 objects on the synthetic image. No SAM recall measurement exists (fixture eval says "identity check … not SAM IoU").
5. **Hosted-demo wording is inconsistent.** The submission says "not deployed (no authentication yet)", while the README describes an `AUDITGLIMMER_ACCESS_CODE`
   gate. Pick one.
6. Supported claims (checked): 144 backend tests pass; 17 browser tests + 1 live spec exist; 7 SAM + 51 Muse ≈ $0.3235; holdout
   metrics; "Muse never sees the register" (`muse_meta.py` sends crop + concept only); "no live Tier 1 yet" is stated honestly.

## Top 5 defects

| # | Severity | Defect | Repro |
|---|---|---|---|
| D1 | High | Correct matches are labelled MISMATCHED when the register maker is a longer legal name or an abbreviation. The prefix-only manufacturer comparison produces false "conflict" alarms on real registers (3/6 holdout positives). | New session, WH-01. Upload a register row `A-001,Industrial generator,"Cumberland Power Systems, Ltd",PX-500,GN-48213,WH-01,…` and `bay_a_generators.png`. Run `generator`: det 1 is MISMATCHED R5 (sessions `judge r4 T17`, `T18`). |
| D2 | Medium | The overview and "Recent sessions" are polluted by about 340 test sessions: 360 sessions, 2,821 pending reviews, 133 VERIFIED shown to a cold visitor. | Open `/`. |
| D3 | Medium | A report is marked **FINAL** ("All decisions are reviewed") when nothing has been inspected (18/18 NOT_OBSERVABLE, 0 runs). | Create a session, load the demo dataset, open Report, or call `GET /api/sessions/{sid}/report?format=json` → `report_state: "FINAL"` (`judge r4 empty report`). |
| D4 | Medium | The guided-demo happy path shows red "Run partial · Run error: 2 step(s) failed" on the first click. These are intentional failure-mode fixtures, but nothing says so at that point, so a first-time judge reads it as broken. | Start guided demo → Run inspection. |
| D5 | Low | The live session title claims "two Muse reads" but only one was made. On `/challenge` Case A, the panel says "provider object id 1" while the overlay badge says "2" for the same region. | Home page live list; `/challenge` Case A. |

Also noted: on the Evidence page, Case B creates a new DEMO session as a side effect of a page view when none exists. At 375 px there is no page
overflow, and the tab bar scrolls sideways (acceptable). All pages loaded in about 0.6–1.3 s, with no console errors or 4xx/5xx responses.

## The 3 highest-impact fixes

1. **Normalise manufacturer comparison** (strip legal suffixes like Ltd/Inc/Co., place names and punctuation, and use token-subset matching either way). If a maker is
   only "not corroborated" rather than "contradicted", return PROBABLE, not MISMATCHED. Then restate the holdout as "5/6 correct suggestions, of which N
   flagged as conflicts". This turns the main honest result into a clean one.
2. **Clean the stage.** Hide or archive test sessions (filter `e2e*`, `verify*`, `judge*`, or add an "archived" flag) so the overview shows only the
   guided demo, the evidence challenge and the 5 live sessions. Label the intentional demo failures inline ("expected: malformed-output test
   case").
3. **Make the claims exact.** Rename the "two Muse reads" session. Add "1 unsafe (s14) remains" to the post-hoc row. Qualify "5/6" with the MISMATCHED
   labels. Make the report state DRAFT/EMPTY when no inspection run exists.
