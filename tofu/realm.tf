variable "realm_name" {
  description = "Name of the demo realm"
  type        = string
  default     = "demo"
}

variable "webauthn_rp_id" {
  description = "WebAuthn Relying Party ID — must be a bare hostname without port (e.g. 'localhost' or 'auth.example.com')"
  type        = string
  default     = "localhost"
}

variable "login_theme" {
  description = "Login theme name. null = Keycloak default. Use 'keycloak-theme' for the custom Keycloakify theme, 'keycloak.v2' or 'keycloak' for built-ins."
  type        = string
  default     = null
}

variable "account_theme" {
  description = "Account console theme name. null = Keycloak default. Use 'keycloak-theme' for the custom Single-Page account theme, 'keycloak.v3' for built-in."
  type        = string
  default     = null
}

variable "email_theme" {
  description = "Email theme name. null = Keycloak default. Use 'keycloak-theme' for the custom FreeMarker email templates."
  type        = string
  default     = null
}


# Destruction lock: Conditionally protected based on var.prevent_destroy
# Uses random_id keeper pattern as workaround for variable limitation in lifecycle blocks.
# Set var.prevent_destroy = true in production environments.
resource "random_id" "demo_realm_lock" {
  for_each = var.prevent_destroy ? { demo = true } : {}

  byte_length = 8

  keepers = {
    realm_id = keycloak_realm.demo.id
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "keycloak_realm" "demo" {
  realm             = var.realm_name
  enabled           = true
  display_name      = "Demo Realm"
  display_name_html = "<b>Demo</b> Realm"

  # Signature algorithm for tokens
  default_signature_algorithm = "RS256"

  # SSL/TLS requirements
  ssl_required = "none" # For local development; use "external" in production

  # ── Login and Registration Settings ──────────────────────────────────────
  # Disable self-registration for security. Users should be onboarded through
  # a controlled process (manual admin provisioning, LDAP sync, etc.)
  registration_allowed = false

  # Allow username to match external systems (e.g., LDAP, external IdP)
  registration_email_as_username = false

  # Prevent username changes to maintain consistency across integrated systems
  edit_username_allowed = false

  # Enable password reset ("Forgot password" link) for user convenience
  # Monitor for abuse; consider rate limiting at reverse proxy level
  reset_password_allowed = true

  # Remember Me: Allow session cookies to persist across browser restarts
  remember_me = true

  # Email verification: Disabled for local testing, enable in production
  verify_email = false

  # Allow login with email address (in addition to username)
  login_with_email_allowed = true

  # Prevent duplicate email addresses for better account recovery security
  duplicate_emails_allowed = false

  # ── Token Lifespans and Sessions ─────────────────────────────────────────
  # OAuth2 Device Flow
  oauth2_device_code_lifespan    = local.token_lifespans.oauth2_device_code_lifespan
  oauth2_device_polling_interval = local.token_lifespans.oauth2_device_polling_interval

  # Access Tokens (short-lived by design)
  access_token_lifespan                   = local.token_lifespans.access_token_lifespan
  access_token_lifespan_for_implicit_flow = local.token_lifespans.access_token_lifespan_for_implicit_flow

  # Action Tokens (password reset, email verification, admin actions)
  action_token_generated_by_user_lifespan  = local.token_lifespans.action_token_generated_by_user_lifespan
  action_token_generated_by_admin_lifespan = local.token_lifespans.action_token_generated_by_admin_lifespan

  # Authorization Codes (OIDC/OAuth2 flows)
  access_code_lifespan             = local.token_lifespans.access_code_lifespan
  access_code_lifespan_login       = local.token_lifespans.access_code_lifespan_login
  access_code_lifespan_user_action = local.token_lifespans.access_code_lifespan_user_action

  # Refresh Tokens
  revoke_refresh_token = local.token_lifespans.revoke_refresh_token

  # SSO Sessions
  sso_session_idle_timeout             = local.session_lifespans.sso_session_idle_timeout
  sso_session_max_lifespan             = local.session_lifespans.sso_session_max_lifespan
  sso_session_idle_timeout_remember_me = local.session_lifespans.sso_session_idle_timeout_remember_me
  sso_session_max_lifespan_remember_me = local.session_lifespans.sso_session_max_lifespan_remember_me

  # Offline Sessions (for offline_access scope)
  offline_session_idle_timeout         = local.session_lifespans.offline_session_idle_timeout
  offline_session_max_lifespan_enabled = local.session_lifespans.offline_session_max_lifespan_enabled
  offline_session_max_lifespan         = local.session_lifespans.offline_session_max_lifespan

  # ── Advanced Configuration (Realm Attributes) ────────────────────────────
  # Granular control over specific action token types and admin event retention
  attributes = local.realm_attributes

  # Security: Strong password policy (from locals)
  password_policy = local.password_policy_strong

  # OTP Policy for 2FA (from locals)
  otp_policy {
    type      = local.otp_policy_default.type
    algorithm = local.otp_policy_default.algorithm
    digits    = local.otp_policy_default.digits
    period    = local.otp_policy_default.period
  }

  # Web Authentication (WebAuthn/FIDO2)
  web_authn_policy {
    relying_party_entity_name     = "Demo Keycloak"
    relying_party_id              = local.webauthn_policy_default.relying_party_id
    signature_algorithms          = local.webauthn_policy_default.signature_algorithms
    user_verification_requirement = local.webauthn_policy_default.user_verification_requirement
  }

  # Security defenses: headers and brute force detection (from realm-security.tf)
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
      max_login_failures               = local.brute_force_detection.max_login_failures
      wait_increment_seconds           = local.brute_force_detection.wait_increment_seconds
      quick_login_check_milli_seconds  = local.brute_force_detection.quick_login_check_milli_seconds
      minimum_quick_login_wait_seconds = local.brute_force_detection.minimum_quick_login_wait_seconds
      max_failure_wait_seconds         = local.brute_force_detection.max_failure_wait_seconds
      failure_reset_time_seconds       = local.brute_force_detection.failure_reset_time_seconds
    }
  }

  # Internationalization (from locals)
  internationalization {
    supported_locales = local.i18n_default.supported_locales
    default_locale    = local.i18n_default.default_locale
  }

  # SMTP configuration: only when email is enabled
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

  # ── Feature Flags ────────────────────────────────────────────────────────
  # Organizations (Keycloak 26+)
  organizations_enabled = true

  # ── Themes ───────────────────────────────────────────────────────────────
  # Set to null to use Keycloak's built-in defaults
  # Custom jar: cd keycloak/theme && npm run deploy
  # Built-in options: login → keycloak / keycloak.v2, account → keycloak.v3, email → keycloak
  login_theme   = var.login_theme
  account_theme = var.account_theme
  email_theme   = var.email_theme

  # ── Protection ───────────────────────────────────────────────────────────
  # Prevent accidental deletion via Terraform (requires explicit import removal)
  # Note: This is separate from our random_id keeper pattern above
  lifecycle {
    prevent_destroy = false # Set true in production
  }
}

