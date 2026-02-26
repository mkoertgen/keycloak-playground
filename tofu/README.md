# OpenTofu Configuration

Provisions a demo Keycloak realm with test users, OIDC clients, groups, and organizations.

## What's Provisioned

### Keycloak

- **Realm `demo`**: password policy, brute force protection, security headers, event logging, OTP/WebAuthn, organizations
- **OIDC client `demo-app`**: confidential, Authorization Code + PKCE, `http://localhost:3000`, backchannel logout support
- **Client scopes**:
  - `groups` - Group membership with simple names (e.g., "admins")
  - `groups_fullpath` - Group membership with hierarchical paths (e.g., "/department/admins")
- **Test users** (password: `Password123!`):
  - `alice` (<alice@democorp.com>) - Demo Corp member, admins + demo-team-alpha
  - `bob` (<bob@acme.example>) - Acme Inc member, developers + demo-team-beta
  - `admin` (<admin@test.local>) - Test Industries member, all groups
- **Groups**: `admins`, `developers`, `external`, `demo-team-alpha`, `demo-team-beta`
- **Organizations** (domain-based):
  - `Demo Corp` (democorp.com)
  - `Acme Inc` (acme.example)
  - `Test Industries` (test.local)

## Usage

```bash
# Keycloak must be running first
docker compose up -d keycloak

tofu init
tofu plan
tofu apply

# Outputs
tofu output
tofu output -raw test_client_secret

tofu destroy
```

## Configuration

All resources are configurable via Terraform variables declared next to the related resources/providers (`provider.tf`, `realm.tf`, `users.tf`, `organizations.tf`):

- **Organizations**: `var.organizations` - Define organizations with domains for multi-tenancy
- **Test Users**: `var.test_users` - Customize usernames, emails (matching org domains), names, passwords, and group memberships
- **Groups**: Defined in `groups.tf` - RBAC groups for OIDC claims and app authorization

Example - adding a custom user with group memberships:

```hcl
test_users = [
  {
    username   = "charlie"
    email      = "charlie@newcorp.io"
    first_name = "Charlie"
    last_name  = "Brown"
    groups     = ["developers", "demo-team-alpha"]
  }
]
```

- **2FA Policy**: `var.require_2fa` (default: `false`) - Make TOTP mandatory for all users
- **Themes**: `var.login_theme`, `var.account_theme`, `var.email_theme` - Customize UI

Example: Add a custom organization and user:

```hcl
organizations = {
  # Keep defaults...
  "custom-org" = {
    name        = "Custom Org"
    domain      = "custom.example"
    description = "Custom organization"
  }
}

test_users = [
  # Keep defaults...
  { username = "charlie", email = "charlie@custom.example", first_name = "Charlie", last_name = "Brown" }
]
```

Edit `terraform.tfvars` to change the Keycloak URL, credentials, realm name, or base domain.

## TOTP Pre-seeding

`users.tf` runs `seed_totp.py` for any user with `otp_secret` set in `terraform.tfvars`. The script calls `PUT /admin/realms/{realm}/users/{id}` with a `UserRepresentation` containing the TOTP credential (`secretEncoding: BASE32`).

## Testing

```bash
# OIDC discovery
curl http://localhost:8080/realms/demo/.well-known/openid-configuration | jq

# Admin console (master realm credentials: admin/admin)
open http://localhost:8080/admin/demo/console
```

See `../smoke-tests/` for the full test suite.

## Warning

Local development only. SSL disabled (`ssl_required = "none"`), plaintext credentials, no email verification.
