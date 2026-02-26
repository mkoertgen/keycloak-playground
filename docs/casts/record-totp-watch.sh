#!/usr/bin/env bash
# Record: TOTP code generation (single code display)
# Usage:  bash docs/casts/record-totp-watch.sh
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ../..)"

asciinema rec "$ROOT/docs/casts/totp-watch.cast" \
  --title "Keycloak Playground – TOTP code generator" \
  --cols 80 --rows 10 \
  --command "bash -c '
    cd \"$ROOT/smoke-tests\"
    echo \"=== TOTP Code Generator (alice@democorp.com) ===\"
    echo
    echo \"Current TOTP code:\"
    uv run python totp.py
    echo
    echo \"For live countdown: uv run python totp.py --watch\"
  '"
