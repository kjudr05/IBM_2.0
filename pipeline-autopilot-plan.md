# Pipeline Autopilot — Implementation Plan

## Overview

**Goal:** Build a hackathon-quality CI/CD failure investigation and recovery tool that uses
multi-agent evidence gathering, structured evidence artifacts, a causal chain builder, fix
generation, counterfactual simulation, and a visual animated recovery story.

**Scope:** One complete, reproducible end-to-end failure scenario demonstrated with a public
sample dataset. No confidential or company data. AI provider layer kept modular so
IBM watsonx / Granite can be swapped in without rewriting application code.

**Non-goals (deferred):**
- Live GitHub Actions webhook integration (use sample dataset for MVP)
- Multiple failure scenarios (one deep scenario beats many shallow ones)
- Authentication / multi-user support
- Production deployment / secrets management
- Automated benchmark measurement (methodology defined, measurement deferred)
- Mobile layout

---

## 1. Repository / Folder Structure

```
pipeline-autopilot/
├── AGENTS.md                        # Agent guidance (update after scaffold)
├── README.md
├── docker-compose.yml               # Orchestrates frontend + backend + sandbox
├── Makefile                         # Top-level dev commands
│
├── backend/
│   ├── pyproject.toml               # Python deps — FastAPI, uvicorn, pydantic, httpx
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry, CORS, lifespan
│   │   ├── api/
│   │   │   ├── ingest.py            # POST /api/ingest  (webhook or sample load)
│   │   │   ├── pipeline.py          # GET  /api/pipeline/{id}  (state + graph)
│   │   │   ├── stream.py            # GET  /api/stream/{id}    (SSE event stream)
│   │   │   └── report.py            # GET  /api/report/{id}    (final report)
│   │   ├── agents/
│   │   │   ├── base.py              # BaseInvestigator interface
│   │   │   ├── log_investigator.py
│   │   │   ├── code_investigator.py
│   │   │   ├── dependency_investigator.py
│   │   │   ├── test_investigator.py
│   │   │   ├── infra_investigator.py
│   │   │   ├── history_investigator.py
│   │   │   └── orchestrator.py      # Bob Orchestrator — drives the full flow
│   │   ├── models/
│   │   │   ├── events.py            # PipelineFailureEvent (ingest schema)
│   │   │   ├── evidence.py          # All evidence artifact schemas (Pydantic)
│   │   │   ├── causal.py            # CausalNode, CausalEdge, CausalChain
│   │   │   ├── fix.py               # ProposedFix, ValidationResult
│   │   │   └── report.py            # RecoveryReport
│   │   ├── graph/
│   │   │   ├── builder.py           # Assembles CausalChain from evidence
│   │   │   └── replay.py            # Produces ordered replay steps
│   │   ├── simulation/
│   │   │   └── counterfactual.py    # Predicts system state after fix applied
│   │   ├── ai/
│   │   │   ├── provider.py          # Abstract AIProvider interface
│   │   │   ├── mock_provider.py     # Deterministic provider for MVP demo
│   │   │   └── watsonx_provider.py  # IBM watsonx stub (connect later)
│   │   ├── db/
│   │   │   ├── database.py          # SQLite connection + init
│   │   │   └── store.py             # Read/write pipeline state
│   │   └── bus/
│   │       └── evidence_bus.py      # In-process async evidence collector
│
├── frontend/
│   ├── package.json                 # React + TypeScript + Vite + React Flow + Framer Motion
│   ├── Dockerfile
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── types/                   # TypeScript mirrors of backend Pydantic models
│   │   │   ├── events.ts
│   │   │   ├── evidence.ts
│   │   │   ├── causal.ts
│   │   │   └── fix.ts
│   │   ├── state/
│   │   │   ├── storyMachine.ts      # XState or plain reducer: HEALTHY→RECOVERING
│   │   │   └── pipelineStore.ts     # Zustand store: graph data, evidence, replay
│   │   ├── api/
│   │   │   ├── client.ts            # Typed fetch wrappers
│   │   │   └── sse.ts               # SSE hook — drives state machine transitions
│   │   ├── components/
│   │   │   ├── SystemCanvas/        # React Flow canvas — main visual stage
│   │   │   │   ├── SystemCanvas.tsx
│   │   │   │   ├── nodes/           # ServiceNode, AgentNode, EvidenceNode
│   │   │   │   └── edges/           # AnimatedEdge, FailureEdge, EvidenceEdge
│   │   │   ├── StoryBar/            # Top progress strip: 12 story steps
│   │   │   ├── EvidencePanel/       # Sliding panel — Level 2 + 3 disclosure
│   │   │   │   ├── CausalChain.tsx
│   │   │   │   ├── EvidenceCard.tsx
│   │   │   │   └── TechnicalDrill.tsx
│   │   │   ├── ReplayControls/      # Play / pause / step replay
│   │   │   ├── CounterfactualSplit/ # Side-by-side broken vs. fixed view
│   │   │   └── RecoveryReport/      # Final summary card
│   │   └── hooks/
│   │       ├── useSSE.ts
│   │       └── useReplay.ts
│
├── sample-data/
│   ├── scenario-001/                # Single controlled failure scenario
│   │   ├── README.md                # Describes the scenario in plain language
│   │   ├── failure_event.json       # Ingest payload
│   │   ├── git_diff.patch
│   │   ├── ci_log.txt
│   │   ├── test_results.xml
│   │   ├── dependency_before.json
│   │   ├── dependency_after.json
│   │   ├── dockerfile.txt
│   │   ├── ci_config.yml
│   │   └── history.json             # Previous failures for this repo
│   └── scenarios.json               # Index of available scenarios
│
└── tests/
    ├── backend/
    │   ├── test_evidence_schemas.py
    │   ├── test_causal_builder.py
    │   ├── test_orchestrator.py
    │   └── test_counterfactual.py
    └── frontend/
        └── (Vitest unit tests for state machine + evidence parsing)
```

