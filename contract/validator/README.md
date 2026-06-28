# contract/validator

Static, deterministic checks run **before** any QC compile/backtest. This is the tool-layer enforcement
the anti-bias protocol relies on (docs/08 layer 2): the sealed holdout is unreachable because code that
touches it fails here.

## Run

```bash
python validate.py /workspace/algo.py        # exits with findings; OK if none
python validate.py ../templates/starter_algorithm.py
```

Or import: `from validator.validate import validate; validate(source, sealed_holdout={...})`.

## Checks (see `validate.py` docstring for detail)

1. AST safety — forbidden imports (`os`/`sys`/`subprocess`/`requests`), `eval`/`exec`, raw IO/network.
2. Split discipline — no reads of the sealed-holdout symbols/date range during design.
3. Signal shape — `on_data` present with entry/exit logic; no look-ahead in indicator warm-up.
4. QC idioms — no overwriting indicator method names (`self.rsi = ...`); PEP8-ish.
5. No NL-in-code — body parses as valid Python.

The Modeling agent MUST pass this before compiling (contract workflow step 4). Add it to CI against
`templates/starter_algorithm.py`.
