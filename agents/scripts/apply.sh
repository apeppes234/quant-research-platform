#!/usr/bin/env bash
# ============================================================================
# Control-plane sync: create/update the environment + all agents via the `ant`
# CLI, then write the captured IDs into .env. Idempotent-ish: first run creates,
# later runs should `update --version N` (see TODO). Run via `make agents-apply`.
#
# STATUS: scaffold. The create-vs-update logic and ${VAR} substitution are
# sketched, not battle-tested. See docs/02 (ant CLI) + docs/03 (topology).
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."          # -> agents/
DRY_RUN="${1:-}"

# `ant` resolves ANTHROPIC_API_KEY from the environment (load .env first).
[ -f ../.env ] && set -a && . ../.env && set +a

apply() {  # apply <yaml-after-substitution> -> prints created/updated agent id
  if [ "$DRY_RUN" = "--dry-run" ]; then ant beta:agents create --debug < /dev/stdin >/dev/null 2>&1 || true; cat >/dev/null; echo "DRYRUN"; return; fi
  ant beta:agents create --transform id -r < /dev/stdin
}

subst() { envsubst < "$1"; }     # expand ${VARS} in a yaml file

# 1) Environment ----------------------------------------------------------------
# MANAGED_ENVIRONMENT_ID=$(ant beta:environments create --transform id -r < environments/cloud.environment.yaml)

# 2) Specialists (capture each ID) ---------------------------------------------
# PAPER_AGENT_ID=$(subst specialists/paper.agent.yaml      | apply)
# MARKET_AGENT_ID=$(subst specialists/market.agent.yaml    | apply)
# DATA_AGENT_ID=$(subst specialists/data.agent.yaml        | apply)
# FEATURE_AGENT_ID=$(subst specialists/feature.agent.yaml  | apply)
# MODELING_AGENT_ID=$(subst specialists/modeling.agent.yaml| apply)
# BACKTEST_AGENT_ID=$(subst specialists/backtest.agent.yaml| apply)
# RISK_AGENT_ID=$(subst specialists/risk-auditor.agent.yaml| apply)
# REPORT_AGENT_ID=$(subst specialists/report.agent.yaml    | apply)
# export PAPER_AGENT_ID MARKET_AGENT_ID DATA_AGENT_ID FEATURE_AGENT_ID \
#        MODELING_AGENT_ID BACKTEST_AGENT_ID RISK_AGENT_ID REPORT_AGENT_ID

# 3) Manager (roster references the specialist IDs above) -----------------------
# RESEARCH_MANAGER_AGENT_ID=$(subst research-manager.agent.yaml | apply)

# 4) Persist IDs into .env (orchestrator reads them) ----------------------------
# {
#   echo "RESEARCH_MANAGER_AGENT_ID=$RESEARCH_MANAGER_AGENT_ID"
#   echo "MANAGED_ENVIRONMENT_ID=$MANAGED_ENVIRONMENT_ID"
#   # ...specialist ids...
# } >> ../.env

echo "TODO: implement create-vs-update (ant beta:agents update --agent-id ID --version N) and ID capture."
echo "See docs/02 'SDK / CLI quick reference' and agents/README.md 'Apply order'."
