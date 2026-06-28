FROM python:3.11-slim
WORKDIR /app
RUN pip install uv
COPY mcp/knowledge/pyproject.toml .
RUN uv lock && uv sync --frozen
COPY mcp/knowledge/src/ src/
COPY knowledge/ knowledge/
COPY contract/ contract/
COPY docs/04-quantconnect.md docs/04-quantconnect.md
COPY docs/07-iteration-rubric.md docs/07-iteration-rubric.md
COPY docs/08-antibias-guardrails.md docs/08-antibias-guardrails.md
COPY docs/11-authoring-contract.md docs/11-authoring-contract.md
ENV MCP_TRANSPORT=streamable-http
CMD ["uv", "run", "src/server.py"]
