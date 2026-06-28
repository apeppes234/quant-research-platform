import json

from app.events.schema import is_terminal_event, normalize_event


def test_thread_created_maps_to_node_add():
    event = {
        "id": "evt_1",
        "type": "session.thread_created",
        "processed_at": "2026-06-27T00:00:00Z",
        "session_thread_id": "thread_1",
        "agent_name": "Research Manager",
    }

    normalized = normalize_event(event)

    assert normalized["kind"] == "node.add"
    assert normalized["payload"]["threadId"] == "thread_1"
    assert normalized["payload"]["agentName"] == "Research Manager"


def test_requires_action_idle_does_not_break_stream():
    event = {
        "id": "evt_2",
        "type": "session.status_idle",
        "stop_reason": {"type": "requires_action"},
    }

    assert is_terminal_event(event) is False


def test_end_turn_idle_breaks_stream():
    event = {
        "id": "evt_3",
        "type": "session.status_idle",
        "stop_reason": {"type": "end_turn"},
    }

    assert is_terminal_event(event) is True


def test_qc_read_backtest_result_maps_to_backtest_update():
    event = {
        "id": "evt_4",
        "type": "agent.mcp_tool_result",
        "session_thread_id": "thread_1",
        "name": "read_backtest",
        "content": [{"type": "text", "text": '{"statistics": {"Sharpe Ratio": "1.2"}}'}],
    }

    normalized = normalize_event(event)

    assert normalized["kind"] == "backtest.update"
    assert normalized["payload"]["tool"] == "read_backtest"
    assert normalized["payload"]["result"]["statistics"]["Sharpe Ratio"] == "1.2"


def test_workspace_write_maps_to_artifact_write():
    event = {
        "id": "evt_5",
        "type": "agent.tool_use",
        "session_thread_id": "thread_modeling",
        "name": "write",
        "input": {"file_path": "/workspace/algo.py", "content": "class StarterStrategy: ..."},
    }

    normalized = normalize_event(event)

    assert normalized["kind"] == "artifact.write"
    assert normalized["payload"]["threadId"] == "thread_modeling"
    assert normalized["payload"]["artifact"] == {
        "path": "/workspace/algo.py",
        "name": "algo.py",
        "kind": "algo",
    }


def test_non_file_bus_write_stays_node_badge():
    event = {
        "id": "evt_6",
        "type": "agent.tool_use",
        "session_thread_id": "thread_modeling",
        "name": "write",
        "input": {"file_path": "/tmp/scratch.txt", "content": "notes"},
    }

    normalized = normalize_event(event)

    assert normalized["kind"] == "node.badge"


def test_search_knowledge_result_maps_to_provenance():
    event = {
        "id": "evt_7",
        "type": "agent.mcp_tool_result",
        "session_thread_id": "thread_modeling",
        "name": "search_knowledge",
        "content": [
            {
                "type": "text",
                "text": '[{"text":"Pairs pattern","source":"repo","citation":"notebook cell 1","corpus":"repo","score":0.91}]',
            }
        ],
    }

    normalized = normalize_event(event)

    assert normalized["kind"] == "provenance.add"
    assert normalized["payload"]["citations"][0]["citation"] == "notebook cell 1"
    assert normalized["payload"]["citations"][0]["corpus"] == "repo"
    # provider is inferred from corpus when not explicit
    assert normalized["payload"]["citations"][0]["provider"] == "quantresearch_repo"


def test_search_knowledge_provenance_preserves_structured_metadata():
    event = {
        "id": "evt_8",
        "type": "agent.mcp_tool_result",
        "session_thread_id": "thread_paper",
        "name": "search_knowledge",
        "content": [
            {
                "type": "text",
                "text": json.dumps(
                    [
                        {
                            "text": "Time series momentum across futures.",
                            "source": "https://arxiv.org/abs/2401.01234",
                            "citation": "Researcher (2024). Momentum. arXiv:2401.01234",
                            "corpus": "papers",
                            "score": 0.88,
                            "metadata": {
                                "provider": "arxiv",
                                "title": "Time Series Momentum",
                                "source_url": "https://arxiv.org/abs/2401.01234",
                                "pdf_url": "https://arxiv.org/pdf/2401.01234",
                                "tags": ["arxiv", "q-fin", "momentum"],
                            },
                        }
                    ]
                ),
            }
        ],
    }

    citation = normalize_event(event)["payload"]["citations"][0]
    assert citation["provider"] == "arxiv"
    assert citation["title"] == "Time Series Momentum"
    assert citation["pdf_url"] == "https://arxiv.org/pdf/2401.01234"
    assert citation["source_url"] == "https://arxiv.org/abs/2401.01234"
    assert citation["tags"] == ["arxiv", "q-fin", "momentum"]
    # full metadata is still preserved alongside the lifted fields
    assert citation["metadata"]["title"] == "Time Series Momentum"


def test_snooping_ledger_write_maps_to_ledger_entry():
    event = {
        "id": "evt_8",
        "type": "agent.tool_use",
        "session_thread_id": "thread_risk",
        "name": "write",
        "input": {
            "file_path": "/mnt/memory/snooping-ledger/variant-1.json",
            "content": '{"variant_id":"variant-1","in_sample_sharpe":1.4,"holdout_sharpe":0.9,"trials_to_date":3}',
        },
    }

    normalized = normalize_event(event)

    assert normalized["kind"] == "ledger.entry"
    assert normalized["payload"]["entry"]["variant_id"] == "variant-1"
    assert normalized["payload"]["entry"]["holdout_sharpe"] == 0.9


def test_always_ask_tool_use_maps_to_confirmation_request():
    event = {
        "id": "evt_tool_ask",
        "type": "agent.mcp_tool_use",
        "session_thread_id": "thread_backtest",
        "name": "create_optimization",
        "evaluated_permission": "ask",
        "input": {"project_id": 123, "parameter": "lookback"},
    }

    normalized = normalize_event(event)

    assert normalized["kind"] == "tool.confirmation.requested"
    assert normalized["payload"]["toolUseId"] == "evt_tool_ask"
    assert normalized["payload"]["sessionThreadId"] == "thread_backtest"
    assert normalized["payload"]["tool"] == "create_optimization"


def test_report_write_maps_to_artifact_write():
    event = {
        "id": "evt_report",
        "type": "agent.tool_use",
        "session_thread_id": "thread_report",
        "name": "write",
        "input": {"file_path": "/mnt/session/outputs/report.pdf", "content": "<pdf bytes>"},
    }

    normalized = normalize_event(event)

    assert normalized["kind"] == "artifact.write"
    assert normalized["payload"]["artifact"] == {
        "path": "/mnt/session/outputs/report.pdf",
        "name": "report.pdf",
        "kind": "report",
    }


def test_outcome_end_includes_default_criteria():
    event = {
        "id": "evt_9",
        "type": "span.outcome_evaluation_end",
        "iteration": 2,
        "result": "needs_revision",
        "explanation": "Out-of-sample performance failed: holdout Sharpe was 0.7",
    }

    normalized = normalize_event(event)

    assert normalized["kind"] == "rubric.end"
    assert normalized["payload"]["iteration"] == 2
    assert len(normalized["payload"]["criteria"]) == 5
    assert normalized["payload"]["criteria"][0]["status"] == "fail"
