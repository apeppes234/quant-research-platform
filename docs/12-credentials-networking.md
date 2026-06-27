# 12 — Credentials & networking

## The rule that shapes everything

Hosted Managed Agents can only reach MCP servers at **public HTTPS URLs** (Streamable HTTP), and MCP
credentials are injected from **vaults** at egress — **never put secrets in prompts or agent definitions**
(they'd persist in the session event history). See docs/02.

## Where each secret lives

| Secret | Where it lives | Why |
|---|---|---|
| `ANTHROPIC_API_KEY` | orchestrator env + `ant` CLI env (`.env`) | data-plane SDK + control-plane CLI |
| `QUANTCONNECT_USER_ID` / `_API_TOKEN` | **env on the self-hosted QC MCP container** | QC MCP authenticates to QC per-process with these (docs/04); they never go to a vault |
| `QC_MCP_INBOUND_BEARER` | env on the QC auth proxy **+ an Anthropic vault** (`static_bearer`, keyed to the QC MCP URL) | the QC MCP has no inbound auth; the proxy enforces a bearer; the agent presents it via the vault |
| `FRED_API_KEY`, `SEC_EDGAR_USER_AGENT` | env on the respective MCP wrapper containers | the wrappers call the upstream APIs |
| MCP inbound bearers for `search_knowledge` / FRED / EDGAR / GDELT / arXiv | proxy env **+ Anthropic vault** (one `static_bearer` per URL) | same pattern as QC: protect each self-hosted endpoint |

## Vault setup (per session, via the SDK)

```python
vault = client.beta.vaults.create(name="quant-research")
client.beta.vaults.credentials.create(vault.id, auth={
    "type": "static_bearer",
    "mcp_server_url": MCP_QUANTCONNECT_URL,   # matched by URL
    "token": QC_MCP_INBOUND_BEARER,
})
# ...one credential per MCP URL...
session = client.beta.sessions.create(agent=AGENT_ID, environment_id=ENV_ID, vault_ids=[vault.id])
```

Anthropic matches each credential to the MCP server by URL and adds it to the outbound request at egress.
For OAuth-based MCPs use `mcp_oauth` (auto-refreshed); for env-var-style secrets to non-MCP CLIs use
`environment_variable` (substituted at egress, sandbox sees a placeholder).

## Networking (the environment)

Use a `limited` environment and allow exactly what's needed:

```yaml
config:
  type: cloud
  networking:
    type: limited
    allow_mcp_servers: true          # lets the container reach the agent's configured MCP URLs
    allow_package_managers: false    # flip true only if a tool needs pip/npm at runtime
    allowed_hosts: []                # add non-MCP hosts here if ever needed
```

If `allow_mcp_servers` is false **and** the MCP domains aren't in `allowed_hosts`, the container can't
reach the MCP servers and **tools fail silently** — the single most common setup mistake.

## Self-hosting MCPs at public HTTPS (local dev)

Hosted agents can't reach `localhost`. For local dev, expose each MCP through a tunnel (cloudflared / ngrok)
and put the public URL in `.env` (`MCP_*_URL`). The auth proxy in front of each MCP enforces the inbound
bearer so the public URL isn't open. For production, run the MCPs behind a real TLS terminator (the proxy)
in your VPC and restrict by the vault bearer + (optionally) IP allowlist.

## The QC MCP topology (concrete)

```
[hosted agent] --https--> [QC auth proxy : nginx, checks QC_MCP_INBOUND_BEARER]
                              --localnet--> [quantconnect/mcp-server : MCP_TRANSPORT=streamable-http,
                                             QUANTCONNECT_USER_ID/API_TOKEN in env]
                                              --https--> quantconnect.com/api/v2
```

Only the proxy is published; the QC MCP container is internal. See
[`mcp/quantconnect/`](../mcp/quantconnect/) and `docker-compose.yml`.