---

## 2. Data Models

### 2.1 Ingest / Failure Event

```
PipelineFailureEvent
  id: str                      # uuid
  repo: str                    # e.g. "acme/payments-service"
  branch: str
  commit_sha: str
  pipeline_run_id: str
  timestamp: datetime
  failure_stage: str           # e.g. "test", "build", "deploy"
  raw_log_url: str             # or embedded
  raw_log_text: str
  git_diff_patch: str
  test_results_xml: str
  dependency_before: dict
  dependency_after: dict
  dockerfile_content: str
  ci_config_content: str
  history: list[HistoricalRun]
```

### 2.2 Evidence Artifacts (Pydantic models, all extend BaseEvidence)

```
BaseEvidence
  evidence_id: str
  agent_id: str
  pipeline_id: str
  created_at: datetime
  confidence: float            # 0.0 – 1.0
  summary: str                 # plain-language one-liner

FailureEvidence(BaseEvidence)
  error_class: str
  error_message: str
  stack_trace: list[str]
  failure_timestamp: datetime
  affected_stage: str

ChangeEvidence(BaseEvidence)
  changed_files: list[ChangedFile]   # {path, additions, deletions, diff_hunk}
  changed_functions: list[str]
  commit_sha: str
  author: str
  commit_message: str

DependencyEvidence(BaseEvidence)
  added: list[DepChange]             # {name, old_version, new_version}
  removed: list[DepChange]
  changed: list[DepChange]
  breaking_changes: list[str]        # identified incompatibilities

TestEvidence(BaseEvidence)
  failed_tests: list[FailedTest]     # {name, class, message, duration}
  flaky_tests: list[str]
  regression_tests: list[str]        # tests that previously passed
  total_run: int
  total_failed: int

InfraEvidence(BaseEvidence)
  dockerfile_issues: list[str]
  ci_config_issues: list[str]
  env_var_issues: list[str]
  image_changes: list[str]

HistoricalEvidence(BaseEvidence)
  similar_failures: list[SimilarFailure]  # {date, root_cause, fix_applied}
  recurrence_count: int
  last_seen: datetime
  known_fix: str | None
```

