# ══════════════════════════════════════════════════════════════════════════════
# Security Defaults (Reusable Across Realms)
# ══════════════════════════════════════════════════════════════════════════════
#
# This file centralizes security configuration objects that can be reused across
# both the demo realm and master realm:
#
# • security_headers:    HTTP security headers (CSP, X-Frame-Options, etc.)
# • brute_force_detection: Login attempt throttling configurations
# • password_policy:     Password complexity requirements
# • otp_policy:          TOTP/2FA settings
# • webauthn_policy:     WebAuthn/FIDO2 configuration defaults
# • i18n:                Internationalization settings
# • token_lifespans:     OAuth2/OIDC token and session duration settings
#
# These objects are designed to be used directly in realm security_defenses
# blocks using attribute syntax:
#
#   security_defenses {
#     headers               = local.security_headers
#     brute_force_detection = local.brute_force_detection_standard
#   }
#
# This approach:
# • Eliminates repetitive field-by-field assignments
# • Makes security policies explicit and centralized
# • Enables easy comparison between standard vs. strict configurations
# • Simplifies updates (change once, applies everywhere)

locals {
  # ── HTTP Security Headers ───────────────────────────────────────────────────
  # Common security headers applied to all Keycloak HTTP responses.
  # These protect against clickjacking, XSS, MIME sniffing, and more.
  security_headers = {
    x_frame_options                     = "DENY"
    content_security_policy             = "frame-src 'self'; frame-ancestors 'self'; object-src 'none';"
    content_security_policy_report_only = ""
    x_content_type_options              = "nosniff"
    x_robots_tag                        = "none"
    x_xss_protection                    = "1; mode=block"
    strict_transport_security           = "max-age=31536000; includeSubDomains"
  }

  # ── Brute Force Detection ──────────────────────────────────────────────────
  # Base configuration for login attempt throttling.
  # Realms override max_login_failures using merge() at the usage site.
  brute_force_detection = {
    permanent_lockout                = false
    max_login_failures               = 10 # standard; override to 5 for strict
    wait_increment_seconds           = 60
    quick_login_check_milli_seconds  = 1000
    minimum_quick_login_wait_seconds = 60
    max_failure_wait_seconds         = 900
    failure_reset_time_seconds       = 43200 # 12 hours
  }

  # ── Password Policy ─────────────────────────────────────────────────────────
  # Strong password requirements applied realm-wide.
  # Format: Keycloak password policy string (space-separated rules)
  password_policy_strong = "upperCase(1) and length(12) and notUsername(undefined) and passwordHistory(5) and lowerCase(1) and digits(1)"

  # ── OTP Policy (Time-based One-Time Password) ───────────────────────────────
  # Default 2FA configuration using TOTP (Google Authenticator, Authy, etc.)
  otp_policy_default = {
    type      = "totp"
    algorithm = "HmacSHA256"
    digits    = 6
    period    = 30
  }

  # ── WebAuthn Policy (FIDO2 / Passkeys) ──────────────────────────────────────
  # Configuration for hardware security keys and platform authenticators.
  # Note: relying_party_id must match your domain (no port).
  webauthn_policy_default = {
    relying_party_id              = var.webauthn_rp_id
    signature_algorithms          = ["ES256", "RS256"]
    user_verification_requirement = "preferred"
  }

  # ── Internationalization ────────────────────────────────────────────────────
  # Language support for login pages, emails, and admin console.
  i18n_default = {
    supported_locales = ["en", "de"]
    default_locale    = "en"
  }

  # ── Token Lifespans ─────────────────────────────────────────────────────────
  # Production-hardened token durations balancing security with usability.
  # Shorter tokens = better security, but too short = user frustration.
  # Durations use Terraform duration string format: "5m", "1h", "24h", etc.
  token_lifespans = {
    # OAuth2 device flow
    oauth2_device_code_lifespan    = "10m"
    oauth2_device_polling_interval = 5

    # Access tokens (short-lived by design, refreshed via refresh token)
    access_token_lifespan                   = "5m"  # Short-lived by design
    access_token_lifespan_for_implicit_flow = "15m" # Slightly longer for implicit flow

    # Action tokens (password reset, email verification, etc.)
    action_token_generated_by_user_lifespan  = "30m" # User-initiated actions (default)
    action_token_generated_by_admin_lifespan = "12h" # Admin-initiated actions

    # Authorization codes (OAuth2/OIDC redirect flow)
    access_code_lifespan             = "1m" # Very short, used only during redirect
    access_code_lifespan_login       = "1m"
    access_code_lifespan_user_action = "1m"

    # Refresh tokens
    revoke_refresh_token = false # Don't revoke on use (allows rotation)
  }

  # ── SSO Session Settings ────────────────────────────────────────────────────
  # Single sign-on session durations for browser-based login flows.
  session_lifespans = {
    sso_session_idle_timeout             = "2h"  # Idle timeout (increased from default 30m)
    sso_session_max_lifespan             = "10h" # Absolute max
    sso_session_idle_timeout_remember_me = "4h"  # Extended for "remember me"
    sso_session_max_lifespan_remember_me = "24h" # Extended for "remember me"

    # Offline sessions (for offline_access scope)
    offline_session_idle_timeout         = "1h"  # Reduced from default 30d
    offline_session_max_lifespan_enabled = true  # Enforce max lifespan
    offline_session_max_lifespan         = "24h" # Reduced from default 60d
  }

  # ── Realm Attributes ────────────────────────────────────────────────────────
  # Lower-level realm configuration exposed via attributes map.
  # These settings provide granular control not available via top-level realm args.
  #
  # Note: Durations here use SECONDS (integers), not duration strings.
  realm_attributes = {
    # Action token lifespans (in seconds, not duration strings)
    "actionTokenGeneratedByUserLifespan.verify-email"                 = "86400" # 24h
    "actionTokenGeneratedByUserLifespan.idp-verify-account-via-email" = "3600"  # 1h
    "actionTokenGeneratedByUserLifespan.reset-credentials"            = "600"   # 10m
    "actionTokenGeneratedByUserLifespan.execute-actions"              = "1800"  # 30m

    # Admin events expiration (terraform-provider-keycloak doesn't have dedicated resource)
    "adminEventsExpiration" = "604800" # 7 days

    # Client offline session intervals (in seconds)
    "clientOfflineSessionIdleTimeout" = "3600"  # 1h
    "clientOfflineSessionMaxLifespan" = "86400" # 24h
  }
}
