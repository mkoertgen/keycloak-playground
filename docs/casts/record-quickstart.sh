#!/usr/bin/env bash
# Record: quick start (docker compose up)
# Usage:  bash docs/casts/record-quickstart.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ..)"

asciinema rec docs/casts/quickstart.cast \
  --title "Keycloak Playground – Quick Start (docker compose up)" \
  --cols 120 --rows 30 \
  --command "bash -c '
    echo \"=== Keycloak Playground – Quick Start ===\"
    echo
    docker compose pull --quiet
    docker compose up -d
    echo
    echo \"Waiting for Keycloak to be healthy...\"
    until curl -sf http://localhost:8080/health/ready > /dev/null 2>&1; do printf .; sleep 2; done
    echo
    docker compose ps
    echo
    echo \"Keycloak ready at http://localhost:8080  (admin/admin)\"
  '"