### 2.3 Causal Graph

```
CausalNode
  node_id: str
  node_type: Enum[CHANGE, FAILURE, CASCADE, ROOT_CAUSE, FIX]
  label: str                   # display text
  description: str             # plain-language explanation
  evidence_ids: list[str]      # supporting evidence references
  confidence: float

CausalEdge
  edge_id: str
  source_node_id: str
  target_node_id: str
  relation: str                # e.g. "caused", "contributed_to", "triggered"
  explanation: str

CausalChain
  chain_id: str
  pipeline_id: str
  nodes: list[CausalNode]
  edges: list[CausalEdge]
  root_cause_node_id: str
  narrative: str               # 2–3 sentence plain-language explanation
```

### 2.4 Fix and Validation

```
ProposedFix
  fix_id: str
  pipeline_id: str
  root_cause_node_id: str
  description: str             # plain language
  fix_type: Enum[DEPENDENCY_CHANGE, CODE_PATCH, CONFIG_CHANGE, ENV_FIX]
  patch: str | None            # unified diff
  dependency_changes: list[DepChange] | None
  config_changes: dict | None
  rationale: str               # why this fix addresses the root cause

ValidationResult
  validation_id: str
  fix_id: str
  status: Enum[PASSED, FAILED, PARTIAL]
  simulated_test_results: list[TestResult]
  confidence: float
  validation_narrative: str
```

### 2.5 Recovery Report

```
RecoveryReport
  report_id: str
  pipeline_id: str
  created_at: datetime
  root_cause_summary: str      # Level 1 — one sentence
  causal_explanation: str      # Level 2 — paragraph
  evidence_summary: dict       # Level 3 — links to each evidence artifact
  proposed_fix: ProposedFix
  validation_result: ValidationResult
  causal_chain: CausalChain
  replay_steps: list[ReplayStep]
  counterfactual: CounterfactualResult
```

---

## 3. Agent Architecture

### 3.1 BaseInvestigator Interface

Every investigator implements:

```
class BaseInvestigator:
  agent_id: str
  async def investigate(event: PipelineFailureEvent) -> BaseEvidence
```

Investigators are stateless. The orchestrator owns state.

### 3.2 Evidence Bus

A simple async in-process collector. The orchestrator:
1. Dispatches all six investigators concurrently (asyncio.gather).
2. Collects results via the Evidence Bus.
3. Proceeds to causal chain construction once all evidence is received (or timeout).

The bus exposes an async `publish(evidence)` method and an `await_all()` method.
For the MVP, this is purely in-process. A message queue could replace it later.

### 3.3 Bob Orchestrator Flow

```
orchestrator.run(event) →
  1. emit SSE: AGENTS_ACTIVATING
  2. asyncio.gather all 6 investigators
  3. emit SSE: EVIDENCE_FLOWING (one event per artifact as it arrives)
  4. collect all evidence → emit SSE: EVIDENCE_CONVERGING
  5. causal_graph.builder.build(all_evidence) → CausalChain
  6. emit SSE: ROOT_CAUSE_IDENTIFIED
  7. fix_generator.generate(causal_chain) → ProposedFix
  8. emit SSE: FIX_PROPOSED
  9. counterfactual.simulate(event, proposed_fix) → CounterfactualResult
  10. emit SSE: COUNTERFACTUAL_SIMULATING
  11. validator.validate(proposed_fix) → ValidationResult
  12. emit SSE: SYSTEM_RECOVERING
  13. build RecoveryReport
  14. emit SSE: COMPLETE
```

### 3.4 AI Provider Interface

```
class AIProvider (abstract):
  async def analyze(prompt: str, context: dict) -> str
  async def extract_structured(prompt: str, schema: type[BaseModel]) -> BaseModel
```

`MockProvider` returns deterministic responses keyed on `prompt_key` — allows the
demo to run without any external API calls.

`WatsonxProvider` calls the watsonx.ai inference endpoint using the same interface.

