# Test Client - OIDC Demo with Back-Channel Logout

FastAPI OIDC client demonstrating proper OpenID Connect integration with Keycloak, including **OIDC Back-Channel Logout** support.

## Features

- ✅ **Authorization Code Flow with PKCE** - Modern OIDC authentication
- ✅ **Back-Channel Logout** - Automated session termination from Keycloak
- ✅ **Admin API** - Manual session termination (like GitLab's fallback)
- ✅ **Session Tracking** - In-memory session store for logout validation
- ✅ **Prometheus Metrics** - Observability via `/metrics` endpoint
- ✅ **OpenAPI/Swagger** - Interactive API docs at `/docs`
- ✅ **Health Check** - `/health` endpoint for monitoring

## Quick Start

```bash
# Start services (from repo root)
docker compose up -d

# Or for local development: Configure environment
cp .env.example .env
# Edit .env with your OIDC_CLIENT_SECRET (from: cd ../tofu && tofu output -json)

# Access test client
open http://localhost:3000

# Interactive API documentation
open http://localhost:3000/docs

# View logs
docker compose logs -f test-client
```

## API Documentation

All endpoints are automatically documented via OpenAPI/Swagger:

- **Swagger UI**: http://localhost:3000/docs (interactive, try-it-out)
- **ReDoc**: http://localhost:3000/redoc (clean documentation)

**Endpoint Categories:**

- **HTML**: `/`, `/login`, `/callback`, `/logout`, `/profile`
- **OIDC**: `/backchannel-logout` - Back-Channel Logout from Keycloak
- **API**: `/api/userinfo`, `/api/sessions` - JSON endpoints
- **Admin API**: `/admin/logout/*` - Manual session termination
- **Health**: `/health`, `/metrics` - Monitoring

## Back-Channel Logout Implementation

### What is Back-Channel Logout?

OIDC Back-Channel Logout is a server-to-server mechanism where the Identity Provider (Keycloak) notifies applications when a user logs out, without requiring browser interaction.

**Flow:**

1. User logs into test-client via Keycloak
2. Test-client stores session mapping: `{session_id → {sub, sid}}`
3. Admin clicks "Sign out" in Keycloak Admin Console
4. Keycloak sends POST request to `/backchannel-logout` with a `logout_token` (JWT)
5. Test-client validates token, finds matching session(s), and invalidates them

### Logout Token Structure

```json
{
  "iss": "http://keycloak:8080/realms/demo",
  "sub": "user-id-123",
  "aud": "demo-app",
  "iat": 1234567890,
  "exp": 1234567950,
  "sid": "keycloak-session-id",
  "events": {
    "http://schemas.openid.net/event/backchannel-logout": {}
  }
}
```

**Key properties:**

- Must contain `sid` (session ID) or `sub` (user ID)
- Must NOT contain `nonce` (differentiates logout tokens from ID tokens)
- Must contain `events` with backchannel-logout event type

### Implementation in `app.py`

```python
@app.route("/backchannel-logout", methods=["POST"])
def backchannel_logout():
    logout_token = request.form.get("logout_token")

    # Decode JWT (signature verification optional for demo)
    claims = jwt.decode(logout_token, None, claims_options={"verify_signature": False})

    # Validate: must NOT contain nonce
    if "nonce" in claims:
        return {"error": "Invalid logout_token"}, 400

    # Find sessions by sid (session ID) or sub (user ID)
    sid = claims.get("sid")
    sub = claims.get("sub")

    # Invalidate matching sessions
    for session_id, session_data in active_sessions.items():
        if (sid and session_data["sid"] == sid) or
           (sub and session_data["sub"] == sub):
            del active_sessions[session_id]

    return "", 200
```

### Configuration in Keycloak

Backchannel Logout URL is configured in the OIDC client settings (automated via OpenTofu):

```hcl
# tofu/oidc-clients.tf
resource "keycloak_openid_client" "demo_app" {
  backchannel_logout_url              = "http://localhost:3000/backchannel-logout"
  backchannel_logout_session_required = true
}
```

**Manual configuration:**

1. Admin Console → Clients → demo-app → Settings
2. Set **Backchannel logout URL**: `http://localhost:3000/backchannel-logout`
3. Enable **Backchannel logout session required**

## Testing Back-Channel Logout

### Test 1: Logout from Keycloak Admin Console

```bash
# 1. Login to test-client
open http://localhost:3000/login
# Complete authentication in browser

# 2. Admin Console: Force logout
open http://localhost:8080/admin/master/console/#/demo/users
# → Select user → Sessions tab → "Sign out" button

# 3. Watch test-client logs
docker compose logs -f test-client
# Expected output:
# [BACKCHANNEL] Logout received - sid: abc-123, sub: user-456
# [BACKCHANNEL] Removed 1 sessions: ['session-789']

# 4. Verify session removed
curl http://localhost:3000/api/sessions
# { "total": 0, "sessions": {} }
```

### Test 2: Multiple Sessions (Same User)

```bash
# 1. Login from different browsers/windows
# Browser 1: http://localhost:3000/login
# Browser 2: http://localhost:3000/login (incognito)

# 2. Check active sessions
curl http://localhost:3000/api/sessions
# { "total": 2, "sessions": {...} }

# 3. Logout one session from Keycloak
# Admin Console → User → Sessions → Sign out specific session

# 4. Verify only one session removed
curl http://localhost:3000/api/sessions
# { "total": 1, "sessions": {...} }
```

### Test 3: Compare with GitLab

To see the difference between proper implementation (test-client) and missing support (GitLab):

**Test-client (works):**

```bash
# Logout from Keycloak → Immediately logged out from app
docker compose logs -f test-client
# [BACKCHANNEL] Logout received - sid: ...
```

**GitLab (broken - requires manual cleanup):**

- GitLab does NOT support back-channel logout ([gitlab#449119](https://gitlab.com/gitlab-org/gitlab/-/issues/449119))
- User remains logged in until:
  - Session expires (hours/days)
  - Manual logout via GitLab Admin API
  - Server restart

This is why the `automation/` scripts exist - to manually terminate GitLab sessions.

## Admin API - Manual Session Termination

The test-client includes an **Admin API** similar to GitLab's admin logout endpoint. This demonstrates manual session termination when backchannel logout is unavailable.

### Endpoints

**Force logout by username:**

```bash
POST /admin/logout/<username>
Authorization: Bearer <admin-token>
```

**Force logout by subject ID (more precise):**

```bash
POST /admin/logout/sub/<sub>
Authorization: Bearer <admin-token>
```

### Configuration

Set admin token via environment variable:

```bash
export ADMIN_API_TOKEN=secret-admin-token
# Default: dev-admin-secret
```

### Usage Examples

**1. Logout by username:**

```bash
curl -X POST http://localhost:3000/admin/logout/john.doe \
  -H "Authorization: Bearer dev-admin-secret"

# Response:
# {
#   "success": true,
#   "username": "john.doe",
#   "sessions_terminated": 2
# }
```

**2. Logout by subject ID:**

```bash
# First, find the user's sub from /api/sessions
curl http://localhost:3000/api/sessions

# Then force logout
curl -X POST http://localhost:3000/admin/logout/sub/abc-123-def \
  -H "Authorization: Bearer dev-admin-secret"

# Response:
# {
#   "success": true,
#   "sub": "abc-123-def",
#   "sessions_terminated": 1
# }
```

**3. Verify sessions removed:**

```bash
curl http://localhost:3000/api/sessions
# { "total": 0, "sessions": {} }
```

### Comparison: Test-Client vs GitLab

| Feature            | Test-Client               | GitLab                          |
| ------------------ | ------------------------- | ------------------------------- |
| Backchannel Logout | ✅ Implemented            | ❌ Not supported ([#449119][1]) |
| Admin API Logout   | ✅ `/admin/logout/<user>` | ✅ `POST /users/:id/logout`     |
| Use Case           | Demo & fallback           | Required workaround             |

[1]: https://gitlab.com/gitlab-org/gitlab/-/issues/449119

**Why both?**

- **Backchannel logout**: Automated, instant, proper OIDC standard
- **Admin API**: Fallback when backchannel doesn't work (like GitLab)

This test-client demonstrates both approaches, while GitLab only has the manual API workaround.

## Production Considerations

### 1. Signature Verification

The demo skips JWT signature verification for simplicity. Production must verify:

```python
from authlib.jose import jwk

# Fetch Keycloak's JWKS
jwks = requests.get(f"{OIDC_ISSUER}/.well-known/openid-configuration").json()["jwks_uri"]
public_key = jwk.loads(jwks, key_id)

# Verify signature
claims = jwt.decode(
    logout_token,
    public_key,
    claims_options={"require": ["iss", "aud", "sid"]}
)
```

### 2. Distributed Session Store

The demo uses in-memory `active_sessions` dict. Production needs:

- **Redis** - Shared session store across instances
- **Database** - Persistent session tracking
- **Cache invalidation** - Broadcast logout to all app instances

### 3. Token Validation

Implement full validation per [OIDC Back-Channel Logout Spec](https://openid.net/specs/openid-connect-backchannel-1_0.html):

- ✅ Verify `iss` matches Keycloak issuer
- ✅ Verify `aud` contains client ID
- ✅ Check `exp` (expiration)
- ✅ Reject if `nonce` present
- ✅ Require `sid` or `sub`
- ✅ Verify `events` contains backchannel-logout event

### 4. Rate Limiting

Protect endpoint from abuse with FastAPI middleware:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/backchannel-logout")
@limiter.limit("100/minute")
async def backchannel_logout(request: Request, logout_token: str = Form(...)):
    ...
```

## Environment Variables

| Variable             | Default                            | Description                     |
| -------------------- | ---------------------------------- | ------------------------------- |
| `OIDC_ISSUER`        | `http://keycloak:8080/realms/demo` | Keycloak issuer URL             |
| `OIDC_CLIENT_ID`     | `demo-app`                         | OIDC client ID                  |
| `OIDC_CLIENT_SECRET` | (from Keycloak)                    | OIDC client secret              |
| `OIDC_REDIRECT_URI`  | `http://localhost:3000/callback`   | OAuth callback URL              |
| `APP_SECRET_KEY`     | (auto-generated)                   | Session encryption key (64 hex) |
| `ADMIN_API_TOKEN`    | `dev-admin-secret`                 | Admin API authorization         |

**Configuration via `.env` file** (Pydantic Settings with dotenv support):

```bash
# Copy example and edit
cp .env.example .env

# Get client secret from OpenTofu
cd ../tofu && tofu output -json | jq -r '.oidc_client_secrets.value."demo-app"'
```

## Dependencies

Defined in `pyproject.toml`:

```toml
[project]
dependencies = [
    "fastapi[standard]==0.115.0",              # Web framework + CLI tools
    "authlib==1.3.1",                          # OIDC client
    "cryptography>=41.0.0",                    # JWT handling (authlib dependency)
    "httpx==0.27.0",                           # Async HTTP client
    "jinja2==3.1.4",                           # Template engine
    "itsdangerous==2.2.0",                     # Session signing
    "prometheus-fastapi-instrumentator==7.0.0", # Metrics
    "python-multipart==0.0.9",                 # Form parsing
    "pydantic-settings>=2.0.0",                # Settings with .env support
]
```

## Development

```bash
# Local development (requires Keycloak running)
cd test-client

# Install dependencies (creates venv + installs from pyproject.toml)
uv sync

# Configure environment
cp .env.example .env

export OIDC_ISSUER=http://localhost:8080/realms/demo
export OIDC_CLIENT_ID=demo-app
export OIDC_CLIENT_SECRET=$(cd ../tofu && tofu output -json | jq -r '.oidc_client_secrets.value."demo-app"')

# Or use .env file (automatically loaded by Pydantic Settings)

# Run development server with auto-reload
uv run fastapi dev app.py --port 3000
# Access: http://localhost:3000
# API docs: http://localhost:3000/docs
```

## References

- [OIDC Back-Channel Logout Spec](https://openid.net/specs/openid-connect-backchannel-1_0.html)
- [Keycloak Logout Documentation](https://www.keycloak.org/docs/latest/securing_apps/index.html#logout)
- [GitLab Issue #449119](https://gitlab.com/gitlab-org/gitlab/-/issues/449119) - Missing support
- [omniauth_openid_connect #177](https://github.com/omniauth/omniauth_openid_connect/issues/177) - Gem limitation
