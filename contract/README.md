# contract/ — the "expertise" layer (constrain → validate → run)

This is what makes the system trustworthy without a giant prompt (docs/00, docs/11). Modeled on
QuantDinger's `get_indicator_authoring_contract()` + `validate_indicator_code()`.

| File | What |
|---|---|
| `strategy_authoring_contract.md` | The rules a valid strategy must follow, in prose + the rubric (docs/07). Retrievable via `search_knowledge` (corpus=`contract`). |
| `contract.json` | Same rules as a versioned, machine-consumable object (the Modeling agent + validator both read it). |
| `validator/validate.py` | Static checks run **before** compile/backtest — the mechanical anti-look-ahead enforcement point. |
| `validator/README.md` | What each check does and how to run it. |
| `templates/starter_algorithm.py` | A compiling QC `QCAlgorithm` skeleton with the train/val/sealed-holdout split wired and signal hooks stubbed. |

## The flow the Modeling agent must follow

```
search_knowledge(contract, repo) → start from starter_algorithm.py → write algo.py
   → validate.py MUST pass → QC create_compile + read_compile (fix all warnings) → backtest
```

The validator passing is a hard gate (docs/11): the sealed holdout is unreachable *because the code that
touches it fails validation*, not because we asked nicely.
