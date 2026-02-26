# ── Custom client scopes ──────────────────────────────────────────────────────

# groups scope: exposes group membership as "groups" claim (simple names)
# Some applications prefer simple group names without full hierarchical paths.
# Example: "admins" instead of "/department/team/admins"
resource "keycloak_openid_client_scope" "groups" {
  realm_id               = keycloak_realm.demo.id
  name                   = "groups"
  description            = "Group membership (simple names)"
  include_in_token_scope = true
  consent_screen_text    = "Group membership information"
}

resource "keycloak_openid_group_membership_protocol_mapper" "groups" {
  realm_id            = keycloak_realm.demo.id
  client_scope_id     = keycloak_openid_client_scope.groups.id
  name                = "groups"
  claim_name          = "groups"
  full_path           = false # Simple names only
  add_to_id_token     = true
  add_to_access_token = true
  add_to_userinfo     = true
}

# groups_fullpath scope: exposes group membership with full hierarchical paths
# Some applications need full paths for hierarchical authorization.
# Example: "/department/team/admins" for nested group structures
resource "keycloak_openid_client_scope" "groups_fullpath" {
  realm_id               = keycloak_realm.demo.id
  name                   = "groups_fullpath"
  description            = "Group membership (full paths)"
  include_in_token_scope = true
  consent_screen_text    = "Group membership with full paths"
}

resource "keycloak_openid_group_membership_protocol_mapper" "groups_fullpath" {
  realm_id            = keycloak_realm.demo.id
  client_scope_id     = keycloak_openid_client_scope.groups_fullpath.id
  name                = "groups_fullpath"
  claim_name          = "groups_fullpath"
  full_path           = true # Full hierarchical paths
  add_to_id_token     = true
  add_to_access_token = true
  add_to_userinfo     = true
}

# organization scope: built-in by KC 26 when organizations_enabled = true.
# KC auto-creates it with its own mapper and attaches it as an optional scope
# to all clients — no further management needed here.
