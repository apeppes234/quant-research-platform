"""Session lifecycle + user-event sending.

Creates sessions referencing the pre-built Research Manager agent (RESEARCH_MANAGER_AGENT_ID) + the
environment, attaches the credential vault (per docs/12) and the two memory stores (lessons + snooping
ledger, per docs/06/08), and sends user events.

User events we send (docs/02):
  - user.message                                  (conversational)
  - user.define_outcome {description, rubric, max_iterations:5}   (graded loop — docs/07; NO separate message)
  - user.interrupt                                (steering: stop/redirect)
  - user.tool_confirmation {tool_use_id, result}  (approve gated tools, e.g. create_optimization)
  - user.custom_tool_result {...}                 (only if a host-side custom tool is ever declared)

STATUS: scaffold.
"""


async def create_session(client, agent_id: str, environment_id: str,
                          vault_ids: list[str], memory_store_ids: list[str]) -> str:
    """Create a session; attach vaults + memory-store resources; return session_id. Scaffold."""
    raise NotImplementedError("scaffold — see docs/02/06/08/12")


async def define_outcome(client, session_id: str, description: str, rubric_markdown: str,
                         max_iterations: int = 5) -> None:
    """Send user.define_outcome with the 5-gate rubric (docs/07). Scaffold."""
    raise NotImplementedError("scaffold")
