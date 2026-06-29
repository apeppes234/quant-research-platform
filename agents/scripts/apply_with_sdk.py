"""Create Managed Agents control-plane resources via the Anthropic Python SDK.

This is a fallback for environments where the `ant` CLI is not installed. It
accepts already-rendered YAML and prints only the created resource id so
agents/scripts/apply.sh can keep its existing deterministic ID/SHA flow.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from anthropic import Anthropic

BETA_HEADER = ["managed-agents-2026-04-01"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=("agent", "environment"))
    parser.add_argument("yaml_path", type=Path)
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Missing required env var: ANTHROPIC_API_KEY", file=sys.stderr)
        return 2

    payload = yaml.safe_load(args.yaml_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        print(f"{args.yaml_path} did not parse to a YAML object", file=sys.stderr)
        return 2

    client = Anthropic(api_key=api_key)
    if args.kind == "environment":
        response = client.beta.environments.create(
            **_only_keys(payload, "name", "description", "config", "metadata", "scope"),
            betas=BETA_HEADER,
        )
    else:
        response = client.beta.agents.create(
            **_only_keys(
                payload,
                "name",
                "model",
                "description",
                "system",
                "tools",
                "mcp_servers",
                "skills",
                "multiagent",
                "metadata",
            ),
            betas=BETA_HEADER,
        )

    print(_get_id(response))
    return 0


def _only_keys(payload: dict[str, Any], *keys: str) -> dict[str, Any]:
    return {key: payload[key] for key in keys if key in payload and payload[key] is not None}


def _get_id(response: Any) -> str:
    if isinstance(response, dict) and response.get("id"):
        return str(response["id"])
    value = getattr(response, "id", None)
    if value:
        return str(value)
    raise RuntimeError("Anthropic SDK response did not include an id")


if __name__ == "__main__":
    raise SystemExit(main())
