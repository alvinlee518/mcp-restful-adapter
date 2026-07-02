"""Tests for spec_converter — Swagger 2.0 → OpenAPI 3.0 conversion."""

from __future__ import annotations

import pytest

from mcp_restful_adapter.spec_converter import (
    convert_swagger_to_openapi,
    is_swagger_2,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_swagger_2() -> dict:
    return {
        "swagger": "2.0",
        "info": {"title": "Test API", "version": "1.0"},
        "host": "api.example.com",
        "basePath": "/v1",
        "schemes": ["https"],
        "paths": {},
    }


@pytest.fixture
def full_swagger_2() -> dict:
    return {
        "swagger": "2.0",
        "info": {"title": "Full API", "version": "2.0", "description": "desc"},
        "host": "api.example.com",
        "basePath": "/api",
        "schemes": ["https", "http"],
        "consumes": ["application/json"],
        "produces": ["application/json"],
        "security": [{"apiKey": []}],
        "tags": [{"name": "user", "description": "User ops"}],
        "externalDocs": {"url": "https://docs.example.com"},
        "paths": {
            "/users": {
                "get": {
                    "tags": ["user"],
                    "summary": "List users",
                    "operationId": "listUsers",
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "type": "integer",
                            "description": "Max results",
                            "minimum": 1,
                            "maximum": 100,
                        },
                        {
                            "name": "status",
                            "in": "query",
                            "type": "array",
                            "items": {"type": "string"},
                            "collectionFormat": "multi",
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Success",
                            "schema": {
                                "type": "array",
                                "items": {"$ref": "#/definitions/User"},
                            },
                        },
                        "400": {"description": "Bad request"},
                    },
                },
                "post": {
                    "tags": ["user"],
                    "summary": "Create user",
                    "operationId": "createUser",
                    "parameters": [
                        {
                            "name": "body",
                            "in": "body",
                            "required": True,
                            "description": "User to create",
                            "schema": {"$ref": "#/definitions/User"},
                        }
                    ],
                    "responses": {"201": {"description": "Created"}},
                },
            },
            "/users/{id}": {
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "type": "integer",
                        "format": "int64",
                    }
                ],
                "get": {
                    "tags": ["user"],
                    "summary": "Get user",
                    "operationId": "getUser",
                    "responses": {
                        "200": {
                            "description": "Success",
                            "schema": {"$ref": "#/definitions/User"},
                        }
                    },
                },
                "put": {
                    "tags": ["user"],
                    "summary": "Update user",
                    "operationId": "updateUser",
                    "parameters": [
                        {
                            "name": "body",
                            "in": "body",
                            "required": True,
                            "schema": {"$ref": "#/definitions/User"},
                        }
                    ],
                    "responses": {"200": {"description": "Updated"}},
                },
            },
            "/users/{id}/avatar": {
                "post": {
                    "tags": ["user"],
                    "summary": "Upload avatar",
                    "operationId": "uploadAvatar",
                    "consumes": ["multipart/form-data"],
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "type": "integer",
                        },
                        {
                            "name": "file",
                            "in": "formData",
                            "type": "file",
                            "required": True,
                            "description": "Avatar image",
                        },
                        {
                            "name": "caption",
                            "in": "formData",
                            "type": "string",
                            "description": "Image caption",
                        },
                    ],
                    "responses": {"200": {"description": "Uploaded"}},
                }
            },
        },
        "definitions": {
            "User": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "id": {"type": "integer", "format": "int64"},
                    "name": {"type": "string"},
                    "role": {
                        "type": "string",
                        "enum": ["admin", "user"],
                    },
                    "address": {"$ref": "#/definitions/Address"},
                },
            },
            "Address": {
                "type": "object",
                "properties": {
                    "street": {"type": "string"},
                    "city": {"type": "string"},
                },
            },
        },
        "securityDefinitions": {
            "apiKey": {
                "type": "apiKey",
                "name": "X-API-Key",
                "in": "header",
            },
            "basic": {"type": "basic"},
            "oauth2": {
                "type": "oauth2",
                "flow": "accessCode",
                "authorizationUrl": "https://auth.example.com/authorize",
                "tokenUrl": "https://auth.example.com/token",
                "scopes": {"read": "Read access", "write": "Write access"},
            },
        },
    }


