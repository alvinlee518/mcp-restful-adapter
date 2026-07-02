"""Convert Swagger 2.0 specifications to OpenAPI 3.0 format."""

from __future__ import annotations

import copy
import re
from typing import Any


def is_swagger_2(spec: dict[str, Any]) -> bool:
    """Check if a spec is Swagger 2.0."""
    return "swagger" in spec and str(spec["swagger"]).startswith("2")


def convert_swagger_to_openapi(spec: dict[str, Any]) -> dict[str, Any]:
    """Convert a Swagger 2.0 specification to OpenAPI 3.0 format.

    Args:
        spec: A Swagger 2.0 specification dict.

    Returns:
        A new dict in OpenAPI 3.0 format.
    """
    spec = copy.deepcopy(spec)
    result: dict[str, Any] = {"openapi": "3.0.3"}

    # 1. Info (pass through, fill in required fields)
    info = spec.get("info", {})
    if not isinstance(info, dict):
        info = {}
    info.setdefault("title", "API")
    info.setdefault("version", "1.0.0")
    # Clean up empty nested objects that fail validation
    if isinstance(info.get("license"), dict) and "name" not in info["license"]:
        info["license"] = {"name": "Unknown"}
    result["info"] = info

    # 2. Servers: host + basePath + schemes → servers[].url
    result["servers"] = _convert_servers(spec)

    # 3. Paths
    result["paths"] = _convert_paths(spec)

    # 4. Components
    components = _convert_components(spec)
    if components:
        result["components"] = components

    # 5. Security (pass through, rewrite $refs)
    if "security" in spec:
        result["security"] = spec["security"]

    # 6. Tags (pass through)
    if "tags" in spec:
        result["tags"] = spec["tags"]

    # 7. External docs (pass through)
    if "externalDocs" in spec:
        result["externalDocs"] = spec["externalDocs"]

    return result


def _convert_servers(spec: dict[str, Any]) -> list[dict[str, str]]:
    """Convert host/basePath/schemes to OpenAPI 3.0 servers array."""
    host = spec.get("host", "")
    base_path = spec.get("basePath", "")
    schemes = spec.get("schemes", ["https"])

    if not host:
        return []

    servers = []
    for scheme in schemes:
        url = f"{scheme}://{host}{base_path}".rstrip("/")
        servers.append({"url": url})

    return servers


def _convert_paths(spec: dict[str, Any]) -> dict[str, Any]:
    """Convert all paths and their operations."""
    paths: dict[str, Any] = {}
    global_consumes = spec.get("consumes", ["application/json"])
    global_produces = spec.get("produces", ["application/json"])

    for path_key, path_item in spec.get("paths", {}).items():
        new_path_item: dict[str, Any] = {}

        # Path-level parameters (shared by all operations)
        if "parameters" in path_item:
            new_params = []
            for param in path_item["parameters"]:
                converted = _convert_parameter(param)
                if converted:
                    new_params.append(converted)
            if new_params:
                new_path_item["parameters"] = new_params

        # Convert each HTTP method operation
        http_methods = {"get", "post", "put", "delete", "patch", "head", "options"}
        for method in http_methods:
            if method not in path_item:
                continue

            operation = path_item[method]
            new_op = _convert_operation(
                operation, global_consumes, global_produces
            )
            new_path_item[method] = new_op

        paths[path_key] = new_path_item

    return paths


def _convert_operation(
    operation: dict[str, Any],
    global_consumes: list[str],
    global_produces: list[str],
) -> dict[str, Any]:
    """Convert a single Swagger 2.0 operation to OpenAPI 3.0."""
    new_op: dict[str, Any] = {}

    # Pass-through fields
    for field in ("tags", "summary", "description", "operationId", "deprecated",
                  "security"):
        if field in operation:
            new_op[field] = operation[field]

    # External docs
    if "externalDocs" in operation:
        new_op["externalDocs"] = operation["externalDocs"]

    consumes = operation.get("consumes", global_consumes)
    produces = operation.get("produces", global_produces)

    # Separate parameters: regular params vs body/formData
    parameters = operation.get("parameters", [])
    regular_params = []
    body_params = []
    form_params = []

    for param in parameters:
        param = _resolve_ref_param(param)
        location = param.get("in", "")
        if location == "body":
            body_params.append(param)
        elif location == "formData":
            form_params.append(param)
        else:
            converted = _convert_parameter(param)
            if converted:
                regular_params.append(converted)

    # Set parameters (path, query, header, cookie)
    if regular_params:
        new_op["parameters"] = regular_params

    # Set requestBody from body or formData params
    request_body = _build_request_body(body_params, form_params, consumes)
    if request_body:
        new_op["requestBody"] = request_body

    # Convert responses
    if "responses" in operation:
        new_op["responses"] = _convert_responses(operation["responses"], produces)
    else:
        new_op["responses"] = {"200": {"description": "Successful response"}}

    return new_op


