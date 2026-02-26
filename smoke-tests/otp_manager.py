"""TOTP manager preventing code reuse within 30s validity window"""

import logging
import time

import pyotp

logger = logging.getLogger(__name__)


class OTPManager:
  """Tracks used TOTP codes and waits for next window if reused"""

  def __init__(self):
    self._used_codes: dict[str, str] = {}

  def get_totp_code(self, secret: str, digest: str = "sha256", wait_if_reused: bool = True) -> str:
    """Get TOTP code, waiting for new one if current code was already used"""
    totp = pyotp.TOTP(secret, digest=digest)
    code = totp.now()
    last_used = self._used_codes.get(secret)

    if wait_if_reused and code == last_used:
      wait_time = self._time_until_next_code(totp)
      logger.warning(f"TOTP code reused, waiting {wait_time:.1f}s for next window")
      time.sleep(wait_time)
      code = totp.now()

    self._used_codes[secret] = code
    return code

  def _time_until_next_code(self, totp: pyotp.TOTP) -> float:
    """Calculate seconds until next TOTP window (includes 0.5s buffer)"""
    interval = totp.interval
    current_time = time.time()
    time_in_window = current_time % interval
    time_remaining = interval - time_in_window
    return time_remaining + 0.5

  def reset(self) -> None:
    """Clear all tracked codes"""
    self._used_codes.clear()


otp_manager = OTPManager()
