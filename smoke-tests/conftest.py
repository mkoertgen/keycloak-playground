"""pytest configuration and fixtures for smoke tests"""

import logging

import pytest
from playwright.sync_api import Browser, Page

from services.keycloak import KeycloakService
from settings import settings

logger = logging.getLogger(__name__)

# Configure logging based on settings
log_level_value = getattr(logging, settings.log_level.upper(), logging.INFO)
print(f"Log level: {settings.log_level.upper()} ({log_level_value})")

logging.basicConfig(
  level=log_level_value,
  format="%(asctime)s [%(levelname)8s] %(name)s - %(message)s",
  datefmt="%H:%M:%S",
  force=True,  # Force reconfiguration even if already configured
)

# Silence noisy loggers
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)


def pytest_configure(config):
  """Configure pytest with Playwright tracing and log level from settings"""
  trace_mode = settings.playwright.trace
  logger.info(f"Playwright tracing: {trace_mode.value}")

  # Tell pytest-playwright what trace mode to use
  # The attribute is 'tracing' (derived from --tracing CLI option)
  if hasattr(config.option, "tracing"):
    config.option.tracing = trace_mode.value
    logger.debug(f"Set tracing={trace_mode.value}")

  # Update pytest's CLI log level to match LOG_LEVEL setting
  # Note: log_cli_level expects the string name (e.g., 'DEBUG'), not the int
  if hasattr(config.option, "log_cli_level"):
    config.option.log_cli_level = settings.log_level.upper()


@pytest.fixture(scope="session")
def browser_type_launch_args(pytestconfig):
  """Configure browser launch arguments based on settings"""
  launch_args = {}

  if settings.playwright.headful and not pytestconfig.getoption("--headed", default=False):
    launch_args["headless"] = False
    logger.info(f"Browser headless=False (PLAYWRIGHT__HEADFUL={settings.playwright.headful})")

  slowmo_cli = pytestconfig.getoption("--slowmo", default=0)
  if slowmo_cli == 0 and settings.playwright.slowmo > 0:
    launch_args["slow_mo"] = settings.playwright.slowmo
    logger.info(f"Browser slow_mo={settings.playwright.slowmo}ms")

  # Note: WebAuthn tests work perfectly in headless mode (CI environment) without special flags.
  # Headful mode issues (empirical findings, no official documentation found):
  #   - WSL: System passkey dialog causes NotAllowedError (display works but WebAuthn APIs fail)
  #   - Windows: Works fine (dialog appears but tests pass)
  #   - Native Linux: Untested - TODO: Verify with colleague on native Linux system
  # Recommendation: Use headless for CI/development, headful debugging tested working on Windows host.

  return launch_args


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
  """Configure browser context arguments"""
  return browser_context_args


@pytest.fixture(scope="session")
def keycloak_webauthn_context(browser: Browser):
  """Provide page with registered WebAuthn device in Keycloak.

  Session-scoped for performance (expensive setup). Deletes existing test device
  before registering new one (CI-compatible: virtual authenticator is ephemeral).

  Concurrency: One test run per user per stage (concurrent runs conflict on device deletion).
  """
  if not settings.keycloak.user or not settings.keycloak.password:
    pytest.skip("KEYCLOAK__USER and KEYCLOAK__PASSWORD not configured")
  if not settings.keycloak.otp_secret:
    pytest.skip("KEYCLOAK__OTP_SECRET required for WebAuthn setup")

  context = browser.new_context()
  page = context.new_page()

  cdp = context.new_cdp_session(page)
  cdp.send("WebAuthn.enable")
  cdp.send(
    "WebAuthn.addVirtualAuthenticator",
    {
      "options": {
        "protocol": "ctap2",
        "transport": "usb",
        "hasResidentKey": True,
        "hasUserVerification": True,
        "isUserVerified": True,
      }
    },
  )

  keycloak = KeycloakService(page)
  keycloak._navigate_to_account_console()
  keycloak.login(handle_2fa=False)
  otp_shown = keycloak._handle_totp_if_prompted()
  if not otp_shown:
    context.close()
    pytest.skip("OTP form not visible after login — conditional 2FA not active for this user, skipping WebAuthn test")
  page.wait_for_load_state("networkidle")
  keycloak.setup_webauthn_device("playwright-test-device")
  keycloak.logout()
  context.clear_cookies()
  page.goto(settings.keycloak.account_url)

  yield page

  context.close()


@pytest.fixture
def logged_in_keycloak(page: Page):
  """Logged-in KeycloakService with automatic logout cleanup"""
  keycloak = KeycloakService(page)
  keycloak.login_to_account_console()
  page.wait_for_load_state("networkidle")

  yield keycloak

  # Cleanup: Always logout, even if test fails
  try:
    keycloak.logout()
  except Exception as e:
    print(f"Warning: Logout failed: {e}")
