# infra/ — local infrastructure

Supporting infra for the data plane. The agent loop/containers run on Anthropic (not here) — see
docs/01 "What runs where".

| Path | What |
|---|---|
| `postgres/init.sql` | DB init: orchestrator state tables + (if `VECTORDB_KIND=pgvector`) the `knowledge_chunks` table from `knowledge/schema/vectordb_schema.sql`. |
| `env/.env.example` | Pointer to the root `.env.example` (the single source of env truth). |

Services themselves are defined in the root `docker-compose.yml`. Networking note (docs/12): hosted agents
need **public HTTPS** to reach our MCP servers — for local dev, tunnel them (cloudflared/ngrok) and put the
public URL in `.env`.
