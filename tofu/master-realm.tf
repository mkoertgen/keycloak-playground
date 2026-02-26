# Master realm hardening
#
# The built-in "master" realm is created by Keycloak itself. We manage it as a
# resource (not just a data source) so we can enforce brute-force detection,
# password policy, and security headers.
#
# The `import` block below tells OpenTofu to adopt the pre-existing master realm
# on the very first `tofu apply` — no manual `tofu import` command needed.
#
# ── Master realm: Required but minimize exposure ──────────────────────────────
# 
# ⚠️  You CANNOT disable the master realm - it's required for:
#     • Creating/deleting realms
#     • Managing realm-level administrators
#     • Global Keycloak configuration
# 
# ✅  However, you SHOULD minimize its attack surface:
# 
# 1. Use per-realm admin permissions for day-to-day operations
#    → Each realm can have its own admins who only manage that realm
#    → Reduces need for master realm access
#    → See: https://www.keycloak.org/docs/latest/server_admin/index.html#_per_realm_admin_permissions
# 
# 2. Hide the admin console behind internal-only hostname (KC_HOSTNAME_ADMIN)
#    → Admin console (/admin/*) only accessible on internal domain/VPN
#    → Public hostname returns 404 for admin paths
#    → See below for configuration
# 
# 3. Minimize master realm users
#    → Only keep infrastructure/IaC service accounts
#    → Human admins use per-realm admin permissions instead
# 
# 4. Never expose master realm login pages publicly
#    → /realms/master/account/* should be internal-only
# ─────────────────────────────────────────────────────────────────────────────
#
# ── Hiding the admin console in production ────────────────────────────────────
# Keycloak 26+ supports a dedicated admin hostname via KC_HOSTNAME_ADMIN.
# When set, the admin console (/admin/*) and master-realm account console are
# ONLY served on that hostname — the public hostname returns 404 for those paths.
#
# Production pattern (e.g. in your Keycloak Operator CRD or Nix module):
#   KC_HOSTNAME=https://auth.example.com
#   KC_HOSTNAME_ADMIN=https://auth-admin.internal.example.com
#
# The admin hostname is then:
#   - only reachable via VPN / internal DNS
#   - or fronted by a load-balancer that restricts source IPs
#
# For Docker Compose local dev this is less relevant, but the env var is
# documented in docker-compose.yaml as a commented-out example.
# ─────────────────────────────────────────────────────────────────────────────

import {
  to = keycloak_realm.master
  id = "master"
}

resource "keycloak_realm" "master" {
  realm   = "master"
  enabled = true

  # ALWAYS PROTECTED: Master realm is critical infrastructure
  lifecycle {
    prevent_destroy = true
  }

  # Strong password policy (from locals — even stronger than demo)
  password_policy = local.password_policy_strong

  # SMTP configuration: Reuses cross-cutting email/SMTP variables from variables.tf
  # Enable with var.email_enabled = true for password reset emails to master realm admins
  dynamic "smtp_server" {
    for_each = var.email_enabled ? [1] : []
    content {
      host              = var.smtp_host
      port              = var.smtp_port
      from              = var.smtp_from
      from_display_name = var.smtp_from_display_name
      starttls          = var.smtp_starttls

      auth {
        username = var.smtp_username
        password = var.smtp_password
      }
    }
  }

  # Security defenses: headers and brute force detection (from realm-security.tf)
  # Master realm uses stricter brute force protection (5 failures vs 10)
  security_defenses {
    headers {
      x_frame_options                     = local.security_headers.x_frame_options
      content_security_policy             = local.security_headers.content_security_policy
      content_security_policy_report_only = local.security_headers.content_security_policy_report_only
      x_content_type_options              = local.security_headers.x_content_type_options
      x_robots_tag                        = local.security_headers.x_robots_tag
      x_xss_protection                    = local.security_headers.x_xss_protection
      strict_transport_security           = local.security_headers.strict_transport_security
    }

    brute_force_detection {
      permanent_lockout                = local.brute_force_detection.permanent_lockout
      max_login_failures               = 5 # Stricter than standard (10)
      wait_increment_seconds           = local.brute_force_detection.wait_increment_seconds
      quick_login_check_milli_seconds  = local.brute_force_detection.quick_login_check_milli_seconds
      minimum_quick_login_wait_seconds = local.brute_force_detection.minimum_quick_login_wait_seconds
      max_failure_wait_seconds         = local.brute_force_detection.max_failure_wait_seconds
      failure_reset_time_seconds       = local.brute_force_detection.failure_reset_time_seconds
    }
  }
}

# Admin audit log for the master realm — tracks all admin console actions.
# More important here than on the demo realm since this is the admin surface.
resource "keycloak_realm_events" "master" {
  realm_id = keycloak_realm.master.id

  # No regular user logins on master → user events not needed
  events_enabled    = false
  events_expiration = 0

  events_listeners = ["jboss-logging"]

  # Admin events: capture every configuration change with full request details.
  # Essential for audit trails and incident response.
  admin_events_enabled         = true
  admin_events_details_enabled = true
}

# ── Master realm: static admin users ─────────────────────────────────────────

variable "master_admin_users" {
  description = "Static admin users to create in the master realm (receive admin role)"
  type = list(object({
    username   = string
    email      = string
    first_name = optional(string, "")
    last_name  = optional(string, "")
    password   = optional(string, "ChangeMe123!")
    temporary  = optional(bool, true)
  }))
  default = []
}

locals {
  master_admin_users_map = { for u in var.master_admin_users : u.username => u }
}

# Destruction lock: Conditionally protect master admin users
# Uses random_id keeper pattern as workaround for variable limitation in lifecycle blocks.
# Set var.prevent_destroy = true in production to protect critical admin accounts.
resource "random_id" "master_admin_users_lock" {
  for_each = var.prevent_destroy ? local.master_admin_users_map : {}

  byte_length = 8

  keepers = {
    user_id = keycloak_user.master_admin_users[each.key].id
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "keycloak_user" "master_admin_users" {
  for_each = local.master_admin_users_map

  realm_id       = keycloak_realm.master.id
  username       = each.key
  enabled        = true
  email          = each.value.email
  email_verified = true
  first_name     = each.value.first_name
  last_name      = each.value.last_name

  initial_password {
    value     = each.value.password
    temporary = each.value.temporary # true by default → force password change on first login
  }

  # Enforce 2FA for Terraform-managed master realm admins
  # (Does not affect existing users outside Terraform scope)
  required_actions = ["CONFIGURE_TOTP"]
}

# Grant each admin user the built-in "admin" role of the master realm
data "keycloak_role" "master_admin_role" {
  realm_id = keycloak_realm.master.id
  name     = "admin"
}

resource "keycloak_user_roles" "master_admin_users" {
  for_each = local.master_admin_users_map

  realm_id = keycloak_realm.master.id
  user_id  = keycloak_user.master_admin_users[each.key].id

  role_ids = [data.keycloak_role.master_admin_role.id]
}
