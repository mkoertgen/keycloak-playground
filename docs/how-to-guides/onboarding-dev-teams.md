# Onboarding Dev Teams on Keycloak

A compact guide for integrating your application with Keycloak OIDC.

## Quick Reference: Test Client

The included [test-client](../../test-client/) demonstrates a complete OIDC integration with FastAPI. Use it as a reference implementation for your own apps.

**Key Features:**

- Authorization Code Flow with PKCE
- **Back-Channel Logout** (BCL) — critical for security
- Session management and tracking
- Admin API integration for session termination
- Prometheus metrics

## Critical: Back-Channel Logout

**What is it?** OIDC Back-Channel Logout allows Keycloak to notify your app when a user logs out or is disabled—enabling immediate session termination.

**Why it matters:** Without BCL, disabled users can continue accessing your app until their session expires (hours or days). This is a **security risk**.

### How to Implement

Your app needs an endpoint to receive logout tokens from Keycloak:

```python
@app.post("/backchannel-logout")
async def backchannel_logout(logout_token: str = Form()):
    """Keycloak calls this when a user logs out"""
    # 1. Verify and decode the logout token (JWT)
    claims = jwt.decode(logout_token, ...)

    # 2. Extract user identifier
    sid = claims.get("sid")  # Session ID
    sub = claims.get("sub")  # User ID

    # 3. Terminate the user's session in your app
    session_manager.logout(sid=sid, sub=sub)

    return Response(status_code=200)
```

See [test-client/app.py](../../test-client/app.py) for the full implementation.

### Configuration in Keycloak

In your OIDC client configuration (OpenTofu example):

```hcl
resource "keycloak_openid_client" "app" {
  realm_id  = keycloak_realm.demo.id
  client_id = "my-app"

  # Enable Back-Channel Logout
  backchannel_logout_url           = "https://my-app.example.com/backchannel-logout"
  backchannel_logout_session_required = true
  backchannel_logout_revoke_offline_sessions = true
}
```

### GitLab Example: What's Missing

GitLab and many other systems **do not support** OIDC Back-Channel Logout:

