# Pipeline Autopilot

**Causal Replay for CI/CD**

Pipeline Autopilot transforms a CI/CD failure into an understandable investigation and recovery process.
It uses multi-agent evidence gathering, a causal chain builder, fix generation, counterfactual simulation,
and an animated visual recovery story.

## Quick Start

```bash
make load-demo  # Start services, load scenario-001, and print the browser URL
make test       # Run backend + frontend tests
make clean      # Remove containers and local data
```

## Running the Demo (Task 16)

**Prerequisites:** Docker and Docker Compose must be installed and running.

```bash
make load-demo
```

This single command:

1. Builds and starts the backend (`:8000`) and frontend (`:5173`) via Docker Compose.
2. Waits for the backend health endpoint to be ready.
3. POSTs `scenario-001` to the backend, creating a new pipeline run.
4. Prints the browser URL and pipeline ID.

Once the command completes, open **http://localhost:5173** in your browser.

The frontend will show a "Load Demo" button. Click it — the SSE stream opens automatically
and drives the full visual story:

```
scenario-001 loaded
  → backend pipeline starts (agents activate, evidence gathered)
  → frontend connects to SSE stream
  → story events consumed (causal chain, fix, counterfactual)
  → visual story plays through all 12 states
  → final RecoveryReport is visible (bottom-right overlay)
```

To stop and clean up:

```bash
make clean
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

```bash
make dev   # Start backend + frontend via Docker Compose (foreground, with logs)
make test  # Run backend (pytest) and frontend (Vitest) tests in containers
```

See [`pipeline-autopilot-plan.md`](../pipeline-autopilot-plan.md) for the full architecture plan.
