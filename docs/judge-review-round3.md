# Judge review, round 3: AuditGlimmer

Date: 2026-10-31. I reviewed blind: I did not open any `docs/judge-*` file other than this one, `docs/remediation-evidence/`, `docs/judge-evidence/`, or the release, blocker, plan or evaluation-report files I was told to avoid.
Environment: the API reported `{"mode":"demo","live_approved":false,"segmentation_model":"fixture-sam","extraction_model":"fixture-muse"}`. I made no paid calls and started, stopped or reconfigured no server.
Screenshots and exports are in `/private/tmp/claude-501/-Users-shroddhaghosh-Desktop-Hackathons-Meta-Global-AI-Developer-Hackathon/c772fe5e-ae8e-4d44-998c-b12a85b996f6/scratchpad/judge3/`.
Another process held the Playwright MCP browser, so I used the Claude Browser pane and the repo's own headless Playwright (`e2e/node_modules`), driven by scripts in the scratchpad.

## 1. Judging criteria (verified)

**Source:** https://cerebralvalley.ai/e/meta-ai-developer-hackathon (the `.md` rendering of the same page), fetched 2026-10-31.

- **Indie track:** "Judged on creativity, technical ambition, and whether it works."
- **Startup track:** "Judged on technical execution and whether it holds up in production."
- The page gives **no scoring weights**. The phrase "Both criteria are weighted equally" refers to application review, not to project judging.
- **Themes:** "Build for Your World" or "Push the Frontier".
- **Expected tools:** "Use the Muse Spark series, Muse Wonder, Muse Image and SAM 3.1 through Meta Model API".
- **Key dates:** submissions due Nov 4, 9:00 PM ET; judging Nov 4–8; finals Nov 9.

The submission names the Indie track ("owner to confirm"). I therefore scored the three Indie criteria with **equal weights (33.3% each)**.

The submission draft (`docs/submission-final.md`) cites "official weights" of Impact 30 / Use of Meta AI Tooling 25 / Technical Depth 20 / Demo 25. **That rubric is not on the official page.** It only appears in third-party repositories and blogs. For transparency, section 9 also gives a sensitivity score under it.

## 2. Guided demo (from the overview page)

I clicked **Start guided demo** on `/`. The click is real; I used request interception only to rename the session it creates to `judge r3 guided demo` (`ses_41d16468bd18`). I then ran `industrial generator` and `forklift` and walked through Reconciliation, Review queue, Report and Observability.

**Works:**
- The flow runs end to end with no crashes.
- Masks are overlaid on the images, and each detected region shows its evidence, the rule applied, the tier and an explanation.
- The ledger outcome was 18 assets: VERIFIED 2, PROBABLE 6, MISMATCHED 2, UNVERIFIED 5, NOT_OBSERVABLE 3. There were 16 decisions, 11 of which need review.
- Failure modes are handled deliberately:
  - malformed JSON is reported as such;
  - the `estimated_value_usd` field the model was asked not to produce is rejected;
  - a timeout is reported;
  - a serial duplicated in the register becomes PROBABLE (rule R2b);
  - the same serial seen on two objects becomes PROBABLE (rule R2d);
  - a "pallet jack" reported where a forklift was expected is flagged as a type disagreement.
- The Observability page lists 30 fixture calls (segment, extract and confirm) at $0.

**Rough edges in the happy path:**
- Both runs end as **"Run partial"**, with a red **"Run error: 2 step(s) failed"**. These are the scripted failure fixtures, but a judge sees red errors in the main demo.
- The overview counts every stored session: 207+ sessions, 3,487 assets and **1,673 pending reviews**. The recent-sessions list is dominated by test and earlier-judge sessions. This hurts the first impression.

Screenshots: `01-overview.png` … `08-trace.png`.

## 3. Stored real Meta evidence

I checked the provider-call log read-only (`sqlite3 mode=ro`) and found these LIVE calls:

