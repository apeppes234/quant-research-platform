"""Managed Agents raw event -> frontend wire event normalization.

Keep this table in sync with docs/09-visual-ui.md.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

QC_RESULT_TOOLS = {
    "read_backtest",
    "read_backtest_chart",
    "read_backtest_orders",
    "read_backtest_insights",
}
KNOWLEDGE_RESULT_TOOLS = {"search_knowledge"}

LOCAL_FILE_WRITE_TOOL_PARTS = ("write", "edit")
FILE_BUS_PATH_PATTERN = re.compile(
    r"(/(?:workspace|mnt/session/outputs)/[A-Za-z0-9._/\-]*"
    r"(?:features[A-Za-z0-9._-]*\.parquet|data_manifest\.json|algo\.py|results\.json|audit\.json|report\.pdf))"
)
SNOOPING_LEDGER_PATH_PATTERN = re.compile(
    r"(/mnt/memory/[A-Za-z0-9._/\-]*(?:snooping|ledger)[A-Za-z0-9._/\-]*\.json)"
)

RUBRIC_CRITERIA = [
    ("holdout_sharpe", "Out-of-sample performance", "Holdout Sharpe > 1.0"),
    ("is_oos_gap", "Overfit guard", "|in-sample Sharpe - holdout Sharpe| < 0.5"),
    ("look_ahead", "Look-ahead audit", "Zero look-ahead findings"),
    ("deflated_sharpe", "Multiple-testing correction", "Deflated Sharpe Ratio > 0"),
    ("max_drawdown", "Tail risk", "Max drawdown < 25%"),
]


def normalize_event(raw: Any) -> dict[str, Any] | None:
    event_type = _get(raw, "type")
    if not event_type:
        return None

    event_id = str(_get(raw, "id", default=f"{event_type}:unknown"))
    base = {
        "id": event_id,
        "type": event_type,
        "processedAt": _plain(_get(raw, "processed_at")),
    }

    if event_type == "session.thread_created":
        return _event(
            base,
            "node.add",
            threadId=_get(raw, "session_thread_id", "thread_id"),
            agentName=_get(raw, "agent_name", default="Agent"),
        )

    if event_type in {
        "session.thread_status_running",
        "session.thread_status_idle",
        "session.thread_status_terminated",
    }:
        status = event_type.rsplit("_", 1)[-1]
        return _event(
            base,
            "node.status",
            threadId=_get(raw, "session_thread_id", "thread_id"),
            status=status,
            stopReason=_plain(_get(raw, "stop_reason")),
        )

    if event_type in {
        "session.status_running",
        "session.status_idle",
        "session.status_rescheduling",
        "session.status_terminated",
    }:
        status = event_type.rsplit("_", 1)[-1]
        return _event(
            base,
            "session.status",
            status=status,
            stopReason=_plain(_get(raw, "stop_reason")),
        )

    if event_type == "agent.thread_message_sent":
        return _event(
            base,
            "edge.animate",
            fromThreadId=_get(raw, "from_session_thread_id", "from_thread_id"),
            toThreadId=_get(raw, "to_session_thread_id", "to_thread_id"),
            direction="delegate",
            content=_text_from_content(_get(raw, "content")),
        )

    if event_type == "agent.thread_message_received":
        return _event(
            base,
            "edge.animate",
            fromThreadId=_get(raw, "from_session_thread_id", "from_thread_id"),
            toThreadId=_get(raw, "to_session_thread_id", "to_thread_id"),
            direction="result",
            content=_text_from_content(_get(raw, "content")),
        )

    if event_type in {"agent.tool_use", "agent.mcp_tool_use"}:
        tool = _get(raw, "name", "tool_name", default="tool")
        thread_id = _get(raw, "session_thread_id", "thread_id")
        input_value = _plain(_get(raw, "input"))
        confirmation = _tool_confirmation_from_raw(raw, event_id, tool, thread_id, input_value)
        if confirmation is not None:
            return _event(base, "tool.confirmation.requested", **confirmation)
        ledger_entry = _ledger_entry_from_tool_input(tool, input_value)
        if ledger_entry is not None:
            return _event(
                base,
                "ledger.entry",
                threadId=thread_id,
                tool=tool,
                label="Writing snooping ledger",
                entry=ledger_entry,
            )
        artifact = _artifact_from_tool_input(tool, input_value)
        if artifact is not None:
            return _event(
                base,
                "artifact.write",
                threadId=thread_id,
                tool=tool,
                label=f"Writing {artifact['name']}",
                input=input_value,
                artifact=artifact,
            )
        return _event(
            base,
            "node.badge",
            threadId=thread_id,
            tool=tool,
            label=_tool_label(event_type, tool, active=True),
            input=input_value,
        )

    if event_type in {"agent.tool_result", "agent.mcp_tool_result"}:
        tool = _get(raw, "name", "tool_name", default="tool")
        if event_type == "agent.mcp_tool_result" and tool in KNOWLEDGE_RESULT_TOOLS:
            result = _tool_result_payload(raw)
            return _event(
                base,
                "provenance.add",
                threadId=_get(raw, "session_thread_id", "thread_id"),
                tool=tool,
                label=_tool_label(event_type, tool, active=False),
                citations=_citations_from_knowledge_result(result),
                result=result,
            )
        if event_type == "agent.mcp_tool_result" and tool in QC_RESULT_TOOLS:
            return _event(
                base,
                "backtest.update",
                threadId=_get(raw, "session_thread_id", "thread_id"),
                tool=tool,
                label=_tool_label(event_type, tool, active=False),
                result=_tool_result_payload(raw),
            )
        return _event(
            base,
            "node.badge",
            threadId=_get(raw, "session_thread_id", "thread_id"),
            tool=tool,
            label=_tool_label(event_type, tool, active=False),
        )

    if event_type == "agent.message":
        return _event(
            base,
            "agent.text",
            threadId=_get(raw, "session_thread_id", "thread_id"),
            text=_text_from_content(_get(raw, "content")),
        )

    if event_type == "agent.thinking":
        return _event(
            base,
            "agent.thinking",
            threadId=_get(raw, "session_thread_id", "thread_id"),
            text=_text_from_content(_get(raw, "content")),
        )

    if event_type == "span.model_request_start":
        return _event(
            base,
            "cost.start",
            threadId=_get(raw, "session_thread_id", "thread_id"),
        )

    if event_type == "span.model_request_end":
        return _event(
            base,
            "cost.add",
            threadId=_get(raw, "session_thread_id", "thread_id"),
            usage=_plain(_get(raw, "model_usage", "usage")),
        )

    if event_type == "span.outcome_evaluation_start":
        return _event(
            base,
            "rubric.start",
            iteration=_get(raw, "iteration"),
            criteria=_criteria_from_raw(raw),
        )

    if event_type == "span.outcome_evaluation_ongoing":
        return _event(
            base,
            "rubric.ongoing",
            iteration=_get(raw, "iteration"),
            explanation=_get(raw, "explanation"),
            criteria=_criteria_from_raw(raw),
        )

    if event_type == "span.outcome_evaluation_end":
        return _event(
            base,
            "rubric.end",
            iteration=_get(raw, "iteration"),
            result=_get(raw, "result"),
            explanation=_get(raw, "explanation"),
            criteria=_criteria_from_raw(raw),
            usage=_plain(_get(raw, "usage")),
        )

    if event_type == "agent.thread_context_compacted":
        return _event(
            base,
            "thread.compacted",
            threadId=_get(raw, "session_thread_id", "thread_id"),
        )

    if event_type.startswith("user."):
        content = _text_from_content(_get(raw, "content"))
        if event_type == "user.define_outcome":
            content = _get(raw, "description", default=content)
        if event_type == "user.interrupt":
            content = _get(raw, "reason", default=content)
        if event_type == "user.tool_confirmation":
            content = _get(raw, "result", default=content)
        return _event(
            base,
            "user.event",
            userEventType=event_type,
            content=content,
            processed=_get(raw, "processed_at") is not None,
            toolUseId=_get(raw, "tool_use_id"),
            result=_get(raw, "result"),
            sessionThreadId=_get(raw, "session_thread_id", "thread_id"),
        )

    return _event(base, "raw.event", payload=_plain(raw))


def is_terminal_event(raw: Any) -> bool:
    event_type = _get(raw, "type")
    if event_type == "session.status_terminated":
        return True
    if event_type != "session.status_idle":
        return False
    stop_reason = _get(raw, "stop_reason")
    return _get(stop_reason, "type") != "requires_action"


def event_id(raw: Any) -> str | None:
    value = _get(raw, "id")
    return str(value) if value is not None else None


def _event(base: dict[str, Any], kind: str, **payload: Any) -> dict[str, Any]:
    return {**base, "kind": kind, "payload": payload}


def _get(obj: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if obj is None:
            continue
        if isinstance(obj, Mapping) and name in obj:
            return obj[name]
        if hasattr(obj, name):
            return getattr(obj, name)
    return default


def _plain(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_plain(item) for item in value]
    if hasattr(value, "model_dump"):
        return _plain(value.model_dump())
    if hasattr(value, "dict"):
        return _plain(value.dict())
    return str(value)


def _text_from_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, Mapping):
        return str(content.get("text") or content.get("content") or "")
    if isinstance(content, list):
        parts = [_text_from_content(item) for item in content]
        return "\n".join(part for part in parts if part)
    return str(content)


def _tool_label(event_type: str, tool: str, *, active: bool) -> str:
    if event_type.startswith("agent.mcp"):
        prefix = "MCP"
    else:
        prefix = "Tool"
    suffix = "running" if active else "done"
    return f"{prefix}: {tool} {suffix}"


def _tool_confirmation_from_raw(
    raw: Any,
    event_id: str,
    tool: Any,
    thread_id: Any,
    input_value: Any,
) -> dict[str, Any] | None:
    permission = _get(raw, "evaluated_permission", "permission", "permission_policy")
    if isinstance(permission, Mapping):
        permission = _get(permission, "type", "value", "policy")
    if str(permission).lower() not in {"ask", "always_ask"}:
        return None
    tool_name = str(tool)
    return {
        "toolUseId": event_id,
        "threadId": thread_id,
        "sessionThreadId": thread_id,
        "tool": tool_name,
        "label": f"Approve {tool_name}",
        "input": input_value,
        "evaluatedPermission": "ask",
    }


def _tool_result_payload(raw: Any) -> Any:
    value = _get(raw, "result", "output", "content", "data")
    if isinstance(value, list):
        text = _text_from_content(value)
        parsed = _json_or_none(text)
        return parsed if parsed is not None else _plain(value)
    if isinstance(value, Mapping):
        text = _text_from_content(value)
        parsed = _json_or_none(text)
        return parsed if parsed is not None else _plain(value)
    if isinstance(value, str):
        parsed = _json_or_none(value)
        return parsed if parsed is not None else value
    return _plain(value)


def _json_or_none(text: str) -> Any | None:
    stripped = text.strip()
    if not stripped or stripped[0] not in "[{":
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None


def _artifact_from_tool_input(tool: str, input_value: Any) -> dict[str, str] | None:
    tool_name = str(tool).lower()
    if not any(part in tool_name for part in LOCAL_FILE_WRITE_TOOL_PARTS):
        return None

    path = _extract_file_bus_path(input_value)
    if path is None:
        return None

    name = path.rsplit("/", 1)[-1]
    return {"path": path, "name": name, "kind": _artifact_kind(name)}


def _ledger_entry_from_tool_input(tool: str, input_value: Any) -> dict[str, Any] | None:
    tool_name = str(tool).lower()
    if not any(part in tool_name for part in LOCAL_FILE_WRITE_TOOL_PARTS):
        return None

    path = _extract_ledger_path(input_value)
    if path is None:
        return None

    content = _extract_json_content(input_value)
    entry = content if isinstance(content, Mapping) else {"raw": content}
    return {**_plain(entry), "path": path}


def _extract_file_bus_path(value: Any) -> str | None:
    for text in _string_values(value):
        match = FILE_BUS_PATH_PATTERN.search(text)
        if match:
            return match.group(1)
    return None


def _extract_ledger_path(value: Any) -> str | None:
    for text in _string_values(value):
        match = SNOOPING_LEDGER_PATH_PATTERN.search(text)
        if match:
            return match.group(1)
    return None


def _extract_json_content(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("content", "text", "new_str", "replacement"):
            if key in value:
                parsed = _json_or_none(str(value[key]))
                return parsed if parsed is not None else value[key]
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, str):
        parsed = _json_or_none(value)
        return parsed if parsed is not None else value
    return _plain(value)


def _string_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        values: list[str] = []
        for item in value.values():
            values.extend(_string_values(item))
        return values
    if isinstance(value, (list, tuple, set)):
        values = []
        for item in value:
            values.extend(_string_values(item))
        return values
    return [str(value)]


def _artifact_kind(name: str) -> str:
    if name.startswith("features") and name.endswith(".parquet"):
        return "features"
    if name == "data_manifest.json":
        return "manifest"
    if name == "algo.py":
        return "algo"
    if name == "results.json":
        return "results"
    if name == "audit.json":
        return "audit"
    if name == "report.pdf":
        return "report"
    return "artifact"


def _citations_from_knowledge_result(result: Any) -> list[dict[str, Any]]:
    rows = result
    if isinstance(result, Mapping):
        rows = result.get("results") or result.get("items") or []
    if not isinstance(rows, list):
        return []
    citations = []
    for item in rows:
        if not isinstance(item, Mapping):
            continue
        metadata = item.get("metadata")
        metadata_map = metadata if isinstance(metadata, Mapping) else {}
        citation = str(item.get("citation") or "")
        source = str(item.get("source") or "")
        if not citation and not source:
            continue
        corpus = str(item.get("corpus") or metadata_map.get("corpus") or "")

        def _field(name: str) -> Any:
            # prefer a top-level field on the result row, fall back to ingestion metadata
            return item.get(name) if item.get(name) is not None else metadata_map.get(name)

        citations.append(
            {
                "text": str(item.get("text") or "")[:1200],
                "source": source,
                "citation": citation,
                "corpus": corpus,
                "score": item.get("score"),
                # Structured fields the Research tab inspects (provenance stays metadata-complete below).
                "provider": str(_field("provider") or _provider_from_corpus(corpus, source)),
                "title": _string_or_none(_field("title")),
                "source_url": _string_or_none(_field("source_url")),
                "pdf_url": _string_or_none(_field("pdf_url")),
                "local_pdf_path": _string_or_none(_field("local_pdf_path")),
                "source_path": _string_or_none(_field("source_path")),
                "tags": _tag_list(_field("tags")),
                "page_number": _field("page_number") if _field("page_number") is not None else _field("pageNumber"),
                "metadata": _plain(metadata),
            }
        )
    return citations


def _provider_from_corpus(corpus: str, source: str) -> str:
    if "arxiv" in source.lower():
        return "arxiv"
    if "ssrn" in source.lower():
        return "ssrn"
    if corpus == "repo":
        return "quantresearch_repo"
    if corpus == "strategy_library":
        return "quantconnect_strategy_library"
    return ""


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _tag_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, (list, tuple)):
        return [str(tag) for tag in value if str(tag).strip()]
    return []


def _criteria_from_raw(raw: Any) -> list[dict[str, Any]]:
    explicit = _get(raw, "criteria")
    if isinstance(explicit, list):
        return [_plain(item) for item in explicit if isinstance(item, Mapping)]

    explanation = str(_get(raw, "explanation", default="") or "")
    result = str(_get(raw, "result", default="") or "")
    criteria = []
    for criterion_id, label, condition in RUBRIC_CRITERIA:
        status = _criterion_status(explanation, result, criterion_id, label)
        criteria.append(
            {
                "id": criterion_id,
                "label": label,
                "condition": condition,
                "status": status,
                "explanation": _criterion_explanation(explanation, label),
            }
        )
    return criteria


def _criterion_status(explanation: str, result: str, criterion_id: str, label: str) -> str:
    lowered = explanation.lower()
    probes = {criterion_id.replace("_", " "), label.lower()}
    for probe in probes:
        if not probe:
            continue
        for prefix in ("pass", "passed", "satisfied", "true"):
            if re.search(rf"{re.escape(probe)}[^.\n]*(?:{prefix})", lowered):
                return "pass"
        for prefix in ("fail", "failed", "needs revision", "false"):
            if re.search(rf"{re.escape(probe)}[^.\n]*(?:{prefix})", lowered):
                return "fail"
    if result == "satisfied":
        return "pass"
    return "unknown"


def _criterion_explanation(explanation: str, label: str) -> str:
    if not explanation:
        return ""
    for line in explanation.splitlines():
        if label.lower() in line.lower():
            return line.strip("-* 0123456789.")
    return explanation[:280]
