#!/usr/bin/env bash
# Record: tofu init + plan + apply
# Usage:  bash docs/casts/record-tofu.sh
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ../..)"

asciinema rec "$ROOT/docs/casts/tofu-apply.cast" \
  --title "Keycloak Playground – OpenTofu provisioning" \
  --cols 120 --rows 35 \
  --command "bash -c '
    cd \"$ROOT/tofu\"
    echo \"=== OpenTofu – Keycloak Playground provisioning ===\"
    echo
    tofu init -upgrade
    echo
    tofu plan
    echo
    tofu apply -auto-approve
    echo
    echo \"--- outputs ---\"
    tofu output
  '"