# ---------------------------------------------------------------------------
# is_swagger_2
# ---------------------------------------------------------------------------


class TestIsSwagger2:
    def test_detects_swagger_2(self):
        assert is_swagger_2({"swagger": "2.0"}) is True

    def test_rejects_openapi_3(self):
        assert is_swagger_2({"openapi": "3.0.0"}) is False

    def test_rejects_empty(self):
        assert is_swagger_2({}) is False

    def test_string_version(self):
        assert is_swagger_2({"swagger": 2.0}) is True


# ---------------------------------------------------------------------------
# convert_swagger_to_openapi — basics
# ---------------------------------------------------------------------------


class TestConvertBasics:
    def test_sets_openapi_version(self, minimal_swagger_2):
        result = convert_swagger_to_openapi(minimal_swagger_2)
        assert result["openapi"] == "3.0.3"
        assert "swagger" not in result

    def test_preserves_info(self, minimal_swagger_2):
        result = convert_swagger_to_openapi(minimal_swagger_2)
        assert result["info"] == {"title": "Test API", "version": "1.0"}

    def test_does_not_mutate_original(self, minimal_swagger_2):
        import copy

        original = copy.deepcopy(minimal_swagger_2)
        convert_swagger_to_openapi(minimal_swagger_2)
        assert minimal_swagger_2 == original

    def test_passes_through_tags(self, full_swagger_2):
        result = convert_swagger_to_openapi(full_swagger_2)
        assert result["tags"] == [{"name": "user", "description": "User ops"}]

    def test_passes_through_security(self, full_swagger_2):
        result = convert_swagger_to_openapi(full_swagger_2)
        assert result["security"] == [{"apiKey": []}]

    def test_passes_through_external_docs(self, full_swagger_2):
        result = convert_swagger_to_openapi(full_swagger_2)
        assert result["externalDocs"] == {"url": "https://docs.example.com"}


# ---------------------------------------------------------------------------
# Servers conversion
# ---------------------------------------------------------------------------


class TestServersConversion:
    def test_single_scheme(self, minimal_swagger_2):
        result = convert_swagger_to_openapi(minimal_swagger_2)
        assert result["servers"] == [{"url": "https://api.example.com/v1"}]

    def test_multiple_schemes(self, full_swagger_2):
        result = convert_swagger_to_openapi(full_swagger_2)
        assert len(result["servers"]) == 2
        urls = [s["url"] for s in result["servers"]]
        assert "https://api.example.com/api" in urls
        assert "http://api.example.com/api" in urls

    def test_no_host(self):
        spec = {"swagger": "2.0", "info": {"title": "X", "version": "1"}, "paths": {}}
        result = convert_swagger_to_openapi(spec)
        assert result["servers"] == []

    def test_trailing_slash_stripped(self):
        spec = {
            "swagger": "2.0",
            "info": {"title": "X", "version": "1"},
            "host": "example.com",
            "basePath": "/",
            "paths": {},
        }
        result = convert_swagger_to_openapi(spec)
        assert result["servers"][0]["url"] == "https://example.com"


# ---------------------------------------------------------------------------
# Parameter conversion
# ---------------------------------------------------------------------------


