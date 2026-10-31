# Release Checklist — AuditGlimmer submission freeze (2026-10-31, evening; gate work appended 19:30 IST)

Legend: [x] verified by a command or an independent agent in this session · [ ] open · (owner) needs the owner.

## Quality gates (run at freeze)
- [x] Backend: `cd backend && uv run pytest -q` → **104 passed**
- [x] Frontend: `npm --prefix frontend run typecheck` and `run lint` clean
- [x] E2E: `npm --prefix e2e test` → **16 passed, 1 skipped** (paid live journey, `LIVE_JOURNEY=1` only)
- [x] Axe 0 serious/critical on overview/inspect/reconciliation; 375 px no horizontal scroll
- [x] Judge reports frozen with sha256: `judge-review-initial.md`, `judge-review-final.md`
- [x] Running API is DEMO (`auditglimmer-api-demo` launch entry); no paid calls outside the approved study

## Real-photo Muse Spark study (`docs/muse-study-protocol.md`, `docs/muse-study-results.md`)
- [x] Protocol, ground truth, ledger and runner hashed before the first paid call (verified by timestamps)
- [x] 26 Muse calls, $0.158 (cap $0.30), no SAM, no retries
- [x] Independent verifier recomputed every metric from raw data — substantially confirmed; 3 corrections applied
- Pre-registered: exact serial 11/16 (69%, below the 70% bar) · 0/8 invented serials · 0 distractor reads ·
  0 wrong-asset auto-verifications among agreed items · **1 auto-verification on a disputed item → safety gate FAILED**
- Post-hoc (engine fix, same evidence, not pre-registered): correct auto-verifications 3/14 → 7/14
- [x] Two-read gate before Tier 1 built on branch `feature/two-read-gate` (D-16): 138 backend tests incl. 34 gate tests;
  independent adversarial review found 9 issues, all fixed with tests. Experimental safeguard, not a guarantee.
  Stored pre-gate live sessions now show `R2e_CONFIRMATION_MISSING` instead of VERIFIED (post-hoc 7/14 no longer
  reproducible in the app view without re-extraction).
- [x] Fresh holdout prepared and frozen offline: 14 Commons photos, 6 pos / 7 neg / 1 disputed, two AI readers
  (sealed), `fixtures/holdout/FROZEN.sha256`, DEMO dry-run $0.
- [x] D-17 approved rules built: whole-photo regions never auto-verify; Tier 1 needs a corroborating maker/model;
  DEMO fixture A-004 shows two reads disagreeing → review. 143 backend tests, E2E 16 + 1 paid skipped.
- [x] Phase 3 live proof ran under the 19:38 approval, before D-17 arrived: real photo → SAM 3.1 → Muse → WEAK
  (no legible serial, so no second read). 1 SAM + 1 Muse, **$0.00684**. API returned to DEMO immediately.
- [x] (superseded below) footprint before holdout: 7 SAM + 32 Muse ≈ $0.2035.
- [x] Holdout run (owner-approved 19:56 IST): 19 Muse calls, $0.1200; ceiling used $0.1268 of $0.30; API back to DEMO.
  Independently verified: 0 unsafe, serial 5/6, correct suggestion 5/6, second reads 5/5 agree. `docs/holdout-study-results.md`.
- [x] Verified live footprint: **7 SAM + 51 Muse ≈ $0.3235**.
- [ ] (owner) Video: hold until the holdout results are verified; a live recording needs its own approval.

## Defects
- [x] All first-round P1s fixed and verifier-confirmed; V-01..V-05 fixed and re-verified
- [x] N-01 (ledger replace deleted reviews), N-02 (guided demo never showed VERIFIED), N-03 (live sessions unreachable) fixed with tests
  and browser-verified by an independent agent: N-01 VERIFIED (incl. UI confirm dialog cancel/accept), N-02 VERIFIED,
  N-03 PARTIAL → UI filter missed `verify` prefix, fixed (`frontend/src/app/page.tsx`).
- [ ] Open P3s: V-04, V-06, V-07, N-04..N-07; J-07 partial; J-16 partial (shared access code, no per-user auth)

## Truthfulness rules for the video and submission text
- Cite **6 SAM + 31 Muse calls ≈ $0.197** (verified); never 7/5/$0.041.
- DEMO frames must show the DEMO badge ("fixture providers, no model call").
- Live sessions are replays of stored outputs: say "recorded live on 31 Oct", never "running live now".
- State the study result as pre-registered, including the failed safety gate and the 69% transcription rate.

## Safety / config
- [!] `.env` contains the API key with `AUDITGLIMMER_MODE=live` + `AUDITGLIMMER_LIVE_APPROVED=1`. The parent
  folder's `auditglimmer-api` launch entry is **not** pinned to demo — use `auditglimmer-api-demo` only.
- `auditglimmer-api-live-study` launch entry exists (caps: all-time $0.3306 ≈ already spent); remove it after submission.

## Owner actions (not done by the assistant)
- [ ] (owner) Record the ≤3-minute video (script: `docs/demo-improvement-plan.md` §2, plus the study page)
- [ ] (owner) Choose a LICENSE; publish the repo (attribution for CC BY / CC BY-SA photos in `fixtures/*/LICENSES.md`)
- [ ] (owner) Submit on the Cerebral Valley portal before **Nov 4, 9:00 PM ET**
- [ ] (owner) Optional: approve a fresh-photo confirmation run and the double-read gate work
