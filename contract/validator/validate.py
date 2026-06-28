"""Static validator for candidate QuantConnect strategies.

The validator is intentionally conservative and fast: it parses Python source,
checks the mechanical authoring rules in docs/11, and exits before any QC
compile/backtest can run if the candidate touches forbidden surfaces.
"""

from __future__ import annotations

import ast
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

FORBIDDEN_IMPORTS = {
    "aiohttp",
    "httpx",
    "os",
    "pathlib",
    "requests",
    "socket",
    "subprocess",
    "sys",
    "urllib",
}
FORBIDDEN_CALLS = {"__import__", "compile", "eval", "exec", "input", "open"}
QC_INDICATOR_METHODS = {
    "adx",
    "atr",
    "bb",
    "ema",
    "macd",
    "mom",
    "rsi",
    "sma",
    "stoch",
    "vwap",
}
TRADE_CALLS = {
    "buy",
    "emit_insights",
    "limit_order",
    "liquidate",
    "market_order",
    "sell",
    "set_holdings",
    "stop_market_order",
}
ALLOWED_HOLDOUT_FUNCTIONS = {"_segment_bounds", "initialize"}
DEFAULT_SEALED_HOLDOUT = {"start": "2020-01-01", "end": "2023-12-31", "symbols": []}


@dataclass
class Finding:
    rule: str
    line: int
    msg: str

    def to_dict(self) -> dict[str, Any]:
        return {"rule": self.rule, "line": self.line, "msg": self.msg}


@dataclass
class Result:
    ok: bool
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "findings": [finding.to_dict() for finding in self.findings]}


def validate(source: str, sealed_holdout: dict | None = None) -> Result:
    """Validate candidate `algo.py` source against the strategy contract."""

    findings: list[Finding] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return Result(
            ok=False,
            findings=[
                Finding(
                    "no-nl-in-code",
                    exc.lineno or 0,
                    f"not valid Python: {exc.msg}",
                )
            ],
        )

    holdout = {**DEFAULT_SEALED_HOLDOUT, **(sealed_holdout or {})}
    parents = _parent_map(tree)

    _check_forbidden_imports(tree, findings)
    _check_forbidden_calls(tree, findings)
    _check_indicator_shadowing(tree, findings)
    _check_holdout_seal(tree, parents, holdout, findings)
    _check_signal_shape(tree, findings)

    return Result(ok=not findings, findings=findings)


def validate_file(path: Path, sealed_holdout: dict | None = None) -> Result:
    return validate(path.read_text(encoding="utf-8"), sealed_holdout=sealed_holdout)


def _check_forbidden_imports(tree: ast.AST, findings: list[Finding]) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in FORBIDDEN_IMPORTS:
                    findings.append(
                        Finding(
                            "forbidden-import",
                            node.lineno,
                            f"importing {root!r} is forbidden by the authoring contract",
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            if root in FORBIDDEN_IMPORTS:
                findings.append(
                    Finding(
                        "forbidden-import",
                        node.lineno,
                        f"importing from {root!r} is forbidden by the authoring contract",
                    )
                )


def _check_forbidden_calls(tree: ast.AST, findings: list[Finding]) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node.func)
        if name in FORBIDDEN_CALLS:
            findings.append(
                Finding(
                    "forbidden-call",
                    node.lineno,
                    f"calling {name!r} is forbidden by the authoring contract",
                )
            )


def _check_indicator_shadowing(tree: ast.AST, findings: list[Finding]) -> None:
    for node in ast.walk(tree):
        targets: list[ast.AST] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        elif isinstance(node, ast.AugAssign):
            targets = [node.target]

        for target in targets:
            for inner in ast.walk(target):
                if (
                    isinstance(inner, ast.Attribute)
                    and isinstance(inner.value, ast.Name)
                    and inner.value.id == "self"
                    and inner.attr in QC_INDICATOR_METHODS
                ):
                    findings.append(
                        Finding(
                            "indicator-name-shadowing",
                            getattr(inner, "lineno", getattr(node, "lineno", 0)),
                            f"use self._{inner.attr} for indicator storage; do not overwrite self.{inner.attr}",
                        )
                    )


def _check_holdout_seal(
    tree: ast.AST,
    parents: dict[ast.AST, ast.AST],
    holdout: dict,
    findings: list[Finding],
) -> None:
    sealed_strings = {
        value
        for value in [holdout.get("start"), holdout.get("end"), *(holdout.get("symbols") or [])]
        if isinstance(value, str) and value
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id == "HOLDOUT":
            function = _enclosing_function(node, parents)
            if function not in ALLOWED_HOLDOUT_FUNCTIONS:
                findings.append(
                    Finding(
                        "holdout-seal",
                        node.lineno,
                        "HOLDOUT may only be selected in initialize/_segment_bounds, not during design logic",
                    )
                )
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in sealed_strings:
            if _is_holdout_constant_definition(node, parents):
                continue
            function = _enclosing_function(node, parents)
            if function not in ALLOWED_HOLDOUT_FUNCTIONS:
                findings.append(
                    Finding(
                        "holdout-seal",
                        node.lineno,
                        f"sealed holdout value {node.value!r} is referenced outside the segment gate",
                    )
                )


def _check_signal_shape(tree: ast.AST, findings: list[Finding]) -> None:
    on_data = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "on_data"
    ]
    if not on_data:
        findings.append(Finding("signal-shape", 0, "strategy must define on_data(self, data)"))
        return

    body = on_data[0]
    calls = {_call_name(node.func) for node in ast.walk(body) if isinstance(node, ast.Call)}
    if not calls.intersection(TRADE_CALLS):
        findings.append(
            Finding(
                "signal-shape",
                body.lineno,
                "on_data must contain explicit entry/exit order logic",
            )
        )

    has_readiness_guard = any(
        isinstance(node, ast.Attribute) and node.attr in {"is_ready", "is_warming_up"}
        for node in ast.walk(body)
    )
    if not has_readiness_guard:
        findings.append(
            Finding(
                "signal-shape",
                body.lineno,
                "on_data must guard indicator warm-up/readiness before trading",
            )
        )


def _parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


def _call_name(func: ast.AST) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _enclosing_function(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> str | None:
    current = node
    while current in parents:
        current = parents[current]
        if isinstance(current, ast.FunctionDef):
            return current.name
    return None


def _is_holdout_constant_definition(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
    current: ast.AST = node
    while current in parents:
        current = parents[current]
        if isinstance(current, ast.Assign):
            return any(isinstance(target, ast.Name) and target.id == "HOLDOUT" for target in current.targets)
        if isinstance(current, ast.FunctionDef):
            return False
    return False


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python validate.py path/to/algo.py", file=sys.stderr)
        return 2
    result = validate_file(Path(argv[1]))
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
