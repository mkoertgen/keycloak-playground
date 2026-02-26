# Getting Started with Keycloak Playground

This tutorial will guide you through setting up and exploring the Keycloak playground environment from scratch. By the end, you'll have a working Keycloak instance with a custom theme, automated tests, and full observability.

## Prerequisites

- **Docker** (with Compose V2)
- **Git**
- **OpenTofu** (or Terraform) installed

## Step 1: Clone and Start Services

```bash
git clone https://github.com/mkoertgen/keycloak-playground.git
cd keycloak-playground
docker compose up -d
```

This starts:

- **Keycloak** at http://localhost:8080 (admin/admin)
- **Test Client** at http://localhost:3000
- **Grafana** at http://localhost:3001 (admin/admin)
- **Prometheus** at http://localhost:9090

Wait for Keycloak to start (check with `docker compose logs -f keycloak`).

## Step 2: Provision the Demo Realm

```bash
cd tofu
tofu init
tofu plan
tofu apply -auto-approve
```

This creates:

- A `demo` realm with security policies
- Three test users: `alice@democorp.com`, `bob@democorp.com`, `admin@democorp.com` (all with password `Password123!`)
- An OIDC client `test-client` for the demo app
- Pre-configured TOTP secrets for 2FA testing

## Step 3: Explore Keycloak Admin Console

1. Open http://localhost:8080
2. Click **Administration Console** → log in with `admin` / `admin`
3. Switch to the **demo** realm (dropdown in top-left)
4. Explore:
   - **Users** → see `alice`, `bob`, `admin`
   - **Clients** → see `test-client` OIDC configuration
   - **Realm settings** → Events → see event logging configuration

## Step 4: Test OIDC Authentication

1. Open http://localhost:3000
2. Click **Log in**
3. Log in as `alice@democorp.com` / `Password123!`
4. Enter the **6-digit TOTP code** (use the pre-seeded secret `KNGW25ZUNVHU44JYNJBVKZDDMZGWQZCQ` in your authenticator app like Google Authenticator or Authy)
5. You'll see your user info and access token

Try logging out and logging back in to see the full OIDC flow.

## Step 5: Explore Observability

1. Open **Grafana** at http://localhost:3001 (admin/admin)
2. Navigate to **Dashboards** → **Keycloak Metrics**
3. See metrics for:
   - Active sessions
   - Authentication events
   - Login successes/failures
   - User registrations

Open **Prometheus** at http://localhost:9090 to see raw metrics and targets.

## Step 6: Run Smoke Tests

```bash
cd smoke-tests
uv sync

# Copy and edit test configuration
cp local.env.example local.env

# Run tests
uv run pytest -v
```

The tests verify:

- Keycloak health and OIDC discovery
- Token endpoint authentication
- Browser-based login flow with Playwright
- Test client homepage and logout

## Step 7: Customize the Theme

```bash
cd keycloak/theme
npm install
npm run dev
```

This starts a **live development server** at http://localhost:5173. The dev server proxies Keycloak and hot-reloads your React components on every save.

Try modifying files in `src/login/` and see changes instantly in your browser.

## Next Steps

Now that you have the playground running, explore these guides:

- **[Provisioning](../how-to-guides/provisioning.md)** - Learn more about OpenTofu configuration
- **[Custom Theme](../how-to-guides/theme.md)** - Deep dive into Keycloakify theme development
- **[Smoke Tests](../how-to-guides/smoke-tests.md)** - Write additional test cases
- **[Observability](../how-to-guides/observability.md)** - Configure alerts and dashboards
- **[Explanation: Security Architecture](../explanation/adrs/0001-keycloak-security-architecture.md)** - Understand design decisions

## Cleanup

```bash
# Stop services (keep volumes)
docker compose down

# Stop services and remove all data
docker compose down -v

# Destroy provisioned Keycloak resources
cd tofu && tofu destroy
```