def _convert_parameter(param: dict[str, Any]) -> dict[str, Any] | None:
    """Convert a Swagger 2.0 parameter to OpenAPI 3.0 format.

    In Swagger 2.0, type/format/enum/items are inline on the parameter.
    In OpenAPI 3.0, they're nested under a 'schema' key.
    """
    param = _resolve_ref_param(param)

    # If it's still a $ref after resolution, pass through as-is
    if "$ref" in param:
        return param

    location = param.get("in", "")

    # Skip body and formData — handled separately
    if location in ("body", "formData"):
        return None

    new_param: dict[str, Any] = {
        "name": param["name"],
        "in": location,
    }

    if param.get("description"):
        new_param["description"] = param["description"]
    if param.get("required"):
        new_param["required"] = param["required"]
    # Path params are always required in OpenAPI 3.0
    if location == "path":
        new_param["required"] = True

    # Build the schema from inline type fields
    schema = _extract_schema_from_swagger_param(param)
    if schema:
        new_param["schema"] = schema

    # Convert collectionFormat to style/explode
    if "collectionFormat" in param:
        style, explode = _convert_collection_format(param["collectionFormat"])
        if style:
            new_param["style"] = style
        new_param["explode"] = explode

    # Allow empty values → not directly supported in 3.0, skip
    # allowEmptyValue is deprecated in 3.0

    return new_param


def _extract_schema_from_swagger_param(param: dict[str, Any]) -> dict[str, Any]:
    """Extract a JSON Schema from inline Swagger 2.0 parameter type fields."""
    schema: dict[str, Any] = {}

    for field in ("type", "format", "enum", "minimum", "maximum",
                  "minLength", "maxLength", "pattern", "default",
                  "minItems", "maxItems", "uniqueItems"):
        if field in param:
            schema[field] = param[field]

    # Swagger 2.0 type: "file" → OpenAPI 3.0 type: "string", format: "binary"
    if schema.get("type") == "file":
        schema["type"] = "string"
        schema["format"] = "binary"

    # Handle array items
    if "items" in param:
        schema["items"] = _convert_schema_object(param["items"])

    return schema


def _resolve_ref_param(param: dict[str, Any]) -> dict[str, Any]:
    """If param has a $ref, return the ref path rewritten for OpenAPI 3.0."""
    if "$ref" in param:
        ref = param["$ref"]
        # #/parameters/Name → #/components/parameters/Name
        new_ref = _rewrite_ref(ref)
        return {"$ref": new_ref}
    return param


def _build_request_body(
    body_params: list[dict[str, Any]],
    form_params: list[dict[str, Any]],
    consumes: list[str],
) -> dict[str, Any] | None:
    """Build an OpenAPI 3.0 requestBody from Swagger 2.0 body/formData params."""
    if body_params:
        # Use the first body parameter's schema
        body = body_params[0]
        schema = body.get("schema", {})
        schema = _convert_schema_object(schema)

        # Build content map from consumes
        content_types = _resolve_content_types(consumes, is_body=True)
        content: dict[str, Any] = {}
        for ct in content_types:
            content[ct] = {"schema": schema}

        request_body: dict[str, Any] = {"content": content}
        if body.get("description"):
            request_body["description"] = body["description"]
        if body.get("required"):
            request_body["required"] = True

        return request_body

    if form_params:
        # Build schema from formData parameters
        properties: dict[str, Any] = {}
        required: list[str] = []

        for param in form_params:
            prop_schema = _extract_schema_from_swagger_param(param)
            if param.get("description"):
                prop_schema["description"] = param["description"]
            properties[param["name"]] = prop_schema
            if param.get("required"):
                required.append(param["name"])

        schema: dict[str, Any] = {"type": "object", "properties": properties}
        if required:
            schema["required"] = required

        # Determine content type for form data
        has_file = any(p.get("type") == "file" for p in form_params)
        content_type = "multipart/form-data" if has_file else "application/x-www-form-urlencoded"

        return {
            "content": {
                content_type: {"schema": schema}
            }
        }

    return None


