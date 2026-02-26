# ══════════════════════════════════════════════════════════════════════════════
# Multi-Factor Authentication (MFA) Configuration
# ══════════════════════════════════════════════════════════════════════════════
#
# This file configures conditional 2FA for both demo and master realms:
#
# 1. Browser authentication flow with conditional 2FA (OTP or WebAuthn)
#    - Users WITH 2FA credentials: Challenged for second factor
#    - Users WITHOUT 2FA: Authenticate with password only
#    - Important for IaC automation (service accounts without 2FA)
#
# 2. CONFIGURE_TOTP required action (default for new users)
#    - Enforces 2FA enrollment on first login
#    - Applied to both demo and master realms
#
# Flow structure:
#   [ALTERNATIVE]  Cookie
#   [ALTERNATIVE]  Identity Provider Redirector
#   [ALTERNATIVE]  browser-with-otp-forms (subflow)
#     [REQUIRED]     Condition - User Configured
#     [REQUIRED]     Username/Password Form
#     [CONDITIONAL]  browser-with-otp-conditional (subflow)
#       [REQUIRED]     Condition - Credential
#       [ALTERNATIVE]  OTP Form
#       [ALTERNATIVE]  WebAuthn Authenticator
#       [REQUIRED]     Condition - User Configured

locals {
  auth_flow_realms = {
    demo   = keycloak_realm.demo.id
    master = keycloak_realm.master.id
  }
}

resource "keycloak_authentication_flow" "browser_otp" {
  for_each = local.auth_flow_realms

  realm_id    = each.value
  alias       = "browser-with-otp"
  description = "Browser flow with conditional 2FA (OTP or WebAuthn when configured)"
  provider_id = "basic-flow"
}

# 1. Cookie — skip full auth if valid session cookie exists
resource "keycloak_authentication_execution" "cookie" {
  for_each = local.auth_flow_realms

  realm_id          = each.value
  parent_flow_alias = keycloak_authentication_flow.browser_otp[each.key].alias
  authenticator     = "auth-cookie"
  requirement       = "ALTERNATIVE"
}

# 2. Identity Provider Redirector — for SSO/IdP federation
resource "keycloak_authentication_execution" "idp_redirector" {
  for_each = local.auth_flow_realms

  realm_id          = each.value
  parent_flow_alias = keycloak_authentication_flow.browser_otp[each.key].alias
  authenticator     = "identity-provider-redirector"
  requirement       = "ALTERNATIVE"
}

# 3. Forms subflow — condition + password + conditional 2FA
resource "keycloak_authentication_subflow" "forms" {
  for_each = local.auth_flow_realms

  realm_id          = each.value
  parent_flow_alias = keycloak_authentication_flow.browser_otp[each.key].alias
  alias             = "browser-with-otp-forms"
  provider_id       = "basic-flow"
  requirement       = "ALTERNATIVE"
}

# 3.1 Condition: User Configured — guards the forms subflow entry
resource "keycloak_authentication_execution" "forms_condition" {
  for_each = local.auth_flow_realms

  realm_id          = each.value
  parent_flow_alias = keycloak_authentication_subflow.forms[each.key].alias
  authenticator     = "conditional-user-configured"
  requirement       = "REQUIRED"
}

# 3.2 Username / Password
resource "keycloak_authentication_execution" "username_password" {
  for_each = local.auth_flow_realms

  realm_id          = each.value
  parent_flow_alias = keycloak_authentication_subflow.forms[each.key].alias
  authenticator     = "auth-username-password-form"
  requirement       = "REQUIRED"
}

# 3.3 Conditional 2FA subflow — entered only when a 2FA credential exists
resource "keycloak_authentication_subflow" "conditional_otp" {
  for_each = local.auth_flow_realms

  realm_id          = each.value
  parent_flow_alias = keycloak_authentication_subflow.forms[each.key].alias
  alias             = "browser-with-otp-conditional"
  provider_id       = "basic-flow"
  requirement       = "CONDITIONAL"
}

# 3.3.1 Condition: Credential — only challenge if a 2FA credential is configured
resource "keycloak_authentication_execution" "otp_condition" {
  for_each = local.auth_flow_realms

  realm_id          = each.value
  parent_flow_alias = keycloak_authentication_subflow.conditional_otp[each.key].alias
  authenticator     = "conditional-credential"
  requirement       = "REQUIRED"
}

# 3.3.2 OTP Form — TOTP/HOTP authenticator app
resource "keycloak_authentication_execution" "otp_form" {
  for_each = local.auth_flow_realms

  realm_id          = each.value
  parent_flow_alias = keycloak_authentication_subflow.conditional_otp[each.key].alias
  authenticator     = "auth-otp-form"
  requirement       = "ALTERNATIVE"
}

# 3.3.3 WebAuthn — FIDO2 security key or platform authenticator (Touch ID, Windows Hello, …)
resource "keycloak_authentication_execution" "webauthn" {
  for_each = local.auth_flow_realms

  realm_id          = each.value
  parent_flow_alias = keycloak_authentication_subflow.conditional_otp[each.key].alias
  authenticator     = "webauthn-authenticator"
  requirement       = "ALTERNATIVE"
}

# 3.3.4 Condition: User Configured — final gate; ensures the subflow is skipped
#        entirely when no valid 2FA response was provided
resource "keycloak_authentication_execution" "otp_user_configured" {
  for_each = local.auth_flow_realms

  realm_id          = each.value
  parent_flow_alias = keycloak_authentication_subflow.conditional_otp[each.key].alias
  authenticator     = "conditional-user-configured"
  requirement       = "REQUIRED"
}

# Bind the custom flow as the realm's browser flow
resource "keycloak_authentication_bindings" "browser_otp" {
  for_each = local.auth_flow_realms

  realm_id     = each.value
  browser_flow = keycloak_authentication_flow.browser_otp[each.key].alias
}

# CONFIGURE_TOTP as default required action for new users
# Enforces 2FA enrollment on first login for all new users in both realms.
# The conditional authentication flow handles users with/without 2FA credentials gracefully.
resource "keycloak_required_action" "configure_totp" {
  for_each = local.auth_flow_realms

  realm_id       = each.value
  alias          = "CONFIGURE_TOTP"
  name           = "Configure OTP"
  enabled        = true
  default_action = true # Enforce 2FA enrollment on first login
  priority       = 10
}
