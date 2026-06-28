# agents/ — Control plane (version-controlled agent + environment definitions)

These YAML files **are** the agents. They're applied to Anthropic via the `ant` CLI (`make agents-apply`),
which creates/updates each agent and prints its ID. **Create once, reference by ID** — the orchestrator
never calls `agents.create()` in the request path (docs/01, docs/02).

## Files

```
research-manager.agent.yaml      # the sole coordinator (chat + delegation + define_outcome)
specialists/
  paper.agent.yaml               # papers -> hypotheses        (idea-only tier)
  market.agent.yaml              # idea-gen / current context  (idea-only tier)
  data.agent.yaml                # PIT data pulls              (PIT-safe tier)
  feature.agent.yaml             # feature building (QuantBook) (PIT-safe tier)
  modeling.agent.yaml            # authors algo.py to contract  (PIT-safe tier)
  backtest.agent.yaml            # compile + backtest on QC     (PIT-safe tier)
  risk-auditor.agent.yaml        # fresh-context bias audit + snooping ledger writes
  report.agent.yaml              # final PDF/DOCX report
environments/
  cloud.environment.yaml         # limited networking + allow_mcp_servers
scripts/
  apply.sh                       # create specialists -> capture IDs -> create/update Manager w/ roster
```

## Apply order (handled by `scripts/apply.sh`)

1. Create/update the environment → capture `MANAGED_ENVIRONMENT_ID`.
2. Create/update each specialist → capture each `*_AGENT_ID`.
3. Substitute the specialist IDs into the Manager's `multiagent.agents` roster → create/update the Manager
   → capture `RESEARCH_MANAGER_AGENT_ID`.
4. Write the captured IDs into `.env` (the orchestrator reads them).

## Conventions

- `${VAR}` placeholders are filled by `apply.sh` from `.env` / captured IDs. The raw YAML is **not** valid
  to apply as-is until those are substituted.
- MCP servers are declared `{type:url, name, url}` with **no auth** (auth = vaults, attached per session by
  the orchestrator — docs/12).
- The `mcp_toolset` allowlist pattern (`default_config:{enabled:false}` + per-tool `enabled:true`) is how
  we keep QC's live-trading tools off (docs/04).
- Models per docs/03. Run Modeling at `effort: high`/`xhigh`.

See docs/03 (topology) and docs/02 (platform contract).