class TestParameterConversion:
    def test_query_param_inline_type_to_schema(self, full_swagger_2):
        result = convert_swagger_to_openapi(full_swagger_2)
        get_users = result["paths"]["/users"]["get"]
        limit_param = next(p for p in get_users["parameters"] if p["name"] == "limit")

        assert limit_param["in"] == "query"
        assert limit_param["schema"]["type"] == "integer"
        assert limit_param["schema"]["minimum"] == 1
        assert limit_param["schema"]["maximum"] == 100
        assert limit_param["description"] == "Max results"

    def test_path_param_always_required(self, full_swagger_2):
        result = convert_swagger_to_openapi(full_swagger_2)
        path_item = result["paths"]["/users/{id}"]
        # Path-level parameter should be converted with required=true
        id_param = path_item["parameters"][0]
        assert id_param["required"] is True
        assert id_param["in"] == "path"
        assert id_param["schema"]["type"] == "integer"

    def test_array_param_with_collection_format(self, full_swagger_2):
        result = convert_swagger_to_openapi(full_swagger_2)
        get_users = result["paths"]["/users"]["get"]
        status_param = next(
            p for p in get_users["parameters"] if p["name"] == "status"
        )

        assert status_param["schema"]["type"] == "array"
        assert status_param["schema"]["items"] == {"type": "string"}
        assert status_param["style"] == "form"
        assert status_param["explode"] is True

    def test_path_level_parameters_inherited(self, full_swagger_2):
        result = convert_swagger_to_openapi(full_swagger_2)
        path_item = result["paths"]["/users/{id}"]
        # Path-level params should be present
        assert "parameters" in path_item
        id_param = path_item["parameters"][0]
        assert id_param["name"] == "id"
        assert id_param["in"] == "path"


# ---------------------------------------------------------------------------
# Request body conversion
# ---------------------------------------------------------------------------


class TestRequestBodyConversion:
    def test_body_param_to_request_body(self, full_swagger_2):
        result = convert_swagger_to_openapi(full_swagger_2)
        post_users = result["paths"]["/users"]["post"]

        assert "requestBody" in post_users
        rb = post_users["requestBody"]
        assert rb["required"] is True
        assert rb["description"] == "User to create"
        assert "application/json" in rb["content"]
        schema = rb["content"]["application/json"]["schema"]
        assert schema == {"$ref": "#/components/schemas/User"}

    def test_form_data_to_request_body(self, full_swagger_2):
        result = convert_swagger_to_openapi(full_swagger_2)
        upload = result["paths"]["/users/{id}/avatar"]["post"]

        assert "requestBody" in upload
        rb = upload["requestBody"]
        # File param → multipart/form-data
        assert "multipart/form-data" in rb["content"]
        schema = rb["content"]["multipart/form-data"]["schema"]
        assert schema["type"] == "object"
        assert "file" in schema["properties"]
        assert "caption" in schema["properties"]
        assert schema["required"] == ["file"]

    def test_file_type_converted_to_string_binary(self, full_swagger_2):
        """Swagger 2.0 type: 'file' must become type: 'string', format: 'binary'."""
        result = convert_swagger_to_openapi(full_swagger_2)
        upload = result["paths"]["/users/{id}/avatar"]["post"]
        schema = upload["requestBody"]["content"]["multipart/form-data"]["schema"]
        file_prop = schema["properties"]["file"]
        assert file_prop["type"] == "string"
        assert file_prop["format"] == "binary"
        assert "file" not in file_prop.get("type", "")  # not type: "file"

    def test_body_param_not_in_parameters(self, full_swagger_2):
        result = convert_swagger_to_openapi(full_swagger_2)
        post_users = result["paths"]["/users"]["post"]
        # body params should not appear in the parameters list
        assert "parameters" not in post_users or len(
            post_users.get("parameters", [])
        ) == 0


# ---------------------------------------------------------------------------
# Response conversion
# ---------------------------------------------------------------------------


class TestResponseConversion:
    def test_response_schema_to_content(self, full_swagger_2):
        result = convert_swagger_to_openapi(full_swagger_2)
        get_users = result["paths"]["/users"]["get"]
        resp_200 = get_users["responses"]["200"]

        assert resp_200["description"] == "Success"
        assert "content" in resp_200
        schema = resp_200["content"]["application/json"]["schema"]
        assert schema["type"] == "array"
        assert schema["items"] == {"$ref": "#/components/schemas/User"}

    def test_response_without_schema(self, full_swagger_2):
        result = convert_swagger_to_openapi(full_swagger_2)
        get_users = result["paths"]["/users"]["get"]
        resp_400 = get_users["responses"]["400"]
        assert resp_400["description"] == "Bad request"
        assert "content" not in resp_400


