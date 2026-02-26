# ── Demo realm: test users ────────────────────────────────────────────────────

variable "test_users" {
  description = "Demo users to create in the demo realm"
  type = list(object({
    username   = string
    email      = optional(string)
    first_name = optional(string, "")
    last_name  = optional(string, "")
    password   = optional(string, "Password123!")
    temporary  = optional(bool, false)
    groups     = optional(list(string), [])
    # Pre-seeded TOTP secret (base32). When set, a TOTP credential is created via
    # the Admin REST API on first apply, so the user can log in with 2FA immediately
    # without going through the enrolment UI. Must match KEYCLOAK__OTP_SECRET in smoke tests.
    otp_secret = optional(string)
  }))
  default = [
    { username = "alice", email = "alice@democorp.com", first_name = "Alice", last_name = "Smith", groups = ["admins", "demo-team-alpha"] },
    { username = "bob", email = "bob@acme.example", first_name = "Bob", last_name = "Johnson", groups = ["developers", "demo-team-beta"] },
    { username = "admin", email = "admin@test.local", first_name = "Admin", last_name = "User", groups = ["admins", "developers", "external", "demo-team-alpha", "demo-team-beta"] },
  ]
}

locals {
  test_users_map = { for u in var.test_users : u.username => u }
}

resource "keycloak_user" "test_users" {
  for_each = local.test_users_map

  realm_id       = keycloak_realm.demo.id
  username       = each.key
  enabled        = true
  email          = each.value.email != null ? each.value.email : "${each.key}@example.com"
  email_verified = true
  first_name     = each.value.first_name
  last_name      = each.value.last_name

  initial_password {
    value     = each.value.password
    temporary = each.value.temporary
  }
}

output "test_users" {
  description = "Test user accounts created in the demo realm"
  value = {
    for username, user in keycloak_user.test_users : username => {
      email      = user.email
      first_name = user.first_name
      last_name  = user.last_name
    }
  }
}

# Pre-seed TOTP credentials for users that have otp_secret defined.
# Idempotent: deletes and re-creates the credential whenever the secret or user ID changes.
resource "terraform_data" "seed_totp" {
  for_each = { for u in var.test_users : u.username => u if u.otp_secret != null }

  triggers_replace = [
    keycloak_user.test_users[each.key].id,
    sha256(each.value.otp_secret),
  ]

  provisioner "local-exec" {
    command = "python ${path.module}/seed_totp.py --url ${var.keycloak_url} --realm ${var.realm_name} --admin-user ${var.keycloak_admin_username} --admin-password ${var.keycloak_admin_password} --username ${each.key} --secret ${each.value.otp_secret}"
  }
}
