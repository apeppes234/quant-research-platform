#!/usr/bin/env bash
# ============================================================================
# Phase 5 control-plane sync: create the cloud environment, create/reuse all
# eight specialists, then create/reuse the Research Manager with its full
# multiagent coordinator roster filled in.
#
# The ant CLI supports versioned agents. To keep this script deterministic even
# before we track versions, it stores a rendered-YAML SHA next to each ID. If a
# rendered YAML changes, it creates a replacement and updates .env.
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AGENTS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$AGENTS_DIR/.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"
DRY_RUN="${1:-}"

cd "$REPO_ROOT"

if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

usage() {
  cat <<'EOF'
Usage:
  bash agents/scripts/apply.sh [--dry-run]

Environment:
  ANTHROPIC_API_KEY       required by ant for real applies
  MCP_KNOWLEDGE_URL       public HTTPS URL for the search_knowledge MCP
  MCP_QUANTCONNECT_URL    public HTTPS URL for the QC MCP auth proxy
  MCP_FRED_URL            public HTTPS URL for the FRED/ALFRED MCP auth proxy
  MCP_EDGAR_URL           public HTTPS URL for the EDGAR MCP auth proxy
  MCP_GDELT_URL           public HTTPS URL for the GDELT MCP auth proxy
  MCP_ARXIV_URL           public HTTPS URL for the arXiv MCP auth proxy

Outputs:
  MANAGED_ENVIRONMENT_ID, all specialist *_AGENT_ID values, and
  RESEARCH_MANAGER_AGENT_ID are written to .env.
EOF
}

require_var() {
  local name="$1"
  local value="${!name:-}"
  if [ -z "$value" ]; then
    echo "Missing required env var: $name" >&2
    exit 2
  fi
}

render_yaml() {
  perl -pe 's/\$\{([A-Za-z_][A-Za-z0-9_]*)\}/defined $ENV{$1} ? $ENV{$1} : ""/ge' "$1"
}

render_to_temp() {
  local path="$1"
  local rendered
  rendered="$(mktemp)"
  render_yaml "$path" > "$rendered"
  echo "$rendered"
}

set_env() {
  local key="$1"
  local value="$2"
  local tmp
  touch "$ENV_FILE"
  tmp="$(mktemp)"
  awk -v key="$key" -v value="$value" '
    BEGIN { replaced = 0 }
    $0 ~ "^" key "=" { print key "=" value; replaced = 1; next }
    { print }
    END { if (!replaced) print key "=" value }
  ' "$ENV_FILE" > "$tmp"
  mv "$tmp" "$ENV_FILE"
}

sha256_file() {
  shasum -a 256 "$1" | awk '{print $1}'
}

create_or_reuse_agent() {
  local env_key="$1"
  local yaml_file="$2"
  local label="$3"
  local sha_key="${env_key%_ID}_SHA"
  local rendered
  local sha
  local existing="${!env_key:-}"
  local existing_sha="${!sha_key:-}"

  rendered="$(render_to_temp "$AGENTS_DIR/$yaml_file")"
  sha="$(sha256_file "$rendered")"

  if [ -n "$existing" ] && [ "$existing_sha" = "$sha" ] && [ "${REFRESH_AGENT_IDS:-false}" != "true" ]; then
    echo "$env_key already set and YAML unchanged; reusing $existing"
    rm -f "$rendered"
    return
  fi

  if [ -n "$existing" ]; then
    echo "$label YAML changed or refresh requested; creating replacement for $existing..."
  else
    echo "Creating $label..."
  fi

  local new_id
  new_id="$(ant beta:agents create --transform id -r < "$rendered")"
  rm -f "$rendered"
  set_env "$env_key" "$new_id"
  set_env "$sha_key" "$sha"
  export "$env_key=$new_id"
  export "$sha_key=$sha"
}

if [ "$DRY_RUN" = "--help" ] || [ "$DRY_RUN" = "-h" ]; then
  usage
  exit 0
fi