def _convert_responses(
    responses: dict[str, Any],
    produces: list[str],
) -> dict[str, Any]:
    """Convert Swagger 2.0 responses to OpenAPI 3.0 format."""
    new_responses: dict[str, Any] = {}

    for status_code, response in responses.items():
        new_resp: dict[str, Any] = {}

        if "$ref" in response:
            # Rewrite $ref for responses
            new_resp["$ref"] = _rewrite_ref(response["$ref"])
            new_responses[status_code] = new_resp
            continue

        new_resp["description"] = response.get("description", "")

        # Convert response schema to content
        if "schema" in response:
            schema = _convert_schema_object(response["schema"])
            content_types = _resolve_content_types(produces)
            content: dict[str, Any] = {}
            for ct in content_types:
                content[ct] = {"schema": schema}
            new_resp["content"] = content

        # Convert headers
        if "headers" in response:
            new_headers: dict[str, Any] = {}
            for header_name, header_def in response["headers"].items():
                new_header: dict[str, Any] = {}
                if header_def.get("description"):
                    new_header["description"] = header_def["description"]
                schema = _extract_schema_from_swagger_param(header_def)
                if schema:
                    new_header["schema"] = schema
                new_headers[header_name] = new_header
            new_resp["headers"] = new_headers

        new_responses[status_code] = new_resp

    return new_responses


def _convert_components(spec: dict[str, Any]) -> dict[str, Any]:
    """Convert top-level Swagger 2.0 definitions to OpenAPI 3.0 components."""
    components: dict[str, Any] = {}

    # definitions → components.schemas
    if "definitions" in spec:
        schemas: dict[str, Any] = {}
        for name, schema in spec["definitions"].items():
            schemas[name] = _convert_schema_object(schema)
        components["schemas"] = schemas

    # parameters → components.parameters
    if "parameters" in spec:
        params: dict[str, Any] = {}
        for name, param in spec["parameters"].items():
            converted = _convert_parameter(param)
            if converted:
                params[name] = converted
        if params:
            components["parameters"] = params

    # responses → components.responses
    global_produces = spec.get("produces", ["application/json"])
    if "responses" in spec:
        resps: dict[str, Any] = {}
        for name, response in spec["responses"].items():
            resps[name] = _convert_responses({name: response}, global_produces)[name]
        if resps:
            components["responses"] = resps

    # securityDefinitions → components.securitySchemes
    if "securityDefinitions" in spec:
        schemes: dict[str, Any] = {}
        for name, scheme in spec["securityDefinitions"].items():
            schemes[name] = _convert_security_scheme(scheme)
        if schemes:
            components["securitySchemes"] = schemes

    return components


def _convert_schema_object(schema: dict[str, Any]) -> dict[str, Any]:
    """Recursively convert a Swagger 2.0 schema object to OpenAPI 3.0.

    Handles $ref rewriting and nested schema objects.
    """
    if not isinstance(schema, dict):
        return schema

    result: dict[str, Any] = {}

    for key, value in schema.items():
        if key == "$ref" and isinstance(value, str):
            if value.startswith("#/"):
                result["$ref"] = _rewrite_ref(value)
            else:
                # Non-standard $ref (e.g., Springfox Java types)
                resolved = _resolve_java_type_ref(value)
                result.update(resolved)
        elif key == "items" and isinstance(value, dict):
            result["items"] = _convert_schema_object(value)
        elif key in ("properties",) and isinstance(value, dict):
            result[key] = {
                k: _convert_schema_object(v) for k, v in value.items()
            }
        elif key == "additionalProperties" and isinstance(value, dict):
            result[key] = _convert_schema_object(value)
        elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
            result[key] = [_convert_schema_object(item) for item in value]
        else:
            result[key] = value

    return result


def _rewrite_ref(ref: str) -> str:
    """Rewrite Swagger 2.0 $ref paths to OpenAPI 3.0 paths."""
    replacements = [
        (r"^#/definitions/", "#/components/schemas/"),
        (r"^#/parameters/", "#/components/parameters/"),
        (r"^#/responses/", "#/components/responses/"),
    ]
    for pattern, replacement in replacements:
        ref = re.sub(pattern, replacement, ref)
    return ref


