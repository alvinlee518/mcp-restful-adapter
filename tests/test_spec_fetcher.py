"""Tests for spec_fetcher — fetching and parsing API specifications."""

from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio

from mcp_restful_adapter.spec_fetcher import fetch_spec


# ---------------------------------------------------------------------------
# Helpers — mock httpx transport
# ---------------------------------------------------------------------------


class MockTransport(httpx.MockTransport):
    """Convenience wrapper for creating mock transports."""

    @staticmethod
    def json_response(data: dict, content_type: str = "application/json") -> httpx.Response:
        return httpx.Response(
            200,
            json=data,
            headers={"content-type": content_type},
        )

    @staticmethod
    def text_response(text: str, content_type: str = "text/plain") -> httpx.Response:
        return httpx.Response(
            200,
            text=text,
            headers={"content-type": content_type},
        )


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------


class TestFetchSpecJSON:
    @pytest.mark.asyncio
    async def test_fetch_json_spec(self):
        spec_data = {"openapi": "3.0.3", "info": {"title": "Test", "version": "1.0"}}
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json=spec_data)
        )
        # Monkey-patch httpx.AsyncClient to use mock transport
        original_init = httpx.AsyncClient.__init__

        def patched_init(self, *args, **kwargs):
            kwargs["transport"] = transport
            original_init(self, *args, **kwargs)

        httpx.AsyncClient.__init__ = patched_init
        try:
            result = await fetch_spec("https://example.com/openapi.json")
            assert result == spec_data
        finally:
            httpx.AsyncClient.__init__ = original_init

    @pytest.mark.asyncio
    async def test_fetch_json_by_content_type(self):
        spec_data = {"openapi": "3.0.3", "info": {"title": "Test", "version": "1.0"}}
        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                text=json.dumps(spec_data),
                headers={"content-type": "application/json; charset=utf-8"},
            )
        )
        original_init = httpx.AsyncClient.__init__

        def patched_init(self, *args, **kwargs):
            kwargs["transport"] = transport
            original_init(self, *args, **kwargs)

        httpx.AsyncClient.__init__ = patched_init
        try:
            result = await fetch_spec("https://example.com/spec")
            assert result == spec_data
        finally:
            httpx.AsyncClient.__init__ = original_init


# ---------------------------------------------------------------------------
# YAML parsing
# ---------------------------------------------------------------------------


class TestFetchSpecYAML:
    @pytest.mark.asyncio
    async def test_fetch_yaml_spec(self):
        yaml_text = """
openapi: "3.0.3"
info:
  title: Test
  version: "1.0"
paths: {}
"""
        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                text=yaml_text,
                headers={"content-type": "text/yaml"},
            )
        )
        original_init = httpx.AsyncClient.__init__

        def patched_init(self, *args, **kwargs):
            kwargs["transport"] = transport
            original_init(self, *args, **kwargs)

        httpx.AsyncClient.__init__ = patched_init
        try:
            result = await fetch_spec("https://example.com/openapi.yaml")
            assert result["openapi"] == "3.0.3"
            assert result["info"]["title"] == "Test"
        finally:
            httpx.AsyncClient.__init__ = original_init


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestFetchSpecErrors:
    @pytest.mark.asyncio
    async def test_http_error_raises(self):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(404, text="Not Found")
        )
        original_init = httpx.AsyncClient.__init__

        def patched_init(self, *args, **kwargs):
            kwargs["transport"] = transport
            original_init(self, *args, **kwargs)

        httpx.AsyncClient.__init__ = patched_init
        try:
            with pytest.raises(httpx.HTTPStatusError):
                await fetch_spec("https://example.com/notfound")
        finally:
            httpx.AsyncClient.__init__ = original_init

    @pytest.mark.asyncio
    async def test_invalid_content_raises(self):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                text="this is not json or yaml!!!",
                headers={"content-type": "text/plain"},
            )
        )
        original_init = httpx.AsyncClient.__init__

        def patched_init(self, *args, **kwargs):
            kwargs["transport"] = transport
            original_init(self, *args, **kwargs)

        httpx.AsyncClient.__init__ = patched_init
        try:
            with pytest.raises(ValueError, match="Failed to parse"):
                await fetch_spec("https://example.com/bad")
        finally:
            httpx.AsyncClient.__init__ = original_init


class TestFetchSpecFallbacks:
    @pytest.mark.asyncio
    async def test_json_content_type_but_invalid_json_falls_to_yaml(self):
        """When content-type says JSON but body is invalid JSON, fall back to YAML."""
        # The body is valid YAML but not valid JSON
        yaml_body = "openapi: '3.0.3'\ninfo:\n  title: Test\n  version: '1.0'\npaths: {}"
        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                text=yaml_body,
                headers={"content-type": "application/json"},
            )
        )
        original_init = httpx.AsyncClient.__init__

        def patched_init(self, *args, **kwargs):
            kwargs["transport"] = transport
            original_init(self, *args, **kwargs)

        httpx.AsyncClient.__init__ = patched_init
        try:
            result = await fetch_spec("https://example.com/spec")
            assert result["openapi"] == "3.0.3"
        finally:
            httpx.AsyncClient.__init__ = original_init

    @pytest.mark.asyncio
    async def test_yaml_parse_exception_falls_to_json_retry(self):
        """When YAML parsing raises an exception, try JSON as last resort."""
        # This is valid JSON but the content-type triggers YAML first
        # yaml.safe_load returns a string (not a dict), so it won't match isinstance check
        json_body = '{"openapi": "3.0.3", "info": {"title": "Test", "version": "1.0"}, "paths": {}}'
        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                text=json_body,
                headers={"content-type": "text/plain"},
            )
        )
        original_init = httpx.AsyncClient.__init__

        def patched_init(self, *args, **kwargs):
            kwargs["transport"] = transport
            original_init(self, *args, **kwargs)

        httpx.AsyncClient.__init__ = patched_init
        try:
            result = await fetch_spec("https://example.com/spec")
            # Should fall through YAML (returns non-dict) → JSON retry
            assert result["openapi"] == "3.0.3"
        finally:
            httpx.AsyncClient.__init__ = original_init
