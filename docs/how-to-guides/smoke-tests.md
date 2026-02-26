# Smoke Tests

Pytest suite verifying the full Keycloak playground stack after provisioning.

## Gallery

|      Headful browser test (Playwright)       |             JUnit HTML report              |
| :------------------------------------------: | :----------------------------------------: |
| ![Browser test](img/smoke-tests-browser.png) | ![JUnit report](img/smoke-tests-junit.png) |

## Terminal walkthrough

<!-- asciinema cast placeholder — upload and replace the link below
[![asciicast](https://asciinema.org/a/REPLACE_ME.svg)](https://asciinema.org/a/REPLACE_ME)
Record with: bash docs/casts/record-smoke-tests.sh
-->

## Prerequisites

```bash
docker compose up -d     # all services
cd tofu && tofu apply    # provision demo realm
```

## Setup

```bash
cd smoke-tests
uv sync
cp local.env.example local.env   # edit if needed
```

## Run all tests

```bash
uv run pytest -v
```

## Test suites

### `test_01_keycloak.py` — API / no browser

- Server reachability & health
- OIDC discovery, JWKS endpoint
- Token endpoint (client credentials)
- Authorization endpoint structure
- Demo realm configuration

```bash
uv run pytest -v -m "not browser"
```

### `test_02_apps_health.py` — service health

- Test client reachable
- Grafana reachable
- Prometheus reachable

### `test_10_browser_keycloak.py` — Playwright (browser)

- Full login flow (username + TOTP)
- Account console access
- 2FA / TOTP re-enrollment
- Logout

```bash
playwright install chromium   # once
uv run pytest -v -m browser
```

## Playwright options

```bash
PLAYWRIGHT__HEADFUL=true  uv run pytest -m browser -v   # visible browser window
PLAYWRIGHT__SLOWMO=500    uv run pytest -m browser -v   # slow-motion (ms)
```

## HTML report

```bash
# Install reporter
uv add --dev pytest-html

# Generate
uv run pytest -v --html=report.html --self-contained-html

# Open
start report.html     # Windows
open  report.html     # macOS
xdg-open report.html  # Linux
```

## TOTP live codes

```bash
uv run python totp.py           # current code for testuser1
uv run python totp.py <SECRET>  # specific secret
uv run python totp.py --watch   # live countdown
```

<!-- asciinema cast placeholder — upload and replace the link below
[![asciicast](https://asciinema.org/a/REPLACE_ME.svg)](https://asciinema.org/a/REPLACE_ME)
Record with: bash docs/casts/record-totp-watch.sh
-->

## Configuration

| File                | Purpose                                   |
| ------------------- | ----------------------------------------- |
| `common.env`        | Shared defaults (URL, realm, credentials) |
| `local.env`         | Local overrides — not tracked in git      |
| `local.env.example` | Template for `local.env`                  |

Default values (match Tofu provisioning):

```ini
KEYCLOAK__URL=http://localhost:8080
KEYCLOAK__REALM=demo
KEYCLOAK__USER=testuser1@example.com
KEYCLOAK__PASSWORD=Password123!
```

## Troubleshooting

| Symptom            | Fix                                                         |
| ------------------ | ----------------------------------------------------------- |
| Connection refused | `docker compose ps` — check all services are healthy        |
| Realm not found    | `cd tofu && tofu apply`                                     |
| Browser tests fail | `playwright install chromium`                               |
| Auth errors        | Verify users at http://localhost:8080/admin/demo/console    |
| TOTP failure       | Sync system clock; check `otp_secret` in `terraform.tfvars` |

## Resources

- [smoke-tests/README.md](../smoke-tests/README.md)
- [pytest docs](https://docs.pytest.org/)
- [Playwright for Python](https://playwright.dev/python/)
