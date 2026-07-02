#!/usr/bin/env bash
# Publish mcp-restful-adapter to PyPI
#
# Prerequisites:
#   pip install build twine
#   Set TWINE_PASSWORD to your PyPI API token
#
# Usage:
#   ./scripts/publish.sh

set -euo pipefail

echo "🧹 Cleaning old artifacts..."
rm -rf dist/ build/
rm -rf *.egg-info/ src/*.egg-info/ 2>/dev/null || true

echo "🔨 Building package..."
uv build

echo "✅ Checking package..."
uv run twine check dist/*

echo "🚀 Uploading to PyPI..."
uv run twine upload dist/*

echo "🎉 Published successfully!"
