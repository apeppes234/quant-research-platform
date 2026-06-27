# 04 — QuantConnect (VERIFIED from source)

Verified by reading the official repos `github.com/QuantConnect/{mcp-server, Research, Tutorials,
Documentation}`. This corrects an earlier assumption that QC's MCP was stdio-only.

## The MCP server (`QuantConnect/mcp-server`)

- **Python, built on `FastMCP`, dockerized** as `quantconnect/mcp-server` on Docker Hub. Thin client over
  the QC v2 REST API (`https://www.quantconnect.com/api/v2`).
- **Transport:** `transport = os.getenv('MCP_TRANSPORT', 'stdio')`, and `FastMCP(..., host="0.0.0.0")`.
  Defaults to **stdio** (that's the only path the README documents, for Claude Desktop), **but it natively
  supports `streamable-http` and `sse`.** ⟹ We run the official image with `MCP_TRANSPORT=streamable-http`
  and expose it as a **URL MCP** to hosted Managed Agents. No custom bridge needed.
- **Auth:** env vars `QUANTCONNECT_USER_ID` + `QUANTCONNECT_API_TOKEN`. On each call it builds a timestamped
  `Authorization: Basic b64(userId : sha256(token:timestamp))` header. **Auth is per-process (env), NOT
  per-MCP-request, and the MCP endpoint itself exposes NO inbound auth.**

### Consequence for our deployment (important)

Because the QC MCP has no inbound auth and authenticates to QC with its own env creds:

1. QC creds (`QUANTCONNECT_USER_ID`/`QUANTCONNECT_API_TOKEN`) live as **container env on your host** (your
   secrets manager / `.env`), **not** in an Anthropic vault.
2. You must put **your own inbound auth** in front of the endpoint — an auth proxy that requires a bearer
   (see [`mcp/quantconnect/proxy/nginx.conf.example`](../mcp/quantconnect/proxy/nginx.conf.example)) and/or
   `limited` networking `allowed_hosts`.
3. **That proxy bearer** (`QC_MCP_INBOUND_BEARER`) is what you store in an **Anthropic vault** as a
   `static_bearer` credential keyed to the public URL. See docs/12.

## Tool surface (by `src/tools/` module)

Allowlist these **IN** via `mcp_toolset` (`default_config:{enabled:false}` + per-tool `enabled:true`):

| Module | Tools |
|---|---|
| project | `create_project`, `read_project`, `list_projects`, `update_project`, `delete_project` |
| files | `create_file`, `read_file`, `update_file_contents`, `patch_file`, `update_file_name`, `delete_file` |
| compile | `create_compile`, `read_compile` |
| backtests | `create_backtest`, `read_backtest`, `list_backtests`, `read_backtest_chart`, `read_backtest_orders`, `read_backtest_insights`, `update_backtest`, `delete_backtest` |
| optimizations | `estimate_optimization_time`, `create_optimization`, `read_optimization`, `list_optimizations`, `update_optimization`, `abort_optimization`, `delete_optimization` — **`create_optimization` is GATED `always_ask`** (data-snooping; log to ledger, docs/08) |
| object_store | `upload_object`, `read_object_properties`, `read_object_store_file_*`, `list_object_store_files`, `delete_object` |
| lean_versions | (read LEAN engine versions) |
| ai | `check_initialization_errors`, `complete_code`, `enhance_error_message`, `update_code_to_pep8`, `check_syntax`, `search_quantconnect` |
| account / project_collaboration / project_nodes / mcp_server_version | as needed |

**Allowlist these OUT (never enable):**

| Module | Tools (live trading — forbidden) |
|---|---|
| live (`register_live_trading_tools`) | `authorize_connection`, `create_live_algorithm`, `read_live_algorithm`, `list_live_algorithms`, `read_live_chart`, `read_live_logs`, `read_live_portfolio`, `read_live_orders`, `read_live_insights`, `stop_live_algorithm`, `liquidate_live_algorithm` |
| live_commands (`register_live_trading_command_tools`) | `create_live_command`, `broadcast_live_command` |

This is the structural enforcement of "no live trading." Combined with `limited` networking, the agent
literally cannot deploy a live algo.

## The programming model (how a QC algorithm is written)

A QC algorithm is a **project of code files** (Python or C#) subclassing the framework:

- `initialize(self)` — set `self.set_start_date / set_end_date / set_cash`, define the universe + data
  subscriptions (`self.add_equity(...)`), instantiate indicators.
- `on_data(self, data)` — the event-driven loop; place/adjust orders here.

**MCP workflow** (the Modeling + Backtest agents follow this):

```
create_project  →  create_file / update_file_contents / patch_file (write algorithm.py)
                →  create_compile + read_compile  (FIX ALL COMPILE WARNINGS — per QC's own instructions)
                →  create_backtest
                →  read_backtest / read_backtest_chart / read_backtest_orders / read_backtest_insights
```

QC's server `instructions.md` rules to bake into our contract/prompts:
- Create projects via `create_project` (don't write project files locally).
- Python = PEP8 (snake_case); use `update_code_to_pep8` if needed.
- **Never overwrite indicator method names** — use `self._rsi = self.rsi(self._symbol, 14)`, not `self.rsi
  = ...`. Always choose variable names different from the methods called.
- Compile and fix warnings **before** backtesting.
- Prefer `patch_file` for small edits over rewriting the whole file.

## Research / grounding corpora (in the QC repos)

- `Research/Analysis/*.ipynb` — **QuantBook** PIT research notebooks: Kalman pairs trading, cointegration
  pairs, mean-variance optimization, fundamental factor analysis, EMA/VXX cross. QuantBook is the PIT-safe
  research API the **Feature/Data agents** drive (via QC's Jupyter/research tools).
- `Tutorials/04 Strategy Library` — **1000+ named, documented strategies** (CAPM ranking, dynamic
  breakout, dual thrust, pairs/cointegration, fundamental factor, sentiment, Ichimoku, …). Ingest as a
  grounding corpus alongside `letianzj/QuantResearch` (docs/06).

## Why PIT-safe matters here

QC provides survivorship-bias-free, point-in-time price + fundamental data, and a timestamped Dataset
Market (news/sentiment). This is the backbone of the anti-look-ahead guarantee (docs/08): the backtest
engine itself won't let you join future data, so the bias surface shrinks to *how we split train/holdout*
and *how many variants we try* — which the contract + ledger handle.