# ---------------------------------------------------------------------------
# $ref rewriting
# ---------------------------------------------------------------------------


class TestRefRewriting:
    def test_definitions_to_components_schemas(self, full_swagger_2):
        result = convert_swagger_to_openapi(full_swagger_2)
        user_schema = result["components"]["schemas"]["User"]
        # $ref to Address should be rewritten
        assert user_schema["properties"]["address"] == {
            "$ref": "#/components/schemas/Address"
        }

    def test_component_schemas_present(self, full_swagger_2):
        result = convert_swagger_to_openapi(full_swagger_2)
        assert "User" in result["components"]["schemas"]
        assert "Address" in result["components"]["schemas"]


# ---------------------------------------------------------------------------
# Security scheme conversion
# ---------------------------------------------------------------------------


class TestSecurityConversion:
    def test_api_key(self, full_swagger_2):
        result = convert_swagger_to_openapi(full_swagger_2)
        scheme = result["components"]["securitySchemes"]["apiKey"]
        assert scheme["type"] == "apiKey"
        assert scheme["name"] == "X-API-Key"
        assert scheme["in"] == "header"

    def test_basic_to_http(self, full_swagger_2):
        result = convert_swagger_to_openapi(full_swagger_2)
        scheme = result["components"]["securitySchemes"]["basic"]
        assert scheme["type"] == "http"
        assert scheme["scheme"] == "basic"

    def test_oauth2_flow_rename(self, full_swagger_2):
        result = convert_swagger_to_openapi(full_swagger_2)
        scheme = result["components"]["securitySchemes"]["oauth2"]
        assert scheme["type"] == "oauth2"
        assert "flows" in scheme
        # "accessCode" → "authorizationCode"
        assert "authorizationCode" in scheme["flows"]
        flow = scheme["flows"]["authorizationCode"]
        assert flow["authorizationUrl"] == "https://auth.example.com/authorize"
        assert flow["tokenUrl"] == "https://auth.example.com/token"
        assert flow["scopes"] == {"read": "Read access", "write": "Write access"}


# ---------------------------------------------------------------------------
# collectionFormat conversion
# ---------------------------------------------------------------------------


class TestCollectionFormat:
    def test_csv(self):
        from mcp_restful_adapter.spec_converter import _convert_collection_format

        style, explode = _convert_collection_format("csv")
        assert style == "form"
        assert explode is False

    def test_multi(self):
        from mcp_restful_adapter.spec_converter import _convert_collection_format

        style, explode = _convert_collection_format("multi")
        assert style == "form"
        assert explode is True

    def test_pipes(self):
        from mcp_restful_adapter.spec_converter import _convert_collection_format

        style, explode = _convert_collection_format("pipes")
        assert style == "pipeDelimited"
        assert explode is False

    def test_ssv(self):
        from mcp_restful_adapter.spec_converter import _convert_collection_format

        style, explode = _convert_collection_format("ssv")
        assert style == "spaceDelimited"
        assert explode is False


# ---------------------------------------------------------------------------
# End-to-end: converted spec is valid for fastmcp
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_converted_spec_works_with_fastmcp(self, full_swagger_2):
        """The converted spec should be accepted by FastMCP.from_openapi()."""
        import httpx
        from fastmcp import FastMCP

        converted = convert_swagger_to_openapi(full_swagger_2)
        client = httpx.AsyncClient(base_url="https://api.example.com")
        mcp = FastMCP.from_openapi(openapi_spec=converted, client=client)
        assert mcp is not None


# ---------------------------------------------------------------------------
# Additional coverage tests
# ---------------------------------------------------------------------------