# Mapping of common Java/Springfox type names to OpenAPI schemas
_JAVA_TYPE_MAP = {
    "LocalDate": {"type": "string", "format": "date"},
    "LocalDateTime": {"type": "string", "format": "date-time"},
    "LocalTime": {"type": "string", "format": "time"},
    "Instant": {"type": "string", "format": "date-time"},
    "ZonedDateTime": {"type": "string", "format": "date-time"},
    "OffsetDateTime": {"type": "string", "format": "date-time"},
    "BigDecimal": {"type": "number"},
    "BigInteger": {"type": "integer"},
    "UUID": {"type": "string", "format": "uuid"},
    "URI": {"type": "string", "format": "uri"},
    "URL": {"type": "string", "format": "uri"},
    "MultipartFile": {"type": "string", "format": "binary"},
}


def _resolve_java_type_ref(ref: str) -> dict[str, Any]:
    """Resolve a non-standard $ref (e.g., Springfox Java type) to an OpenAPI schema.

    Handles refs like: Error-ModelName{namespace='java.time', name='LocalDate'}
    """
    # Extract the type name from Springfox format
    match = re.search(r"name='(\w+)'", ref)
    type_name = match.group(1) if match else ""

    if type_name in _JAVA_TYPE_MAP:
        return dict(_JAVA_TYPE_MAP[type_name])

    # Unknown Java type — fall back to string
    return {"type": "string"}


def _convert_security_scheme(scheme: dict[str, Any]) -> dict[str, Any]:
    """Convert a Swagger 2.0 security scheme to OpenAPI 3.0."""
    new_scheme: dict[str, Any] = {}

    scheme_type = scheme.get("type", "")

    if scheme_type == "basic":
        new_scheme["type"] = "http"
        new_scheme["scheme"] = "basic"
    elif scheme_type == "apiKey":
        new_scheme["type"] = "apiKey"
        new_scheme["name"] = scheme.get("name", "")
        new_scheme["in"] = scheme.get("in", "header")
    elif scheme_type == "oauth2":
        new_scheme["type"] = "oauth2"
        flows = _convert_oauth2_flows(scheme)
        if flows:
            new_scheme["flows"] = flows
    else:
        new_scheme = scheme

    if scheme.get("description"):
        new_scheme["description"] = scheme["description"]

    return new_scheme


def _convert_oauth2_flows(scheme: dict[str, Any]) -> dict[str, Any]:
    """Convert Swagger 2.0 OAuth2 flow types to OpenAPI 3.0 flow names."""
    flow_type = scheme.get("flow", "")
    flow: dict[str, Any] = {}

    if scheme.get("scopes"):
        flow["scopes"] = scheme["scopes"]

    # Map old flow names to new
    flow_name_map = {
        "implicit": "implicit",
        "password": "password",
        "application": "clientCredentials",
        "accessCode": "authorizationCode",
    }
    flow_name = flow_name_map.get(flow_type, flow_type)

    # Map URLs
    if scheme.get("authorizationUrl"):
        flow["authorizationUrl"] = scheme["authorizationUrl"]
    if scheme.get("tokenUrl"):
        flow["tokenUrl"] = scheme["tokenUrl"]

    return {flow_name: flow}


def _resolve_content_types(
    consumes: list[str], *, is_body: bool = False
) -> list[str]:
    """Resolve content types from Swagger 2.0 consumes/produces list.

    Returns a list of valid content types for OpenAPI 3.0.
    """
    if not consumes:
        return ["application/json"]

    result = []
    for ct in consumes:
        # Skip form-related types for body params (they belong to formData)
        if is_body and ct in (
            "multipart/form-data",
            "application/x-www-form-urlencoded",
        ):
            continue
        result.append(ct)

    return result or ["application/json"]


def _convert_collection_format(
    fmt: str,
) -> tuple[str | None, bool]:
    """Convert Swagger 2.0 collectionFormat to OpenAPI 3.0 style/explode."""
    mapping = {
        "csv": ("form", False),
        "ssv": ("spaceDelimited", False),
        "tsv": ("pipeDelimited", False),  # closest approximation
        "pipes": ("pipeDelimited", False),
        "multi": ("form", True),
    }
    style, explode = mapping.get(fmt, (None, False))
    return style, explode
