"""StageTimer attributes run latency to specialists and tool calls."""

from __future__ import annotations

import logging

from app.events.sse_consumer import StageTimer


def test_specialist_delegation_duration_is_logged(caplog):
    timer = StageTimer()
    with caplog.at_level(logging.INFO, logger="orchestrator.timing"):
        timer.observe(
            {"type": "session.thread_created", "session_thread_id": "t1", "agent_name": "Modeling Agent"},
            now=0.0,
        )
        timer.observe({"type": "agent.thread_message_sent", "to_session_thread_id": "t1"}, now=1.0)
        timer.observe({"type": "agent.thread_message_received", "from_session_thread_id": "t1"}, now=61.0)

    record = next(r for r in caplog.records if "specialist=Modeling Agent" in r.getMessage())
    assert "seconds=60.0" in record.getMessage()
    assert "thread=t1" in record.getMessage()


def test_tool_call_duration_is_logged_with_agent(caplog):
    timer = StageTimer()
    with caplog.at_level(logging.INFO, logger="orchestrator.timing"):
        timer.observe(
            {"type": "session.thread_created", "session_thread_id": "t2", "agent_name": "Backtest Agent"},
            now=0.0,
        )
        timer.observe(
            {"type": "agent.mcp_tool_use", "session_thread_id": "t2", "name": "create_backtest"}, now=5.0
        )
        timer.observe(
            {"type": "agent.mcp_tool_result", "session_thread_id": "t2", "name": "create_backtest"},
            now=485.0,
        )

    record = next(r for r in caplog.records if "tool=create_backtest" in r.getMessage())
    assert "seconds=480.0" in record.getMessage()
    assert "agent=Backtest Agent" in record.getMessage()


def test_unmatched_result_is_silent(caplog):
    timer = StageTimer()
    with caplog.at_level(logging.INFO, logger="orchestrator.timing"):
        # A result with no prior start (e.g. history replay boundary) must not log or raise.
        timer.observe({"type": "agent.tool_result", "session_thread_id": "t3", "name": "read_backtest"}, now=9.0)
        timer.observe({"type": "agent.thread_message_received", "from_session_thread_id": "zz"}, now=9.0)
    assert not caplog.records
