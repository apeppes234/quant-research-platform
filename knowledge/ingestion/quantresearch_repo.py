"""Ingest a locally cloned letianzj/QuantResearch repo -> corpus 'repo'. docs/06.

This is **local** reference material: clone the repo yourself and point QUANTRESEARCH_REPO_PATH at it.
The job never downloads anything. Notebooks are chunked by cell (code cells kept as code, markdown cells
as explanation); .md and .py files are chunked as text. Content is code-pattern grounding for the
Feature/Modeling agents — not a market-data source.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .common import KnowledgeChunk, chunk_text, infer_tags, notebook_cell_chunks

REPO_URL = "https://github.com/letianzj/QuantResearch"
ENV_VAR = "QUANTRESEARCH_REPO_PATH"

# Canonical tag -> substrings matched against the file path AND the chunk text.
TOPIC_VOCAB: dict[str, tuple[str, ...]] = {
    "kalman-filter": ("kalman",),
    "pairs-trading": ("pairs", "pair_trad", "statarb", "stat_arb"),
    "cointegration": ("cointegrat", "johansen"),
    "momentum": ("momentum", "trend"),
    "mean-reversion": ("mean_revers", "mean-revers", "reversion", "ou_process", "ornstein"),
    "garch": ("garch",),
    "arima": ("arima", "arma"),
    "hmm": ("hmm", "hidden_markov", "hidden markov"),
    "regime": ("regime",),
    "fama-french": ("fama", "french", "fama_french"),
    "factor": ("factor",),
    "reinforcement-learning": ("reinforce", "rl_", "q_learning", "q-learning", "policy gradient"),
    "var": ("value_at_risk", "value at risk", "/var", "var_"),
    "risk": ("risk", "drawdown", "volatility"),
}

_SUPPORTED = {".ipynb", ".md", ".py"}


def source_root(path: str | None = None) -> Path | None:
    """Resolve the local repo directory, or None if it is not present."""

    configured = path or os.getenv(ENV_VAR, "")
    if not configured:
        return None
    root = Path(configured).expanduser()
    return root if root.is_dir() else None


def setup_message(path: str | None = None) -> str:
    target = path or os.getenv(ENV_VAR) or "/path/to/QuantResearch"
    return (
        f"[quantresearch_repo] source not found. Clone the repo and set {ENV_VAR}:\n"
        f"    git clone {REPO_URL} {target}\n"
        f"    export {ENV_VAR}={target}\n"
        "Skipping this job (0 chunks)."
    )


def build_chunks(root: Path, *, limit: int | None = None) -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in _SUPPORTED:
            continue
        try:
            chunks.extend(_chunks_for_file(path, root))
        except Exception as exc:  # a single unreadable/corrupt file must not abort the job
            _warn(f"skipping {path} ({exc})")
        if limit and len(chunks) >= limit:
            return chunks[:limit]
    return chunks


def collect_chunks(*, path: str | None = None, limit: int | None = None) -> list[KnowledgeChunk]:
    root = source_root(path)
    if root is None:
        print(setup_message(path), file=sys.stderr)
        return []
    return build_chunks(root, limit=limit)


def ingest(*, path: str | None = None, limit: int | None = None, upsert: bool = True) -> int:
    from .common import upsert_chunks

    chunks = collect_chunks(path=path, limit=limit)
    return upsert_chunks(chunks) if upsert else len(chunks)


def _chunks_for_file(path: Path, root: Path) -> list[KnowledgeChunk]:
    rel = path.relative_to(root)
    citation = f"letianzj/QuantResearch: {rel}"
    base_tags = ["quantresearch", *_path_tags(path)]
    base_meta = {
        "provider": "quantresearch_repo",
        "title": path.stem,
        "source_path": str(rel),
        "citation": citation,
    }

    suffix = path.suffix.lower()
    if suffix == ".ipynb":
        # infer extra tags from the notebook text too
        tags = sorted(set(base_tags) | set(infer_tags(path.read_text(encoding="utf-8", errors="ignore"), TOPIC_VOCAB)))
        return notebook_cell_chunks(path, corpus="repo", tags=tags, citation=str(rel), metadata=base_meta)

    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.strip():
        return []
    language = "python" if suffix == ".py" else "markdown"
    source_type = "code" if suffix == ".py" else "explanation"
    tags = sorted(set(base_tags) | set(infer_tags(f"{path}\n{text}", TOPIC_VOCAB)))
    return chunk_text(
        text,
        corpus="repo",
        source=str(path),
        citation=citation,
        tags=tags,
        metadata={**base_meta, "language": language, "source_type": source_type},
    )


def _path_tags(path: Path) -> list[str]:
    return infer_tags(str(path), TOPIC_VOCAB)


def _warn(message: str) -> None:
    print(f"[quantresearch_repo] WARNING: {message}", file=sys.stderr)
