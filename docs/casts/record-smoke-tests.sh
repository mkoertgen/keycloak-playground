#!/usr/bin/env bash
# Record: pytest smoke tests (API only, skip browser due to headless issues in asciinema)
# Usage:  bash docs/casts/record-smoke-tests.sh
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ../..)"

asciinema rec "$ROOT/docs/casts/smoke-tests.cast" \
  --title "Keycloak Playground – pytest smoke tests" \
  --cols 120 --rows 35 \
  --command "bash -c '
    cd \"$ROOT/smoke-tests\"
    echo \"=== Keycloak Playground – Smoke Tests ===\"
    echo
    uv sync --quiet
    echo
    echo \"Running API tests (browser tests require display)...\"
    uv run pytest -v -m \"not browser\" --tb=short
    echo
    echo \"✓ All API tests passed\"
    echo
    echo \"To run browser tests locally:\"
    echo \"  uv run pytest -v -m browser\"
  '"
