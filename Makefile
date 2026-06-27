# ============================================================================
# Quant Research Platform — common commands
# This is a convenience wrapper. Each target is a stub until the corresponding
# component is implemented (see docs/13-build-phases.md).
# ============================================================================

.PHONY: help agents-apply agents-diff up down logs orchestrator frontend \
        mcp-knowledge ingest test fmt

help:                ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ---- Control plane (Anthropic Managed Agents, via the `ant` CLI) ------------
agents-apply:        ## Create/update all agents + environment from agents/*.yaml (see agents/scripts/apply.sh)
	bash agents/scripts/apply.sh

agents-diff:         ## Show what `agents-apply` would change (dry run)
	bash agents/scripts/apply.sh --dry-run

# ---- Data plane (your Docker services) --------------------------------------
up:                  ## Start all local services (postgres, vector DB, MCPs, orchestrator, frontend)
	docker compose up -d --build

down:                ## Stop all local services
	docker compose down

logs:                ## Tail logs from all services
	docker compose logs -f

orchestrator:        ## Run the orchestrator (FastAPI) locally without Docker
	cd orchestrator && uv run uvicorn app.main:app --reload --port $${ORCHESTRATOR_PORT:-8000}

frontend:            ## Run the frontend dev server locally without Docker
	cd frontend && npm run dev

mcp-knowledge:       ## Run the search_knowledge MCP locally (streamable-http)
	cd mcp/knowledge && MCP_TRANSPORT=streamable-http uv run src/server.py

# ---- Knowledge ingestion -----------------------------------------------------
ingest:              ## Run all ingestion jobs (SSRN, arXiv, QuantResearch repo, QC Strategy Library)
	cd knowledge && uv run python -m ingestion.run_all

# ---- Quality ----------------------------------------------------------------
test:                ## Run all tests
	cd orchestrator && uv run pytest -q || true
	cd frontend && npm test || true

fmt:                 ## Format everything
	cd orchestrator && uv run ruff format . || true
	cd frontend && npm run format || true
