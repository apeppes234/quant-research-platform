"""Typed configuration loaded from the repo-level .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = REPO_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Anthropic (data plane)
    anthropic_api_key: str = ""
    research_manager_agent_id: str = ""   # produced by control plane (agents/scripts/apply.sh)
    managed_environment_id: str = ""
    managed_agent_vault_ids: str = ""
    managed_agent_memory_store_ids: str = ""
    lessons_memory_store_id: str = ""
    snooping_ledger_memory_store_id: str = ""
    auto_create_memory_stores: bool = True

    # Self-hosted MCP endpoints (public HTTPS — docs/12)
    mcp_knowledge_url: str = ""
    mcp_quantconnect_url: str = ""
    mcp_fred_url: str = ""
    mcp_edgar_url: str = ""
    mcp_gdelt_url: str = ""
    mcp_arxiv_url: str = ""

    # Vault inbound bearers (one per MCP URL; stored in an Anthropic vault at session create)
    knowledge_mcp_inbound_bearer: str = ""
    qc_mcp_inbound_bearer: str = ""
    fred_mcp_inbound_bearer: str = ""
    edgar_mcp_inbound_bearer: str = ""
    gdelt_mcp_inbound_bearer: str = ""
    arxiv_mcp_inbound_bearer: str = ""
    auto_create_mcp_vaults: bool = True
    auto_create_qc_mcp_vault: bool = True

    orchestrator_port: int = 8000
    frontend_origin: str = "http://localhost:5173"

    @property
    def vault_id_list(self) -> list[str]:
        return _split_csv(self.managed_agent_vault_ids)

    @property
    def memory_store_resources(self) -> list[dict]:
        resources = [
            {
                "type": "memory_store",
                "memory_store_id": memory_store_id,
                "access": "read_write",
                "instructions": "Managed Agents persistent memory attached by the quant research orchestrator.",
            }
            for memory_store_id in _split_csv(self.managed_agent_memory_store_ids)
        ]
        if self.lessons_memory_store_id:
            resources.append(
                {
                    "type": "memory_store",
                    "memory_store_id": self.lessons_memory_store_id,
                    "access": "read_write",
                    "instructions": "Lessons library: concise notes about strategy ideas that overfit or worked.",
                }
            )
        if self.snooping_ledger_memory_store_id:
            resources.append(
                {
                    "type": "memory_store",
                    "memory_store_id": self.snooping_ledger_memory_store_id,
                    "access": "read_write",
                    "instructions": (
                        "Data-snooping ledger: append every variant and optimization run with IS/OOS "
                        "Sharpe and trials_to_date for Deflated Sharpe computation."
                    ),
                }
            )
        return _dedupe_resources(resources)

    def require_session_config(self) -> None:
        missing = [
            name
            for name, value in {
                "ANTHROPIC_API_KEY": self.anthropic_api_key,
                "RESEARCH_MANAGER_AGENT_ID": self.research_manager_agent_id,
                "MANAGED_ENVIRONMENT_ID": self.managed_environment_id,
            }.items()
            if not value
        ]
        if missing:
            joined = ", ".join(missing)
            raise RuntimeError(f"Missing required Managed Agents configuration: {joined}")


def _split_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _dedupe_resources(resources: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique = []
    for resource in resources:
        key = str(resource.get("memory_store_id") or resource)
        if key in seen:
            continue
        seen.add(key)
        unique.append(resource)
    return unique


@lru_cache
def get_settings() -> Settings:
    return Settings()