| provider / model | operation | status | calls | estimated cost |
|---|---|---|---|---|
| sam-3.1 | segment | ok | 5 | $0.0125 |
| muse-spark-1.3 | extract | ok | 29 | $0.176 |
| muse-spark-1.3 | extract | invalid_output | 1 | $0 |
| muse-spark-1.3 | **confirm (second read)** | — | **0** | — |

Adding the persisted smoke test (1 SAM call) and the nameplate script (1 Muse call) gives **6 SAM + 31 Muse calls, about $0.197**, which matches the latest claim. The submission still contains the older, contradictory figures "7 SAM + 5 Muse" and "6 + 5".

**Masks** (`10-…inspect.png`, `11-…inspect.png`):
- The real SAM 3.1 one-bit masks on the FEMA warehouse and Army forklift photos fit the forklift silhouettes closely, including the cut-outs around the cab and mast. That is convincing segmentation.
- The persisted SAM smoke test on the synthetic demo image (`live-smoke.json`) returned **0 objects** for "generator". So the demo masks are authored fixtures; real SAM does not reproduce them.

**Evidence:**
- The Muse outputs on the real wide photos are honest:
  - "CAT" read, no model or serial, uncertainties listed;
  - "E.P. 268" marked partially readable, confidence 40%.
- All in-app real-photo decisions are **WEAK (R3_TYPE_ONLY)**. No real-photo journey in the app reaches a serial match.

**Observability:**
- The trace page shows real latencies: SAM about 2.4–4.0 s, Muse about 5–8 s.
- It shows tokens in and out, estimated cost, correlation IDs, a provenance graph and an event log.
- The "Live collateral inspection" session is marked **REPORTED**, yet its report is DRAFT with a **CONFLICTING_REVIEWS** flag. The cause is a scripted "confirm, No note" by `live-demo-reviewer`, later voided by `release-coordinator`. That is a confusing showcase artefact.

## 4. Real-photo study: are the claims supported?

**Integrity checks:**
- I recomputed the SHA-256 of the protocol, `ground_truth.json`, `ledger_study.csv` and `eval/muse_study.py`. All four match `PROTOCOL.sha256`.
- `muse-study-preregistered.json` matches its stated hash (`8eedf5dd…a52bd8`).
- There are 26 raw bodies in `eval/results/muse-study-raw/`, and the database holds 26 study calls.

**The pre-registered headline is supported and reported honestly:**
- S1 = 1 unsafe auto-verification (**FAIL**).
- M1 = 11/16 exact transcriptions, 68.8% (CI 44–86%; **just below** the 70% bar).
- M2 = 0/8 serials invented on negatives.
- M3 = 0 distractor numbers reported as the serial.
- U1 = 3/14 correct automatic verifications.

The post-hoc 7/14 is clearly labelled optimistic. The in-document verifier's corrections (134 characters, not 170; four engine losses, not five; Muse side 7 vs engine 4) are applied.

**Limits that cap how much weight the study can carry:**
- n = 26, with a synthetic register.
- **Both readers are AI assistants of the same model family**, not human labellers.
- The study used **full-frame regions with no SAM call**, so it says nothing about SAM.
- The **two-read gate (D-16) was designed after the S1 failure and has never run live**: there are 0 `confirm` calls in the database.
- The fresh 14-photo holdout is frozen but **not run**.

**What the current build shows on real photos:** all 8 serial matches in the study session are now `R2e_CONFIRMATION_MISSING`, and the app displays **VERIFIED 0** (`13-…reconciliation.png`). The shipped configuration therefore has **no demonstrated automatic verification on any real photo**.

**Verdict:** the study's claims are supported as stated, and its honesty is a strength. The product claim that matters ("safe auto-verification on real photos") remains **unvalidated**.

## 5. Ambiguous-verification challenge (DEMO, fixture providers)

Fixture answers are keyed by image SHA-256, so I re-uploaded the bundled `bay_a_generators.png` into new sessions, each paired with a crafted register. Every session is named `judge r3 …`.

