# 11 — Authoring contract (the "expertise" layer)

This is the operationalization of **constrain → validate → run** (docs/00). It is what makes the system
trustworthy without a giant prompt. Lives in [`contract/`](../contract/). Modeled on QuantDinger's
`get_indicator_authoring_contract()` + `validate_indicator_code()` pattern (the one genuinely reusable
concept from that codebase).

## Three pieces

| Piece | File | What it is |
|---|---|---|
| **Contract (human + machine)** | `contract/strategy_authoring_contract.md` | The rules a valid strategy must follow, in prose + the rubric (docs/07). Retrievable via `search_knowledge` (corpus=`contract`). |
| **Contract (structured)** | `contract/contract.json` | The same rules as a versioned JSON object the Modeling agent and validator both consume. |
| **Validator** | `contract/validator/validate.py` | Static checks run **before** compile/backtest. The mechanical enforcement point for anti-look-ahead. |
| **Starter template** | `contract/templates/starter_algorithm.py` | A compiling QC algorithm skeleton with the train/val/holdout split wired and signal columns stubbed. |

## What the contract specifies (contract.json shape)

```jsonc
{
  "version": "strategy-contract-v1",
  "workflow": [
    "retrieve relevant patterns via search_knowledge",
    "write algo.py from the starter template",
    "run the validator (must pass)",
    "create_compile + read_compile (fix ALL warnings)",
    "create_backtest on train+validation only",
    "evaluate sealed holdout exactly once",
    "hand results.json to the Risk auditor"
  ],
  "required": {
    "splits": ["train", "validation", "holdout"],   // holdout sealed during design
    "evaluation": "walk-forward",
    "signal_contract": "algorithm must expose its entry/exit logic in on_data; no future data",
    "outputs": "results.json with BOTH in-sample and sealed-holdout segments"
  },
  "forbidden": [
    "natural language in code",
    "import os | sys | subprocess | requests  (no arbitrary IO/network)",
    "reading validation/holdout data during feature construction",
    "hand-joined future-timestamped data",
    "overwriting QC indicator method names (use self._rsi = self.rsi(...))",
    "calling create_optimization without an approved, ledgered request"
  ],
  "rubric_ref": "see contract/strategy_authoring_contract.md (rubric) and docs/07"
}
```

## The validator (`validate.py`)

Pure, fast, no network. Input = the candidate `algo.py` (+ the data manifest). Output = `{ok: bool,
findings: [{rule, line, msg}]}`. Checks (mirror `forbidden` above):

1. **AST safety** — no forbidden imports; no `eval`/`exec`; no raw file/network IO outside QC APIs.
2. **Split discipline** — the code references the train/validation split for fitting and never reads the
   holdout symbol/date range during design (string + AST heuristics + the contract's sealed-holdout dates).
3. **Signal shape** — entry/exit logic present; indicators warmed up without peeking ahead.
4. **QC idioms** — no overwriting indicator method names; PEP8 (delegate to QC `update_code_to_pep8` if not).
5. **No NL-in-code** — the body is valid Python, not prose.

The **Modeling agent must run the validator and pass it before compiling** (enforced in its `system`
prompt and by the contract workflow). The validator is also a CI check on the starter template.

## Why a validator and not just prompt rules

Prompts drift and the model can rationalize. A deterministic validator is the **tool-layer enforcement**
that docs/08 layer 2 relies on: the holdout is unreachable not because we asked nicely, but because the
code that touches it fails validation and never reaches the backtest engine.

## Relationship to QuantConnect

The contract is QC-aware (docs/04): the workflow targets `create_project`/`create_file`/`create_compile`/
`create_backtest`; the starter template is a real QC `QCAlgorithm` subclass with `initialize`/`on_data`
and the split dates parameterized.
