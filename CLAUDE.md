# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP RESTful Adapter converts RESTful APIs (Swagger 2.0 / OpenAPI 3.0 specs) into MCP Servers. It leverages **fastmcp's built-in `FastMCP.from_openapi()`** for spec parsing, tool creation, schema conversion, and HTTP proxying — this project is a thin config/adapter layer on top.

## Build & Run

```bash
uv sync                           # Install dependencies
uv run mcp-restful-adapter        # Run the CLI entry point
uv run pytest tests/ -v           # Run unit tests
uv run pytest tests/ --cov=mcp_restful_adapter  # Run with coverage
```

## Architecture

```
src/mcp_restful_adapter/
  __init__.py          # Package init — exports __version__
  _version.py          # Version string
  cli.py               # main() — reads env vars, orchestrates the pipeline
  spec_fetcher.py      # async fetch + JSON/YAML parse
  spec_converter.py    # Swagger 2.0 → OpenAPI 3.0 dict transformation (manual, no extra deps)
  server.py            # Build httpx.AsyncClient + RouteMap filtering + FastMCP.from_openapi()
```

**Pipeline flow**: fetch spec → detect version → convert if Swagger 2.0 → `FastMCP.from_openapi(spec, client, route_maps)` → `server.run(transport="stdio", show_banner=False)`

Key design decisions:
- **Filtering via fastmcp `RouteMap`** — each tag gets one `MCPType.TOOL` rule (OR logic), final `MCPType.EXCLUDE` drops unmatched routes
- **`show_banner=False` is mandatory** — stdio transport uses JSON-RPC; any banner text corrupts the protocol
- **httpx.AsyncClient** is passed to `from_openapi()` with `X-Requested-From` + `Authorization: Bearer` headers and optional `base_url`
- **Swagger 2.0 converter** handles: servers, definitions→components, body params→requestBody, inline types→schema, `$ref` rewriting (including Springfox Java types), collectionFormat→style/explode, securityDefinitions, OAuth2 flows, multiple consumes/produces content types
- **`API_SPEC_URL` and `API_BASE_URL` are required** env vars; `API_METHODS` defaults to all methods

## Dependencies

- `fastmcp` (>=3.4.2) — MCP server framework with `FastMCP.from_openapi()` built-in
- `httpx` (>=0.28.1) — async HTTP for fetching specs and proxying API calls
- `pyyaml` (>=6.0) — YAML spec parsing fallback
- Build backend: `uv_build` (not setuptools)
