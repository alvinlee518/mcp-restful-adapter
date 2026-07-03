"""Tests for server — building MCP server from OpenAPI specs."""

from __future__ import annotations

import asyncio

import httpx
import pytest
from fastmcp import Client, FastMCP

from mcp_restful_adapter.server import build_server, _build_route_maps


@pytest.fixture
def sample_openapi_spec() -> dict:
    return {
        "openapi": "3.0.3",
        "info": {"title": "Test API", "version": "1.0"},
        "servers": [{"url": "https://api.example.com"}],
        "paths": {
            "/users": {
                "get": {
                    "tags": ["user"],
                    "operationId": "listUsers",
                    "summary": "List users",
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {"type": "integer"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "name": {"type": "string"},
                                            },
                                        },
                                    }
                                }
                            },
                        }
                    },
                },
                "post": {
                    "tags": ["user", "admin"],
                    "operationId": "createUser",
                    "summary": "Create user",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["name"],
                                    "properties": {
                                        "name": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {"201": {"description": "Created"}},
                },
            },
            "/products": {
                "get": {
                    "tags": ["product"],
                    "operationId": "listProducts",
                    "summary": "List products",
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"items": {"type": "array"}},
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/health": {
                "get": {
                    "operationId": "healthCheck",
                    "summary": "Health check",
                    "responses": {"200": {"description": "OK"}},
                },
            },
        },
    }


class TestBuildServer:
    def test_returns_fastmcp_instance(self, sample_openapi_spec):
        server = build_server(sample_openapi_spec)
        assert isinstance(server, FastMCP)

    def test_custom_name(self, sample_openapi_spec):
        server = build_server(sample_openapi_spec, name="My Server")
        assert server.name == "My Server"

    def test_with_base_url(self, sample_openapi_spec):
        server = build_server(
            sample_openapi_spec, base_url="https://custom.example.com"
        )
        assert isinstance(server, FastMCP)

    def test_with_token(self, sample_openapi_spec):
        server = build_server(
            sample_openapi_spec,
            extra_headers={"Authorization": "Bearer my-secret-token"},
        )
        assert isinstance(server, FastMCP)

    def test_with_extra_headers(self, sample_openapi_spec):
        server = build_server(
            sample_openapi_spec,
            extra_headers={"X-Custom": "value", "X-Tenant": "acme"},
        )
        assert isinstance(server, FastMCP)

    def test_extra_headers_empty(self, sample_openapi_spec):
        server = build_server(sample_openapi_spec, extra_headers={})
        assert isinstance(server, FastMCP)

    def test_extra_headers_none(self, sample_openapi_spec):
        server = build_server(sample_openapi_spec, extra_headers=None)
        assert isinstance(server, FastMCP)


