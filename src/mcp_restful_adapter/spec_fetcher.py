"""Fetch and parse OpenAPI/Swagger specifications from URLs."""

from __future__ import annotations

import json
from typing import Any

import httpx


def _parse_json_object(text: str) -> dict[str, Any]:
    result = json.loads(text)
    if not isinstance(result, dict):
        raise ValueError("API specification root must be an object")
    return result


async def fetch_spec(url: str) -> dict[str, Any]:
    """Fetch an API specification from a URL and parse it as JSON or YAML.

    Args:
        url: The URL to fetch the specification from.

    Returns:
        The parsed specification as a dictionary.

    Raises:
        httpx.HTTPStatusError: If the HTTP request fails.
        ValueError: If the response cannot be parsed as JSON or YAML.
    """
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    text = response.text

    # Try JSON first
    if "json" in content_type or url.endswith(".json"):
        try:
            return _parse_json_object(text)
        except json.JSONDecodeError:
            pass

    # Fall back to YAML
    try:
        import yaml

        result = yaml.safe_load(text)
        if isinstance(result, dict):
            return result
    except Exception:
        pass

    # Last resort: try JSON again (some servers return JSON with wrong content-type)
    try:
        return _parse_json_object(text)
    except json.JSONDecodeError:
        raise ValueError(
            f"Failed to parse spec from {url} as JSON or YAML. "
            f"Content-Type: {content_type}"
        )
