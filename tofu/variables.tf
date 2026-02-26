# Cross-cutting variables used across multiple resources.
# Resource-specific variables are co-located with their resources.
# See provider.tf, realm.tf, users.tf, organizations.tf, and groups.tf.

variable "prevent_destroy" {
  description = "Protect critical resources (realms) from accidental destruction. Creates resource locks when true."
  type        = bool
  default     = false
}

# ── Email/SMTP Configuration (reusable across realms) ────────────────────────

variable "email_enabled" {
  description = "Enable email/SMTP configuration for realms. Requires SMTP settings to be provided."
  type        = bool
  default     = false
}

variable "smtp_host" {
  description = "SMTP server hostname"
  type        = string
  default     = ""
}

variable "smtp_port" {
  description = "SMTP server port"
  type        = string
  default     = "587"
}

variable "smtp_from" {
  description = "SMTP 'from' email address"
  type        = string
  default     = ""
}

variable "smtp_from_display_name" {
  description = "SMTP 'from' display name"
  type        = string
  default     = "Keycloak"
}

variable "smtp_username" {
  description = "SMTP authentication username"
  type        = string
  default     = ""
  sensitive   = true
}

variable "smtp_password" {
  description = "SMTP authentication password"
  type        = string
  default     = ""
  sensitive   = true
}

variable "smtp_starttls" {
  description = "Use STARTTLS for SMTP connection"
  type        = bool
  default     = true
}
