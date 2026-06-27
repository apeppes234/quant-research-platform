# 02 — Managed Agents platform (VERIFIED)

Everything here was verified against Anthropic's current Managed Agents product contract. Treat it as the
source of truth for what the platform can do. **Do not assume behavior not listed here — look it up.**

## Mandatory flow: Agent (once) → Session (every run)

- `POST /v1/agents` creates a **persisted, versioned** agent. `model`, `system`, `tools`, `mcp_servers`,
  `skills`, `multiagent` all live **on the agent**, never on the session.
- `POST /v1/sessions` references a pre-created agent by ID (`agent="agent_..."` for latest, or
  `{type:"agent", id, version}` to pin) + an `environment_id`.
- Beta header `managed-agents-2026-04-01` (the SDK + `ant` set it automatically).

**Control plane = `ant` CLI + YAML; data plane = SDK.** See [`agents/`](../agents/) for the YAML and
[`orchestrator/`](../orchestrator/) for the SDK usage.

## Environments

A reusable template for the per-session container. Key field is `networking`:

- `unrestricted` — full egress (except a legal blocklist).
- `limited` — deny-by-default; opt in via `allowed_hosts`, `allow_package_managers`, `allow_mcp_servers`.

**For this project use `limited`** with `allow_mcp_servers: true` (or list each MCP domain in
`allowed_hosts`). Otherwise the container can't reach our MCP servers and tools fail silently. See
[`agents/environments/cloud.environment.yaml`](../agents/environments/cloud.environment.yaml) and docs/12.

## The SSE event stream (this is what the UI renders)

Receive via `GET /v1/sessions/{id}/events/stream` (SSE) or `GET .../events` (paginated poll). Every event
carries `id`, `type`, `processed_at`. **The stream has no replay** — see the reconnect pattern in docs/10.

Event types we rely on (grouped):

| Event | Carries | Used for |
|---|---|---|
| `session.status_running` / `_idle` / `_rescheduling` / `_terminated` | `_idle` carries `stop_reason` | session-level node status; the **idle-break gate** (docs/10) |
| `session.thread_created` | `session_thread_id`, `agent_name` | **add an agent node to the canvas** |
| `session.thread_status_running` / `_idle` / `_terminated` | `_idle` carries `stop_reason` | **node pulses "working" / settles "idle"** |
| `agent.thread_message_sent` / `_received` | `to_/from_session_thread_id`, `content` | **animate delegation / result edges** |
| `agent.message` | text blocks | agent output (inspector) |
| `agent.thinking` | thinking blocks | "thinking…" shimmer (inspector) |
| `agent.tool_use` / `agent.tool_result` | tool name/input | node badge ("compiling on QC", "searching papers") |
| `agent.mcp_tool_use` / `agent.mcp_tool_result` | MCP tool name/input | node badge for MCP calls |
| `agent.custom_tool_use` | name, input, `id` | host-side custom tool → orchestrator must reply `user.custom_tool_result` |
| `span.model_request_start` / `_end` | `_end` carries `model_usage` (input/output/cache tokens) | **token/cost meter** |
| `span.outcome_evaluation_start` / `_ongoing` / `_end` | `_end` carries `iteration`, `result`, `explanation`, `usage` | **iteration panel: criteria ✓/✗, iteration counter** |
| `agent.thread_context_compacted` | — | context was summarized (info) |

The stream also **echoes back** user-sent events (`user.message`, `user.interrupt`,
`user.tool_confirmation`, `user.custom_tool_result`, `user.define_outcome`), each with `processed_at`
(`null` = queued, timestamp = processed). Use this to drive optimistic/pending UI.

## `user.define_outcome` — the iteration engine

Not a field on `sessions.create()`. You create a normal session, then **send a `user.define_outcome`
event** (no separate `user.message` — the agent starts on receipt).

```json
{
  "type": "user.define_outcome",
  "description": "<the task>",
  "rubric": { "type": "text", "content": "<markdown rubric>" },   // or {type:"file", file_id}
  "max_iterations": 5
}
```

- A separate **grader** (independent context window) scores each iteration against the rubric and feeds
  per-criterion gaps back to the agent.
- `max_iterations` default **3**, max **20**.
- `span.outcome_evaluation_end.result` ∈ `satisfied` | `needs_revision` | `max_iterations_reached` |
  `failed` | `interrupted`. Only `satisfied`/`max_iterations_reached`/`failed` are terminal.
- Rubric must be **explicit, independently gradeable** criteria (not vibes). Our rubric is in docs/07.

