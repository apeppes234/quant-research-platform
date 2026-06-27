# Documentation index

Read in order if you're new (or an LLM without prior context). Each doc is self-contained.

| # | Doc | What it covers |
|---|---|---|
| 00 | [Overview](00-overview.md) | The vision and the one guiding principle (constrain → validate → run) |
| 01 | [Architecture](01-architecture.md) | The whole system on one page; control vs data plane; what runs where |
| 02 | [Managed Agents platform](02-managed-agents-platform.md) | **Verified** Anthropic Managed Agents primitives: agents/sessions/environments, the SSE event stream schema, `define_outcome`, one-level delegation, memory stores, vaults, MCP transport rules |
| 03 | [Agent topology](03-agent-topology.md) | The Research Manager + 8 specialists: models, tools, roster, file-bus pipeline order |
| 04 | [QuantConnect](04-quantconnect.md) | **Verified** from QC source: MCP transport/auth/tool surface, the live-trading allowlist-out, the programming + research model |
| 05 | [Data layer & trust tiers](05-data-trust-tiers.md) | PIT-safe (backtest path) vs idea-only (walled off); sources; which agent gets which |
| 06 | [Knowledge layer](06-knowledge-layer.md) | `search_knowledge` MCP over a vector DB; corpora; ingestion |
| 07 | [Iteration & rubric](07-iteration-rubric.md) | The `define_outcome` loop; the exact pass/fail gates |
| 08 | [Anti-bias guardrails](08-antibias-guardrails.md) | The look-ahead / data-snooping pillar (engine + protocol + agent + process) |
| 09 | [Visual UI](09-visual-ui.md) | The 7 canvas views and the exact event→visual bindings |
| 10 | [Orchestrator](10-orchestrator.md) | FastAPI SSE→websocket relay; reconnect-with-consolidation; the idle-break gate; steering |
| 11 | [Authoring contract](11-authoring-contract.md) | The "expertise" layer: contract + validator + library |
| 12 | [Credentials & networking](12-credentials-networking.md) | Vaults, `limited` networking, self-hosting MCPs at public HTTPS |
| 13 | [Build phases](13-build-phases.md) | The 5-phase build order, with concrete done-criteria |
| 14 | [Decisions](14-decisions.md) | ADR-style log: what's decided + why, and what's still open |

## Provenance of the "verified" claims

Docs 02 and 04 are marked **verified** because they were written after reading primary sources, not from
memory:

- **Managed Agents** — the Anthropic `claude-api` skill's `shared/managed-agents-*.md` reference set
  (the current product contract).
- **QuantConnect** — direct reading of the official repos `github.com/QuantConnect/{mcp-server, Research,
  Tutorials, Documentation}`.

If you extend these, re-verify against the same primary sources rather than trusting older notes.
