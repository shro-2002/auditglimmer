# AuditGlimmer — Blind Judge Review (Role A, FINAL / Round 2)

Date: 2026-10-31. Same reviewer, role and blindness rules as `judge-review-initial.md`, which is frozen and not modified. I was not told what the engineering team changed. Every finding below comes from observed browser and API behaviour, the read-only DB and raw files, and test runs. No `.md` file other than my own was read. No live or paid calls were made, and no configuration change or restart was done. The server was in **DEMO** mode throughout.

Evidence: `auditglimmer/docs/judge-evidence/final/` (10 screenshots and `report-control-session.html`).
Fresh round-2 sessions: `ses_a117e490d5d9` (guided demo, Scenario F), `ses_3644c8b8e760` (Scenario A, manual UI ledger), `ses_7333573382e0` (control and review tests), `ses_7d2e58eb0bff` (Scenario C), `ses_fdbd5005d1d0` (Scenario E).

---

## 1. Score: initial vs final

The official rubric is still **unverified** (see the initial review, section 1). Reported weights are used.

| Category | Weight | Initial | Final | Why it moved |
|---|---|---|---|---|
| Impact | 30% | 5 | **5** | Rule-engine credibility improved: counting conflicts are now flagged and human-confirmed assets are reported separately. But there is still **no real-photo run that produces a verified or probable match**. The live sessions are unchanged (0 VERIFIED, 0 PROBABLE), and the nameplate photo has still never been run live. |
| Use of Meta AI Tooling | 25% | 6 | **6** | The landing page now explains the SAM 3.1 and Muse Spark 1.3 roles. The live trace page labels evidence "LIVE — server currently DEMO". But the live footprint has not changed (the same 5 SAM and 4 Muse calls, $0.0306), and the live sessions are not reachable from the UI (N-03). |
| Demo | 25% | 5 | **6.5** | Added: a value-proposition panel with a 6-step pipeline, "Start guided demo", auto-selection of the image with detections, "fixture conf." labelling, a rendered report preview with a DRAFT banner, and mode-aware headers (`01`, `03`, `06`, `07`). Still missing: the guided path never shows a VERIFIED result (N-02), demo images are cartoons, and the recent-sessions list can show only test sessions (N-03). |
| Technical Depth | 20% | 7 | **7.5** | Added: a server-side run lock (409 RUN_IN_PROGRESS), append-only review history with a CONFLICTING_REVIEWS flag, a COMPETING_FOR_ASSET flag, a decoder pixel limit, INVALID_NUMBER validation, and a mandatory note on confirmation. Tests: **97 backend tests pass; 16 e2e tests pass with 1 skipped (paid live journey), including an axe check (0 serious) and a 375px responsive check**. Pulling it down: a new P1, where replacing the ledger hard-deletes human reviews (N-01). |

**Initial weighted:** 0.30×5 + 0.25×6 + 0.25×5 + 0.20×7 = 1.50 + 1.50 + 1.25 + 1.40 = **5.65 / 10**
**Final weighted:** 0.30×5 + 0.25×6 + 0.25×6.5 + 0.20×7.5 = 1.50 + 1.50 + 1.625 + 1.50 = **6.13 / 10 (61.3 / 100)**

### Diagnostic grades (NON-OFFICIAL)
| Dimension | Initial | Final | Basis |
|---|---|---|---|
| Business credibility | 5 | 5.5 | Clear problem framing on the landing page, but no real-world success shown |
| UX | 6 | 7.5 | Guided demo, inline validation, draft report preview, auto-selected image. N-02 and N-03 remain |
| Reliability | 7 | 7 | Double-submit, NaN and decoder-bomb cases are fixed. Offset by N-01 (data loss on ledger replace) |
| Safety & financial correctness | 6 | 7 | No VERIFIED inflation. A human confirmation cannot override conflicting identifier evidence. Invalid values are flagged |
| Trustworthiness of outputs | 7 | 7 | Review history and conflict flags were added, but a failed upload can erase the trail (N-01) |
| Competitive differentiation | 5 | 5.5 | Cardinality conflicts and evidence tiers are visible. Still not demonstrated on real imagery |
| Deployment readiness | 3 | 3.5 | An access-code gate exists in the code (seen only in a mocked e2e test) but is not active here. Next.js dev server. No auth on DELETE |

---

## 2. Status of each initial defect (re-run by its original repro)