class TestOperationExternalDocs:
    def test_operation_external_docs(self):
        spec = {
            "swagger": "2.0",
            "info": {"title": "X", "version": "1"},
            "host": "example.com",
            "basePath": "/",
            "paths": {
                "/test": {
                    "get": {
                        "operationId": "test",
                        "externalDocs": {"url": "https://docs.example.com/test"},
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        result = convert_swagger_to_openapi(spec)
        assert result["paths"]["/test"]["get"]["externalDocs"] == {
            "url": "https://docs.example.com/test"
        }


class TestOperationNoResponses:
    def test_default_response_when_no_responses(self):
        spec = {
            "swagger": "2.0",
            "info": {"title": "X", "version": "1"},
            "host": "example.com",
            "basePath": "/",
            "paths": {
                "/test": {
                    "get": {"operationId": "test"}
                }
            },
        }
        result = convert_swagger_to_openapi(spec)
        responses = result["paths"]["/test"]["get"]["responses"]
        assert "200" in responses
        assert responses["200"]["description"] == "Successful response"


class TestRefParamResolution:
    def test_resolve_ref_parameter(self):
        spec = {
            "swagger": "2.0",
            "info": {"title": "X", "version": "1"},
            "host": "example.com",
            "basePath": "/",
            "paths": {
                "/test": {
                    "get": {
                        "operationId": "test",
                        "parameters": [
                            {"$ref": "#/parameters/LimitParam"}
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
            "parameters": {
                "LimitParam": {
                    "name": "limit",
                    "in": "query",
                    "type": "integer",
                }
            },
        }
        result = convert_swagger_to_openapi(spec)
        # Top-level parameters should be in components.parameters
        assert "parameters" in result["components"]
        assert "LimitParam" in result["components"]["parameters"]

    def test_path_level_body_param_skipped(self):
        """Body params at the path level should be skipped (return None)."""
        spec = {
            "swagger": "2.0",
            "info": {"title": "X", "version": "1"},
            "host": "example.com",
            "basePath": "/",
            "paths": {
                "/items": {
                    "parameters": [
                        {
                            "name": "body",
                            "in": "body",
                            "schema": {"type": "object"},
                        }
                    ],
                    "get": {
                        "operationId": "getItem",
                        "responses": {"200": {"description": "OK"}},
                    },
                }
            },
        }
        result = convert_swagger_to_openapi(spec)
        # Body param at path level should be filtered out
        path_item = result["paths"]["/items"]
        assert "parameters" not in path_item or path_item.get("parameters") == []


class TestResponseRefRewriting:
    def test_response_ref_rewriting(self):
        spec = {
            "swagger": "2.0",
            "info": {"title": "X", "version": "1"},
            "host": "example.com",
            "basePath": "/",
            "paths": {
                "/test": {
                    "get": {
                        "operationId": "test",
                        "responses": {
                            "200": {"$ref": "#/responses/SuccessResponse"}
                        },
                    }
                }
            },
            "responses": {
                "SuccessResponse": {
                    "description": "Success",
                }
            },
        }
        result = convert_swagger_to_openapi(spec)
        resp = result["paths"]["/test"]["get"]["responses"]["200"]
        assert resp["$ref"] == "#/components/responses/SuccessResponse"


class TestResponseHeaders:
    def test_response_headers_conversion(self):
        spec = {
            "swagger": "2.0",
            "info": {"title": "X", "version": "1"},
            "host": "example.com",
            "basePath": "/",
            "paths": {
                "/test": {
                    "get": {
                        "operationId": "test",
                        "responses": {
                            "200": {
                                "description": "OK",
                                "headers": {
                                    "X-Rate-Limit": {
                                        "type": "integer",
                                        "description": "Rate limit",
                                    }
                                },
                            }
                        },
                    }
                }
            },
        }
        result = convert_swagger_to_openapi(spec)
        resp = result["paths"]["/test"]["get"]["responses"]["200"]
        assert "headers" in resp
        header = resp["headers"]["X-Rate-Limit"]
        assert header["description"] == "Rate limit"
        assert header["schema"]["type"] == "integer"


class TestTopLevelReusableComponents:
    def test_top_level_parameters(self):
        spec = {
            "swagger": "2.0",
            "info": {"title": "X", "version": "1"},
            "host": "example.com",
            "basePath": "/",
            "paths": {},
            "parameters": {
                "SkipParam": {
                    "name": "skip",
                    "in": "query",
                    "type": "integer",
                }
            },
        }
        result = convert_swagger_to_openapi(spec)
        assert "SkipParam" in result["components"]["parameters"]
        assert result["components"]["parameters"]["SkipParam"]["name"] == "skip"

    def test_top_level_responses(self):
        spec = {
            "swagger": "2.0",
            "info": {"title": "X", "version": "1"},
            "host": "example.com",
            "basePath": "/",
            "paths": {},
            "responses": {
                "NotFound": {
                    "description": "Not found",
                }
            },
        }
        result = convert_swagger_to_openapi(spec)
        assert "NotFound" in result["components"]["responses"]
        assert result["components"]["responses"]["NotFound"]["description"] == "Not found"


class TestSchemaObjectEdgeCases:
    def test_non_dict_schema_passthrough(self):
        from mcp_restful_adapter.spec_converter import _convert_schema_object

        # Non-dict should pass through unchanged
        assert _convert_schema_object("string") == "string"
        assert _convert_schema_object(42) == 42

    def test_additional_properties(self):
        from mcp_restful_adapter.spec_converter import _convert_schema_object

        schema = {
            "type": "object",
            "additionalProperties": {"$ref": "#/definitions/Value"},
        }
        result = _convert_schema_object(schema)
        assert result["additionalProperties"]["$ref"] == "#/components/schemas/Value"

    def test_allof_anyof_oneof(self):
        from mcp_restful_adapter.spec_converter import _convert_schema_object

        schema = {
            "allOf": [
                {"$ref": "#/definitions/Base"},
                {"type": "object", "properties": {"extra": {"type": "string"}}},
            ],
            "anyOf": [
                {"$ref": "#/definitions/TypeA"},
                {"$ref": "#/definitions/TypeB"},
            ],
            "oneOf": [
                {"type": "string"},
                {"type": "integer"},
            ],
        }
        result = _convert_schema_object(schema)
        assert result["allOf"][0]["$ref"] == "#/components/schemas/Base"
        assert result["anyOf"][0]["$ref"] == "#/components/schemas/TypeA"
        assert result["oneOf"][0] == {"type": "string"}


class TestSecuritySchemeEdgeCases:
    def test_unknown_security_type(self):
        from mcp_restful_adapter.spec_converter import _convert_security_scheme

        scheme = {"type": "customAuth", "x-custom": "value"}
        result = _convert_security_scheme(scheme)
        # Unknown types pass through
        assert result["type"] == "customAuth"

    def test_security_scheme_with_description(self):
        from mcp_restful_adapter.spec_converter import _convert_security_scheme

        scheme = {
            "type": "basic",
            "description": "HTTP Basic auth",
        }
        result = _convert_security_scheme(scheme)
        assert result["description"] == "HTTP Basic auth"
        assert result["type"] == "http"


class TestResolveContentTypes:
    def test_picks_json_from_list(self):
        from mcp_restful_adapter.spec_converter import _resolve_content_types

        result = _resolve_content_types(["application/xml", "application/json"])
        assert "application/json" in result
        assert "application/xml" in result

    def test_picks_custom_json_type(self):
        from mcp_restful_adapter.spec_converter import _resolve_content_types

        result = _resolve_content_types(["application/vnd.api+json"])
        assert result == ["application/vnd.api+json"]

    def test_defaults_to_json_when_empty(self):
        from mcp_restful_adapter.spec_converter import _resolve_content_types

        result = _resolve_content_types([])
        assert result == ["application/json"]

    def test_skips_form_types_for_body(self):
        from mcp_restful_adapter.spec_converter import _resolve_content_types

        result = _resolve_content_types(
            ["multipart/form-data", "application/x-www-form-urlencoded", "application/json"],
            is_body=True,
        )
        assert result == ["application/json"]
        assert "multipart/form-data" not in result

    def test_keeps_all_types_for_response(self):
        from mcp_restful_adapter.spec_converter import _resolve_content_types

        result = _resolve_content_types(
            ["application/json", "application/xml"],
        )
        assert result == ["application/json", "application/xml"]


# ---------------------------------------------------------------------------
# Springfox / real-world edge cases
# ---------------------------------------------------------------------------


class TestWildcardContentType:
    """Springfox generates */* for produces; should be normalized to application/json."""

    def test_wildcard_normalized_to_json(self):
        from mcp_restful_adapter.spec_converter import _resolve_content_types

        result = _resolve_content_types(["*/*"])
        assert result == ["application/json"]

    def test_application_wildcard_normalized(self):
        from mcp_restful_adapter.spec_converter import _resolve_content_types

        result = _resolve_content_types(["application/*"])
        assert result == ["application/json"]

    def test_wildcard_in_full_response_conversion(self, minimal_swagger_2):
        minimal_swagger_2["paths"] = {
            "/test": {
                "get": {
                    "produces": ["*/*"],
                    "responses": {
                        "200": {
                            "description": "OK",
                            "schema": {"type": "string"},
                        }
                    },
                }
            }
        }
        result = convert_swagger_to_openapi(minimal_swagger_2)
        content = result["paths"]["/test"]["get"]["responses"]["200"]["content"]
        assert "application/json" in content
        assert "*/*" not in content


class TestOriginalRefStripping:
    """Springfox adds originalRef to $ref objects; must be stripped in OpenAPI 3.0."""

    def test_original_ref_stripped_from_schema(self):
        from mcp_restful_adapter.spec_converter import _convert_schema_object

        schema = {"$ref": "#/definitions/Foo", "originalRef": "Foo"}
        result = _convert_schema_object(schema)
        assert "originalRef" not in result
        assert result == {"$ref": "#/components/schemas/Foo"}

    def test_original_ref_stripped_in_definitions(self, minimal_swagger_2):
        minimal_swagger_2["paths"] = {}
        minimal_swagger_2["definitions"] = {
            "Foo": {
                "type": "object",
                "properties": {
                    "bar": {"$ref": "#/definitions/Bar", "originalRef": "Bar"},
                },
            },
            "Bar": {"type": "string"},
        }
        result = convert_swagger_to_openapi(minimal_swagger_2)
        foo_schema = result["components"]["schemas"]["Foo"]
        bar_ref = foo_schema["properties"]["bar"]
        assert "originalRef" not in bar_ref


class TestEmptyContactCleanup:
    """Empty contact object in info should be removed."""

    def test_empty_contact_removed(self, minimal_swagger_2):
        minimal_swagger_2["info"] = {
            "title": "Test",
            "version": "1.0",
            "contact": {},
        }
        result = convert_swagger_to_openapi(minimal_swagger_2)
        assert "contact" not in result["info"]

    def test_non_empty_contact_preserved(self, minimal_swagger_2):
        minimal_swagger_2["info"] = {
            "title": "Test",
            "version": "1.0",
            "contact": {"name": "API Support", "email": "support@example.com"},
        }
        result = convert_swagger_to_openapi(minimal_swagger_2)
        assert result["info"]["contact"]["name"] == "API Support"


class TestFileTypeInNestedSchemas:
    """type: file in nested schemas (e.g., items) must be converted."""

    def test_file_type_in_array_items(self):
        from mcp_restful_adapter.spec_converter import _convert_schema_object

        schema = {"type": "array", "items": {"type": "file"}}
        result = _convert_schema_object(schema)
        assert result["items"]["type"] == "string"
        assert result["items"]["format"] == "binary"

    def test_file_type_in_properties(self):
        from mcp_restful_adapter.spec_converter import _convert_schema_object

        schema = {
            "type": "object",
            "properties": {
                "upload": {"type": "file"},
            },
        }
        result = _convert_schema_object(schema)
        assert result["properties"]["upload"]["type"] == "string"
        assert result["properties"]["upload"]["format"] == "binary"
