# Pipeline Autopilot

**Causal Replay for CI/CD**

Pipeline Autopilot transforms a CI/CD failure into an understandable investigation and recovery process.
It uses multi-agent evidence gathering, a causal chain builder, fix generation, counterfactual simulation,
and an animated visual recovery story.

## Quick Start

```bash
make dev        # Start backend + frontend via Docker Compose
make load-demo  # Load sample scenario-001 into the running backend
make test       # Run backend + frontend tests
make clean      # Remove containers and local data
```

## Project Structure

```
pipeline-autopilot/
├── backend/        Python + FastAPI investigation engine
├── frontend/       React + TypeScript + Vite visual interface
├── sample-data/    Controlled CI failure scenarios (no live data required)
├── tests/          Backend (pytest) and frontend (Vitest) tests
└── data/           SQLite database (created at runtime, git-ignored)
```

## Demo Scenario

**scenario-001 — "The Silent Semver Break"**

A dependency is bumped from v2 to v3. The new major version removes a function used by the
payments service. Three downstream tests fail. The system identifies the root cause, proposes
a fix, and simulates recovery.

See [`sample-data/scenario-001/README.md`](sample-data/scenario-001/README.md) for details.

## Development

See [`pipeline-autopilot-plan.md`](../pipeline-autopilot-plan.md) for the full architecture plan.
