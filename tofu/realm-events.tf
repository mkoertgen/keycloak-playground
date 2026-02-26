resource "keycloak_realm_events" "demo_events" {
  realm_id = keycloak_realm.demo.id

  # User events for auditing
  events_enabled    = true
  events_expiration = 604800 # 7 days in seconds

  events_listeners = [
    "jboss-logging"
  ]

  # Important security events to track
  enabled_event_types = [
    "LOGIN",
    "LOGIN_ERROR",
    "LOGOUT",
    "REGISTER",
    "REGISTER_ERROR",
    "UPDATE_PASSWORD",
    "UPDATE_PASSWORD_ERROR",
    "VERIFY_EMAIL",
    "REMOVE_TOTP",
    "UPDATE_TOTP",
    "SEND_VERIFY_EMAIL",
    "SEND_RESET_PASSWORD",
    "UPDATE_EMAIL",
    "CLIENT_LOGIN",
    "CLIENT_LOGIN_ERROR",
  ]

  # Admin events for tracking configuration changes
  admin_events_enabled         = true
  admin_events_details_enabled = true # Include full details in admin events
}
