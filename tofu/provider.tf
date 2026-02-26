terraform {
  required_version = ">= 1.0"

  required_providers {
    keycloak = {
      source  = "keycloak/keycloak"
      version = "~> 5.6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.8"
    }
  }
}

variable "keycloak_url" {
  description = "Keycloak server URL"
  type        = string
  default     = "http://localhost:8080"
}

variable "keycloak_client_id" {
  description = "Client ID for Terraform authentication"
  type        = string
  default     = "admin-cli"
}

variable "keycloak_admin_username" {
  description = "Keycloak admin username"
  type        = string
  default     = "admin"
}

variable "keycloak_admin_password" {
  description = "Keycloak admin password"
  type        = string
  sensitive   = true
  default     = "admin"
}

provider "keycloak" {
  url       = var.keycloak_url
  client_id = var.keycloak_client_id
  username  = var.keycloak_admin_username
  password  = var.keycloak_admin_password
  base_path = ""
  realm     = "master"
}

