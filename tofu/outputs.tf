output "realm_name" {
  description = "The name of the created realm"
  value       = keycloak_realm.demo.realm
}

output "realm_id" {
  description = "The ID of the created realm"
  value       = keycloak_realm.demo.id
}

output "keycloak_urls" {
  description = "Important Keycloak URLs"
  value = {
    realm_url       = "${var.keycloak_url}/realms/${var.realm_name}"
    account_console = "${var.keycloak_url}/realms/${var.realm_name}/account"
    admin_console   = "${var.keycloak_url}/admin/${var.realm_name}/console"
    oidc_config     = "${var.keycloak_url}/realms/${var.realm_name}/.well-known/openid-configuration"
  }
}
