# orchestrator/ — Data plane (FastAPI)

Owns session lifecycle, consumes the Managed Agents SSE stream, and relays normalized events to the
browser over websockets. **The reliability-critical component** — see [`docs/10-orchestrator.md`](../docs/10-orchestrator.md)
for the three patterns that must be exactly right (stream-first, reconnect-with-consolidation, idle-break
gate).

## Run

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000      # or: make orchestrator
```

Reads config from `../.env` (see `.env.example`): `ANTHROPIC_API_KEY`, `RESEARCH_MANAGER_AGENT_ID`,
`MANAGED_ENVIRONMENT_ID`, the `MCP_*_URL`s, vault/secret material.

## Layout

```
app/
  main.py                  # FastAPI app factory; mounts routes
  config.py                # pydantic-settings: env -> typed config
  clients/anthropic_client.py   # thin wrapper over client.beta.{agents,sessions,vaults,memory_stores,files}
  sessions/
    manager.py             # create/resume sessions; attach vaults + memory stores; send user events; define_outcome
    lifecycle.py           # status polling; archive-safe teardown (post-idle race, docs/10)
  events/
    sse_consumer.py        # consume Managed Agents SSE: stream-first, reconnect+consolidate, idle-break gate
    ws_relay.py            # fan-out normalized events to connected browsers
    schema.py              # raw event.type -> normalized {kind,payload} (KEEP IN SYNC with docs/09 table)
  routes/
    sessions.py            # POST /sessions ; POST /sessions/{id}/message ; POST /sessions/{id}/define_outcome
    stream.py              # WS  /sessions/{id}/stream
    steering.py            # POST /sessions/{id}/interrupt ; POST /sessions/{id}/confirm
tests/
```

## Contracts you must not break

- **Event normalization** (`events/schema.py`) is the wire format between orchestrator and frontend. It
  must match the bindings table in [`docs/09-visual-ui.md`](../docs/09-visual-ui.md).
- **Idle ≠ done.** Only break on `session.status_terminated` or `session.status_idle` with
  `stop_reason.type != "requires_action"`. (docs/10)
- **Create agents once.** Never call `agents.create()` here — load `RESEARCH_MANAGER_AGENT_ID` from env.
  The control plane (`agents/`) owns agent creation.

## SDK note

Uses the beta namespaces: `client.beta.agents/sessions/environments/vaults/memory_stores/files`. The SDK
sets the `managed-agents-2026-04-01` beta header automatically. See docs/02 for method names.
