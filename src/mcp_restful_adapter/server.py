"""Build and run the MCP server from an OpenAPI specification."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from fastmcp import FastMCP
from fastmcp.server.providers.openapi.routing import MCPType, RouteMap
from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp_restful_adapter._version import __version__ as _version
from mcp_restful_adapter.logging import LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)


async def inject_auth(request: httpx.Request):
    """Forward the MCP client's Authorization header to the backend API.

    fastmcp strips the Authorization header from incoming MCP requests by
    default. This hook reads it from the current HTTP context and injects
    it into the outgoing httpx request. Only active for HTTP transports.
    """
    from fastmcp.server.context import _current_transport
    from fastmcp.server.dependencies import get_http_request

    if _current_transport.get() == "stdio":
        return

    mcp_request = get_http_request()
    auth = mcp_request.headers.get("authorization")
    if auth and "authorization" not in request.headers:
        request.headers["authorization"] = auth


async def log_request(request: httpx.Request):
    """Log outgoing HTTP request details."""
    body = (
        request.content.decode("utf-8", errors="replace")
        if request.content
        else "(no body)"
    )
    logger.info(
        "[REQUEST] %s %s\n  Headers: %s\n  Body: %s",
        request.method,
        request.url,
        dict(request.headers),
        body,
    )


async def log_response(response: httpx.Response):
    """Log incoming HTTP response details."""
    # Read body if not already consumed
    try:
        await response.aread()
    except Exception:
        pass
    body = (
        response.content.decode("utf-8", errors="replace")
        if response.content
        else "(no body)"
    )
    logger.info(
        "[RESPONSE] %s %s\n  Status: %d\n  Body: %s",
        response.request.method if response.request else "?",
        response.url,
        response.status_code,
        body,
    )


def build_server(
    spec: dict[str, Any],
    base_url: str | None = None,
    name: str = "RESTful API Server",
    tags: set[str] | None = None,
    methods: set[str] | None = None,
    paths: str | None = None,
    exclude_paths: str | None = None,
    extra_headers: dict[str, str] | None = None,
) -> FastMCP:
    """Build a FastMCP server from an OpenAPI specification.

    Args:
        spec: The OpenAPI 3.x specification dict.
        base_url: Base URL for the API.
        name: Name for the MCP server.
        tags: Set of tag names to include (OR logic — match ANY).
        methods: Set of HTTP methods to include (case-insensitive).
        paths: Regex pattern to match against path strings (whitelist).
        exclude_paths: Regex pattern to exclude paths (blacklist).
            Only checked when whitelist does not match (whitelist-first).
        extra_headers: Custom headers to include in every request
            (e.g. ``{"Authorization": "Bearer xxx", "X-Tenant": "acme"}``).

    Returns:
        A configured FastMCP server instance.
    """
    headers: dict[str, str] = {
        "X-Requested-From": f"MCP/{_version}",
    }
    if extra_headers:
        headers.update(extra_headers)

    # Build httpx client
    client_kwargs: dict[str, Any] = {
        "headers": headers,
        "timeout": 30.0,
        "follow_redirects": True,
        "event_hooks": {
            "request": [inject_auth, log_request],
            "response": [log_response],
        },
    }
    if base_url:
        client_kwargs["base_url"] = base_url

    client = httpx.AsyncClient(**client_kwargs)

    # Build RouteMaps for filtering
    route_maps = _build_route_maps(tags, methods, paths, exclude_paths)

    # Create MCP server from OpenAPI spec
    mcp = FastMCP.from_openapi(
        openapi_spec=spec,
        client=client,
        name=name,
        route_maps=route_maps,
        validate_output=False,
    )

    # Health check endpoint (only useful for HTTP transports)
    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "version": _version,
            }
        )

    return mcp


def _build_route_maps(
    tags: set[str] | None,
    methods: set[str] | None,
    paths: str | None,
    exclude_paths: str | None = None,
) -> list[RouteMap]:
    """Build RouteMap list for filtering endpoints.

    Strategy (whitelist-first):
    1. Whitelist match → TOOL (skip blacklist).
    2. Blacklist match → EXCLUDE.
    3. No whitelist → default TOOL (blacklist-only mode).
    4. Catch-all → EXCLUDE.
    """
    route_maps: list[RouteMap] = []

    # Normalize methods to uppercase list, or "*" for all
    allowed_methods: list[str] | str = "*"
    if methods:
        allowed_methods = [m.upper() for m in methods]

    # 1. Whitelist: highest priority — match → TOOL
    if paths:
        if tags:
            for tag in tags:
                route_maps.append(
                    RouteMap(
                        methods=allowed_methods,
                        pattern=paths,
                        tags={tag},
                        mcp_type=MCPType.TOOL,
                    )
                )
        else:
            route_maps.append(
                RouteMap(
                    methods=allowed_methods,
                    pattern=paths,
                    mcp_type=MCPType.TOOL,
                )
            )

    # 2. Blacklist: exclude matched paths (only reached if whitelist didn't match)
    if exclude_paths:
        route_maps.append(
            RouteMap(
                methods=allowed_methods,
                pattern=exclude_paths,
                mcp_type=MCPType.EXCLUDE,
            )
        )

    # 3. No whitelist: accept everything (blacklist-only mode)
    if not paths:
        if tags:
            for tag in tags:
                route_maps.append(
                    RouteMap(
                        methods=allowed_methods,
                        tags={tag},
                        mcp_type=MCPType.TOOL,
                    )
                )
        else:
            route_maps.append(
                RouteMap(
                    methods=allowed_methods,
                    mcp_type=MCPType.TOOL,
                )
            )

    # 4. Catch-all: exclude everything not matched above
    route_maps.append(RouteMap(mcp_type=MCPType.EXCLUDE))

    return route_maps
