# Provisioning (OpenTofu)

[OpenTofu](https://opentofu.org/) bootstraps the entire Keycloak demo realm from scratch.
Nothing needs to be configured in the Admin UI by hand.

## What gets provisioned

| Resource                  | Details                                                                                               |
| ------------------------- | ----------------------------------------------------------------------------------------------------- |
| Realm `demo`              | Password policy, brute-force protection, security headers, event logging, OTP/WebAuthn, Organizations |
| OIDC client `test-client` | Confidential, Authorization Code + PKCE, `http://localhost:3000`, service account                     |
| Client scope `groups`     | `GroupMembershipMapper` → `groups` claim                                                              |
| Users                     | `testuser1`, `testuser2`, `admin` — password `Password123!`, TOTP pre-seeded                          |

## Gallery

|      Keycloak Admin Console – demo realm       |
| :--------------------------------------------: |
| ![Admin Console](img/keycloak-admin-realm.png) |

## Terminal walkthrough

<!-- asciinema cast placeholder — upload and replace the link below
[![asciicast](https://asciinema.org/a/REPLACE_ME.svg)](https://asciinema.org/a/REPLACE_ME)
Record with: bash docs/casts/record-tofu.sh
-->

```bash
# Keycloak must be running first
docker compose up -d keycloak

cd tofu
tofu init
tofu plan
tofu apply

# Inspect outputs
tofu output
tofu output -raw test_client_secret
```

## Tear down

```bash
cd tofu
tofu destroy              # remove all Keycloak resources

# Stop containers
docker compose down       # keep volumes
docker compose down -v    # also wipe Keycloak DB
```

## Configuration

Edit `tofu/terraform.tfvars`:

```hcl
keycloak_url      = "http://localhost:8080"
admin_username    = "admin"
admin_password    = "admin"
realm_name        = "demo"
base_domain       = "localhost"
custom_theme      = false   # true → activates keycloakify theme
```

## TOTP pre-seeding

`users.tf` calls `seed_totp.py` for every user that has `otp_secret` set in
`terraform.tfvars`. The script uses `PUT /admin/realms/{realm}/users/{id}` with a
`UserRepresentation` containing the TOTP credential (`secretEncoding: BASE32`).

This lets `testuser1` authenticate with a stable OTP secret across `tofu destroy` +
`tofu apply` cycles — required for repeatable automated smoke tests.

## OIDC smoke check

```bash
# Discovery document
curl http://localhost:8080/realms/demo/.well-known/openid-configuration | jq

# Token endpoint (client credentials)
CLIENT_SECRET=$(cd tofu && tofu output -raw test_client_secret)
curl -s -X POST http://localhost:8080/realms/demo/protocol/openid-connect/token \
  -d "grant_type=client_credentials" \
  -d "client_id=test-client" \
  -d "client_secret=$CLIENT_SECRET" | jq .access_token
```

## Resources

- [tofu/README.md](../tofu/README.md) — full reference
- [OpenTofu docs](https://opentofu.org/docs/)
- [terraform-provider-keycloak](https://registry.terraform.io/providers/keycloak/keycloak/latest/docs)
