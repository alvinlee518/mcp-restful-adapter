FROM docker.m.daocloud.io/library/python:3.11-slim-bullseye

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ src/

# Install dependencies (no dev deps)
RUN uv sync --no-dev

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# Default: streamable-http mode
ENV MCP_TRANSPORT=streamable-http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

ENTRYPOINT ["uv", "run", "mcp-restful-adapter"]
