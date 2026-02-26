"""Configuration for automation service."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Automation service settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Keycloak
    keycloak_url: str
    keycloak_admin_user: str
    keycloak_admin_password: SecretStr
    keycloak_realm: str = "factory"

    # GitLab
    gitlab_url: str
    gitlab_admin_token: SecretStr

    # GitLab Webhook (for FastAPI server)
    gitlab_webhook_secret: SecretStr | None = None

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False

    # Group Sync Scheduler
    # Cron expression: "minute hour day month day_of_week"
    # Examples:
    #   "* * * * *"     - Every minute (demo)
    #   "*/5 * * * *"   - Every 5 minutes
    #   "*/10 * * * *"  - Every 10 minutes
    #   "*/30 * * * *"  - Every 30 minutes
    #   "0 * * * *"     - Every hour
    group_sync_cron: str = "* * * * *"  # Default: every minute for demo
    group_sync_enabled: bool = True
