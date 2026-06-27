"""Typed configuration loaded from environment (.env). See ../.env.example and docs/12.

STATUS: scaffold — fields sketched; wire pydantic-settings when implementing.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    # Anthropic (data plane)
    anthropic_api_key: str = ""
    research_manager_agent_id: str = ""   # produced by control plane (agents/scripts/apply.sh)
    managed_environment_id: str = ""

    # Self-hosted MCP endpoints (public HTTPS — docs/12)
    mcp_knowledge_url: str = ""
    mcp_quantconnect_url: str = ""
    mcp_fred_url: str = ""
    mcp_edgar_url: str = ""
    mcp_gdelt_url: str = ""
    mcp_arxiv_url: str = ""

    # Vault inbound bearers (one per MCP URL; stored in an Anthropic vault at session create)
    qc_mcp_inbound_bearer: str = ""

    orchestrator_port: int = 8000


# settings = Settings()   # instantiate at app startup