- [gitlab#449119](https://gitlab.com/gitlab-org/gitlab/-/issues/449119) — GitLab doesn't support BCL
- [omniauth_openid_connect#177](https://github.com/omniauth/omniauth_openid_connect/issues/177) — Underlying Ruby gem lacks support

**Result:** When users are disabled in Keycloak, GitLab sessions remain active. You need workarounds like the [automation service](user-lifecycle-automation.md) to terminate sessions via API.

## Working with Scopes

### Standard Scopes

Your app receives these claims by default:

- `sub` — User ID (UUID)
- `email` — Email address
- `name` — Full name
- `preferred_username` — Username

### Additional Scopes: Groups

Request the `groups` scope to receive group membership:

```python
# Client configuration
oauth.register(
    "keycloak",
    client_kwargs={
        "scope": "openid email profile groups"  # Add 'groups'
    }
)
```

The token will include:

```json
{
  "groups": ["/admins", "/developers", "/team-alpha"]
}
```

**Use case:** Role-based access control (RBAC) in your app.

**GitLab limitation:** GitLab can read the `groups` claim but **cannot** automatically assign users to GitLab groups. See [Gap 1: OIDC Group Assignment](user-lifecycle-automation.md#gap-1-oidc-group-assignment).

### Custom Scopes: Organizations

Add custom claims via Keycloak client scopes:

1. **Create Client Scope** (in Keycloak):
   - Name: `organization`
   - Protocol: `openid-connect`
   - Add Mapper: User Attribute → `organization` (token claim name: `org`)

2. **Assign to Client**:
   - Go to your client → Client Scopes tab
   - Add `organization` scope

3. **Request in your app**:

```python
oauth.register(
    "keycloak",
    client_kwargs={
        "scope": "openid email profile organization"
    }
)
```

Token includes:

```json
{
  "org": "acme-corp"
}
```

## Role-Based Access Control (RBAC)

Keycloak **Realm Roles** enable fine-grained authorization in your app. Roles are included in the JWT's `realm_access.roles` claim.

**Example JWT payload:**

```json
{
  "sub": "user-uuid",
  "realm_access": {
    "roles": ["admin", "user_read"]
  }
}
```

### Spring Boot Example

Extract realm roles and map them to Spring Security authorities:

```kotlin
class KeycloakRoleConverter : Converter<Jwt, Collection<GrantedAuthority>> {
    override fun convert(jwt: Jwt): Collection<GrantedAuthority> =
        jwt.claims["realm_access"]
            ?.let { it as Map<*, *> }
            ?.get("roles")
            ?.let { it as Collection<*> }
            ?.map { SimpleGrantedAuthority("ROLE_${it.toString().uppercase()}") }
            ?: emptyList()
}

@Configuration
class SecurityConfig {
    @Bean
    fun jwtAuthenticationConverter(): JwtAuthenticationConverter =
        JwtAuthenticationConverter().apply {
            setJwtGrantedAuthoritiesConverter(KeycloakRoleConverter())
        }
}
```

Then use `@PreAuthorize` for method-level authorization:

```kotlin
@GetMapping("/admin/users")
@PreAuthorize("hasRole('ADMIN')")
fun listUsers(): List<User> { ... }
```

**References:**

- [Baeldung: Keycloak with Spring Boot](https://www.baeldung.com/spring-boot-keycloak) — Comprehensive guide
- [Spring Security: Method Security](https://docs.spring.io/spring-security/reference/servlet/authorization/method-security.html) — Official docs
- [Keycloak: Securing Spring Boot Apps](https://www.keycloak.org/docs/latest/securing_apps/#_spring_boot_adapter) — Official Keycloak guide

## Framework Examples

### Single-Page Apps (SPAs)

**React / Vue / Angular:**

- [AuthJS (Auth.js)](https://authjs.dev/) — Universal auth library (recommended)
- [Oidc-client-ts](https://github.com/authts/oidc-client-ts) — TypeScript OIDC client
- [Vue OIDC Client](https://github.com/authjs/next-auth) — Vue 3 plugin

**Example (Auth.js):**

```ts
import { Issuer } from "openid-client";

const keycloak = await Issuer.discover("http://localhost:8080/realms/demo");
const client = new keycloak.Client({
  client_id: "spa-app",
  redirect_uris: ["http://localhost:3000/callback"],
  response_types: ["code"],
  token_endpoint_auth_method: "none", // Public client
});
```

### Backend Frameworks

**Spring Boot (Java):**

- [Spring Security OAuth2](https://spring.io/guides/tutorials/spring-boot-oauth2/) — Official guide
- Supports BCL via `spring-security-oauth2-client`

**Example (application.yml):**

```yaml
spring:
  security:
    oauth2:
      client:
        registration:
          keycloak:
            client-id: spring-app
            client-secret: ${CLIENT_SECRET}
            authorization-grant-type: authorization_code
            scope: openid,profile,email,groups
        provider:
          keycloak:
            issuer-uri: http://localhost:8080/realms/demo
            user-name-attribute: preferred_username
```

**Node.js / Express:**

- [Passport.js with passport-openidconnect](http://www.passportjs.org/packages/passport-openidconnect/)
- [node-oidc-provider](https://github.com/panva/node-oidc-provider) — Full OIDC server

**Django (Python):**

- [mozilla-django-oidc](https://github.com/mozilla/mozilla-django-oidc) — Mozilla's OIDC plugin

## Testing Your Integration

Use the [smoke-tests](smoke-tests.md) as a reference for testing:

1. **Login flow** — Authorization Code Flow with PKCE
2. **Token validation** — Verify signature, expiration, claims
3. **Back-Channel Logout** — Test logout token reception
4. **Session expiration** — Test token refresh

**Run smoke tests:**

```bash
cd smoke-tests
uv sync
uv run pytest
```

## Common Pitfalls

### 1. Missing Back-Channel Logout

**Symptom:** Disabled users can still access your app.

**Fix:** Implement `/backchannel-logout` endpoint and configure `backchannel_logout_url` in Keycloak.

### 2. CORS Errors (SPAs)

**Symptom:** Browser blocks token requests.

**Fix:** Configure CORS in Keycloak client settings:

- Web Origins: `http://localhost:3000` (your SPA URL)

### 3. Group Claims Not Received

**Symptom:** Token doesn't include `groups` array.

**Fix:**

- Add `groups` to requested scopes
- Ensure user is member of at least one group in Keycloak

### 4. Session Persistence After User Disable

**Symptom:** Keycloak doesn't revoke tokens when user is disabled.

**Fix:** See [Gap 3: Keycloak Session Persistence](user-lifecycle-automation.md#gap-3-keycloak-session-persistence) — you need explicit logout via Admin API.

## Next Steps

- **Production Hardening:** See [ADR on Keycloak Hardening](../explanation/adrs/) _(coming soon)_
- **User Lifecycle Automation:** [Onboarding & Offboarding](user-lifecycle-automation.md)
- **Observability:** [Monitoring Keycloak](observability.md)
