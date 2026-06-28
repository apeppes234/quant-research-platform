FROM python:3.11-slim
WORKDIR /app
RUN pip install uv
COPY mcp/data-sources/shared/pyproject.toml .
RUN uv lock && uv sync --frozen
COPY mcp/data-sources/shared/src/ src/
ENV MCP_TRANSPORT=streamable-http
ENV DATASOURCE_NAME=all
CMD ["uv", "run", "src/server.py"]