if [ "$DRY_RUN" = "--dry-run" ]; then
  echo "--- agents/environments/cloud.environment.yaml"
  cat "$AGENTS_DIR/environments/cloud.environment.yaml"
  export PAPER_AGENT_ID="${PAPER_AGENT_ID:-agent_paper_dryrun}"
  export MARKET_AGENT_ID="${MARKET_AGENT_ID:-agent_market_dryrun}"
  export DATA_AGENT_ID="${DATA_AGENT_ID:-agent_data_dryrun}"
  export FEATURE_AGENT_ID="${FEATURE_AGENT_ID:-agent_feature_dryrun}"
  export MODELING_AGENT_ID="${MODELING_AGENT_ID:-agent_modeling_dryrun}"
  export BACKTEST_AGENT_ID="${BACKTEST_AGENT_ID:-agent_backtest_dryrun}"
  export RISK_AGENT_ID="${RISK_AGENT_ID:-agent_risk_dryrun}"
  export REPORT_AGENT_ID="${REPORT_AGENT_ID:-agent_report_dryrun}"
  echo "--- agents/specialists/paper.agent.yaml"
  render_yaml "$AGENTS_DIR/specialists/paper.agent.yaml"
  echo "--- agents/specialists/market.agent.yaml"
  render_yaml "$AGENTS_DIR/specialists/market.agent.yaml"
  echo "--- agents/specialists/data.agent.yaml"
  render_yaml "$AGENTS_DIR/specialists/data.agent.yaml"
  echo "--- agents/specialists/feature.agent.yaml"
  render_yaml "$AGENTS_DIR/specialists/feature.agent.yaml"
  echo "--- agents/specialists/modeling.agent.yaml"
  render_yaml "$AGENTS_DIR/specialists/modeling.agent.yaml"
  echo "--- agents/specialists/backtest.agent.yaml"
  render_yaml "$AGENTS_DIR/specialists/backtest.agent.yaml"
  echo "--- agents/specialists/risk-auditor.agent.yaml"
  render_yaml "$AGENTS_DIR/specialists/risk-auditor.agent.yaml"
  echo "--- agents/specialists/report.agent.yaml"
  render_yaml "$AGENTS_DIR/specialists/report.agent.yaml"
  echo "--- agents/research-manager.agent.yaml"
  render_yaml "$AGENTS_DIR/research-manager.agent.yaml"
  exit 0
fi

if ! command -v ant >/dev/null 2>&1; then
  echo "The ant CLI is not installed or is not on PATH; cannot apply Managed Agents control-plane YAML." >&2
  exit 127
fi

require_var ANTHROPIC_API_KEY
require_var MCP_KNOWLEDGE_URL
require_var MCP_QUANTCONNECT_URL
require_var MCP_FRED_URL
require_var MCP_EDGAR_URL
require_var MCP_GDELT_URL
require_var MCP_ARXIV_URL

if [ -n "${MANAGED_ENVIRONMENT_ID:-}" ]; then
  echo "MANAGED_ENVIRONMENT_ID already set in .env; reusing $MANAGED_ENVIRONMENT_ID"
else
  echo "Creating Managed Agents cloud environment..."
  MANAGED_ENVIRONMENT_ID="$(
    ant beta:environments create --transform id -r < "$AGENTS_DIR/environments/cloud.environment.yaml"
  )"
  set_env MANAGED_ENVIRONMENT_ID "$MANAGED_ENVIRONMENT_ID"
  export MANAGED_ENVIRONMENT_ID
fi

create_or_reuse_agent PAPER_AGENT_ID "specialists/paper.agent.yaml" "Paper Agent"
create_or_reuse_agent MARKET_AGENT_ID "specialists/market.agent.yaml" "Market Agent"
create_or_reuse_agent DATA_AGENT_ID "specialists/data.agent.yaml" "Data Agent"
create_or_reuse_agent FEATURE_AGENT_ID "specialists/feature.agent.yaml" "Feature Agent"
create_or_reuse_agent MODELING_AGENT_ID "specialists/modeling.agent.yaml" "Modeling Agent"
create_or_reuse_agent BACKTEST_AGENT_ID "specialists/backtest.agent.yaml" "Backtest Agent"
create_or_reuse_agent RISK_AGENT_ID "specialists/risk-auditor.agent.yaml" "Risk Auditor"
create_or_reuse_agent REPORT_AGENT_ID "specialists/report.agent.yaml" "Report Agent"
create_or_reuse_agent RESEARCH_MANAGER_AGENT_ID "research-manager.agent.yaml" "Phase 5 Research Manager agent"

echo "Applied Phase 5 control plane:"
echo "  MANAGED_ENVIRONMENT_ID=$MANAGED_ENVIRONMENT_ID"
echo "  PAPER_AGENT_ID=$PAPER_AGENT_ID"
echo "  MARKET_AGENT_ID=$MARKET_AGENT_ID"
echo "  DATA_AGENT_ID=$DATA_AGENT_ID"
echo "  FEATURE_AGENT_ID=$FEATURE_AGENT_ID"
echo "  MODELING_AGENT_ID=$MODELING_AGENT_ID"
echo "  BACKTEST_AGENT_ID=$BACKTEST_AGENT_ID"
echo "  RISK_AGENT_ID=$RISK_AGENT_ID"
echo "  REPORT_AGENT_ID=$REPORT_AGENT_ID"
echo "  RESEARCH_MANAGER_AGENT_ID=$RESEARCH_MANAGER_AGENT_ID"
