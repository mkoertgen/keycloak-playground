"""
Application Health Checks

Fast smoke tests to verify that key applications are up and responding.
These tests check basic reachability with simple GET requests.

For complete authentication flow testing, see browser tests (test_03_*.py).

Run with: pytest test_02_apps_health.py -v
"""

import pytest
import requests

from settings import settings


def test_app_health():
  """Verify Keycloak is reachable and returns OK status (< 500)"""
  url = f"{settings.keycloak.url}/"
  response = requests.get(url, timeout=settings.timeout, allow_redirects=True)
  assert response.status_code < 500, f"Keycloak at {url} returned server error: {response.status_code}"


if __name__ == "__main__":
  pytest.main([__file__, "-v"])
