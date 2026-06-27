"""HTTP routes for session control (the frontend chat/steering calls these).

  POST /sessions                          -> create a session (returns session_id)
  POST /sessions/{id}/message             -> send a user.message
  POST /sessions/{id}/define_outcome      -> start the graded loop (docs/07)

STATUS: scaffold.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/sessions", tags=["sessions"])

# @router.post("")                       async def create(...): ...
# @router.post("/{session_id}/message")  async def message(...): ...
# @router.post("/{session_id}/define_outcome") async def outcome(...): ...
