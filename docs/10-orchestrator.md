# 10 — Orchestrator

The orchestrator ([`orchestrator/`](../orchestrator/), Python / FastAPI) is the **data plane**: it owns
session lifecycle, consumes the Managed Agents SSE stream, and relays normalized events to the browser over
websockets. **This is the part to get right** — it's what keeps the canvas accurate and crash-proof.

## Responsibilities

1. **Session lifecycle** (`app/sessions/`): create sessions referencing the pre-built Research Manager
   agent ID + environment ID; attach `vault_ids` + memory-store `resources`; send `user.message`,
   `user.define_outcome`, `user.interrupt`, `user.tool_confirmation`, `user.custom_tool_result`.
2. **Event ingestion** (`app/events/sse_consumer.py`): consume `sessions.events.stream`, apply the
   reconnect-with-consolidation pattern, normalize via `schema.py`, and obey the idle-break gate.
3. **Relay** (`app/events/ws_relay.py` + `app/routes/stream.py`): push normalized events to the browser
   over a websocket, with per-event `id` so the client can dedupe.
4. **Steering** (`app/routes/steering.py`): accept interrupt/approve from the UI and translate to the
   corresponding `events.send(...)`.
5. **Session outputs** (`app/routes/sessions.py`): list/download `/mnt/session/outputs/*` through the
   Managed Agents Files API, including `results.json` and `report.pdf`.

## The three patterns that must be exactly right

### 1. Stream-first, then send

Open the SSE stream **before** sending the kickoff event, or you miss the first events (they arrive
buffered as one batch). For full history on (re)connect, also fetch `events.list`.

### 2. Reconnect with consolidation (SSE has no replay)

On every (re)connect: open the stream, fetch `events.list` history, **yield history first then live,
deduping by `event.id`**. The dedupe must gate only the *handler*, not the *terminal checks* — a terminal
event present in the history must still break the loop.

```python
seen = set()
stream = client.beta.sessions.events.stream(session_id=sid)   # open first
for ev in client.beta.sessions.events.list(session_id=sid).data:   # history
    seen.add(ev.id); handle(ev)
for ev in stream:                                              # live tail
    if ev.id not in seen:
        seen.add(ev.id); handle(ev)
    if ev.type == "session.status_terminated": break
    if ev.type == "session.status_idle" and ev.stop_reason.type != "requires_action": break
```

### 3. The idle-break gate (idle ≠ done)

Do **not** break on `session.status_idle` alone — the session idles transiently (between parallel tools,
awaiting a `user.tool_confirmation`, awaiting a `user.custom_tool_result`). Break only when:

- `session.status_terminated`, **or**
- `session.status_idle` with `stop_reason.type != "requires_action"` (i.e. `end_turn` / `retries_exhausted`).

`requires_action` means the agent is waiting on *you* — handle it (send the confirmation / tool result),
don't break.

## Normalization (`app/events/schema.py`)

Map raw Managed Agents events to the compact shape the frontend expects (the bindings table in docs/09).
Keep this map as the single source of truth for the wire format between orchestrator and UI. Example:

```python
# raw event.type            -> normalized {kind, payload} pushed over ws
"session.thread_created"     -> {"kind": "node.add",    "payload": {"threadId", "agentName"}}
"session.thread_status_idle" -> {"kind": "node.status", "payload": {"threadId", "status": "idle", "stopReason"}}
"agent.thread_message_sent"  -> {"kind": "edge.animate","payload": {"from", "to", "dir": "delegate"}}
"agent.mcp_tool_use"         -> {"kind": "node.badge",  "payload": {"threadId", "tool", "label"}}
"span.model_request_end"     -> {"kind": "cost.add",    "payload": {"threadId", "usage"}}
"span.outcome_evaluation_end"-> {"kind": "rubric",      "payload": {"iteration", "result", "explanation"}}
```

## Other gotchas (from the platform docs)

- **`processed_at`** distinguishes queued (`null`) vs processed — use for optimistic/pending chat UI.
- **Tool confirmation:** on `agent.tool_use` with `evaluated_permission == "ask"`, reply
  `user.tool_confirmation{tool_use_id: event.id, result}` — note `tool_use_id` is the **event id**, not a
  `toolu_` id. In multiagent, echo `session_thread_id` from the originating event.
- **Post-idle status race:** the stream emits idle slightly before the queryable status flips — poll
  `sessions.retrieve` before any `archive`/`delete`.
- **Custom tools:** if we ever declare a host-side custom tool, the orchestrator must catch
  `agent.custom_tool_use` and reply `user.custom_tool_result` over the same authenticated stream (the
  session deadlocks if the stream drops with a pending custom-tool call — so the reconnect pattern is
  load-bearing).

## Files

```
orchestrator/app/
  main.py                 # FastAPI app factory; mounts routes; starts ws relay
  config.py               # env (ANTHROPIC_API_KEY, agent/env IDs, vault ids)
  clients/anthropic_client.py   # thin wrapper around the beta SDK namespaces
  sessions/manager.py     # create/resume sessions; send user events; define_outcome
  sessions/lifecycle.py   # status polling, archive-safe teardown
  events/sse_consumer.py  # patterns 1–3 above
  events/ws_relay.py      # fan-out normalized events to connected browsers
  events/schema.py        # raw event -> normalized {kind,payload} map (sync w/ docs/09)
  routes/sessions.py      # POST /sessions, POST /sessions/{id}/message, /define_outcome
                          # GET /sessions/{id}/results, /report, /files, /files/{file_id}/download
  routes/stream.py        # WS /sessions/{id}/stream
  routes/steering.py      # POST /sessions/{id}/interrupt, /confirm
```
