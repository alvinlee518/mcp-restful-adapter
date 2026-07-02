"""CLI entry point for mcp-restful-adapter."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from mcp_restful_adapter.logging import setup_logging


def main() -> None:
    """Entry point: fetch spec, convert if needed, build and run MCP server."""

    setup_logging()

    # 1. Read environment variables
    spec_url = os.environ.get("API_SPEC_URL")
    if not spec_url:
        print("Error: API_SPEC_URL environment variable is required.", file=sys.stderr)
        sys.exit(1)

    base_url = os.environ.get("API_BASE_URL")
    if not base_url:
        print("Error: API_BASE_URL environment variable is required.", file=sys.stderr)
        sys.exit(1)

    tags_str = os.environ.get("API_TAGS")
    methods_str = os.environ.get("API_METHODS")
    paths_pattern = os.environ.get("API_PATHS")
    headers_str = os.environ.get("API_HEADERS")

    # Parse filter values
    tags = {t.strip() for t in tags_str.split(",") if t.strip()} if tags_str else None
    methods = (
        {m.strip().upper() for m in methods_str.split(",") if m.strip()}
        if methods_str
        else None
    )

    # Parse custom headers (JSON format)
    extra_headers = None
    if headers_str:
        try:
            extra_headers = json.loads(headers_str)
            if not isinstance(extra_headers, dict):
                print("Error: API_HEADERS must be a JSON object.", file=sys.stderr)
                sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: API_HEADERS is not valid JSON: {e}", file=sys.stderr)
            sys.exit(1)

    # 2. Fetch the spec
    from mcp_restful_adapter.spec_fetcher import fetch_spec

    print(f"Fetching spec from {spec_url}...", file=sys.stderr)
    try:
        spec = asyncio.run(fetch_spec(spec_url))
    except Exception as e:
        print(f"Error: Failed to fetch spec: {e}", file=sys.stderr)
        sys.exit(1)
    print(
        f"Spec loaded: {spec.get('info', {}).get('title', 'Unknown')}", file=sys.stderr
    )

    # 3. Convert Swagger 2.0 → OpenAPI 3.0 if needed
    from mcp_restful_adapter.spec_converter import (
        convert_swagger_to_openapi,
        is_swagger_2,
    )

    if is_swagger_2(spec):
        print("Detected Swagger 2.0, converting to OpenAPI 3.0...", file=sys.stderr)
        spec = convert_swagger_to_openapi(spec)

    # 4. Build and run the MCP server (filtering via RouteMap inside)
    from mcp_restful_adapter.server import build_server

    server_name = spec.get("info", {}).get("title", "RESTful API Server")
    print(
        f"Filters: tags={tags or 'all'}, methods={methods or 'all'}, "
        f"paths={paths_pattern or 'all'}",
        file=sys.stderr,
    )

    try:
        mcp = build_server(
            spec,
            base_url=base_url,
            name=server_name,
            tags=tags,
            methods=methods,
            paths=paths_pattern,
            extra_headers=extra_headers,
        )
    except Exception as e:
        print(f"Error: Failed to build MCP server: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Starting MCP server: {server_name}", file=sys.stderr)
    mcp.run(transport="stdio", show_banner=False)