resource "keycloak_role" "minimal_role" {
  realm_id    = keycloak_realm.demo.id
  name        = "minimal-role"
  description = "Role with minimal privileges for all users"
}

# Assign default roles
resource "keycloak_default_roles" "default" {
  realm_id = keycloak_realm.demo.id
  default_roles = [
    keycloak_role.minimal_role.name,
    "account/view-profile",
    "account/manage-account"
  ]
}

# ── Realm Events (Audit Logging) ─────────────────────────────────────────────
# Track user authentication events and admin configuration changes
resource "keycloak_realm_events" "demo" {
  realm_id = keycloak_realm.demo.id

  # User events: Login, logout, registration, etc.
  events_enabled    = true
  events_expiration = 604800 # 7 days in seconds

  # Event listeners: jboss-logging writes to Keycloak server logs
  events_listeners = ["jboss-logging"]

  # Admin events: Track all configuration changes (realm settings, users, clients, etc.)
  # Essential for audit trails and compliance
  admin_events_enabled         = true
  admin_events_details_enabled = true

  # Events to track (user authentication events)
  # Full list: https://www.keycloak.org/docs-api/latest/javadocs/org/keycloak/events/EventType.html
  enabled_event_types = [
    "LOGIN",
    "LOGIN_ERROR",
    "LOGOUT",
    "REGISTER",
    "UPDATE_PASSWORD",
    "UPDATE_TOTP",
    "VERIFY_EMAIL",
    "REMOVE_TOTP",
  ]
}