| Test | Session | Register | Result | Verdict |
|---|---|---|---|---|
| T1 look-alike decoy | ses_f03d0131f27e | A-001 GN-48213 + D-001 GN-48231 (same make/model) | VERIFIED A-001 | correct |
| T2 serial-only row | ses_a0d2e6e0a64f | Z-001: type + serial, **blank make and model** | **VERIFIED Z-001** on serial alone (also flagged COMPETING_FOR_ASSET) | risky: no positive corroboration needed |
| T3 same serial, other maker | ses_c791fb4d1960 | Voltane + GN-48213 | MISMATCHED (CONFLICTING_MANUFACTURER) | correct |
| T4 duplicate serial across facilities | ses_d725b6882d7f | GN-48213 at WH-01 and WH-02 | PROBABLE R2b | correct |
| T5 serial only at another facility | ses_30b366b932d0 | GN-48213 at WH-02 | MISMATCHED (FACILITY_MISMATCH) | correct |
| T6 normalisation | ses_30333580c73a | `gn 482.13` | VERIFIED N-001 | correct (separator-insensitive) |
| T7 type conflict | ses_cfe6465c03df | register says Forklift | MISMATCHED (TYPE_CONFLICT) | correct |
| T8 blank asset type | ses_a0054413387d | type empty | ledger rejected (400) | correct |
| T9 full-frame on a wide scene | ses_5c9b95bbe1f9 | A-001 only; 5-generator bay photo declared "one close-up" | **VERIFIED A-001, CONFIRMED_BY_SECOND_READ** | **unsafe in DEMO**: the whole 5-unit frame is attributed to one asset |

**Human-review guardrails (`ses_f03d0131f27e`):**
- A confirm with an empty note is rejected (400).
- Confirming an asset that another object already holds is rejected (409).
- Confirming a non-candidate is rejected (409).
- A noted confirm of the decoy on type-only evidence is accepted, but it is reported separately as HUMAN_CONFIRMED. That is acceptable human authority.

**How the Tier 1 two-read gate behaves:**
- **The order of checks is correct:** register duplicates, conflicts and uncertain serials are handled before the gate. The gate then requires the second read to agree on serial, manufacturer and type, to see exactly one serial, to describe no standalone plate and to have no register conflict.
- **In DEMO the gate is vacuous:** no fixture defines a `muse_confirm`, so the second read is identical by construction. The demo can never show the gate withholding Tier 1, and T9 shows it rubber-stamping a frame that contains four other units' plates.
- **The standalone-plate check depends on Muse's free-text wording:**
  - the same 5735 nameplate was labelled "generator nameplate" in the direct call (`live-muse-nameplate.json`) but "generator" in study item s14;
  - so the heuristic would not have fired on the exact case that failed S1;
  - s14 is now held back only because its confirmation read is missing.
- **Shared-mistake risk is acknowledged:** the second read is the same model on the same pixels, and `test_shared_model_mistake_is_not_caught_by_agreement_alone` documents that agreement can share a mistake.
- **Disputed serials:** they cannot be exercised in DEMO, and the gate's real effect on s14-like cases is untested.
- **Backend tests:** 138 pass, including `test_tier1_gate.py`.

## 6. Audit report

I exported the guided session as JSON (46 kB), HTML (15 kB) and CSV (10 kB); all returned 200. Copies are in the scratchpad as `report-guided.*`.

**Strengths:**
- The report states DRAFT while reviews are open.
- It carries the DEMO notice, a strong disclaimer (a photo does not prove ownership, authenticity, condition or value; UNVERIFIED does not mean missing) and the ledger SHA-256.
- It lists per-asset reasons and decision IDs, with the provider calls and cost in the JSON.
- Viewing the report changes nothing; only `download=true` marks the session reported.

**Gap:** the HTML report contains **0 `<img>` elements**. There are no evidence crops or masks, and decisions are referenced only by ID. This weakens the overview's "every status traces back to a photo crop" claim for anyone reading the exported artefact offline.

