# Keycloak Organizations (Keycloak 26+)
# Organizations allow multi-tenancy and domain-based user assignment
# https://www.keycloak.org/docs/latest/server_admin/#organizations
#
# Requires:
# - Keycloak 26+ with organizations feature enabled
# - Terraform Keycloak Provider with organization support (keycloak/keycloak >= 5.6)
# - organizations_enabled = true in realm settings (see realm.tf)

variable "organizations" {
  description = "Organizations for multi-tenancy (Keycloak 26+)"
  type = map(object({
    name        = string
    alias       = optional(string, "")
    domain      = string
    description = optional(string, "")
  }))
  default = {}
}

resource "keycloak_organization" "organizations" {
  for_each = var.organizations

  name        = each.value.name
  alias       = each.value.alias != "" ? each.value.alias : each.key
  description = each.value.description
  realm       = keycloak_realm.demo.id
  enabled     = true

  # Domain configuration (optional)
  # Only add domain if not empty
  dynamic "domain" {
    for_each = each.value.domain != "" ? [1] : []
    content {
      name     = each.value.domain
      verified = true
    }
  }
}

output "organizations" {
  description = "Created Keycloak organizations"
  value = {
    for key, org in keycloak_organization.organizations :
    key => {
      id     = org.id
      name   = org.name
      domain = org.domain
    }
  }
}