## Multiagent: coordinator delegates ONE level only

- `multiagent` is a **top-level field on the agent** (not a `tools[]` entry, not on the session):
  `{type:"coordinator", agents:[<roster>]}`.
- Roster entries: bare `"agent_id"` (latest), `{type:"agent", id, version}`, or `{type:"self"}`.
- **Depth > 1 is ignored.** A subagent's own roster does not cascade. ⟹ our topology must be flat: the
  Research Manager is the only coordinator; the 8 specialists are leaves. Pipeline order is driven by the
  Manager's instructions + the file bus (docs/03).
- Limits: roster ≤ 20; ≤ 25 concurrent threads; threads share the container filesystem but **not**
  conversation history or tools.
- Per-subagent streams: `GET /v1/sessions/{sid}/threads/{tid}/stream` (the agent inspector drills in here).

## Memory stores (persistent across sessions)

- Workspace-scoped collections of small text files (`mem_...`), FUSE-mounted into the container at
  `/mnt/memory/<store-name>/`. The agent reads/writes them with ordinary file tools.
- Attach via `resources:[{type:"memory_store", memory_store_id, access:"read_write"|"read_only",
  instructions:"..."}]` at **session-create time only**. Max 8 per session.
- Every mutation creates an immutable **version** (`memver_...`) — audit + rollback + `redact`.
- **We use two memory stores:** a **lessons library** (what worked / didn't, with why) and the
  **data-snooping ledger** (variants tried, deflated-Sharpe inputs). See docs/07 and docs/08.

## Tools on an agent (three kinds)

1. **Prebuilt toolset** `agent_toolset_20260401` — `bash`, `read`, `write`, `edit`, `glob`, `grep`,
   `web_fetch`, `web_search`. Enable all, disable per-tool via `configs`.
2. **MCP toolset** `mcp_toolset` — references a server declared in the agent's `mcp_servers`. Allowlist
   pattern: `default_config:{enabled:false}` + `configs:[{name:<tool>, enabled:true}]`. **This is how we
   allowlist OUT QuantConnect's live-trading tools** (docs/04).
3. **Custom (client-side) tools** — agent emits `agent.custom_tool_use`, session goes idle, your
   orchestrator executes and replies `user.custom_tool_result`. (We don't need these for QC since QC's MCP
   works over HTTP — see docs/04 — but the pattern exists if a secret must stay host-side.)

## MCP servers + vaults (CRITICAL transport rule)

- Agents declare MCP servers as `{type:"url", name, url}` over **Streamable HTTP** — **no stdio**. Hosted
  Managed Agents can only reach **URL-reachable** MCP servers. ⟹ everything we self-host
  (`search_knowledge`, QuantConnect, FRED/EDGAR/GDELT/arXiv) must be exposed at a **public HTTPS URL**.
- **No auth in the agent definition.** MCP credentials live in **vaults** (`client.beta.vaults`), attached
  to a session via `vault_ids`. Anthropic injects the credential to the server URL at egress; auto-refreshes
  OAuth. Vault credential kinds: `mcp_oauth`, `static_bearer` (by URL), `environment_variable` (by name,
  substituted at egress for non-MCP/CLI calls). See docs/12.

## Permission policies / steering

- Per-tool `permission_policy`: `always_allow` (default) or `always_ask`. On `always_ask` the session goes
  idle; reply with `user.tool_confirmation` (`tool_use_id` = the event `id`, `result:"allow"|"deny"`).
  **We gate `create_optimization`** (data-snooping risk) with `always_ask` (docs/08).
- `user.interrupt` jumps the queue and forces idle ("stop/redirect").

## Files (the artifact bridge)

- **In:** upload via Files API, attach as `resources:[{type:"file", file_id, mount_path}]` (read-only).
- **Out:** the agent writes to `/mnt/session/outputs/`; list with `files.list({scope_id: session.id,
  betas:["managed-agents-2026-04-01"]})`, download with `files.download(id)`. (~1–3s indexing lag.)

## SDK / CLI quick reference

- Python SDK: `client.beta.{agents,sessions,environments,vaults,memory_stores,files}.*`. Stream:
  `client.beta.sessions.events.stream(session_id=...)`; send: `client.beta.sessions.events.send(...)`.
- `ant` CLI (control plane): `ant beta:agents create < x.agent.yaml`, `ant beta:agents update --agent-id
  ID --version N < x.agent.yaml`, `ant beta:environments create < env.yaml`.