## 7. Muse Spark's contribution vs a no-Muse baseline, and SAM's role

**Muse Spark:**
- **What is measured:** 11/16 exact serial reads, 0/8 invented serials, 0/4 distractors taken as the serial, and 2 of 3 misreads self-flagged as uncertain. The pre-registered run produced 3/14 correct automatic verifications against the baseline's 0, with no wrong-asset verification among agreed items.
- **The comparison is weak:** "no Muse = 0" is a strawman. There is no OCR baseline (for example Tesseract or a cloud OCR) and no human-time baseline, so the *incremental* value of Muse over cheaper OCR is unknown.
- **The shipped gated configuration shows 0 automatic verifications on real photos.** Today Muse's demonstrated value is better structured evidence for human review, not removed field work.

**SAM 3.1:**
- **What is used:** 5 in-app calls on 4 real photos. Live eval: 4/4 objects found, a correct empty result for an absent object, and nothing returned for the vague prompt "machine". The masks are visually good.
- **What is not measured:** SAM's effect on extraction accuracy (no IoU, and no comparison of crop vs full frame). The 26-image study bypassed SAM entirely.
- **What it does in the product:** SAM is architecturally central to the story ("finds the equipment") but empirically peripheral. Its real job (isolating the unit and plate for the reader) has not been shown to improve any outcome.

## 8. Top 5 defects

1. **HIGH — The safety gate is unvalidated live, and the shipped build shows 0 real-photo automatic verifications.**
   - What happens: there are 0 LIVE `confirm` calls; the holdout has not run; every stored LIVE serial match is R2e_CONFIRMATION_MISSING.
   - Reproduce: open `/sessions/ses_8cde3ee6a3bb/reconciliation` → VERIFIED 0. Then run `sqlite3 'file:backend/data/auditglimmer.db?mode=ro' "select operation,count(*) from provider_calls where mode='live' group by 1"`, which returns no `confirm` rows.
2. **HIGH — In DEMO, the full-frame option auto-verifies a multi-unit scene, and the two-read gate is vacuous in DEMO.**
   - Reproduce:
     1. Create a session at WH-01 with a one-row ledger (A-001, GN-48213).
     2. Upload `fixtures/images/bay_a_generators.png`.
     3. `POST /runs {"concept":"generator","region":"full_frame"}`.
   - Result: VERIFIED A-001 with `CONFIRMED_BY_SECOND_READ` for a frame showing five generators and five plates (`20-T9-fullframe-wide-scene-verified.png`).
   - Cause: the fixture returns object #1's evidence for the whole frame, and with no `muse_confirm` in any fixture, the second read cannot disagree.
3. **MEDIUM-HIGH — The submission materials misstate the rules and contradict themselves.**
   - What happens:
     - "Official weights" 30/25/20/25 are not on the official page, which lists Indie: creativity, technical ambition, works; no weights.
     - The same document gives "7 SAM + 5 Muse ≈ $0.041", "6 SAM + 31 Muse ≈ $0.197" and "6 SAM + 5 Muse ≈ $0.039".
     - The README still says LIVE is "UNVERIFIED against the real API".
     - The video and repository links are empty; there is no hosted demo.
   - Reproduce: read `docs/submission-final.md` and `README.md`.
4. **MEDIUM — Tier 1 relies on the absence of contradiction rather than positive corroboration, and on a brittle keyword heuristic.**
   - What happens:
     - A register row with type and serial only (blank make and model) auto-verifies on the serial alone (T2, `ses_a0d2e6e0a64f`, `21-T2-serial-only-row-verified.png`). This is risky for short numeric serials such as "5735", which are only 4 characters.
     - The standalone-plate check depends on Muse saying "nameplate"; the same plate was described as "generator" in s14.
   - Reproduce: T2 in section 5. Compare `observed_object_type` in `eval/results/live-muse-nameplate.json` with s14 in `/api/sessions/ses_8cde3ee6a3bb/detections`.
