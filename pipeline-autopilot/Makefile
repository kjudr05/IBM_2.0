.PHONY: dev test load-demo clean backend-shell frontend-shell

# Start backend + frontend via Docker Compose (rebuilds images)
dev:
	docker compose up --build

# Run backend (pytest) and frontend (vitest) tests
test:
	docker compose run --rm backend pytest tests/ -v
	docker compose run --rm frontend npx vitest run

# ---------------------------------------------------------------------------
# load-demo — one-command end-to-end demo (Task 16)
#
# Flow:
#   1. Start backend + frontend via Docker Compose (detached, with build).
#   2. Wait for the backend health endpoint to become ready (up to 60s).
#   3. POST scenario-001 to the backend — returns the new pipeline_id.
#   4. Print the browser URL so the operator can open it and watch the story.
#
# The frontend connects to the backend SSE stream automatically as soon as the
# operator clicks "Load Demo" in the browser — or, if the pipeline_id is
# already in the URL, the story starts immediately on page load.
#
# Prerequisites: Docker + Docker Compose must be installed and running.
# ---------------------------------------------------------------------------

load-demo:
	@echo "==> Starting services (backend :8000, frontend :5173)..."
	docker compose up --build --detach
	@echo "==> Waiting for backend to be healthy..."
	@for i in $$(seq 1 30); do \
	  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then \
	    echo "    Backend is ready."; \
	    break; \
	  fi; \
	  if [ $$i -eq 30 ]; then \
	    echo "    ERROR: Backend did not become healthy after 30 attempts."; \
	    echo "    Check logs with: docker compose logs backend"; \
	    exit 1; \
	  fi; \
	  echo "    Waiting... ($$i/30)"; \
	  sleep 2; \
	done
	@echo "==> Loading scenario-001 into the backend..."
	@RESULT=$$(curl -sf -X POST http://localhost:8000/api/scenarios/001/load); \
	if [ -z "$$RESULT" ]; then \
	  echo "    ERROR: Failed to load scenario. Check: docker compose logs backend"; \
	  exit 1; \
	fi; \
	PIPELINE_ID=$$(echo "$$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['pipeline_id'])"); \
	echo ""; \
	echo "==> Scenario loaded! Pipeline ID: $$PIPELINE_ID"; \
	echo ""; \
	echo "    Open your browser at:"; \
	echo "    http://localhost:5173"; \
	echo ""; \
	echo "    The frontend will show the investigation story automatically."; \
	echo "    The SSE stream drives the visual story to the final RecoveryReport."; \
	echo ""

# Remove all containers and the local SQLite data directory
clean:
	docker compose down --volumes --remove-orphans
	rm -rf data/

# Drop into a shell inside the running backend container
backend-shell:
	docker compose exec backend bash

# Drop into a shell inside the running frontend container
frontend-shell:
	docker compose exec frontend sh
