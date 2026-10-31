# Hackathon Compliance — Meta AI Developer Hackathon (checked 2026-10-31)

> **Update (2026-10-31, real-photo study):** 26 further `muse-spark-1.3` calls ($0.158) ran in the pre-registered real-photo study (`docs/muse-study-results.md`). Verified live footprint now: **6 SAM + 31 Muse calls ≈ $0.197**. Pre-registered outcome: exact serial reads 11/16 (69%), 0 invented serials on 8 negatives, 0 wrong-asset auto-verifications among agreed items, but 1 auto-verification on a disputed item (safety gate failed as pre-registered).

> **Correction (2026-10-31, independent judge audit):** stored artifacts substantiate **6 SAM + 5 Muse calls ≈ $0.0388** (SQLite: 5 SAM + 4 Muse = $0.0306; `eval/results/live-smoke.json`: 1 SAM; `eval/results/live-muse-nameplate.json`: 1 Muse $0.0057). The 7th SAM call (first smoke call) was console-only and has no persisted artifact. The nameplate call ran via a direct script, not through the app pipeline. Treat "7 SAM / ≈$0.041" as claimed, "6 SAM / ≈$0.039" as verified.


Sources: Official Rules inside the Cerebral Valley waiver page
(https://cerebralvalley.ai/e/meta-ai-developer-hackathon/waiver), event page
(https://cerebralvalley.ai/e/meta-ai-developer-hackathon), Meta page
(https://dev.meta.ai/events/global-hackathon). The submission form itself requires sign-in and was
not inspected.

| Requirement | Official text / finding | AuditGlimmer status |
|---|---|---|
| Deadline | Nov 4, 9:00 PM ET; judging Nov 4–8; winners Nov 9 | open — owner submits |
| Portal | cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit | owner action |
| Track | Indie developer (individuals/students, teams ≤ 4) or Startup | Indie appears to fit — owner confirms |
| Meta technology | "build with Meta AI products, including Muse Spark, Glimmer, SAM 3" | uses **SAM 3.1** and **Muse Spark 1.3** via Meta Model API, verified live |
| Judging (official weights) | Impact 30%, Use of Meta AI Tooling 25%, Technical Depth & Execution 20%, Demo 25% | see submission-final.md |
| Demo video | implied by Demo criterion; length/hosting NOT FOUND | script ready; recording is an owner action |
| Public repo / licence / hosted URL | NOT FOUND in public pages | repo not yet under git; no hosted URL (auth missing) |
| Original work; open source allowed if licences followed | stated | dependencies' licences recorded; SAM License for `meta-sam-parser`; photo licences in `fixtures/real/LICENSES.md` (one CC BY-SA asset needs attribution) |
| Build window | "Ten days", Oct 26 – Nov 4 | AuditGlimmer was created 2026-10-31 inside the window (new folder, no code from other projects) |
| AI-assistant disclosure | NOT FOUND | recommend disclosing that development used an AI coding assistant (Claude Code) |
| Eligibility | 18+, sanctioned regions excluded, Meta/CV staff excluded | owner confirms |
| Credits | "$150 in Meta Model API credits, valid for a 10-day development window"; Credit Terms not read | spend so far ≈ $0.041 est.; whether credits applied is unverified |
| Licence grant | entrants grant organisers a perpetual, royalty-free licence to the submission | owner should be aware before submitting |

## Unresolved questions (owner)

1. Video maximum length and hosting (assume ≤ 3 min until confirmed).
2. Whether a public repository and/or hosted demo URL is required.
3. Whether AI-assistant use must be disclosed (recommended regardless).
4. Indie-track wording ("individual builders" vs teams of four) — confirm your entry type.
5. Credit Terms content and whether the $150 credit covered the live calls.
6. CC BY-SA photo: keep with attribution or swap for a public-domain nameplate photo.