| ID | Sev | Status | Evidence |
|---|---|---|---|
| J-01 | P1 | **Resolved** | Confirming the type-only WEAK decision with reviewer "x" now returns 422 (name needs at least 2 characters). Without a note, or with a blank note, it returns 400 "confirm requires a note (at least 10 characters)". With a valid note, A-013 becomes **HUMAN_CONFIRMED**, counted separately in `by_status`, the overview, the report and the CSV. Confirming the WEAK decision onto A-010, which has a conflicting serial match, leaves A-010 **MISMATCHED** ("Human-confirmed, but conflicting identifier evidence is unresolved"). Single-reviewer and free-text identity remain under J-16. |
| J-02 | P1 | **Resolved** | Confirm by Judge One (with the ownership note), then reject by Judge Three: the decision shows `flags` including **CONFLICTING_REVIEWS** and a `review_history` of 2 entries. The HTML and JSON reports contain Judge One's action and note. The report page shows "CONFLICTING REVIEWS 1" (`06-report-page.png`). The CSV carries the flag but only the latest reviewer (N-06). |
| J-03 | P2 | **Resolved** | Double-clicking in the UI created 1 run (`run_bb7992b99fea`). Two concurrent API POSTs gave one 202 and one **409 RUN_IN_PROGRESS**. |
| J-04 | P2 | **Resolved** | `1e309` and `NaN` now produce `INVALID_NUMBER` warnings: "ledger_value is not a finite number (NaN/overflow); ignored". The report disclaimer still says values are "reproduced as stated" and does not surface the ignored rows (N-07, P3). |
| J-05 | P2 | **Resolved** | Status stays `inspected` after GET report. The UI says "Viewing this page changes nothing" and shows DRAFT. |
| J-06 | P2 | **Resolved** | In Scenario C, all three decisions pointing at C-010 carry **COMPETING_FOR_ASSET** with "3 distinct detected…" in the explanation. |
| J-07 | P2 | **Partially** | Demo zero-match calls now persist raw output (`raw/call_b33479a5fe73.txt` = `[]`). The two historical live zero-match SAM calls (`call_85416016b1be`, `call_2a04638f6b71`) still have no raw output. Whether live zero-match output is now persisted cannot be verified without a live call. |
| J-08 | P2 | **Partially** | There is now a value-proposition panel and test sessions are collapsed under "Automated test sessions (N)". But the recent list is the last 8 sessions, so after any e2e run it shows **only** test sessions (N-03). "verify R2 …" engineering sessions appear as normal sessions. The live session still contains a review voiding a "scripted Playwright confirmation". |
| J-09 | P2 | **Resolved** | After a run the view lands on `bay_b_forklifts.png` with 5 masks. Confidence is labelled "fixture conf. 94%" (`03-after-run-forklift.png`). |
| J-10 | P2 | **Resolved** | Row 17 now gets the WARNING **FACILITY_MISMATCH**: "asset is at WH-02, not this session's facility WH-01…" (`05-ledger-validation.png`). |
| J-11 | P3 | **Resolved** | Live decision text now reads "asset type (forklift) and manufacturer (HYSTER)" (and CAT). Asset reasons are now neutral ("see the linked decision for the rule applied"). |
| J-12 | P3 | **Resolved** | Concepts are canonicalised consistently: "forklifts" becomes forklift, "Pallet Racking" racking, "air compressor" compressor, and "generator worth $1M owned by borrower" is stored as `generator`, so the free text is not forwarded. Unsupported concepts get an explicit 400. |
| J-13 | P3 | **Resolved** | `-500` no longer triggers FORMULA_NEUTRALIZED. The 30000×30000 PNG now gets 413 "image pixel count exceeds the decoder safety limit". |
| J-14 | P3 | **Partially** | There is a rendered inline HTML preview with DRAFT state, open and conflicting counts, and the disclaimer. `format=pdf` still returns 422; only json, html and csv are allowed. |
| J-15 | P3 | **Resolved** | The live trace shows "Evidence produced in **LIVE** — server currently DEMO" (`07-live-session-trace.png`). |
| J-16 | P1 (deployment) | **Unresolved** | OpenAPI has no `securitySchemes`, and `DELETE /api/sessions/{sid}` has no security (a probe on a non-existent id returned 404, so I did not delete anything). Reviewer identity is free text. An access-code gate exists in the frontend (e2e test "401 opens the access-code prompt"), but it is not active on this instance and I could not observe it working. |

Summary: **11 resolved, 4 partially resolved, 1 unresolved**.

---

## 3. New defects found in round 2

