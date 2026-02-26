#!/usr/bin/env bash
# Record: Keycloakify live-reload dev session
# Usage:  bash docs/casts/record-theme-dev.sh
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ../..)"

asciinema rec "$ROOT/docs/casts/theme-dev.cast" \
  --title "Keycloak Playground – Keycloakify live dev" \
  --cols 120 --rows 25 \
  --command "bash -c '
    cd \"$ROOT/keycloak/theme\"
    echo \"=== Keycloakify – live inject into Keycloak ===\"
    echo
    echo \"Starting dev server at http://localhost:5173 ...\"
    echo \"(live-injects into Keycloak, no jar build needed)\"
    echo
    timeout 8 npm run dev || true
    echo
    echo \"Build & stage jar for production:\"
    echo \"  npm run build-keycloak-theme\"
    echo \"  docker compose restart keycloak\"
    echo \"  cd ../../tofu && tofu apply  # themes configured in terraform.tfvars\"
  '"
