"""HTTP routes for steering a running session (docs/02 steering, docs/10).

  POST /sessions/{id}/interrupt   -> send user.interrupt (stop/redirect)
  POST /sessions/{id}/confirm     -> send user.tool_confirmation {tool_use_id, result}
                                     (tool_use_id == the triggering event id, NOT a toolu_ id;
                                      in multiagent, echo session_thread_id)

STATUS: scaffold.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/sessions", tags=["steering"])

# @router.post("/{session_id}/interrupt") async def interrupt(...): ...
# @router.post("/{session_id}/confirm")   async def confirm(...): ...
