# Final demo video — verification notes (1 Nov 2026)

Engine: nilbuild/video-demo `767bfb8` (skill at `~/.claude/skills/video-demo`), workspace
`~/.video-demo/auditglimmer-frontend` (outside the repo). Filmed from a pinned production build (`next build`,
static export) of a **private copy** of `frontend/`; the app source was not modified for filming.

## File checks
| Check | Result |
|---|---|
| `AuditGlimmer_Final_Demo.mp4` decodes end to end (`ffmpeg -v error -f null`) | no errors |
| Resolution / frame rate | 1920×1080, 60 fps (per scene 55.7–60.6 fps in motion; worst gap 273 ms in `muse`, under 2% of frames over 50 ms in any clip) |
| Duration | 161.8 s (2:42). Official maximum not published on the public event page — **owner to confirm in the submission portal** |
| Audio | present on every scene (mean −18.3 dB) |
| Spoken lines vs narration calls | 22 / 22 (3+3+4+4+3+5), no overrun reported by the engine |
| Credentials on screen | none: header shows `credentials: absent`, `live approved: no` |
| Stills read by eye | 13 stills in `stills/`; no clipped UI, text legible |

## Data integrity
- Every API response in the film is a **genuine AuditGlimmer response**, captured by
  `~/.video-demo/auditglimmer-frontend/seed/capture.py` from an isolated DEMO API (port 8010) running on a copy of
  the local database with test/judge/verify sessions removed **from the copy only**. Images are the stored bytes.
  An uncaptured request returns 404; nothing is synthesised.
- Recorded-live scenes (`sam`, `muse` part 1, `reconcile` Case A, `impact`) use stored outputs of real `sam-3.1`
  and `muse-spark-1.3` calls from 31 Oct; the narration says "recorded … replayed, no new model call".
  Values shown and spoken match storage: Muse `visible_manufacturer = HYSTER`, model and serial null with
  uncertainty notes, `model_confidence 0.85`; decision WEAK `R3_TYPE_ONLY`, candidates R-002/R-003.
- Fixture scenes (`muse` second read, `reconcile` Case B, `review`) are the "Evidence challenge (DEMO)" session;
  the DEMO badge is visible and the narration says "demo case" / "synthetic demo data".
- The review in scene 5 was performed for real on the copy during capture (POST 200); the film replays that
  response and the post-review reads.
- Spoken figures: holdout 5/6 exact serials, 0 unsafe, second reads 5/5 agree, $0.12
  (`docs/holdout-study-results.md`, independently verified); original study 11/16 exact, 0 invented on negatives,
  1 disputed unsafe verification (`docs/muse-study-results.md`). The two-read gate is called supporting evidence,
  not proof. No production certification is claimed.
- No paid calls were made to produce the video.

## Files
`AuditGlimmer_Final_Demo.mp4` (229 MB master, git-ignored) · `scenes/*.mp4` (git-ignored) · `stills/*.png` ·
`manifest.json` · `review-page.html` (the engine's corpus page; expects the engine's relative asset paths) ·
`NARRATION.md` · this file.