class TestBuildServerEdgeCases:
    def test_empty_paths(self):
        spec = {
            "openapi": "3.0.3",
            "info": {"title": "Empty", "version": "1.0"},
            "paths": {},
        }
        server = build_server(spec)
        assert isinstance(server, FastMCP)

    def test_no_servers_in_spec(self):
        spec = {
            "openapi": "3.0.3",
            "info": {"title": "No Server", "version": "1.0"},
            "paths": {
                "/test": {
                    "get": {
                        "operationId": "test",
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        server = build_server(spec, base_url="https://fallback.example.com")
        assert isinstance(server, FastMCP)


# ---------------------------------------------------------------------------
# RouteMap filtering tests
# ---------------------------------------------------------------------------


class TestRouteMapFiltering:
    """Test that RouteMap-based filtering correctly includes/excludes tools."""

    def _get_tool_names(self, server: FastMCP) -> set[str]:
        """Get all tool names from the server via an in-memory client."""

        async def _list():
            client = Client(server)
            async with client:
                tools = await client.list_tools()
                return {t.name for t in tools}

        return asyncio.run(_list())

    def test_no_filters_includes_all(self, sample_openapi_spec):
        server = build_server(sample_openapi_spec)
        tools = self._get_tool_names(server)
        assert tools == {"listUsers", "createUser", "listProducts", "healthCheck"}

    def test_filter_by_tag(self, sample_openapi_spec):
        server = build_server(sample_openapi_spec, tags={"user"})
        tools = self._get_tool_names(server)
        # "user" tag: listUsers (user), createUser (user,admin)
        # NOT: listProducts (product), healthCheck (no tags)
        assert tools == {"listUsers", "createUser"}

    def test_filter_by_multiple_tags_or_logic(self, sample_openapi_spec):
        server = build_server(sample_openapi_spec, tags={"user", "product"})
        tools = self._get_tool_names(server)
        # user OR product
        assert tools == {"listUsers", "createUser", "listProducts"}

    def test_filter_by_method(self, sample_openapi_spec):
        server = build_server(sample_openapi_spec, methods={"GET"})
        tools = self._get_tool_names(server)
        # Only GET operations
        assert tools == {"listUsers", "listProducts", "healthCheck"}

    def test_filter_by_method_post_only(self, sample_openapi_spec):
        server = build_server(sample_openapi_spec, methods={"POST"})
        tools = self._get_tool_names(server)
        assert tools == {"createUser"}

    def test_filter_by_tag_and_method(self, sample_openapi_spec):
        server = build_server(
            sample_openapi_spec, tags={"user"}, methods={"GET"}
        )
        tools = self._get_tool_names(server)
        # tag=user AND method=GET → only listUsers
        assert tools == {"listUsers"}

    def test_filter_by_path_regex(self, sample_openapi_spec):
        server = build_server(sample_openapi_spec, paths=r"^/users")
        tools = self._get_tool_names(server)
        assert tools == {"listUsers", "createUser"}

    def test_filter_excludes_all(self, sample_openapi_spec):
        server = build_server(sample_openapi_spec, tags={"nonexistent"})
        tools = self._get_tool_names(server)
        assert tools == set()

    def test_filter_method_and_path(self, sample_openapi_spec):
        server = build_server(
            sample_openapi_spec, methods={"GET"}, paths=r"/health"
        )
        tools = self._get_tool_names(server)
        assert tools == {"healthCheck"}

    def test_tag_filter_excludes_untagged(self, sample_openapi_spec):
        """Operations without tags are excluded when tag filter is active."""
        server = build_server(sample_openapi_spec, tags={"product"})
        tools = self._get_tool_names(server)
        # healthCheck has no tags → excluded
        assert "healthCheck" not in tools
        assert tools == {"listProducts"}


class TestBuildRouteMaps:
    """Unit tests for _build_route_maps helper."""

    def test_no_filters(self):
        maps = _build_route_maps(None, None, None)
        assert len(maps) == 2  # catch-all TOOL + EXCLUDE
        from fastmcp.server.providers.openapi.routing import MCPType

        assert maps[0].mcp_type == MCPType.TOOL
        assert maps[1].mcp_type == MCPType.EXCLUDE

    def test_single_tag(self):
        from fastmcp.server.providers.openapi.routing import MCPType

        maps = _build_route_maps({"user"}, None, None)
        assert len(maps) == 2  # one tag rule + EXCLUDE
        assert maps[0].tags == {"user"}
        assert maps[0].mcp_type == MCPType.TOOL
        assert maps[1].mcp_type == MCPType.EXCLUDE

    def test_multiple_tags(self):
        from fastmcp.server.providers.openapi.routing import MCPType

        maps = _build_route_maps({"user", "product"}, None, None)
        assert len(maps) == 3  # two tag rules + EXCLUDE
        tags = {frozenset(m.tags) for m in maps[:-1]}
        assert frozenset({"user"}) in tags
        assert frozenset({"product"}) in tags
        assert maps[-1].mcp_type == MCPType.EXCLUDE

    def test_methods(self):
        maps = _build_route_maps(None, {"GET", "POST"}, None)
        assert set(maps[0].methods) == {"GET", "POST"}

    def test_paths(self):
        maps = _build_route_maps(None, None, r"^/api/")
        assert maps[0].pattern == r"^/api/"


# ---------------------------------------------------------------------------
# Whitelist + Blacklist tests
# ---------------------------------------------------------------------------


class TestWhitelistBlacklist:
    """Test whitelist-first strategy with API_PATHS + API_PATHS_EXCLUDE."""

    def _get_tool_names(self, server: FastMCP) -> set[str]:
        async def _list():
            client = Client(server)
            async with client:
                tools = await client.list_tools()
                return {t.name for t in tools}

        return asyncio.run(_list())

    def test_whitelist_only(self, sample_openapi_spec):
        """Whitelist matches → included, non-matches → excluded."""
        server = build_server(sample_openapi_spec, paths=r"/users")
        tools = self._get_tool_names(server)
        assert tools == {"listUsers", "createUser"}

    def test_blacklist_only(self, sample_openapi_spec):
        """No whitelist + blacklist → exclude matched, keep rest."""
        server = build_server(sample_openapi_spec, exclude_paths=r"/health")
        tools = self._get_tool_names(server)
        assert tools == {"listUsers", "createUser", "listProducts"}

    def test_whitelist_priority_over_blacklist(self, sample_openapi_spec):
        """Path matching both whitelist and blacklist → included (whitelist wins)."""
        server = build_server(
            sample_openapi_spec,
            paths=r"/users",
            exclude_paths=r"/users",
        )
        tools = self._get_tool_names(server)
        assert tools == {"listUsers", "createUser"}

    def test_whitelist_then_blacklist(self, sample_openapi_spec):
        """Whitelist misses → blacklist catches → excluded."""
        server = build_server(
            sample_openapi_spec,
            paths=r"/health",
            exclude_paths=r"health",
        )
        tools = self._get_tool_names(server)
        # whitelist matches /health → TOOL, but blacklist also matches
        # Since whitelist is checked first and matches, /health is INCLUDED
        assert tools == {"healthCheck"}

    def test_blacklist_excludes_unmatched_by_whitelist(self, sample_openapi_spec):
        """Whitelist doesn't match → blacklist excludes the rest."""
        server = build_server(
            sample_openapi_spec,
            paths=r"/health",
            exclude_paths=r"/users",
        )
        tools = self._get_tool_names(server)
        # /health matches whitelist → TOOL
        # /users doesn't match whitelist → check blacklist → matches → EXCLUDE
        # /products doesn't match whitelist → check blacklist → no match → EXCLUDE (catch-all)
        assert tools == {"healthCheck"}

    def test_blacklist_with_method_filter(self, sample_openapi_spec):
        """Blacklist + method filter work together."""
        server = build_server(
            sample_openapi_spec,
            methods={"GET"},
            exclude_paths=r"/health",
        )
        tools = self._get_tool_names(server)
        assert tools == {"listUsers", "listProducts"}

    def test_build_route_maps_whitelist_blacklist(self):
        """Verify RouteMap ordering for whitelist-first strategy."""
        from fastmcp.server.providers.openapi.routing import MCPType

        maps = _build_route_maps(
            None, None, r"/include", r"/exclude"
        )
        # Expected: [whitelist TOOL, blacklist EXCLUDE, catch-all EXCLUDE]
        assert len(maps) == 3
        assert maps[0].mcp_type == MCPType.TOOL
        assert maps[0].pattern == r"/include"
        assert maps[1].mcp_type == MCPType.EXCLUDE
        assert maps[1].pattern == r"/exclude"
        assert maps[2].mcp_type == MCPType.EXCLUDE

    def test_build_route_maps_blacklist_only(self):
        """No whitelist → default TOOL + blacklist EXCLUDE + catch-all."""
        from fastmcp.server.providers.openapi.routing import MCPType

        maps = _build_route_maps(None, None, None, r"/exclude")
        # Expected: [blacklist EXCLUDE, default TOOL, catch-all EXCLUDE]
        assert len(maps) == 3
        assert maps[0].mcp_type == MCPType.EXCLUDE
        assert maps[0].pattern == r"/exclude"
        assert maps[1].mcp_type == MCPType.TOOL
        assert maps[2].mcp_type == MCPType.EXCLUDE
