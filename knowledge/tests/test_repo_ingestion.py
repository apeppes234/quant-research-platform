"""Tests for the local QuantResearch and QuantConnect Strategy Library jobs."""

from __future__ import annotations

import json
from pathlib import Path

from ingestion import quantresearch_repo, strategy_library


def _write_notebook(path: Path, cells: list[tuple[str, str]]) -> None:
    payload = {
        "cells": [
            {"cell_type": ctype, "source": [src], "metadata": {}, "outputs": [], "execution_count": None}
            if ctype == "code"
            else {"cell_type": ctype, "source": [src], "metadata": {}}
            for ctype, src in cells
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


# --------------------------------------------------------------------------- QuantResearch


def test_quantresearch_missing_dir_returns_empty(capsys, monkeypatch):
    monkeypatch.delenv("QUANTRESEARCH_REPO_PATH", raising=False)
    assert quantresearch_repo.collect_chunks() == []
    err = capsys.readouterr().err
    assert "QUANTRESEARCH_REPO_PATH" in err and "git clone" in err


def test_quantresearch_notebook_cell_chunks(tmp_path):
    _write_notebook(
        tmp_path / "kalman_pairs.ipynb",
        [("markdown", "# Kalman filter pairs trading"), ("code", "import numpy as np\nbeta = kalman(y, x)")],
    )
    chunks = quantresearch_repo.build_chunks(tmp_path)
    assert len(chunks) == 2

    md = next(c for c in chunks if c.metadata["cell_type"] == "markdown")
    code = next(c for c in chunks if c.metadata["cell_type"] == "code")

    assert md.corpus == "repo" and code.corpus == "repo"
    assert code.metadata["provider"] == "quantresearch_repo"
    assert code.metadata["language"] == "python"
    assert code.metadata["source_type"] == "code"
    assert md.metadata["source_type"] == "explanation"
    assert code.metadata["cell_index"] == 1
    assert "source_path" in code.metadata
    # tags inferred from path + text
    assert "kalman-filter" in code.tags
    assert "pairs-trading" in code.tags


def test_quantresearch_markdown_and_python(tmp_path):
    (tmp_path / "momentum_strategy.py").write_text("# momentum signal\nret = price.pct_change(20)", encoding="utf-8")
    (tmp_path / "notes.md").write_text("## Cointegration and mean reversion\nJohansen test notes.", encoding="utf-8")
    chunks = quantresearch_repo.build_chunks(tmp_path)
    by_lang = {c.metadata.get("language") for c in chunks}
    assert "python" in by_lang and "markdown" in by_lang
    py = next(c for c in chunks if c.metadata.get("language") == "python")
    assert "momentum" in py.tags
    md = next(c for c in chunks if c.metadata.get("language") == "markdown")
    assert "cointegration" in md.tags and "mean-reversion" in md.tags


def test_quantresearch_limit(tmp_path):
    for i in range(5):
        (tmp_path / f"f{i}.py").write_text(f"x = {i}\n\ny = {i}\n", encoding="utf-8")
    assert len(quantresearch_repo.build_chunks(tmp_path, limit=2)) == 2


# --------------------------------------------------------------------------- Strategy Library


def test_strategy_library_missing_dir_returns_empty(capsys, monkeypatch):
    for var in strategy_library.ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    assert strategy_library.collect_chunks() == []
    err = capsys.readouterr().err
    assert "STRATEGY_LIBRARY_PATH" in err and "git clone" in err


def test_strategy_library_python_and_markdown(tmp_path):
    strat = tmp_path / "MomentumStrategy"
    strat.mkdir()
    (strat / "main.py").write_text(
        "class MomentumAlgorithm(QCAlgorithm):\n    def Initialize(self): pass  # universe selection\n",
        encoding="utf-8",
    )
    (strat / "README.md").write_text("# Momentum Strategy\nAn alpha model using trend signals.", encoding="utf-8")
    (strat / "Alpha.cs").write_text("public class MomentumAlphaModel { } // execution model", encoding="utf-8")

    chunks = strategy_library.build_chunks(tmp_path)
    assert chunks
    for c in chunks:
        assert c.corpus == "strategy_library"
        assert c.metadata["provider"] == "quantconnect_strategy_library"
        assert c.metadata["disclaimer"].startswith("implementation pattern")
        assert c.metadata["title"] == "MomentumStrategy"
        assert c.metadata["strategy_family"] == "momentum"

    langs = {c.metadata["language"] for c in chunks}
    assert {"python", "markdown", "csharp"} <= langs
    cs = next(c for c in chunks if c.metadata["language"] == "csharp")
    assert cs.metadata["source_type"] == "code"


def test_strategy_library_tags_and_citation(tmp_path):
    strat = tmp_path / "OptionsPairs"
    strat.mkdir()
    (strat / "main.py").write_text("# pairs trading with options and risk management stop loss", encoding="utf-8")
    chunk = strategy_library.build_chunks(tmp_path)[0]
    assert "pairs-trading" in chunk.tags
    assert "options" in chunk.tags
    assert "risk-management" in chunk.tags
    assert chunk.citation.startswith("QuantConnect Strategy Library:")
    assert "quantconnect" in chunk.tags


def test_strategy_library_source_path_env(tmp_path, monkeypatch):
    (tmp_path / "s.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setenv("STRATEGY_LIBRARY_PATH", str(tmp_path))
    assert strategy_library.source_root() == tmp_path
