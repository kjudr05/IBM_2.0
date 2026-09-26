.PHONY: dev test load-demo clean backend-shell frontend-shell

# Start backend + frontend via Docker Compose (rebuilds images)
dev:
	docker compose up --build

# Run backend (pytest) and frontend (vitest) tests
test:
	docker compose run --rm backend pytest tests/ -v
	docker compose run --rm frontend npx vitest run

# Load sample scenario-001 into the running backend
load-demo:
	curl -s -X POST http://localhost:8000/api/scenarios/001/load | python3 -m json.tool

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