5. **MEDIUM — Demo hygiene and report completeness.**
   - What happens:
     - The overview aggregates all 200+ test and judge sessions (1,673 pending reviews).
     - The guided-demo happy path shows red "Run error / Run partial".
     - The showcase LIVE session is "REPORTED" but DRAFT with conflicting scripted reviews.
     - The exported HTML report contains no evidence images.
   - Reproduce: open `/`, click Start guided demo, then open `/sessions/ses_936bef692a74/report` and run `grep -c "<img" report.html` (returns 0).

## 9. Scores

The criteria are the official Indie track criteria, equally weighted because no weights are published. The Meta-model theme requirement is met (SAM 3.1 and Muse Spark through Meta Model API).

| Criterion (official) | Weight | Score /10 | Rationale |
|---|---|---|---|
| Creativity | 33.3% | 6 | Well-chosen, unglamorous workflow (collateral audits); a distinctive epistemic stance (UNVERIFIED ≠ missing; the model never decides a match). The core pattern (segment → read → match) is conventional. |
| Technical ambition | 33.3% | 7 | Pre-registered study with hashes and an independent re-check, provenance graph, two-read gate, SSE, spend caps, an official SAM wire parser, 138 passing tests. Limited by an unused SAM path in the study, a gate that has never run live, and an unrun holdout. |
| Whether it works | 33.3% | 5 | DEMO works end to end and the guardrails hold. On real photos, the shipped build demonstrates no automatic verification, in-app real journeys end WEAK, the demo shows red errors, and nothing is deployed. |
| **Weighted total** | | | **60 / 100** |

**Sensitivity check under the unofficial 30/25/20/25 rubric** the submission cites: Impact 6, Meta tooling 6, Technical depth 7, Demo 5, giving **59.5 / 100**. The conclusion is the same either way.

**Overall:** this is a credible, unusually honest engineering submission that stays below prize level. The central promise (safe automatic verification from real photos) is not yet shown working in the shipped configuration, and SAM's contribution is unmeasured.

## 10. Three changes that would most raise the score

1. **Prove the gated pipeline on real photos.**
   - Run the frozen 14-photo holdout live (under $0.30) and publish the results next to the pre-registered study.
   - Re-extract the 8 study serial matches with second reads so the app shows real gated VERIFIED counts.
   - Add a fixture whose `muse_confirm` disagrees so the demo visibly shows the gate withholding Tier 1.
   - This moves "whether it works" the most.
2. **Make SAM measurably matter and close the ambiguity holes.**
   - Use SAM to isolate the plate or serial region for the second read, and measure crop vs full frame on the holdout.
   - Block Tier 1 on full-frame regions unless exactly one plate and one serial are reported.
   - Require at least one positive corroborating field (make or model) for Tier 1, and replace the keyword standalone check with a structured schema field.
3. **Fix the demo and the submission package.**
   - Scope the overview to demo and showcase sessions, and put failure fixtures behind a toggle so the happy path is clean.
   - Resolve the conflicting review on the showcase session, and embed evidence crops in the HTML report.
   - Deploy a read-only hosted replay of the LIVE sessions and record the 3-minute video.
   - Correct `submission-final.md`: use the official criteria, a single verified call count, and an updated README.

## Appendix: sessions created by this review (all DEMO, $0)

- `ses_41d16468bd18` judge r3 guided demo
- `ses_f03d0131f27e` T1
- `ses_a0d2e6e0a64f` T2
- `ses_c791fb4d1960` T3
- `ses_d725b6882d7f` T4
- `ses_30b366b932d0` T5
- `ses_30333580c73a` T6
- `ses_cfe6465c03df` T7
- `ses_a0054413387d` T8
- `ses_5c9b95bbe1f9` judge r3 T9 full-frame wide scene

One review was recorded in T1: reviewer "judge r3" confirmed the decoy D-001 on WEAK evidence, with a note marking it a test.
