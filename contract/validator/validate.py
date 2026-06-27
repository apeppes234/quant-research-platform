"""Static validator for candidate strategies — the mechanical anti-look-ahead gate (docs/08, docs/11).

Pure + fast + no network. Run by the Modeling agent BEFORE compiling, and as a CI check on the starter
template. Input: candidate algo.py source (+ optional data manifest with the sealed-holdout date range).
Output: {ok: bool, findings: [{rule, line, msg}]}.

Checks mirror contract.json `forbidden`:
  1. AST safety        — no forbidden imports (os/sys/subprocess/requests); no eval/exec; no raw IO/network.
  2. Split discipline  — code never reads the holdout symbol/date range during design (AST + string + the
                         contract's sealed-holdout dates from the manifest).
  3. Signal shape      — entry/exit logic present in on_data; indicators warmed up without peeking ahead.
  4. QC idioms         — no overwriting indicator method names (self.rsi = ... is a finding); PEP8-ish.
  5. No NL-in-code     — the body parses as valid Python (ast.parse succeeds).

STATUS: scaffold — signatures + the rule list; implement the AST visitors.
"""
from __future__ import annotations
import ast
from dataclasses import dataclass, field

FORBIDDEN_IMPORTS = {"os", "sys", "subprocess", "requests"}
FORBIDDEN_CALLS = {"eval", "exec"}
# Indicator method names that must not be shadowed (extend from QC docs/04).
QC_INDICATOR_METHODS = {"rsi", "sma", "ema", "macd", "bb", "atr", "adx", "stoch"}


@dataclass
class Finding:
    rule: str
    line: int
    msg: str


@dataclass
class Result:
    ok: bool
    findings: list[Finding] = field(default_factory=list)


def validate(source: str, sealed_holdout: dict | None = None) -> Result:
    """Validate candidate strategy source against the contract. Scaffold.

    sealed_holdout (optional): {"symbols": [...], "start": "YYYY-MM-DD", "end": "YYYY-MM-DD"} — the date
    range the design phase must NOT touch (check 2).
    """
    findings: list[Finding] = []

    # check 5 — must parse as Python
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return Result(ok=False, findings=[Finding("no-nl-in-code", e.lineno or 0, f"not valid Python: {e}")])

    # TODO check 1: walk imports/calls -> FORBIDDEN_IMPORTS / FORBIDDEN_CALLS
    # TODO check 4: detect `self.<indicator_method> = ...` assignments -> finding
    # TODO check 2: detect references to sealed_holdout dates/symbols during design
    # TODO check 3: ensure on_data exists with entry/exit logic; indicator warm-up sane
    _ = tree

    return Result(ok=not findings, findings=findings)


if __name__ == "__main__":  # quick manual check
    import sys
    src = open(sys.argv[1]).read() if len(sys.argv) > 1 else ""
    r = validate(src)
    print("OK" if r.ok else "FAIL", [f.__dict__ for f in r.findings])
