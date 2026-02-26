# Keycloak Groups for RBAC and Authorization
#
# Groups are exported via OIDC "groups" claim (via client-scopes.tf) and can be used for:
# - Application authorization and role mapping
# - Fine-grained access control in downstream applications
# - Team/department organization
#
# Two group claim variants are available:
# - groups_fullpath: Full hierarchical paths (e.g., "/parent/child")
# - groups: Simple group names (e.g., "child")
#
# Some applications prefer full paths for hierarchical authorization,
# others prefer simple names for easier mapping.

variable "groups" {
  description = "Keycloak groups for RBAC and authorization"
  type = map(object({
    description = string
  }))
  default = {}
}

resource "keycloak_group" "groups" {
  for_each = var.groups

  realm_id = keycloak_realm.demo.id
  name     = each.key

  # Groups are flat (no parent_id) for simplicity
  # Can be nested later if needed
}

# Group memberships (one resource per group, with list of members)
# Members are dynamically computed from user variables (groups field)
resource "keycloak_group_memberships" "memberships" {
  for_each = var.groups

  realm_id = keycloak_realm.demo.id
  group_id = keycloak_group.groups[each.key].id

  members = [
    for user in var.test_users :
    keycloak_user.test_users[user.username].username
    if contains(user.groups, each.key)
  ]

  # Ensure all users are created before assigning memberships
  depends_on = [keycloak_user.test_users]
}

output "groups" {
  description = "Created Keycloak groups"
  value = {
    for name, group in keycloak_group.groups :
    name => {
      id   = group.id
      path = group.path
    }
  }
}