Investigators call `provider.extract_structured(...)` and parse the result into
their respective evidence schema.

---

## 4. Causal Graph Model

The causal graph is a directed acyclic graph (DAG):

- **Root** — the triggering change (e.g. dependency bump in commit X)
- **Intermediate nodes** — how the change cascades (e.g. API contract broken → test failure)
- **Terminal node** — the observed failure visible in CI logs

Building the chain:
1. Log investigator identifies the observable failure.
2. Code investigator identifies the triggering change.
3. Dependency/Infra/Test investigators identify what the change affected.
4. The builder links nodes: CHANGE → DEPENDENCY_BREAK → TEST_FAILURE → BUILD_FAIL.
5. Edges carry `explanation` strings for the non-technical audience.

The `narrative` field on CausalChain is the plain-language sentence shown to a non-technical judge.

---

## 5. Animation / State Model

The frontend drives a **story machine** with 12 named states (matching the visual story):

```
HEALTHY
CHANGE_DETECTED
FAILURE_PROPAGATING
AGENTS_ACTIVATING
EVIDENCE_FLOWING
EVIDENCE_CONVERGING
ROOT_CAUSE_IDENTIFIED
FIX_PROPOSED
COUNTERFACTUAL_SIMULATING
COUNTERFACTUAL_SHOWN
SYSTEM_RECOVERING
HEALTHY (recovered)
```

**SSE events from backend drive state transitions.**

Each state has:
- A set of active React Flow nodes/edges (what is lit up on canvas)
- An animation intent (pulse, flow-particle, collapse, expand)
- A story bar step highlighted
- A caption string for the non-technical audience

`pipelineStore` (Zustand) holds:
- `storyState`: current story machine state
- `graphNodes` / `graphEdges`: React Flow data
- `evidenceByAgent`: map of agent_id → evidence artifact
- `causalChain`: the assembled chain
- `proposedFix`
- `validationResult`
- `replaySteps`: ordered list for manual replay
- `counterfactual`: before/after node states

---

## 6. React Flow Canvas Design

### Node Types

| Node Type        | Represents                       | Visual                         |
|------------------|----------------------------------|--------------------------------|
| ServiceNode      | A service in the software system | Rounded box, icon, health ring |
| AgentNode        | An investigation agent           | Hexagon with agent name        |
| EvidenceNode     | A travelling evidence artifact   | Small animated card            |
| CausalNode       | A step in the causal chain       | Chain link shape               |
| RootCauseNode    | The identified root cause        | Bright highlight, pulsing      |
| FixNode          | The proposed fix                 | Green checkmark aura           |

### Edge Types

| Edge Type     | Represents                        | Visual                         |
|---------------|-----------------------------------|--------------------------------|
| HealthyEdge   | Normal system data flow           | Thin grey animated dash        |
| FailureEdge   | Failure propagating               | Red particle stream            |
| EvidenceEdge  | Evidence travelling to agent      | Blue animated dot stream       |
| CausalEdge    | Causal relationship in chain      | Orange solid with label        |

### Canvas Layers (z-index stacking)

1. Background grid (subtle)
2. Edges
3. Nodes
4. Floating evidence particle overlays (CSS animation, not React Flow nodes)
5. Story caption overlay (top-center)

---

## 7. SSE Event Protocol

Backend sends newline-delimited JSON events:

```json
{ "type": "STATE_TRANSITION",  "state": "AGENTS_ACTIVATING", "ts": "..." }
{ "type": "EVIDENCE_ARRIVED",  "agent_id": "log_investigator", "evidence": {...}, "ts": "..." }
{ "type": "CAUSAL_CHAIN",      "chain": {...}, "ts": "..." }
{ "type": "FIX_PROPOSED",      "fix": {...}, "ts": "..." }
{ "type": "VALIDATION_RESULT", "result": {...}, "ts": "..." }
{ "type": "REPORT_READY",      "report_id": "...", "ts": "..." }
{ "type": "ERROR",             "message": "...", "ts": "..." }
```

