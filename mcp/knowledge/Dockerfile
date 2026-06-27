FROM python:3.11-slim
WORKDIR /app
RUN pip install uv
COPY pyproject.toml .
RUN uv lock && uv sync --frozen
COPY src/ src/
ENV MCP_TRANSPORT=streamable-http
CMD ["uv", "run", "src/server.py"]
