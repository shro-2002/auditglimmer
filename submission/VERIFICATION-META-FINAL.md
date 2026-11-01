# AuditGlimmer_Meta_Final.mp4 — verification record

File: `submission/AuditGlimmer_Meta_Final.mp4` (not in git; `submission/*.mp4` is ignored)
SHA-256 `02c22ab734b016a578895462f1dee469e50036d25224837a1b4c06db07ead615` · **174.91 s** · 1920×1080 · 30 fps · H.264 + AAC stereo · −18.9 LUFS
Fallback kept untouched: `submission/AuditGlimmer_Demo_v3.mp4` (SHA-256 `70fedde5…`, unchanged).
Not published, pushed or submitted.

## Live Meta calls (owner-approved 1 Nov 2026, ceiling $5)
Recorded once by the one-shot Ultrademo project `ultrademo-workspace/projects/auditglimmer-live-2026-11-01`
(`.paid-capture.lock` blocks any re-run). The API ran in LIVE mode with process caps of 6 requests and $0.10 per run, 8 requests
per session, and a $1.3153 lifetime total. It was stopped right after the take.

| Session | Call | Model | Status | Latency | Est. cost |
|---|---|---|---|---|---|
| `ses_c2be9f15d7fe` (warehouse, FEMA public-domain photo) | segment | sam-3.1 | ok | 4,126 ms | $0.002500 |
| same | extract | muse-spark-1.3 | ok | 6,625 ms | $0.004694 |
| `ses_54d4781e4fbb` (h11 plate, CC BY-SA 4.0, full-frame, SAM not called) | extract | muse-spark-1.3 | ok | 6,949 ms | $0.006170 |
| same | confirm (second extraction) | muse-spark-1.3 | ok | 8,926 ms | $0.008618 |

**Incremental spend: $0.021982** (ledger total $0.315271 → $0.337253; 56 → 60 live calls). These are estimates from published
prices; the Meta console bill is authoritative. A DB snapshot was taken first: `backend/data/pre-live-2026-11-01.db`.

## Genuine results shown
- Warehouse photo, concept "forklift": SAM 3.1 returned **1 mask** (detector 90%). Muse read maker **CAT**, serial **not visible**
  (uncertainty noted), giving **WEAK** (`R3_TYPE_ONLY`). Candidates R-004 and R-005 come from a synthetic demonstration register (`fixtures/real/ledger_real.csv`).
- h11 plate (separate Muse-only run, SAM not called): Muse read **28756**, the second extraction read **28756**, giving
  **PROBABLE** (`R2e_WHOLE_PHOTO_ASSOCIATION_UNSUPPORTED`). The single candidate is **T-h11** of the 44-row test register; the planted decoy D-h11 is not offered.
- No VERIFIED on any real photo. VERIFIED appears only on the labelled synthetic fixture.

## Labels used on screen
`LIVE META CALL · 1 Nov 2026` (today's calls) · `DETERMINISTIC RULES` (decisions on that live evidence) ·
`TEST DATA` / `TEST REGISTER` (planted decoy, 44-row register) · `STORED STUDY DATA` (retrospective 0/6 vs 5/6, holdout numbers) ·
`SYNTHETIC FIXTURE` (no model called). Waits during the live runs are jump-cut, and the badge says "time-compressed".

## Production safeguards
- Live scenes are **imported** (`importFrom`) into the editorial project `auditglimmer-meta-final-2026-11-01`. That project's capture refuses
  to run unless its API on port 8011 reports DEMO, so a re-render cannot make paid calls.
- Rehearsed first against the DEMO API at $0 (`auditglimmer-live-dryrun`).

## Checks
| Check | Result |
|---|---|
| Runtime | 174.91 s (target 160–175, max 180) |
| Silence ≥ 1.5 s / black ≥ 0.3 s | none / none |
| Narration | Kokoro (local). Each line starts with its scene; spot-checked by transcription |
| Model names on screen | `sam-3.1`, `muse-spark-1.3` (app header and provider-call table) |
| Credentials | header shows only `credentials: present`; the first 12 characters of the key do not appear in project assets |

## Remaining limitations
- No public repository URL exists, so the end card omits it.
- No real photo reached automatic verification. The real successes are a type and maker match (WEAK) and a correct single candidate (PROBABLE).
- The h11 plate was already in the frozen holdout. Today's run is a fresh execution in a new session, not new-data evidence.
- The voice is local TTS: clear but flat, and captions are static.
