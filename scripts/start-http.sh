#!/usr/bin/env bash
#
# Start MCP RESTful Adapter in streamable-http mode.
#
# Usage:
#   ./scripts/start-http.sh
#
# Required:
#   API_SPEC_URL       - OpenAPI/Swagger spec URL
#   API_BASE_URL       - Backend API base URL
#
# Optional (override defaults):
#   MCP_PORT, MCP_HOST, API_METHODS, API_PATHS_EXCLUDE,
#   API_HEADERS, API_MAX_RESPONSE_SIZE, LOG_LEVEL

set -euo pipefail

# ── Required ────────────────────────────────────────────────────
export API_SPEC_URL="${API_SPEC_URL:-}"
export API_BASE_URL="${API_BASE_URL:-}"

if [[ -z "$API_SPEC_URL" || -z "$API_BASE_URL" ]]; then
  echo "Error: API_SPEC_URL and API_BASE_URL are required." >&2
  echo "" >&2
  echo "Example:" >&2
  echo "  API_SPEC_URL=https://your-api/v2/api-docs \\" >&2
  echo "  API_BASE_URL=https://your-api \\" >&2
  echo "  $0" >&2
  exit 1
fi

# ── Transport ───────────────────────────────────────────────────
export MCP_TRANSPORT="${MCP_TRANSPORT:-streamable-http}"
export MCP_HOST="${MCP_HOST:-0.0.0.0}"
export MCP_PORT="${MCP_PORT:-8000}"

# ── Filters ─────────────────────────────────────────────────────
export API_METHODS="${API_METHODS:-GET,POST}"
export API_PATHS_EXCLUDE="${API_PATHS_EXCLUDE:-}"
export API_MAX_RESPONSE_SIZE="${API_MAX_RESPONSE_SIZE:-500000}"

# ── Headers ─────────────────────────────────────────────────────
export API_HEADERS="${API_HEADERS:-}"

# ── Logging ─────────────────────────────────────────────────────
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

# ── Start ───────────────────────────────────────────────────────
echo "Starting MCP RESTful Adapter (streamable-http)" >&2
echo "  Spec:    $API_SPEC_URL" >&2
echo "  Backend: $API_BASE_URL" >&2
echo "  Listen:  http://${MCP_HOST}:${MCP_PORT}/mcp" >&2
echo "  Methods: $API_METHODS" >&2
echo "  Max response: ${API_MAX_RESPONSE_SIZE} bytes" >&2
echo "" >&2

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
exec uv run --project "$SCRIPT_DIR" mcp-restful-adapter
