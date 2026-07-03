"""Tests for cli.py main() entry point."""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMainMissingEnvVars:
    def test_missing_api_spec_url_exits(self):
        """main() should exit with error if API_SPEC_URL is not set."""
        env = {"API_BASE_URL": "https://api.example.com"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                from mcp_restful_adapter.cli import main
                main()
            assert exc_info.value.code == 1

    def test_missing_api_base_url_exits(self):
        """main() should exit with error if API_BASE_URL is not set."""
        env = {"API_SPEC_URL": "https://example.com/spec.json"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                from mcp_restful_adapter.cli import main
                main()
            assert exc_info.value.code == 1


class TestMainNormalFlow:
    def test_main_openapi_3_flow(self):
        """main() should fetch, filter, build, and run for OpenAPI 3.0."""
        spec = {
            "openapi": "3.0.3",
            "info": {"title": "Test API", "version": "1.0"},
            "servers": [{"url": "https://api.example.com"}],
            "paths": {
                "/test": {
                    "get": {
                        "operationId": "test",
                        "tags": ["demo"],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }

        mock_mcp = MagicMock()
        env = {
            "API_SPEC_URL": "https://example.com/spec.json",
            "API_BASE_URL": "https://api.example.com",
            "API_METHODS": "GET",
            "API_TAGS": "demo",
        }

        with patch.dict(os.environ, env, clear=True):
            with (
                patch("mcp_restful_adapter.spec_fetcher.fetch_spec", new_callable=AsyncMock, return_value=spec),
                patch("mcp_restful_adapter.server.build_server", return_value=mock_mcp) as mock_build,
            ):
                from mcp_restful_adapter.cli import main
                main()

                mock_build.assert_called_once()
                call_kwargs = mock_build.call_args
                assert call_kwargs.kwargs["base_url"] == "https://api.example.com"
                assert call_kwargs.kwargs["tags"] == {"demo"}
                assert call_kwargs.kwargs["methods"] == {"GET"}
                mock_mcp.run.assert_called_once_with(transport="stdio", show_banner=False)

    def test_main_swagger_2_conversion(self):
        """main() should detect Swagger 2.0 and convert to OpenAPI 3.0."""
        swagger_spec = {
            "swagger": "2.0",
            "info": {"title": "Swagger API", "version": "1.0"},
            "host": "api.example.com",
            "basePath": "/v1",
            "schemes": ["https"],
            "paths": {},
        }

        mock_mcp = MagicMock()
        env = {
            "API_SPEC_URL": "https://example.com/swagger.json",
            "API_BASE_URL": "https://api.example.com",
        }

        with patch.dict(os.environ, env, clear=True):
            with (
                patch("mcp_restful_adapter.spec_fetcher.fetch_spec", new_callable=AsyncMock, return_value=swagger_spec),
                patch("mcp_restful_adapter.server.build_server", return_value=mock_mcp) as mock_build,
            ):
                from mcp_restful_adapter.cli import main
                main()

                # The spec passed to build_server should be converted (have "openapi" key)
                call_spec = mock_build.call_args.args[0]
                assert "openapi" in call_spec
                assert "swagger" not in call_spec

    def test_main_with_extra_headers(self):
        """main() should pass API_HEADERS to build_server."""
        spec = {
            "openapi": "3.0.3",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {},
        }
        mock_mcp = MagicMock()
        env = {
            "API_SPEC_URL": "https://example.com/spec.json",
            "API_BASE_URL": "https://api.example.com",
            "API_HEADERS": '{"Authorization": "Bearer secret-token-123", "X-Tenant": "acme"}',
        }

        with patch.dict(os.environ, env, clear=True):
            with (
                patch("mcp_restful_adapter.spec_fetcher.fetch_spec", new_callable=AsyncMock, return_value=spec),
                patch("mcp_restful_adapter.server.build_server", return_value=mock_mcp) as mock_build,
            ):
                from mcp_restful_adapter.cli import main
                main()

                headers = mock_build.call_args.kwargs["extra_headers"]
                assert headers["Authorization"] == "Bearer secret-token-123"
                assert headers["X-Tenant"] == "acme"

    def test_main_with_path_filter(self):
        """main() should pass API_PATHS to build_server."""
        spec = {
            "openapi": "3.0.3",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {},
        }
        mock_mcp = MagicMock()
        env = {
            "API_SPEC_URL": "https://example.com/spec.json",
            "API_BASE_URL": "https://api.example.com",
            "API_PATHS": r"^/api/v1/",
        }

        with patch.dict(os.environ, env, clear=True):
            with (
                patch("mcp_restful_adapter.spec_fetcher.fetch_spec", new_callable=AsyncMock, return_value=spec),
                patch("mcp_restful_adapter.server.build_server", return_value=mock_mcp) as mock_build,
            ):
                from mcp_restful_adapter.cli import main
                main()

                assert mock_build.call_args.kwargs["paths"] == r"^/api/v1/"

    def test_main_with_exclude_paths(self):
        """main() should pass API_PATHS_EXCLUDE to build_server."""
        spec = {
            "openapi": "3.0.3",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {},
        }
        mock_mcp = MagicMock()
        env = {
            "API_SPEC_URL": "https://example.com/spec.json",
            "API_BASE_URL": "https://api.example.com",
            "API_PATHS_EXCLUDE": r"(?i)(delete|remove)",
        }

        with patch.dict(os.environ, env, clear=True):
            with (
                patch("mcp_restful_adapter.spec_fetcher.fetch_spec", new_callable=AsyncMock, return_value=spec),
                patch("mcp_restful_adapter.server.build_server", return_value=mock_mcp) as mock_build,
            ):
                from mcp_restful_adapter.cli import main
                main()

                assert mock_build.call_args.kwargs["exclude_paths"] == r"(?i)(delete|remove)"


class TestMainErrorPaths:
    def test_headers_not_json_object(self):
        """main() should exit if API_HEADERS is not a JSON object."""
        env = {
            "API_SPEC_URL": "https://example.com/spec.json",
            "API_BASE_URL": "https://api.example.com",
            "API_HEADERS": '"just a string"',
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                from mcp_restful_adapter.cli import main
                main()
            assert exc_info.value.code == 1

    def test_headers_invalid_json(self):
        """main() should exit if API_HEADERS is not valid JSON."""
        env = {
            "API_SPEC_URL": "https://example.com/spec.json",
            "API_BASE_URL": "https://api.example.com",
            "API_HEADERS": "{invalid json}",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                from mcp_restful_adapter.cli import main
                main()
            assert exc_info.value.code == 1

    def test_fetch_spec_failure(self):
        """main() should exit if fetching the spec fails."""
        env = {
            "API_SPEC_URL": "https://example.com/spec.json",
            "API_BASE_URL": "https://api.example.com",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch(
                "mcp_restful_adapter.spec_fetcher.fetch_spec",
                new_callable=AsyncMock,
                side_effect=Exception("Connection refused"),
            ):
                with pytest.raises(SystemExit) as exc_info:
                    from mcp_restful_adapter.cli import main
                    main()
                assert exc_info.value.code == 1

    def test_build_server_failure(self):
        """main() should exit if building the server fails."""
        spec = {
            "openapi": "3.0.3",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {},
        }
        env = {
            "API_SPEC_URL": "https://example.com/spec.json",
            "API_BASE_URL": "https://api.example.com",
        }
        with patch.dict(os.environ, env, clear=True):
            with (
                patch("mcp_restful_adapter.spec_fetcher.fetch_spec", new_callable=AsyncMock, return_value=spec),
                patch("mcp_restful_adapter.server.build_server", side_effect=Exception("Invalid spec")),
            ):
                with pytest.raises(SystemExit) as exc_info:
                    from mcp_restful_adapter.cli import main
                    main()
                assert exc_info.value.code == 1
