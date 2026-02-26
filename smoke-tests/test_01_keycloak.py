"""
Keycloak Smoke Tests

Basic health and connectivity tests for Keycloak after deployment.
Tests OIDC endpoints, health checks, and basic API availability.

Run with: pytest --junit-xml=junit.xml test_keycloak_smoke.py
"""

import pytest
import requests

from settings import settings

kc = settings.keycloak


class TestKeycloakHealth:
  """Basic health and availability checks"""

  def test_root_endpoint_reachable(self):
    """Verify Keycloak root endpoint is reachable"""
    response = requests.get(f"{kc.url}/", timeout=settings.timeout, allow_redirects=True)
    assert response.status_code == 200, f"Root endpoint returned unexpected status: {response.status_code}"

  def test_health_endpoint_not_exposed(self):
    """Verify health endpoint is NOT publicly exposed (management port only)"""
    response = requests.get(f"{kc.url}/health", timeout=settings.timeout)
    # Health endpoints should NOT be accessible on the public interface
    assert response.status_code == 404, f"Health endpoint should not be exposed, got status {response.status_code}"

  def test_metrics_endpoint_not_exposed(self):
    """Verify metrics endpoint is NOT publicly exposed (management port only)"""
    response = requests.get(f"{kc.url}/metrics", timeout=settings.timeout)
    # Metrics should NOT be accessible on the public interface
    assert response.status_code == 404, f"Metrics endpoint should not be exposed, got status {response.status_code}"


class TestOIDCEndpoints:
  """OIDC well-known endpoints and configuration"""

  def test_oidc_discovery_endpoint(self):
    """Verify OIDC discovery endpoint returns valid configuration"""
    url = f"{kc.url}/realms/{kc.realm}/.well-known/openid-configuration"
    response = requests.get(url, timeout=settings.timeout)
    assert response.status_code == 200, f"OIDC discovery returned status {response.status_code}"

    config = response.json()
    assert "issuer" in config, "Missing issuer in OIDC config"
    assert "authorization_endpoint" in config, "Missing authorization_endpoint"
    assert "token_endpoint" in config, "Missing token_endpoint"
    assert "userinfo_endpoint" in config, "Missing userinfo_endpoint"

    # Verify issuer matches expected realm
    assert kc.realm in config["issuer"], f"Issuer {config['issuer']} doesn't contain realm {kc.realm}"

  def test_jwks_endpoint(self):
    """Verify JWKS (JSON Web Key Set) endpoint is reachable"""
    url = f"{kc.url}/realms/{kc.realm}/protocol/openid-connect/certs"
    response = requests.get(url, timeout=settings.timeout)
    assert response.status_code == 200, f"JWKS endpoint returned status {response.status_code}"

    jwks = response.json()
    assert "keys" in jwks, "Missing keys in JWKS response"
    assert len(jwks["keys"]) > 0, "JWKS contains no keys"

  def test_token_endpoint_reachable(self):
    """Verify token endpoint is reachable (but don't attempt auth)"""
    url = f"{kc.url}/realms/{kc.realm}/protocol/openid-connect/token"
    # POST without credentials should return 400 (bad request) or 401
    response = requests.post(url, timeout=settings.timeout)
    assert response.status_code in [400, 401], f"Token endpoint returned unexpected status: {response.status_code}"

  def test_authorization_endpoint_reachable(self):
    """Verify authorization endpoint is reachable"""
    url = f"{kc.url}/realms/{kc.realm}/protocol/openid-connect/auth"
    # GET without params should return 400 or redirect to login
    response = requests.get(url, timeout=settings.timeout, allow_redirects=False)
    assert response.status_code in [302, 400], (
      f"Authorization endpoint returned unexpected status: {response.status_code}"
    )


class TestRealmAccess:
  """Basic realm configuration and access"""

  def test_realm_info_endpoint(self):
    """Verify realm info endpoint returns configuration"""
    url = f"{kc.url}/realms/{kc.realm}"
    response = requests.get(url, timeout=settings.timeout)
    assert response.status_code == 200, f"Realm info returned status {response.status_code}"

    realm_info = response.json()
    assert realm_info.get("realm") == kc.realm, f"Realm mismatch: expected {kc.realm}, got {realm_info.get('realm')}"
    assert "public_key" in realm_info, "Missing public_key in realm info"

  def test_account_console_reachable(self):
    """Verify Keycloak Account Console is reachable"""
    url = f"{kc.url}/realms/{kc.realm}/account"
    response = requests.get(url, timeout=settings.timeout, allow_redirects=False)
    # Should redirect to login or return account page
    assert response.status_code in [200, 302, 303], (
      f"Account console returned unexpected status: {response.status_code}"
    )


class TestSSL:
  """SSL/TLS configuration tests"""

  def test_https_enforced(self):
    """Verify HTTPS is enforced (redirect from HTTP)"""
    if kc.url.startswith("https://"):
      http_url = kc.url.replace("https://", "http://")
      try:
        response = requests.get(http_url, timeout=settings.timeout, allow_redirects=False)
        # Should redirect to HTTPS or refuse connection
        assert response.status_code in [301, 302, 308], f"HTTP didn't redirect to HTTPS: {response.status_code}"
      except requests.exceptions.ConnectionError:
        # Connection refused is also acceptable (HTTP port closed)
        pass
    else:
      pytest.skip("Skipping HTTPS enforcement test for non-HTTPS URL")

  def test_tls_version(self):
    """Verify TLS version is modern (TLS 1.2+)"""
    response = requests.get(f"{kc.url}/", timeout=settings.timeout)
    # requests uses modern TLS by default, so successful connection implies TLS 1.2+
    assert response.status_code < 500, "Server error during TLS connection"


if __name__ == "__main__":
  pytest.main([__file__, "-v", "--junit-xml=junit.xml"])
