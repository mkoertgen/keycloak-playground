#!/usr/bin/env python3
"""Quick TOTP code generator matching the realm OTP policy (HmacSHA256, 6 digits, 30s).

Usage:
  uv run python totp.py                         # alice (from local.env / KEYCLOAK__OTP_SECRET)
  uv run python totp.py YOURSECRET              # any base32 secret
  uv run python totp.py --watch                 # refresh every second until Ctrl-C
  uv run python totp.py YOURSECRET --watch
"""

import sys
import time

import pyotp

from settings import settings


def current_code(secret: str) -> tuple[str, int]:
  totp = pyotp.TOTP(secret, digest="sha256")
  code = totp.now()
  remaining = int(totp.interval - (time.time() % totp.interval))
  return code, remaining


def main() -> None:
  args = [a for a in sys.argv[1:] if not a.startswith("-")]
  watch = "--watch" in sys.argv

  if args:
    secret = args[0]
  elif settings.keycloak.otp_secret:
    secret = settings.keycloak.otp_secret.get_secret_value()
  else:
    print("No secret provided. Pass as argument or set KEYCLOAK__OTP_SECRET.", file=sys.stderr)
    sys.exit(1)

  if watch:
    try:
      while True:
        code, remaining = current_code(secret)
        print(f"\r{code}  ({remaining:2d}s) ", end="", flush=True)
        time.sleep(1)
    except KeyboardInterrupt:
      print()
  else:
    code, remaining = current_code(secret)
    print(f"{code}  ({remaining}s remaining)")


if __name__ == "__main__":
  main()
