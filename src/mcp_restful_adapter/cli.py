"""CLI entry point for mcp-restful-adapter."""

from __future__ import annotations

import asyncio
import json
import os
import sys

from mcp_restful_adapter.logging import setup_logging


def main() -> None:
    """Entry point: fetch spec, convert if needed, build and run MCP server."""

    logger = setup_logging()

    # 1. Read environment variables
    spec_url = os.environ.get("API_SPEC_URL")
    if not spec_url:
        logger.error("API_SPEC_URL environment variable is required.")
        sys.exit(1)

    base_url = os.environ.get("API_BASE_URL")
    if not base_url:
        logger.error("API_BASE_URL environment variable is required.")
        sys.exit(1)

    tags_str = os.environ.get("API_TAGS")
    methods_str = os.environ.get("API_METHODS")
    paths_pattern = os.environ.get("API_PATHS")
    exclude_paths_pattern = os.environ.get("API_PATHS_EXCLUDE")
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
                logger.error("API_HEADERS must be a JSON object.")
                sys.exit(1)
        except json.JSONDecodeError as e:
            logger.error("API_HEADERS is not valid JSON: %s", e)
            sys.exit(1)

    # 2. Fetch the spec
    from mcp_restful_adapter.spec_fetcher import fetch_spec

    logger.info("Fetching spec from %s...", spec_url)
    try:
        spec = asyncio.run(fetch_spec(spec_url))
    except Exception as e:
        logger.error("Failed to fetch spec: %s", e)
        sys.exit(1)
    logger.info("Spec loaded: %s", spec.get("info", {}).get("title", "Unknown"))

    # 3. Convert Swagger 2.0 → OpenAPI 3.0 if needed
    from mcp_restful_adapter.spec_converter import (
        convert_swagger_to_openapi,
        is_swagger_2,
    )

    if is_swagger_2(spec):
        logger.info("Detected Swagger 2.0, converting to OpenAPI 3.0...")
        spec = convert_swagger_to_openapi(spec)

    # 4. Build and run the MCP server (filtering via RouteMap inside)
    from mcp_restful_adapter.server import build_server

    server_name = spec.get("info", {}).get("title", "RESTful API Server")
    logger.info(
        "Filters: tags=%s, methods=%s, paths=%s, exclude_paths=%s",
        tags or "all",
        methods or "all",
        paths_pattern or "all",
        exclude_paths_pattern or "none",
    )

    try:
        mcp = build_server(
            spec,
            base_url=base_url,
            name=server_name,
            tags=tags,
            methods=methods,
            paths=paths_pattern,
            exclude_paths=exclude_paths_pattern,
            extra_headers=extra_headers,
        )
    except Exception as e:
        logger.error("Failed to build MCP server: %s", e)
        sys.exit(1)

    # Transport configuration
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))

    logger.info("Starting MCP server: %s (transport=%s)", server_name, transport)

    if transport == "stdio":
        mcp.run(transport="stdio", show_banner=False)
    else:
        mcp.run(
            transport=transport,
            host=host,
            port=port,
            show_banner=False,
        )
