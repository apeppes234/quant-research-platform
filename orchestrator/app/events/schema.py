"""Raw Managed Agents event -> normalized {kind, payload} for the frontend.

THIS IS THE WIRE FORMAT between orchestrator and UI. KEEP IN SYNC with the bindings table in
docs/09-visual-ui.md. The frontend reducer (frontend/src/store/sessionStore.ts) consumes exactly these
`kind`s. Add a new mapping here and a matching case in the reducer together.

STATUS: scaffold — the map below is the intended contract; implement `normalize()` to produce it.
"""

# raw event.type                  -> normalized {kind, payload}
NORMALIZATION = {
    "session.thread_created":        ("node.add",     ("threadId", "agentName")),
    "session.thread_status_running": ("node.status",  ("threadId", "status")),
    "session.thread_status_idle":    ("node.status",  ("threadId", "status", "stopReason")),
    "session.thread_status_terminated": ("node.status", ("threadId", "status")),
    "agent.thread_message_sent":     ("edge.animate", ("from", "to", "dir")),     # dir="delegate"
    "agent.thread_message_received": ("edge.animate", ("from", "to", "dir")),     # dir="result"
    "agent.message":                 ("agent.text",   ("threadId", "text")),
    "agent.thinking":                ("agent.thinking", ("threadId",)),           # -> shimmer
    "agent.tool_use":                ("node.badge",   ("threadId", "tool", "label")),
    "agent.mcp_tool_use":            ("node.badge",   ("threadId", "tool", "label")),
    "agent.custom_tool_use":         ("custom_tool",  ("threadId", "name", "input", "id")),  # needs reply
    "span.model_request_end":        ("cost.add",     ("threadId", "usage")),
    "span.outcome_evaluation_start": ("rubric.start", ("iteration",)),
    "span.outcome_evaluation_end":   ("rubric.end",   ("iteration", "result", "explanation")),
}


def normalize(raw_event) -> dict:
    """Map a raw SDK event object to {'kind': str, 'id': str, 'payload': dict}. Scaffold."""
    raise NotImplementedError("scaffold — implement per NORMALIZATION + docs/09")