| ID | Sev | Repro | Expected | Observed |
|---|---|---|---|---|
| **N-01** | **P1** | Session `ses_7d2e58eb0bff` (Scenario C): confirm a decision (Pat Lee, valid note), then upload `quote.csv` (0 accepted, 1 rejected) via `POST /sessions/{sid}/ledger`. Then re-upload the original `ledger_C.csv`. | An upload with zero accepted rows is refused or asks for confirmation. Existing reviews are preserved or archived. | The register drops to **0 assets**, and all 13 decisions become NOT_IN_REGISTER. The human review is **hard-deleted**: `reviews` rows for the session = 0, and `reviewed` stays 0 even after restoring the identical ledger. The same wipe happens in session `ses_fdbd5005d1d0` (3 to 0 assets). One mistaken upload destroys the audit trail. |
| N-02 | P2 | Overview → "Start guided demo" → Run inspection (default "forklift") | The guided journey reaches the product's headline outcome (a Tier-1 VERIFIED) | Only forklifts are inspected. Summary: VERIFIED 0, HUMAN_CONFIRMED 0, 13 NOT_OBSERVABLE. Nothing prompts the user to run "generator", which is the only concept that yields VERIFIED in the fixtures. A 3-minute judge never sees a verified match. |
| N-03 | P2 | Run `npm --prefix e2e test`, then open the overview | Human and live sessions stay reachable | "Recent sessions" says "Only automated test sessions are in the recent list" (`10-overview-recent-misclassified.png`). There is no sessions index page, so the two **live evidence sessions** (`ses_34ab4ba56b1b`, `ses_936bef692a74`) cannot be reached from the UI at all. |
| N-04 | P3 | Inspect tab hint: "Supported asset types: compressor, forklift, generator, racking" | Accurate for the current mode | In DEMO, "racking" and "compressor" runs fail outright on every image ("fixture labels exist only for concepts ['forklift','generator']; needs LIVE mode"). The same allowlist rejects "excavator" (400) even when the ledger contains one, which narrows SAM's open vocabulary in LIVE too (cannot verify live). |
| N-05 | P3 | Review queue → a WEAK type-only decision | No candidate preselected | The first candidate (A-010) radio is preselected (`08-review-queue.png`). This nudges a hurried confirmation. It is mitigated by the mandatory note and by MISMATCHED being kept. |
| N-06 | P3 | `GET /report?format=csv` after conflicting reviews | Full review history | The CSV shows only the latest `review_action` and `reviewer` plus the flag. Superseded actions appear only in the HTML and JSON reports. |
| N-07 | P3 | Report for a ledger containing INVALID_NUMBER rows | The report notes the ignored values | The disclaimer says "Ledger values are reproduced as stated", and the report does not list ledger validation issues. |

No P0 found. In no scenario was an unsupported identity auto-verified.

---

## 4. Scenario re-runs (fresh sessions, first-time user)

- **F (3 minutes):** Landing to guided demo to masks took about 20 s of agent time. Value proposition: now clear (`01-landing.png`). SAM's contribution is visible as numbered masks. Muse's contribution is visible as a "Structured visual evidence" panel when a region is selected (`04-region-evidence-panel.png`). Weakness: there is no verified-match moment (N-02), and the live proof is hidden (N-03).
- **A (manual):** Create session, upload ledger through the UI (18 accepted, 2 rejected, FACILITY_MISMATCH shown), images, run, reconciliation, review (the inline validation messages "Enter your name…" and "needs a note of at least 10 characters (0 so far)" are shown; `09-…png`), then the report (DRAFT preview). **Completable without help.**
- **B (lookalikes):** Unchanged and correct. The two LM-25 units are PROBABLE and ambiguous, the type-only unit is WEAK, and confirming both units onto one asset returns 409. On the live real photo, both forklifts are WEAK, and the explanation now names HYSTER. Still no discrimination between lookalikes on real imagery.
- **C (misleading ledger):** The same correct outcomes as round 1 (false serial → MISMATCHED; facility mismatch, wrong manufacturer and duplicate serial all flagged; excavator → NOT_OBSERVABLE). Plus J-06 fixed. **No unsupported VERIFIED.**
- **D (false confidence):** An ownership and value claim in a reviewer note is stored and shown verbatim in the report, attributed to the human, under the disclaimer. No machine-generated text claims ownership, exact identity of a lookalike, an unreadable serial, or value. A Muse fixture output that adds `estimated_value_usd` is still rejected by the schema.
- **E (failures):** Everything I tried returned a typed 4xx (400, 409, 413, 415, 422). Fault injection through fixture cases leads to EVIDENCE_UNUSABLE, and retry works. Gaps: N-01 (data loss), and mid-run refresh is still not testable (demo runs take about 50 ms).

---

