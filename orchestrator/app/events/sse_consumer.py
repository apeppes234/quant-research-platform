"""Consume the Managed Agents SSE event stream for one session.

THE RELIABILITY-CRITICAL FILE. Implements the three patterns from docs/10-orchestrator.md:

  1. Stream-first, then send  — open the stream BEFORE sending the kickoff event, or early events arrive
     buffered as one batch and you lose real-time reactions.

  2. Reconnect-with-consolidation — SSE has NO replay. On every (re)connect: open the stream, fetch
     events.list() history, yield history first then live, deduping by event.id. The dedupe gates only
     the handler — terminal checks must still run for already-seen events.

  3. Idle-break gate — idle != done. Break on session.status_terminated, or session.status_idle with
     stop_reason.type != "requires_action". `requires_action` means the agent is waiting on YOU
     (tool_confirmation / custom_tool_result) — handle it, don't break.

Each consumed raw event is normalized via events/schema.py and handed to ws_relay for fan-out.

STATUS: scaffold — signature + skeleton only.
"""
from typing import AsyncIterator


async def consume(client, session_id: str) -> AsyncIterator[dict]:
    """Yield NORMALIZED events ({kind, payload}) for `session_id` until the session is done.

    Pseudocode (fill in with the real beta SDK calls — docs/02):

        seen = set()
        stream = client.beta.sessions.events.stream(session_id=session_id)   # open FIRST
        for ev in client.beta.sessions.events.list(session_id=session_id).data:   # history
            seen.add(ev.id)
            yield normalize(ev)
        for ev in stream:                                                    # live tail
            if ev.id not in seen:
                seen.add(ev.id)
                yield normalize(ev)
            if ev.type == "session.status_terminated":
                break
            if ev.type == "session.status_idle" and ev.stop_reason.type != "requires_action":
                break
            # if requires_action: surface it so the caller can send tool_confirmation/custom_tool_result
    """
    raise NotImplementedError("scaffold — see docstring + docs/10")
