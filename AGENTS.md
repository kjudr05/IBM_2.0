# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Project

**Pipeline Autopilot** — Causal Replay for CI/CD. IBM Bob 2.0 hackathon project.
Full architecture plan: [`pipeline-autopilot-plan.md`](pipeline-autopilot-plan.md)

## Structure

```
pipeline-autopilot/
├── backend/        Python 3.11 + FastAPI + Pydantic v2 + aiosqlite
├── frontend/       React 18 + TypeScript + Vite + React Flow (@xyflow/react) + Zustand
├── sample-data/    Deterministic CI failure scenarios — no live data required
└── tests/          pytest (backend) + Vitest (frontend)
```

## Commands

```bash
# From pipeline-autopilot/
make dev          # docker compose up --build (backend :8000, frontend :5173)
make test         # run all tests in containers
make load-demo    # POST scenario-001 to running backend
make clean        # remove containers + data/

# Backend single test (from pipeline-autopilot/backend/)
pytest tests/test_causal_builder.py::test_dependency_chain -v

# Frontend single test (from pipeline-autopilot/frontend/)
npx vitest run src/state/storyMachine.test.ts
```

## Non-Obvious Constraints

- **React Flow package name**: the npm package is `@xyflow/react` (not `react-flow-renderer` or `reactflow`)
- **Backend tests live in `tests/` at repo root** (sibling of `backend/`), not inside `backend/`
- **SSE events are newline-delimited JSON** — each event has `type`, payload fields, and `ts`; the 12 event types are defined in the plan section 7
- **MockProvider is the only AI provider for MVP** — `WatsonxProvider` is a stub; do not wire real LLM calls until explicitly requested
- **All evidence artifacts extend `BaseEvidence`** — never return free-text from an investigator; always return a typed Pydantic model
- **Orchestrator runs all 6 investigators via `asyncio.gather`** — investigators must be stateless
- **Counterfactual simulation is deterministic rule-based** — no LLM call; see plan section 10
- **SQLite `data/` directory** is created at runtime and git-ignored — never commit it
- **Frontend state machine has exactly 12 named states** — see `storyMachine.ts` header comment and plan section 5
- **`failure_event.json` is the ingest payload shape** — backend `PipelineFailureEvent` Pydantic model must match it exactly
- **Backend pyproject.toml** is the single source of Python dependencies — do not add a `requirements.txt`

## Task Implementation Order

Tasks are numbered in `pipeline-autopilot-plan.md` section "FIRST IMPLEMENTATION TASKS".
Each task must be completed and approved before starting the next.
Current status: **Task 1 complete** (scaffold only — no application logic implemented yet).
