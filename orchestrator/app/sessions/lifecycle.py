"""Session status polling + archive-safe teardown.

The SSE stream emits `session.status_idle` slightly BEFORE the queryable status flips (post-idle race,
docs/10). So before archive/delete, poll sessions.retrieve() until status != "running" (with a short
backoff) to avoid intermittent 400s.

STATUS: scaffold.
"""


async def archive_when_settled(client, session_id: str, attempts: int = 10) -> None:
    """Poll sessions.retrieve until not running, then archive. Scaffold."""
    raise NotImplementedError("scaffold — see docs/10 'Post-idle status-write race'")
