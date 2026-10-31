# AuditGlimmer — final demo narration (as filmed)

Voice: local Kokoro `af_heart`, generated on this machine (no cloud TTS). 22 spoken lines, in this order; each
plays while the camera is on the subject it names. Source of truth: `~/.video-demo/auditglimmer-frontend/scenes/*.scene.ts`.

## 1 · problem — The problem: collateral checked by hand (27.8 s)
- Financial institutions rely on physical equipment as collateral. But checking that equipment against inspection photos is still slow, manual reconciliation.
- AuditGlimmer turns those photos into traceable evidence, and reconciles it against the register.
- Here is a register of pledged assets, with makes, models and serial numbers, and one real site photo to check it against.

## 2 · sam — SAM 3.1 finds each machine (25.3 s)
- This real photo was inspected live on October thirty-first. What you see is the recorded result, replayed. No new model call is made.
- SAM 3.1 returned a pixel mask for each forklift it found: two separate objects, each with its own position in the photo.
- Segmentation separates the objects. It does not tell us which registered asset each one is.

## 3 · muse — Muse Spark 1.3 reads what is printed (35.8 s)
- Muse Spark 1.3 read only this crop, and returned a structured record. The maker, Hyster, is printed on the machine.
- The model and the serial are not legible, so it says not visible, instead of guessing.
- It also records what it could not read. Extraction is valuable, but fallible, so these notes stay with the evidence.
- In this labelled demo case, a second, independent read of the same plate agrees on the serial. That agreement is supporting evidence, not proof.

## 4 · reconcile — Rules decide, people resolve ambiguity (33.6 s)
- Now the register. The evidence supports two rows: both Hyster forklifts, with different serials.
- Deterministic rules decide, not the model. With no readable serial, two identical machines cannot be told apart, so this goes to a person.
- A supported match looks different. Here a unique serial matches one row, the maker agrees, both reads agree, and nothing conflicts.
- That example is synthetic demo data. No real photo has produced an automatic match yet, and the page says so.

## 5 · review — A named person decides, and the report keeps the trail (34.1 s)
- In this demo case the two reads disagreed on the last digit of the serial, so nothing was verified automatically.
- The reviewer confirmed with a named, written note. The asset now shows as human confirmed, kept separate from automatic verification.
- The audit report states every status, the rule behind it, and the evidence it rests on.

Typed on screen (not spoken): reviewer `A. Auditor`; note `Checked the plate photo: serial reads GN-62040; the second read misread the last digit.`

## 6 · impact — Measured, traced, and honest about limits (40.3 s)
- We tested on fourteen new licensed photos, frozen before the run, with live Meta calls costing twelve cents.
- Muse read five of six legible serials exactly. Zero unsafe matches. And every second read agreed with the first.
- Our first, pre-registered study was harder on us: eleven of sixteen exact, no invented serials, and one disputed match that should not have verified. That failure is why the second read and the stricter rules exist.
- Every Meta call is logged with its model, latency, tokens and cost, next to its raw output.
- AuditGlimmer transforms inspection photographs into traceable financial evidence, and knows when that evidence is not strong enough to trust.