Frontend SSE hook (`useSSE.ts`) dispatches each event into the Zustand store,
which triggers React Flow re-renders and Framer Motion animation sequences.

---

## 8. API Endpoints

| Method | Path                              | Purpose                                          |
|--------|-----------------------------------|--------------------------------------------------|
| POST   | /api/ingest                       | Submit a failure event (or load sample scenario) |
| GET    | /api/pipeline/{id}                | Full pipeline state snapshot                     |
| GET    | /api/stream/{id}                  | SSE event stream for live updates                |
| GET    | /api/report/{id}                  | Final RecoveryReport JSON                        |
| GET    | /api/scenarios                    | List available sample scenarios                  |
| POST   | /api/scenarios/{id}/load          | Load a sample scenario as a new pipeline run     |

All responses use consistent envelope:
```json
{ "data": {...}, "error": null }
```

---

## 9. Sample Scenario Design (scenario-001)

**Scenario Name:** "The Silent Semver Break"

**Plain-language description:**
A developer updates a utility library from v2.3.1 to v3.0.0.
The new major version removes a function used by the payments service.
Tests fail. Build fails. Three downstream services show red.

**Why this scenario:**
- Affects multiple services (shows failure propagation clearly)
- Clear single root cause (one dependency bump)
- Causal chain is short and understandable
- Fix is minimal (pin dependency to last compatible version)
- Validation is checkable (re-run affected tests against pinned version)

**Files in scenario-001:**
- `failure_event.json` — complete ingest payload
- `git_diff.patch` — the dependency file change
- `ci_log.txt` — build output with ImportError stack trace
- `test_results.xml` — JUnit XML with 3 failed tests
- `dependency_before.json` — package-lock state before PR
- `dependency_after.json` — package-lock state after PR
- `dockerfile.txt` — no changes (rules out infra cause)
- `ci_config.yml` — no changes (rules out CI config cause)
- `history.json` — two previous similar failures (same library, older bumps)

**Mock AI responses** are pre-written as deterministic strings keyed on this
scenario. The MockProvider returns them without any LLM call.

---

## 10. Counterfactual Simulation Design

The counterfactual is NOT a real execution. It is a structured prediction:

```
CounterfactualResult
  pipeline_id: str
  fix_id: str
  before_state: SystemSnapshot    # current broken graph layout
  after_state: SystemSnapshot     # predicted recovered layout
  changed_nodes: list[str]        # which nodes change status
  narrative: str                  # "If this fix is applied, the 3 failing tests
                                  #  will pass and the downstream services will recover."

SystemSnapshot
  node_id → NodeHealth            # HEALTHY | DEGRADED | FAILED
```

The `counterfactual.py` module:
1. Takes the current `SystemSnapshot` (all affected nodes = FAILED/DEGRADED).
2. Applies the `ProposedFix` logic rules:
   - If fix_type is DEPENDENCY_CHANGE → mark dependency node HEALTHY
     → propagate: all nodes whose only failure cause was that dep → HEALTHY
3. Returns `CounterfactualResult`.

This is deterministic for the MVP — no LLM call needed.

**Frontend rendering:**
The `CounterfactualSplit` component shows the canvas split vertically:
- Left: current state (red nodes, red edges)
- Right: predicted state (green nodes, healthy edges)
- Animated transition from left to right when user accepts the fix

---

## 11. Replay Model

```
ReplayStep
  step_index: int
  story_state: StoryState          # which state this step belongs to
  caption: str                     # non-technical explanation
  active_node_ids: list[str]       # which nodes to highlight
  active_edge_ids: list[str]
  evidence_in_flight: list[EvidenceParticle]  # {from, to, artifact_type}
  timestamp_offset_ms: int         # playback timing
```

The `replay.py` builder converts the full pipeline result into an ordered list
of `ReplayStep` records. The frontend `useReplay.ts` hook steps through them
at the specified timing offsets when the user uses the replay controls.

---

