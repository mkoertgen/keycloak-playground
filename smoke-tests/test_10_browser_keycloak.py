"""
Browser-based Keycloak Tests
"""

import pytest
from playwright.sync_api import expect

from services.keycloak import KeycloakService
from settings import settings

# Apply markers
pytestmark = [
  pytest.mark.browser,
]


def test_keycloak_login(logged_in_keycloak) -> None:
  """Test Keycloak login with TOTP 2FA and verify account console access

  This verifies users can authenticate to Keycloak and access their account console
  for self-service profile management (password changes, 2FA setup, etc.).

  Fixture automatically handles login and logout (even on test failure).
  """
  keycloak = logged_in_keycloak
  page = keycloak.page

  expect(page).to_have_url(f"{settings.keycloak.url}/realms/{settings.keycloak.realm}/account")
  expect(page).to_have_title("Account Management")


def test_keycloak_login_with_webauthn(keycloak_webauthn_context) -> None:
  """Test Keycloak login with WebAuthn 2FA using virtual authenticator

  Note: This test uses the webauthn_context fixture (not logged_in fixture)
  because it needs special setup for virtual authenticator registration.
  Manual logout included for consistency.
  """
  # Fixture provides page with registered WebAuthn device and logged-out state
  page = keycloak_webauthn_context
  keycloak = KeycloakService(page)

  try:
    # Login with WebAuthn 2FA
    keycloak.login_to_account_console(use_webauthn=True)

    # Verify successful login to account console
    expect(page).to_have_url(f"{settings.keycloak.url}/realms/{settings.keycloak.realm}/account")
    expect(page).to_have_title("Account Management")
  finally:
    # Cleanup: logout to ensure clean state (guaranteed even on failure)
    try:
      keycloak.logout()
    except Exception as e:
      print(f"Warning: Logout failed: {e}")
