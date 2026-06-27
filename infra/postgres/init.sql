-- Postgres init (mounted by docker-compose). docs/01.
-- 1) orchestrator state (sessions/runs metadata) — expand as the orchestrator is built.
-- 2) if VECTORDB_KIND=pgvector, also create the knowledge schema (see knowledge/schema/vectordb_schema.sql;
--    duplicated here only if you want a single init entrypoint — otherwise apply that file separately).

CREATE TABLE IF NOT EXISTS runs (
    session_id   TEXT PRIMARY KEY,
    title        TEXT,
    created_at   TIMESTAMPTZ DEFAULT now(),
    status       TEXT,
    outcome      TEXT          -- satisfied | needs_revision | max_iterations_reached | failed | null
);

-- Snooping ledger is a Managed Agents MEMORY STORE (docs/08), not a table here. A read-only mirror for the
-- BiasLedger UI could live here if you prefer SQL over reading the memory store — decide at Phase 4.