## 5. Meta model verification (round 2)
- **No new live evidence.** The DB has the same **5 live SAM 3.1 calls ($0.0125) and 4 live Muse Spark 1.3 calls ($0.0181), $0.0306 in total**. The raw outputs are in genuine SAM token format with Muse JSON and token usage. I still judge them consistent with real execution, replayed from storage, and **not independently re-verifiable** without an approved live call.
- The claimed baseline "7 SAM, 5 Muse, ~$0.041" is **still not reproduced**.
- Muse never produced an identifier that matched a ledger serial on a real photo, so the core claim (Muse transcription driving a Tier-1 match) remains unproven in live use.

---

## 6. Remaining weaknesses
1. No real-photo success. The impact story still rests on synthetic fixtures whose outputs are authored to match the expected statuses (the demo is circular).
2. Live evidence is undiscoverable in the UI (N-03), and the live sessions contain test-script artefacts.
3. N-01 lets one wrong upload destroy human review records. That is unacceptable for an audit tool.
4. No authentication or reviewer identity on this instance. Dual control is not implemented.
5. The concept allowlist (4 types) limits generality. In DEMO only 2 of those work.

## 7. Evidence of improvements
`01-landing.png` (value proposition, guided demo, Human-confirmed legend, collapsed tests) · `03-after-run-forklift.png` (auto-selected image, fixture-conf label, single run) · `04-region-evidence-panel.png` · `05-ledger-validation.png` (FACILITY_MISMATCH) · `06-report-page.png` (DRAFT, open and conflicting counts, rendered preview) · `07-live-session-trace.png` (LIVE evidence vs DEMO server) · `08-review-queue.png` (note required) · `09-confirm-empty-validation.png` · `report-control-session.html` (HUMAN_CONFIRMED and review history).

## 8. Remaining submission risks
- Any demo footage or text that cites "7 live SAM / 5 live Muse / $0.041" contradicts the stored traces (5 / 4 / $0.0306).
- A judge following the guided demo sees no verified match and cannot find the live sessions.
- If hosted as observed (Next.js dev server, no active auth, unauthenticated DELETE), any visitor could wipe sessions. Through N-01, any visitor could also erase reviews by uploading a bad CSV.

## 9. Internal readiness gates

| Gate | Result | Evidence |
|---|---|---|
| Weighted score ≥ 8.5/10 | **FAIL** | 6.13 |
| No unresolved P0 | **PASS** | None observed in either round |
| No unresolved P1 on the main journey | **FAIL** | N-01: ledger replacement deletes reviews (the Ledger tab is step 1 of the journey). J-16 is a deployment P1 |
| Real Meta pipeline independently verified | **FAIL** | Only stored traces (consistent with genuine). No independent re-execution. Baseline mismatch persists |
| Core report consistent with evidence | **PASS** (with caveat) | HUMAN_CONFIRMED is separated, history and conflicts are shown, the DRAFT state is correct, the disclaimer is accurate. Caveats: N-07, and N-01 can silently remove reviews that the report would otherwise show |
| First-time judge completes the workflow | **PASS** | Scenario A completed through the UI without help. Guided demo works (N-02 is a quality issue, not a blocker) |
| Browser tests & backend regressions pass | **PASS** | `uv run pytest -q`: 97 passed. `npm --prefix e2e test`: 16 passed, 1 skipped (paid live journey, gated by `LIVE_JOURNEY=1`) |
| Demo footage would be technically truthful | **PASS** (conditional) | The UI labels DEMO and fixture output everywhere ("no AI model was called"). It stays truthful only if the footage does not present fixture runs as live and does not cite the unreproduced 7/5/$0.041 figures |
| Hosting strategy safe & testable | **FAIL / not observable** | Only a localhost Next.js dev server was observable. No active auth. The access-code gate was seen only in a mocked e2e test. No hosted URL to test |

## 10. Smallest set of improvements that could change the gate outcome
1. **Fix N-01:** refuse ledger uploads with 0 accepted rows; require explicit confirmation to replace a ledger that has reviews; never hard-delete reviews (archive them with the old ledger hash). This clears the main-journey P1 gate.
2. **One approved, bounded live run** (Approval request R-1 from the initial review: 1 SAM call and up to 2 Muse calls on `generator_nameplate_ccbysa.jpg`, at most $0.02). Persist it and link it from the overview as "Live evidence". This is the only route to the Meta-verification gate and the biggest lever on Impact and Meta-tooling scores.
3. **Guided demo runs both concepts** (or prompts for "generator") so a VERIFIED match is shown. Add a sessions index, or pin the live sessions, so N-03 cannot hide them.
4. **Hosting:** production build, access-code gate enabled and demonstrable, DELETE disabled or authenticated on the public instance.

Even with all four, reaching **8.5** would most likely also need several real photos that show a correct VERIFIED match and correct lookalike handling. In my judgement, Impact and Meta tooling cannot pass about 7 on synthetic fixtures alone.
