"""Thin wrapper around the Anthropic beta SDK namespaces used by the orchestrator.

Centralizes access to client.beta.{sessions, events, vaults, memory_stores, files}. The SDK sets the
`managed-agents-2026-04-01` beta header automatically. Agent creation lives in the CONTROL plane
(agents/), NOT here — this client only references the pre-created agent by id.

STATUS: scaffold.
"""
# import anthropic
# client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

# Convenience accessors to implement:
#   sessions.create(agent=AGENT_ID, environment_id=ENV_ID, vault_ids=[...], resources=[memory stores])
#   sessions.events.stream(session_id=...)  / .list(session_id=...)  / .send(session_id=..., events=[...])
#   vaults.create(...) ; vaults.credentials.create(vault_id, auth={type:"static_bearer", mcp_server_url, token})
#   memory_stores.create(...) ; files.list(scope_id=session_id, betas=["managed-agents-2026-04-01"])
