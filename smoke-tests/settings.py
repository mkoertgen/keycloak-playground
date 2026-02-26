"""Centralized configuration using Pydantic Settings"""

import os
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_smoke_env = os.getenv("SMOKE_ENV", "local")
_base_path = Path(__file__).parent
_env_files = [
  _base_path / "common.env",
  _base_path / f"{_smoke_env}.env",
  _base_path / "local.env",
]


class TraceMode(str, Enum):
  ON = "on"
  OFF = "off"
  ON_FIRST_RETRY = "on-first-retry"
  RETAIN_ON_FAILURE = "retain-on-failure"


class KeycloakConfig(BaseModel):
  model_config = ConfigDict(validate_default=False)
  url: str = "http://localhost:8080"
  realm: str = "demo"
  user: str = "alice@democorp.com"
  password: SecretStr = Field(default=SecretStr("Password123!"))
  otp_secret: Optional[SecretStr] = None

  @property
  def account_url(self) -> str:
    return f"{self.url}/realms/{self.realm}/account"


class PlaywrightConfig(BaseModel):
  headful: bool = False
  slowmo: int = 0
  trace: TraceMode = TraceMode.RETAIN_ON_FAILURE


class SmokeTestSettings(BaseSettings):
  model_config = SettingsConfigDict(
    env_file=_env_files,
    env_file_encoding="utf-8",
    case_sensitive=False,
    extra="ignore",
    env_nested_delimiter="__",
  )

  keycloak: KeycloakConfig = Field(default_factory=lambda: KeycloakConfig.model_construct())
  playwright: PlaywrightConfig = Field(default_factory=lambda: PlaywrightConfig.model_construct())
  # CI detection (GitHub Actions, etc.)
  ci: bool = Field(default=False)
  timeout: int = 10
  log_level: str = "INFO"

  @model_validator(mode="after")
  def apply_ci_defaults(self):
    ci_indicators = os.getenv("CI", "").lower() in ("1", "true", "yes")
    if ci_indicators:
      self.ci = True
      if not os.getenv("PLAYWRIGHT__HEADFUL"):
        self.playwright.headful = False
      if not os.getenv("PLAYWRIGHT__TRACE"):
        self.playwright.trace = "retain-on-failure"
      if not os.getenv("LOG_LEVEL"):
        self.log_level = "INFO"

    print("Configuration loaded from:")
    for env_file in _env_files:
      if env_file.exists():
        print(f"  [OK] {env_file}")
    print(f"Environment: SMOKE_ENV={_smoke_env} | CI={self.ci} | log_level={self.log_level}")
    return self


settings = SmokeTestSettings()
