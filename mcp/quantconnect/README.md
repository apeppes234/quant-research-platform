# mcp/quantconnect — self-hosted QuantConnect MCP (official image + auth proxy)

**We do NOT build a QC MCP — we self-host QC's official one** (`quantconnect/mcp-server` on Docker Hub) in
`streamable-http` mode, behind an auth proxy. Verified from QC's source (docs/04): the server reads
`MCP_TRANSPORT` (defaults stdio, supports `streamable-http`) and authenticates to QC via env vars
`QUANTCONNECT_USER_ID` + `QUANTCONNECT_API_TOKEN`. It exposes **no inbound auth of its own**, hence the proxy.

## Topology (docs/12)

```
[hosted agent] --https--> [proxy: nginx checks QC_MCP_INBOUND_BEARER]  (only this is published)
                            --localnet--> [quantconnect/mcp-server: MCP_TRANSPORT=streamable-http,
                                           QUANTCONNECT_USER_ID/API_TOKEN in env]
                                            --https--> quantconnect.com/api/v2
```

- QC creds live as container **env** (your secrets manager / `.env`), never in an Anthropic vault.
- The proxy bearer (`QC_MCP_INBOUND_BEARER`) goes in an Anthropic **vault** (`static_bearer`, keyed to the
  public QC MCP URL). The orchestrator attaches the vault to each session.

## Tool allowlist (docs/04)

Enable via `mcp_toolset` allowlist (`default_config:{enabled:false}` + per-tool `enabled:true`):
project / files / compile / backtests / object_store / lean_versions / ai (and read-only optimizations
with `create_optimization` **gated `always_ask`**).

**Never enable** the live-trading tools: `create_live_algorithm`, `stop/liquidate_live_algorithm`, the
read-live tools, `authorize_connection`, `create_live_command`, `broadcast_live_command`. This is the
structural "no live trading" guarantee.

## Files

```
docker-compose.qc.yml        # standalone compose for just the QC MCP + proxy (also folded into root compose)
proxy/nginx.conf.example     # inbound bearer check + reverse proxy to the QC MCP container
```

To build QC's image from source instead of Docker Hub: clone `github.com/QuantConnect/mcp-server` and
`docker build -t quantconnect/mcp-server .`.
