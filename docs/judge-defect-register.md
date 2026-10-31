# Judge Defect Register — AuditGlimmer (2026-10-31)

Source of defects: `docs/judge-review-initial.md` (frozen, sha256 in `judge-review-initial.sha256`).
Each row: failure → root cause → regression test → change → observed outcome after fix.
Backend tests: `backend/tests/test_judge_regressions.py` (13 tests). "Verified" column is filled by the
independent verifier (ROLE C), not by the engineer who made the change.

| ID | Sev | Failure (judge) | Root cause | Regression test | Change | Engineer-observed after fix | Verified (ROLE C) |
|---|---|---|---|---|---|---|---|
| J-01 | P1 | Human confirm of type-only evidence made asset VERIFIED; reviewer "x" accepted; note optional | `_asset_results` mapped any human confirm to `VERIFIED`; `ReviewCreate.reviewer` min_length 1; no note rule | `test_j01_human_confirm_gets_its_own_status_not_verified`, `test_j01_confirm_requires_note_and_real_reviewer_name` | New asset status `HUMAN_CONFIRMED` (reason states it is a human assertion, not an identifier match); reviewer ≥2 chars incl. a letter; confirm requires note ≥10 chars | VERIFIED count unchanged after confirm; `HUMAN_CONFIRMED`=1; no-note → 400, "x" → 422 | PASS – ses_b4b942fe2050: "x"/"  a "/"12"→422, no note & whitespace-only note→400; valid confirm of WEAK R3 → A-013 HUMAN_CONFIRMED, VERIFIED stays 2 (see new defect V-01) |
| J-02 | P1 | Conflicting reviews: last write wins; earlier confirm + note vanished from reports | Reconciliation and report used only the latest review | `test_j02_conflicting_reviews_are_flagged_and_kept_in_history` | `review_history` on every decision; `CONFLICTING_REVIEWS` flag when different reviewers reach different outcomes; HTML report lists full history; conflicts keep report DRAFT | Both reviewers + flag appear in API and HTML report | PASS – Judge1 confirm + Judge3 reject on dec_ev_42421677de40: CONFLICTING_REVIEWS flag, both entries + Judge1 note in recon history and HTML report, report DRAFT (see new defect V-02: conflict never clears) |
| J-03 | P2 (P1 live) | Double-click created two runs (double paid calls in LIVE) | No per-session in-flight guard | `test_j03_second_run_while_one_is_active_is_rejected` | 409 `RUN_IN_PROGRESS` if the session has a queued/running run; UI button disabled while pending/active (frontend) | Second POST → 409 | PARTIAL – UI dblclick+3rd click → 1 POST (v03); sequential 2nd POST → 409; but 5 parallel POSTs → 2 runs, 10 parallel → overlapping runs started 2–7 ms apart (TOCTOU, see V-03) |
| J-04 | P2 | `1e309`/`NaN` stored as null with no issue | `float()` accepts inf/nan | `test_j04_non_finite_ledger_values_are_flagged` | Non-finite → `INVALID_NUMBER` warning, value ignored | Issues emitted for both rows | PASS – 1e309, NaN, " nan ", Infinity, -inf, -1e309 → INVALID_NUMBER, value null; -500 → NEGATIVE_VALUE only (minor: -inf/-1e309 also get spurious FORMULA_NEUTRALIZED) |
| J-05 | P2 | Opening Report tab marked session REPORTED | HTML/CSV GET always set `reported_at` | `test_j05_viewing_report_does_not_mark_session_reported`, `test_j05_download_finalizes_only_when_every_decision_is_reviewed` | Report GET side-effect free; `download=true` exports; finalization only when 0 open reviews and 0 conflicts; `report_state` DRAFT/FINAL; HTML banner | Views never change status; full review → FINAL | PASS – HTML/JSON/CSV views and download=true with 8 open reviews leave status "inspected", report DRAFT; all reviewed + no conflicts → FINAL, download=true → "reported" (see V-04 post-final edits) |
| J-06 | P2 | Two lookalikes both PROBABLE→same serial-less asset, unflagged | No cross-decision check for single-candidate claims | `test_j06_two_objects_competing_for_one_asset_are_flagged` | `COMPETING_FOR_ASSET` flag + explanation when ≥2 distinct objects point to one asset (same-serial re-photos exempt) | Flag on both decisions | PASS – scenario C ses_ff3f928b433b: 2 PROBABLE + 1 WEAK → C-010 all carry COMPETING_FOR_ASSET with "3 distinct detected objects point to C-010" text |
| J-07 | P2 | Zero-detection live SAM calls kept no raw output | `record_call` wrote raw only if non-empty | covered by existing provider tests (no live call possible offline) | Live calls persist raw body even when empty | not exercisable without paid call — code path only | PARTIAL – code only: record_call writes raw file when mode==live even if empty; but only the empty text body is kept (request_id/event_types not persisted), so a zero-match call is auditable only as a 0-byte file |
| J-08 | P2 | Landing page dominated by e2e sessions, no product explanation | No landing copy; test sessions share the DB | frontend e2e (agent) | Product explanation + guided demo CTA; e2e sessions collapsed | see frontend report | PASS – landing has product explanation, 6-step pipeline, "Start guided demo"; e2e sessions collapsed under "Automated test sessions" (v01) |
| J-09 | P2 | View stays on image with 0 detections; fixture confidence shown as "det. 94%" | UI picks first image; label generic | frontend e2e | Select first image with detections; fixture confidences labelled | see frontend report | PASS – after forklift run view jumps to bay_b_forklifts.png (5 regions); labels read "fixture conf. 94%" (v03) |
| J-10 | P2 | Ledger asset at another facility accepted silently | No upload-time facility check | `test_j10_facility_mismatch_warned_at_upload` | `FACILITY_MISMATCH` warning at upload | Warning on the WH-02 row | PASS – demo ledger row 17 (A-021, WH-02) and scenario C row 2 get FACILITY_MISMATCH warning at upload |
| J-11 | P3 | "Only asset type supported" though manufacturer narrowed candidates; wrong asset reason for R2b | Fixed explanation strings | covered indirectly (reconcile suite) | Explanation names manufacturer when it narrowed; PROBABLE asset reason points at linked decision rule | text verified manually | PASS – A-005/A-006 reason now "see the linked decision for the rule applied"; R3 manufacturer-narrowing text present in reconcile.py (not exercisable with fixtures, code-read) |
| J-12 | P3 | "generator worth $1M owned by borrower" accepted (raw phrase would reach SAM); "forklifts" rejected | Concept not canonicalised before the run | `test_j12_concept_is_canonicalised_before_reaching_the_model` | Concept canonicalised (plural-aware); only canonical type is stored/sent to SAM; unsupported types → 400 listing supported | `run.concept == "generator"`; "golden retriever" → 400 | PASS – "generator worth $1M owned by borrower"→generator, "forklifts"/"Forklifts"/"fork lift"→forklift, "golden retriever"→400 with supported list; minor: "forklift generator"→generator silently |
| J-13 | P3 | "-500" reported as formula "stored as text"; oversized PNG "not decodable" | Neutralizer flags leading "-"; decompression-bomb error mapped to 415 | `test_j04_…` (asserts no FORMULA on -500), `test_j13_oversized_image_gets_accurate_message` | Numeric ledger values not flagged as formulas; oversized → 413 with pixel limits | as expected | PASS – -500 no FORMULA flag; 30000×30000 PNG → 413 "image pixel count exceeds the decoder safety limit" (message does not state the limit) |
| J-14 | P3 | Report tab raw JSON; `format=pdf` 422 | UI preview = JSON | frontend e2e | Inline rendered HTML report; no PDF option | see frontend report | PASS – Report tab renders HTML in iframe with DRAFT banner, open/conflict counts, export buttons; no raw JSON (v04) |
| J-15 | P3 | Header DEMO while showing LIVE session trace | Global badge only | frontend | Session evidence mode shown on trace/report | see frontend report | PASS – live ses_936bef692a74 trace/report show "Evidence produced in LIVE — server currently DEMO", runs/calls tagged LIVE (v05) |
| J-16 | P1 (deploy) | No auth; anyone can delete/override | Local-only design | `test_j16_access_code_gate_when_configured` | Optional `AUDITGLIMMER_ACCESS_CODE` (≥24 chars, constant-time compare) gating all `/api/*` except health; UI prompt (frontend). Reviewer identity is still self-asserted — see deployment-readiness.md | 401 without/with wrong code; 200 with code | PASS – 2nd backend :8011 with 30-char code: /api/* 401 without/wrong/prefix code (incl. DELETE, POST, query-param on non-image path), 200 with header; health 200; <24-char code refuses to start; pytest J-16 green. Reviewer identity still self-asserted |

## Non-defect findings recorded

- **Baseline claim** "7 SAM / 5 Muse / ≈$0.041": stored artifacts substantiate 6 SAM + 5 Muse ≈ $0.0388.
  Correction notes added to live-integration-report, release-status, submission-final, model-evaluation,
  hackathon-compliance. The nameplate Muse call (serial "5735") was real but ran via a direct script, not
  through the app pipeline — the judge correctly found no in-app nameplate run.
- **Demo circularity** (fixture outputs reproduce fixture expected statuses): a design property of DEMO mode,
  disclosed in UI/report. Only fix is a real in-app live run on real photos → requires owner spend approval.
- **Live session `ses_936bef692a74`** contains a scripted Playwright confirmation voided by a later reject.
  With J-02 the full history now shows both, which is the honest record; not deleted.

## ROLE C verification notes

Verifier: ROLE C (independent), 2026-10-31. Servers left as found (DEMO, fixture providers); no live/paid call made.
Fresh sessions: `verify A` ses_b4b942fe2050, `verify B concurrency` ses_5cbb3c8c8527, `verify B2 concurrency`
ses_335bd8ec11ca, `verify C misleading ledger` ses_ff3f928b433b, `verify D concepts` ses_2bda08526596,
`verify E weird` ses_22ec6127841a, plus two UI "Guided demo" sessions. Screenshots: `docs/remediation-evidence/verifier/`.

### Regression suites
- `cd backend && uv run pytest -q` → **93 passed**, 1 warning.
- `npm --prefix frontend run typecheck` → clean. `npm --prefix frontend run lint` → clean.
- `npm --prefix e2e test` → **16 passed, 1 skipped** (live-journey, skipped without LIVE_JOURNEY=1).

### Safety invariant
- Demo ledger: only A-001 and A-004 VERIFIED (unique serial). Scenario C (false serial, same serial at WH-02,
  wrong manufacturer, two identical BW-300, unpictured excavator, lowercase/trailing-space serial, duplicate serial,
  one serial-less LM-25 vs two in photo): only C-007 VERIFIED (normalised unique serial); C-001/C-002/C-003
  MISMATCHED, C-004/5 and C-008/9 PROBABLE, C-006 NOT_OBSERVABLE, C-010 PROBABLE+COMPETING_FOR_ASSET.
- Every human confirm became HUMAN_CONFIRMED, never VERIFIED; VERIFIED counts never moved on review.
- Adversarial confirms refused: non-candidate asset → 409, EVIDENCE_UNUSABLE → 409, NOT_IN_REGISTER → named VERIFIED
  asset → 409, second reviewer confirming a different asset on an already-confirmed decision → 409.

### New defects found
| ID | Sev | Repro | Observed |
|---|---|---|---|
| V-01 | P2 | Demo session, run forklift+generator. A-010 is MISMATCHED (dec R5, visible serial FL-7781 but manufacturer Hoistline). Confirm the *lookalike* PROBABLE decision (R2a, candidates A-010/11/12) as A-010 with a note. | A-010 asset status flips MISMATCHED → HUMAN_CONFIRMED while the conflicting-serial decision is still open; `_RANK["HUMAN"]` outranks MISMATCHED/VERIFIED in `_asset_results`, so asset-level view hides contrary evidence (report stays DRAFT while it is open, which limits the damage). |
| V-02 | P2 | Two different reviewers disagree on one decision (Judge1 confirm, Judge3 reject), then Judge1 re-reviews to agree (reject). | `CONFLICTING_REVIEWS` stays forever (`_reviews_conflict` scans the whole history, not each reviewer's latest), so the session can never reach FINAL; no resolution path exists. |
| V-03 | P2 (P1 in LIVE) | 5 (then 10) concurrent `POST /api/sessions/{sid}/runs`. | 2 of 5 and 5 of 10 accepted; trace shows runs started 2 ms and 7 ms apart and running concurrently. The RUN_IN_PROGRESS check is a SELECT-then-INSERT with no lock/unique constraint. UI guard holds; API does not. |
| V-04 | P3 | Finalize scenario C (FINAL, downloaded, status "reported"), then POST a new confirm. | Accepted; report recomputes and still says FINAL with different counts; nothing records that the exported FINAL is superseded. |
| V-05 | P3 | Ledger values `-inf`, `-1e309`. | Besides INVALID_NUMBER also emit FORMULA_NEUTRALIZED "stored as text" although the value is stored as null (residue of J-13). |
| V-06 | P3 | Concept "forklift generator" / "not a forklift". | Silently canonicalised to "generator" / "forklift"; no ambiguity error. Harmless to decisions. |
| V-07 | P3 | Confirm note "aaaaaaaaaa". | Accepted (length-only rule); note quality is not checked. By design per register, noted for reviewers. |

### Commands run (abridged)
- curl against :8000: session create, `/demo`, `/ledger` (scenC.csv, weird.csv), `/images` (fixtures, 30000×30000 PNG),
  `/runs` (single, 5× and 10× parallel, concept probes), `/reconciliation`, `/decisions/{id}/review` (validation,
  conflicts, adversarial), `/report?format=html|csv|json[&download=true]`, `/trace`.
- Node Playwright (`e2e/node_modules/playwright`): landing, guided demo, double/triple-click Run inspection, report tab,
  live-session trace/report, reconciliation screenshots.
- Temporary gated backend: `env AUDITGLIMMER_MODE=demo AUDITGLIMMER_LIVE_APPROVED=0 MODEL_API_KEY= AUDITGLIMMER_ACCESS_CODE=<30 chars> AUDITGLIMMER_DATA_DIR=<scratch> AUDITGLIMMER_DATABASE_URL=sqlite:///<scratch>/ag.db uv run uvicorn app.main:create_app --factory --port 8011`, probed, then killed; short-code start → ValueError.
- Code read: `backend/app/main.py` (access_gate, create_run, report), `pipeline.py` (record_call), `providers/sam_meta.py`, `reconcile.py`, `services.py`, `report.py`.

## Repair loop round 2 (engineer, after ROLE C) — loop cap reached, no round 3

| ID | Sev | Root cause | Regression test | Change | Status |
|---|---|---|---|---|---|
| V-01 | P2 | `_asset_results` let a human confirm outrank open MISMATCHED evidence | `test_v01_human_confirm_does_not_hide_open_contrary_evidence` | Human-confirmed asset with an unreviewed MISMATCHED link stays `MISMATCHED` (human_confirmed=true) and names the open decision | fixed, tests green; PASS – ROLE C r2 ses verify R2 V01 V02: confirming lookalike R2a as A-010 leaves A-010 MISMATCHED (human_confirmed=true, reason names open dec_ev_d51955cdee6c); after that decision is rejected → HUMAN_CONFIRMED; VERIFIED stays 2 |
| V-02 | P2 | `_reviews_conflict` scanned whole history | `test_v02_conflict_clears_when_reviewers_converge` | Conflict = reviewers' *latest* outcomes differ | fixed, tests green; PASS – ROLE C r2: Judge1 confirm + Judge3 reject → CONFLICTING_REVIEWS; Judge1 re-reviews reject → flag clears, history (Judge1 note) still in HTML; Judge3 then confirms A-012 → flag returns |
| V-03 | P2 (P1 live) | check-then-insert race on `/runs` | `test_v03_concurrent_run_posts_create_one_run` (10 concurrent → 1×202, 9×409) | process-wide lock around check+insert (single uvicorn worker; multi-worker would need a DB constraint) | fixed, tests green; PASS – ROLE C r2: 10 concurrent → 1×202/9×409; 20 concurrent (twice) → 1×202/19×409, one run each in trace; follow-up run after finish → 202; 2 sessions × 5 concurrent → 1×202 per session (single-worker caveat stands) |
| V-05 | P3 | numeric check required finiteness | `test_v05_negative_infinity_is_not_called_a_formula` | any float literal is a number, finiteness checked separately | fixed |
| V-04 | P3 | no report versioning after FINAL | — | **not fixed** — documented: reviews after a FINAL export recompute the report; the exported file is the record | open |
| V-06 | P3 | `canonical_type` takes first synonym in multi-type phrases | — | **not fixed**; does not affect decisions (run concept only) | open |
| V-07 | P3 | note quality checked by length only | — | **not fixed**; human-confirmed status + named reviewer + history keep it auditable | open |
| J-07 | P2 | partial: request id / event types not persisted for empty live bodies | — | **open** (needs paid call to exercise) | open |
| J-03 | — | UI + API now both enforce single run (see V-03) | — | — | fixed |

Post-round-2 regression: backend `pytest` 97 passed; e2e 16 passed / 1 skipped (paid live journey); frontend typecheck + lint clean.

## Final-judge findings (round 2, `judge-review-final.md`)

| ID | Sev | Status | Notes |
|---|---|---|---|
| N-01 | P1 | **Fixed after final judging — NOT re-judged, NOT ROLE-C verified** | Root cause: `_store_ledger` deleted register + reviews before checking the upload had any accepted rows, with no consent. Fix: 0-accepted upload → 400 `LEDGER_EMPTY`, nothing changes; replacing a register that has reviews → 409 `LEDGER_HAS_REVIEWS` unless `replace=true` (also guards demo reload); on replace, reviews are archived to `backend/data/sessions/<sid>/review-archive/*.json`. UI asks for confirmation before re-sending with replace. Tests: `test_n01_all_rejected_ledger_changes_nothing`, `test_n01_replacing_ledger_with_reviews_requires_explicit_replace_and_archives`. UI confirm dialog not browser-tested. |
| N-02 | P2 | fixed (not re-judged) | Inspect defaults to "generator", the demo bay with serial-backed VERIFIED matches. |
| N-03 | P2 | fixed (not re-judged) | Test sessions (e2e/verify) no longer count toward the 8 recent; new "Real-photo evidence (recorded LIVE Meta runs)" card lists live sessions. Test `test_n03_…`. |
| N-04 | P3 | open | compressor/racking offered but fixture runs fail; allowlist rejects ledger types like "excavator". |
| N-05 | P3 | open | Review form preselects first candidate on low-evidence decisions. |
| N-06 | P3 | open | CSV export carries only latest reviewer. |
| N-07 | P3 | open | Report does not list ledger values ignored as invalid. |
| J-16 | P1 (deploy) | partial | Access gate exists (verified by ROLE C on a gated instance) but no per-user auth; judge could not observe it in the running local instance. |
