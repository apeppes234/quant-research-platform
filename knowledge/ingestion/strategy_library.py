"""Ingest a locally cloned QuantConnect Strategy Library -> corpus 'strategy_library'. docs/06.

Local reference material only: clone QuantConnect's Tutorials repo (or any folder of QC strategy
examples) and point STRATEGY_LIBRARY_PATH at the strategy directory. The job never downloads anything.

These are **implementation patterns**, not validated or profitable strategies — metadata records that
explicitly. They ground the Modeling agent in QC-idiomatic structure (alpha/portfolio/execution models,
universe selection); profitability is only ever established later by the backtest/risk workflow.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .common import KnowledgeChunk, chunk_text, infer_tags, notebook_cell_chunks

REPO_URL = "https://github.com/QuantConnect/Tutorials"
ENV_VARS = ("STRATEGY_LIBRARY_PATH", "QUANTCONNECT_STRATEGY_LIBRARY_PATH", "QC_STRATEGY_LIBRARY_PATH")

DISCLAIMER = "implementation pattern only; not a validated or profitable strategy"

# Canonical tag -> substrings matched against the file path AND the chunk text.
TOPIC_VOCAB: dict[str, tuple[str, ...]] = {
    "momentum": ("momentum", "trend"),
    "mean-reversion": ("mean revers", "mean-revers", "reversion", "contrarian"),
    "pairs-trading": ("pairs", "pair trad", "statistical arbitrage"),
    "factor": ("factor", "fundamental", "value", "quality"),
    "options": ("option", "straddle", "iron condor", "covered call", "put", "call"),
    "futures": ("future", "continuous contract", "roll"),
    "crypto": ("crypto", "bitcoin", "ethereum"),
    "universe-selection": ("universe", "coarse", "fine", "selection"),
    "risk-management": ("risk management", "riskmanagement", "stop loss", "trailing", "maximum drawdown"),
    "portfolio-construction": ("portfolio construction", "portfolioconstruction", "equal weight", "optimization"),
    "alpha-model": ("alpha model", "alphamodel", "insight"),
    "execution-model": ("execution model", "executionmodel", "execution"),
}

_LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".cs": "csharp",
    ".md": "markdown",
    ".txt": "text",
    ".ipynb": "python",
}
_CODE_SUFFIXES = {".py", ".cs"}
_DOC_SUFFIXES = {".md", ".txt"}


def source_root(path: str | None = None) -> Path | None:
    configured = path or _env_path()
    if not configured:
        return None
    root = Path(configured).expanduser()
    return root if root.is_dir() else None


def setup_message(path: str | None = None) -> str:
    target = path or _env_path() or "/path/to/Tutorials/04 Strategy Library"
    return (
        "[strategy_library] source not found. Clone QuantConnect's examples and set "
        f"STRATEGY_LIBRARY_PATH:\n"
        f"    git clone {REPO_URL} /path/to/Tutorials\n"
        f"    export STRATEGY_LIBRARY_PATH='{target}'\n"
        "Confirm QuantConnect's licensing terms before redistributing ingested text (docs/14 O7).\n"
        "Skipping this job (0 chunks)."
    )


def build_chunks(root: Path, *, limit: int | None = None) -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in _LANGUAGE_BY_SUFFIX:
            continue
        try:
            chunks.extend(_chunks_for_file(path, root))
        except Exception as exc:  # one bad file must not abort the job
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
    suffix = path.suffix.lower()
    language = _LANGUAGE_BY_SUFFIX[suffix]
    strategy_name = rel.parts[0] if len(rel.parts) > 1 else path.stem
    citation = f"QuantConnect Strategy Library: {rel}"
    source_type = "code" if suffix in _CODE_SUFFIXES else "explanation" if suffix in _DOC_SUFFIXES else "notebook"

    base_meta = {
        "provider": "quantconnect_strategy_library",
        "title": strategy_name,
        "source_path": str(rel),
        "language": language,
        "strategy_family": _strategy_family(path),
        "citation": citation,
        "disclaimer": DISCLAIMER,
    }
    base_tags = ["quantconnect", "strategy-library", *_path_tags(path)]

    if suffix == ".ipynb":
        tags = sorted(set(base_tags) | set(infer_tags(path.read_text(encoding="utf-8", errors="ignore"), TOPIC_VOCAB)))
        return notebook_cell_chunks(path, corpus="strategy_library", tags=tags, citation=str(rel), metadata=base_meta)

    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.strip():
        return []
    tags = sorted(set(base_tags) | set(infer_tags(f"{path}\n{text}", TOPIC_VOCAB)))
    return chunk_text(
        text,
        corpus="strategy_library",
        source=str(path),
        citation=citation,
        tags=tags,
        metadata={**base_meta, "source_type": source_type},
    )


def _strategy_family(path: Path) -> str | None:
    families = _path_tags(path)
    for family in ("momentum", "mean-reversion", "pairs-trading", "factor", "options", "futures", "crypto"):
        if family in families:
            return family
    return None


def _path_tags(path: Path) -> list[str]:
    return infer_tags(str(path), TOPIC_VOCAB)


def _env_path() -> str:
    for var in ENV_VARS:
        value = os.getenv(var, "")
        if value:
            return value
    return ""


def _warn(message: str) -> None:
    print(f"[strategy_library] WARNING: {message}", file=sys.stderr)
