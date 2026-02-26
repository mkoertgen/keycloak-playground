"""Keycloak Service - authentication and account management"""

import logging

from playwright.sync_api import Page

from otp_manager import otp_manager
from settings import settings

logger = logging.getLogger(__name__)
kc = settings.keycloak


class KeycloakService:
  def __init__(self, page: Page):
    self.page = page

  def login(self, handle_2fa: bool = True) -> bool:
    """Login to Keycloak, skip if session exists. Returns True if login performed."""
    try:
      self.page.get_by_role("textbox", name="Email").wait_for(state="visible", timeout=3000)
    except Exception:
      logger.debug("Keycloak session exists, skipping login")
      return False

    # Perform login
    logger.debug("Keycloak login required (no active session)")
    self.page.get_by_role("textbox", name="Email").fill(kc.user)
    self.page.get_by_role("button", name="Sign In").click()

    self.page.get_by_role("textbox", name="Password").wait_for(state="visible", timeout=5000)
    self.page.get_by_role("textbox", name="Password").fill(kc.password.get_secret_value())
    self.page.get_by_role("button", name="Sign In").click()

    if handle_2fa:
      self._handle_totp_if_prompted()

    return True

  def _handle_totp_if_prompted(self) -> bool:
    """Handle TOTP 2FA if prompted"""
    if not kc.otp_secret:
      logger.debug("No OTP secret configured, skipping TOTP 2FA")
      return False

    try:
      logger.debug("Waiting for TOTP input field...")
      self.page.get_by_label("One-time code").wait_for(state="visible", timeout=3000)
      logger.debug("TOTP 2FA prompt detected")

      code = otp_manager.get_totp_code(secret=kc.otp_secret.get_secret_value(), digest="sha256")

      logger.debug("Filling TOTP code")
      self.page.get_by_label("One-time code").fill(code)
      self.page.get_by_role("button", name="Sign In").click()
      logger.debug("TOTP code submitted successfully")
      return True
    except Exception as e:
      logger.debug(f"No TOTP prompt or error: {e}")
      return False

  def _handle_webauthn_if_prompted(self) -> bool:
    """Handle WebAuthn 2FA if prompted (requires virtual authenticator)"""
    try:
      self.page.get_by_role("link", name="Try Another Way").wait_for(state="visible", timeout=3000)
      logger.debug("WebAuthn choice screen detected, clicking 'Try Another Way'")
      self.page.get_by_role("link", name="Try Another Way").click()

      # Select WebAuthn option
      logger.debug("Selecting WebAuthn authentication method")
      self.page.get_by_text("Use your Passkey to sign in.").click()

      # Select first available device (virtual authenticator)
      self.page.locator("#kc-webauthn-authenticator-transport-0").click()

      # Trigger WebAuthn authentication
      logger.debug("Triggering WebAuthn authentication")
      self.page.get_by_role("button", name="Sign in with Passkey").click()

      # Wait for authentication to complete
      self.page.wait_for_load_state("networkidle", timeout=10000)
      logger.debug("WebAuthn authentication completed successfully")
      return True
    except Exception:
      return False

  def _navigate_to_account_console(self) -> None:
    self.page.goto(kc.account_url)

  def logout(self) -> None:
    """Logout from Keycloak account console"""
    if "/account" not in self.page.url:
      self._navigate_to_account_console()

    self.page.get_by_test_id("options-toggle").click()
    self.page.get_by_role("menuitem", name="Sign out").click()
    self.page.wait_for_url("**/protocol/openid-connect/**", timeout=5000)

  def setup_webauthn_device(self, device_name: str) -> None:
    """Setup WebAuthn device: navigate, delete existing, register new"""
    self._navigate_to_webauthn_settings()
    self._delete_webauthn_device(device_name)
    self._register_webauthn_device(device_name)

  def _navigate_to_webauthn_settings(self) -> None:
    self.page.goto(f"{kc.account_url}/account-security/signing-in")
    self.page.wait_for_load_state("networkidle")

  def _delete_webauthn_device(self, device_name: str) -> bool:
    """Delete WebAuthn device by name. Returns True if deleted."""
    try:
      device_row = self.page.get_by_text(device_name)
      if not device_row.is_visible():
        return False

      self.page.get_by_test_id("webauthn/credential-list").get_by_role("button", name="Delete").click()
      self.page.get_by_role("button", name="Confirm deletion").click()
      self.page.wait_for_timeout(1000)
      return True
    except Exception:
      return False

  def _register_webauthn_device(self, device_name: str) -> None:
    """Register new WebAuthn device (requires virtual authenticator)"""
    self.page.get_by_test_id("webauthn/create").click()
    self.page.get_by_text("Sign out from other devices").click()
    self.page.once("dialog", lambda dialog: dialog.accept(device_name))
    self.page.get_by_role("button", name="Register").click()
    self.page.wait_for_timeout(2000)

  def login_to_account_console(self, use_webauthn: bool = False) -> None:
    """Complete login flow to Keycloak account console"""
    self._navigate_to_account_console()

    if use_webauthn:
      self.login(handle_2fa=False)
      self._handle_webauthn_if_prompted()
    else:
      self.login(handle_2fa=True)

    self.page.wait_for_load_state("networkidle")
