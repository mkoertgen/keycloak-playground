locals {
  oidc_clients = {
    "demo-app" = {
      name                   = "Demo App"
      root_url               = "http://localhost:3000"
      redirect_uris          = ["http://localhost:3000/*", "http://localhost:3000/callback"]
      backchannel_logout_url = "http://localhost:3000/backchannel-logout"
      is_public              = false
      additional_scopes      = []
      direct_access_grants   = true # Enable password grant for smoke tests
    }
  }
}

resource "keycloak_openid_client" "oidc_clients" {
  for_each = local.oidc_clients

  realm_id    = keycloak_realm.demo.id
  client_id   = each.key
  name        = each.value.name
  enabled     = true
  access_type = each.value.is_public ? "PUBLIC" : "CONFIDENTIAL"

  root_url            = each.value.root_url
  valid_redirect_uris = each.value.redirect_uris
  web_origins         = ["+"]

  backchannel_logout_url              = each.value.backchannel_logout_url
  backchannel_logout_session_required = true

  standard_flow_enabled        = true
  implicit_flow_enabled        = false
  direct_access_grants_enabled = each.value.direct_access_grants
  service_accounts_enabled     = !each.value.is_public

  pkce_code_challenge_method = "S256"
  client_authenticator_type  = "client-secret"
  consent_required           = false
}

resource "keycloak_openid_client_default_scopes" "oidc_clients" {
  for_each = local.oidc_clients

  realm_id  = keycloak_realm.demo.id
  client_id = keycloak_openid_client.oidc_clients[each.key].id

  default_scopes = concat(
    each.value.additional_scopes,
    # "organization" is auto-attached by KC 26 as an optional scope when organizations_enabled = true
    # "groups" provides simple group names, "groups_fullpath" provides hierarchical paths (see client-scopes.tf)
    ["profile", "email", "roles", "groups"]
  )
}

# Optional scopes that clients can explicitly request
resource "keycloak_openid_client_optional_scopes" "oidc_clients" {
  for_each = local.oidc_clients

  realm_id  = keycloak_realm.demo.id
  client_id = keycloak_openid_client.oidc_clients[each.key].id

  optional_scopes = [
    "address",
    "phone",
    "offline_access",
    "microprofile-jwt",
    "groups_fullpath", # Additional group claim with full hierarchical paths
  ]
}

output "oidc_client_secrets" {
  description = "OIDC client secrets (confidential clients only)"
  value = {
    for key, cfg in local.oidc_clients :
    key => keycloak_openid_client.oidc_clients[key].client_secret
    if !cfg.is_public
  }
  sensitive = true
}
