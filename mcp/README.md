# mcp/ — Self-hosted MCP servers (tools the agents call)

Every MCP server here is exposed to hosted Managed Agents as a **`{type:url}` Streamable HTTP** server at
a **public HTTPS URL**, with inbound auth enforced by a proxy and the bearer stored in an Anthropic vault
(docs/02, docs/12). **No stdio** — hosted agents can't reach it.

| Dir | Server | Build vs reuse |
|---|---|---|
| [`knowledge/`](knowledge/) | `search_knowledge` over the vector DB (docs/06) | **Build** (FastMCP; mirror QuantDinger's MCP-over-REST thinness) |
| [`quantconnect/`](quantconnect/) | QuantConnect | **Reuse** QC's official image `quantconnect/mcp-server` in `streamable-http` mode, behind an auth proxy (docs/04) |
| [`data-sources/`](data-sources/) | FRED / EDGAR / GDELT / arXiv (docs/05) | **Build** thin FastMCP wrappers over each upstream API |

## Common pattern for the ones we build

```
src/server.py  — FastMCP('<name>', instructions, host="0.0.0.0"); register tools; mcp.run(transport=os.getenv("MCP_TRANSPORT","stdio"))
```

Run with `MCP_TRANSPORT=streamable-http`. Keep them thin (validate inputs, call upstream, return typed
results); no business logic. Redact secrets from outputs. Each gets a Dockerfile + a slot in
`docker-compose.yml` + an entry in `.env` (`MCP_*_URL`) + a vault credential (docs/12).

## Auth model (all of them)

The MCP server itself need not implement inbound auth; put an nginx (or similar) proxy in front that
requires a bearer, and store that bearer in an Anthropic vault keyed to the public URL. QC specifically
authenticates to QC via its own env creds and has no inbound auth — see [`quantconnect/`](quantconnect/).