## 12. Docker / Deployment Strategy

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes:
      - ./sample-data:/app/sample-data:ro
      - ./data:/app/data          # SQLite lives here

  frontend:
    build: ./frontend
    ports: ["5173:5173"]
    environment:
      - VITE_API_URL=http://backend:8000
```

`Makefile` targets:
```
make dev         # docker-compose up --build
make test        # run backend tests + frontend tests
make load-demo   # POST sample scenario-001 to local backend
make clean       # remove containers + SQLite data
```

---

## 13. Testing Strategy

### Backend

- `test_evidence_schemas.py` — validates Pydantic model instantiation and JSON
  round-trips for all evidence types
- `test_causal_builder.py` — given a known evidence set, assert correct
  CausalChain nodes/edges/root_cause_node_id
- `test_orchestrator.py` — end-to-end run with MockProvider: assert all 12 SSE
  events emitted in order, assert RecoveryReport is complete
- `test_counterfactual.py` — given broken SystemSnapshot + fix, assert predicted
  healthy state is correct

Single test:
```
cd backend && pytest tests/test_causal_builder.py::test_dependency_chain -v
```

### Frontend

- State machine unit tests (Vitest) — assert correct transitions on SSE events
- Evidence parsing tests — assert TypeScript types match backend JSON shapes
- No visual regression tests for MVP (deferred)

Single test:
```
cd frontend && npx vitest run src/state/storyMachine.test.ts
```

---

## 14. Benchmark Methodology (measure later, methodology defined now)

For each controlled scenario run, record:

| Metric                          | How to Measure                                      |
|---------------------------------|-----------------------------------------------------|
| Time to root cause              | `AGENTS_ACTIVATING` → `ROOT_CAUSE_IDENTIFIED` delta |
| Manual investigation steps      | Count: 0 for fully automated run                    |
| Tests executed                  | Count from `ValidationResult.simulated_test_results`|
| Fix attempts                    | Count of `ProposedFix` records per pipeline_id      |
| Developer interventions         | Count of manual overrides in UI (0 for full auto)   |
| Root cause accuracy             | Compare identified root_cause_node_id vs. ground    |
|                                 | truth label in scenario README                      |
| Fix validation pass rate        | `ValidationResult.status == PASSED` rate            |

Ground truth labels live in `sample-data/scenario-001/README.md`.

Do not report benchmark numbers until at least 5 deterministic runs are measured.

---

## 15. IBM Bob 2.0 Usage Strategy

This section documents how Bob 2.0 is used **during development** (satisfies hackathon judging criterion 1).

| Bob Capability         | How We Use It                                                    |
|------------------------|------------------------------------------------------------------|
| Agent mode             | Implement each backend module as a separate Bob agent sub-task   |
| Parallel work          | Backend + frontend + sample data authored in parallel Bob tasks  |
| Subagents              | Spawn explore subagents to verify schema consistency across       |
|                        | backend models and frontend TypeScript types                     |
| Document understanding | Feed CI logs, git diffs, JUnit XML to Bob for evidence schema    |
|                        | design validation and for writing mock provider responses        |
| Plan mode              | This document                                                    |

---

## 16. Implementation Phases (ordered by dependency)

### Phase 0 — Scaffold (no external dependencies)
- Repo structure, docker-compose, Makefile
- Backend: FastAPI skeleton, SQLite init, empty agent stubs
- Frontend: Vite + React + TypeScript skeleton, React Flow canvas stub
- Sample data: scenario-001 files

### Phase 1 — Data Layer (backend, no AI)
- All Pydantic evidence models implemented and tested
- Ingest endpoint: parse `PipelineFailureEvent` from JSON
- Evidence bus (in-process)
- Store/retrieve pipeline state in SQLite

### Phase 2 — Agents with Mock Provider (backend)
- All 6 investigators implemented using MockProvider
- Orchestrator runs investigators concurrently, collects evidence
- Causal chain builder produces CausalChain from evidence
- Fix generator produces ProposedFix
- Counterfactual simulator produces CounterfactualResult
- SSE stream emits all 12 events in correct order

### Phase 3 — Vertical Slice End-to-End (backend complete)
- Full `POST /api/scenarios/001/load` → SSE stream → RecoveryReport
- All backend tests passing
- This is the **minimum working demo backend**

### Phase 4 — Visual Canvas (frontend)
- React Flow canvas with ServiceNode, AgentNode node types
- SSE hook consuming events
- Story machine state transitions
- Basic animation: failure edge turns red, agents activate

### Phase 5 — Evidence Panel (frontend)
- EvidencePanel sliding in on evidence arrival
- Causal chain rendered as Level 2 disclosure
- Technical drill-down for Level 3 (raw logs, diffs, test output)

### Phase 6 — Counterfactual + Recovery (frontend)
- CounterfactualSplit component
- SYSTEM_RECOVERING animation: red nodes fade to green sequentially
- RecoveryReport card

### Phase 7 — Replay Controls (frontend)
- ReplayControls: play / pause / step
- `useReplay.ts` steps through `ReplayStep` list

### Phase 8 — Polish (last)
- Story captions for non-technical audience
- Framer Motion transitions between story states
- Responsive layout for demo screen size
- Makefile `make load-demo` one-command demo startup

---

## 17. MVP Vertical Slice (Smallest Working Demo)

The absolute minimum to demonstrate the full story end-to-end:

**Backend (Phase 0–3):**
1. `PipelineFailureEvent` ingest from `scenario-001/failure_event.json`
2. All 6 investigators run with MockProvider (deterministic)
3. Causal chain produced: 4 nodes, 3 edges, root_cause identified
4. Fix proposed: pin `utility-lib` to `2.3.1`
5. Counterfactual: 3 nodes flip from FAILED → HEALTHY
6. Validation: 3 tests pass
7. SSE emits all 12 events
8. RecoveryReport JSON returned

**Frontend (Phase 4 subset):**
1. Canvas shows 5 service nodes + 6 agent nodes
2. SSE events drive node color changes (grey → red → yellow investigating → green recovered)
3. Evidence panel shows root cause text + proposed fix
4. One-sentence caption per story state

This slice is **demonstrable to a non-technical judge** and contains every
conceptual element of the product. All subsequent phases deepen the experience
without changing the core story.

---

## FIRST IMPLEMENTATION TASKS

Ordered — complete each before starting the next.

1. **Create repo scaffold** — directory structure, empty files, docker-compose.yml, Makefile
2. **Implement Pydantic evidence models** — `backend/app/models/` — all schemas, unit tests
3. **Implement ingest endpoint** — parse scenario-001 JSON, store in SQLite
4. **Implement MockProvider** — deterministic responses for scenario-001
5. **Implement all 6 investigators** — each calls MockProvider, returns typed evidence
6. **Implement Evidence Bus + Orchestrator** — concurrent dispatch, collect, emit SSE
7. **Implement Causal Chain builder** — evidence in → CausalChain out, unit tested
8. **Implement Fix Generator + Counterfactual** — deterministic for scenario-001
9. **Implement SSE stream endpoint** — all 12 events flow in correct order
10. **Frontend scaffold** — Vite + React + React Flow canvas + Zustand store
11. **Implement SSE hook + story machine** — state transitions wired to SSE events
12. **Implement ServiceNode + AgentNode + failure animation** — red pulse on FAILURE_PROPAGATING
13. **Implement EvidencePanel** — causal chain + plain-language root cause visible
14. **Implement CounterfactualSplit** — before/after node states shown
15. **Implement RecoveryReport card** — final summary visible
16. **One-command demo** — `make load-demo` loads scenario, auto-starts SSE, plays story

---

## Deferred (explicitly out of MVP scope)

- Live GitHub Actions webhook (real CI integration)
- Multiple scenarios (add after scenario-001 is perfect)
- IBM watsonx provider connection (interface is ready, swap in post-MVP)
- Automated benchmark measurement (methodology defined, execution deferred)
- Authentication
- Mobile layout
- Visual regression tests
- Performance optimization of React Flow canvas for large graphs
- Replay step fine-grained timing (use simple 1s intervals for MVP)
