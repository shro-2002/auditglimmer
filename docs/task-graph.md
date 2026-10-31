# Task Graph (graph-engineering, task-graph discipline)

Method: [codejunkie99/graph-engineering](https://github.com/codejunkie99/graph-engineering)
`references/task-graphs.md` — draw an edge only when a job reads another job's *result*; delete
fake edges; diamond pattern (parallel workers → separate-context verify → single owned merge);
one writer per file; bounded loops; human gate only on irreversible edges.

## DAG as executed

```mermaid
flowchart TD
  ROOT[ROOT: inspect env, isolate project] --> A1[A1 verify Meta API docs]
  ROOT --> A2[A2 user stories + acceptance gates]
  A1 --> A3[A3 API contracts + typed schemas]
  A2 --> A3
  A1 --> A4[A4 ontology + reconciliation rules]
  A2 --> A5[A5 eval protocol + fixture spec]
  A3 --> FREEZE{{contracts frozen}}
  A4 --> FREEZE

  FREEZE --> B1[B1 Frontend UI<br/>owner: frontend worker agent<br/>files: frontend/**]
  FREEZE --> B2[B2 FastAPI, persistence, SSE<br/>owner: coordinator<br/>backend/app/main,db,services,pipeline]
  FREEZE --> B3[B3 SAM adapter + mask normalization<br/>backend/app/providers/sam_meta, fixture]
  FREEZE --> B4[B4 Muse adapter + evidence schema<br/>backend/app/providers/muse_meta, schemas]
  FREEZE --> B5[B5 deterministic reconciliation<br/>backend/app/reconcile.py]
  A5 --> B6[B6 synthetic fixtures<br/>scripts/make_fixtures.py, fixtures/**]
  A5 --> B7[B7 eval harness + tracing<br/>eval/**, ProviderCall table]

  B2 & B3 & B4 --> C2[C2 segmentation → extraction]
  C2 & B5 --> C3[C3 evidence → reconciliation]
  B1 & B2 --> C1[C1 frontend ↔ backend]
  C1 & C3 --> C4[C4 reconciliation → dashboard]
  C4 --> C5[C5 report + review actions]
  B6 --> C2

  C5 --> D1[D1 backend + schema tests]
  C5 --> D2[D2 reconciliation + provenance tests]
  C5 --> D3[D3 UI a11y + browser tests<br/>separate context: e2e verifier agent<br/>files: e2e/**]
  C5 --> D4[D4 provider contract + failure tests]
  C5 --> D5[D5 security/privacy/deps review<br/>separate context: adversarial reviewer, read-only]
  C5 --> D6[D6 end-to-end journey<br/>e2e verifier agent]

  D1 & D2 & D3 & D4 & D5 & D6 --> E[E final owned merge<br/>coordinator only: triage findings, fix, re-run gates]
  E --> G9{{HUMAN GATE: paid live smoke<br/>Gate 9 — blocked: no key / no approval}}
  E --> RC[release candidate, not deployed]
```

## Fake edges deleted

| Assumed sequence | Why it is fake | Effect |
|---|---|---|
| "build backend, then frontend" | the frontend reads the *contract*, not the backend's code | B1 ran in parallel with B2–B5 |
| "write SAM adapter, then fixtures" | fixtures read the fixture spec (A5), not the adapter | B6 ran independently of B3 |
| "verify UI after security review" | D3/D5 read the merged code, not each other | D3, D5 ran concurrently |
| "reconcile after extraction finishes (stored)" | reconciliation reads persisted evidence, not the run | reconciliation is recomputed on read; no edge from the run worker |

Kept real edges: contracts → all B nodes; B2+B3+B4 → C2; everything → E.

## Parallelism actually used (stop rule)

Split only where work never reads sibling results:

- **B1** frontend → one worker agent, exclusive owner of `frontend/**`.
- **B2–B7** backend → coordinator, sequential (they share types and the run worker: splitting would
  have been the "sequential work" case the stop rule warns against).
- **D3+D6** browser verification → separate agent, exclusive owner of `e2e/**`.
- **D5 (+D2, D4 review)** → separate adversarial agent, read-only.
- D1/D2/D4 automated tests were written by the coordinator; the adversarial agent re-checks them
  from a different context.

Spawn cap: 3 agents total. One writer per file enforced by directory ownership.

## Guardrails

- Max 3 repair attempts per failing gate before marking it blocked.
- Paid inference gated by env (`AUDITGLIMMER_LIVE_APPROVED=1`), a CLI flag for the smoke script,
  per-run request and USD caps (`pipeline.Budget`).
- No commits, pushes, deploys or submissions without the user.
