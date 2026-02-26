# Smoke Tests

Pytest suite verifying the Keycloak playground after Tofu provisioning.

## Setup

```bash
# Tofu must already be applied
cd ..
docker compose up -d

cd smoke-tests
uv sync
pytest -v
```

## Test Suites

**`test_01_keycloak.py`** (no browser)

- Server reachability
- OIDC discovery, JWKS
- Token / authorization endpoints
- Realm config

```bash
pytest -v -m "not browser"
```

**`test_10_browser_keycloak.py`** (Playwright)

- Login flow
- Account console
- 2FA / TOTP

```bash
playwright install chromium
pytest -m browser -v
```

## Configuration

- `common.env` — shared settings
- `local.env` — local overrides (not tracked in git); copy from `local.env.example`

Default credentials (from Tofu provisioning):

```bash
KEYCLOAK__URL=http://localhost:8080
KEYCLOAK__REALM=demo
KEYCLOAK__USER=alice@democorp.com
KEYCLOAK__PASSWORD=Password123!
```

## Playwright Options

```bash
PLAYWRIGHT__HEADFUL=true pytest -m browser -v   # visible browser
PLAYWRIGHT__SLOWMO=500 pytest -m browser -v     # slow motion
```

## TOTP Codes

```bash
uv run python totp.py           # current code for alice (reads local.env)
uv run python totp.py <SECRET>  # specific secret
uv run python totp.py --watch   # live countdown
```

## Troubleshooting

**Connection refused**: `docker compose ps` — Keycloak must be healthy.

**Realm not found**: `cd ../tofu && tofu apply`.

**Browser tests fail**: `playwright install chromium`.

**Auth errors**: check users exist at http://localhost:8080/admin/demo/console.
