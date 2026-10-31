# Release Checklist — AuditGlimmer submission freeze (2026-10-31, evening)

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
- [ ] Double-read gate before Tier 1 (recommended fix for the S1 failure) — not built
- [ ] Fresh-photo confirmation of the post-hoc engine numbers — not run (needs owner spend approval)

## Defects
- [x] All first-round P1s fixed and verifier-confirmed; V-01..V-05 fixed and re-verified
- [x] N-01 (ledger replace deleted reviews), N-02 (guided demo never showed VERIFIED), N-03 (live sessions unreachable) fixed with tests — **not re-judged**
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
