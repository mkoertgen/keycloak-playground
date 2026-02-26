#!/usr/bin/env python3
"""Seed a TOTP credential for a Keycloak user via Admin REST API.

Idempotent: deletes any existing credential with the same label, then creates a
fresh one.  Called by the `terraform_data.seed_totp` resource in users.tf.

Usage:
  python seed_totp.py --url http://localhost:8080 --realm demo \\
      --admin-user admin --admin-password admin \\
      --username alice --secret INHEYULYKRLWQZLDHFWTITCBOJZHKMCX

The --secret value must be the raw base32-encoded TOTP shared secret.  It must
match the value in KEYCLOAK__OTP_SECRET used by the smoke tests.
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


def get_token(url: str, admin_user: str, admin_password: str) -> str:
    data = urllib.parse.urlencode(
        {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": admin_user,
            "password": admin_password,
        }
    ).encode()
    req = urllib.request.Request(
        f"{url}/realms/master/protocol/openid-connect/token",
        data=data,
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)["access_token"]


def api(url: str, method: str, token: str, path: str, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{url}{path}",
        data=data,
        method=method,
    )
    req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status == 204:
                return None
            return json.load(resp)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} {method} {path}: {e.read().decode()}", file=sys.stderr)
        raise


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", required=True, help="Keycloak base URL")
    p.add_argument("--realm", required=True, help="Realm name")
    p.add_argument("--admin-user", default="admin", help="Admin username")
    p.add_argument("--admin-password", default="admin", help="Admin password")
    p.add_argument("--username", required=True, help="Target username")
    p.add_argument("--secret", required=True, help="Base32-encoded TOTP secret")
    p.add_argument("--digits", type=int, default=6, help="OTP digit count")
    p.add_argument("--period", type=int, default=30, help="OTP period in seconds")
    p.add_argument(
        "--algorithm",
        default="HmacSHA256",
        help="HMAC algorithm (must match realm OTP policy)",
    )
    p.add_argument("--label", default="totp", help="Credential user label")
    args = p.parse_args()

    token = get_token(args.url, args.admin_user, args.admin_password)

    # Resolve user ID
    users = api(
        args.url,
        "GET",
        token,
        f"/admin/realms/{args.realm}/users?username={urllib.parse.quote(args.username)}&exact=true",
    )
    if not users:
        print(
            f"User {args.username!r} not found in realm {args.realm!r}", file=sys.stderr
        )
        sys.exit(1)
    user_id = users[0]["id"]

    # Delete any existing credential with the same label (idempotency)
    existing = api(
        args.url,
        "GET",
        token,
        f"/admin/realms/{args.realm}/users/{user_id}/credentials",
    )
    for cred in existing or []:
        if cred.get("type") == "otp" and cred.get("userLabel") == args.label:
            print(
                f"  Removing existing TOTP credential {cred['id']!r} ({args.label!r})"
            )
            api(
                args.url,
                "DELETE",
                token,
                f"/admin/realms/{args.realm}/users/{user_id}/credentials/{cred['id']}",
            )

    # Seed the credential via PUT /users/{id} with a credentials array.
    # There is no POST /users/{id}/credentials endpoint in Keycloak — the only way to inject
    # a non-password credential via the Admin REST API is to include it in a UserRepresentation
    # update, which calls RepresentationToModel.createCredentials → createCredentialThroughProvider.
    #
    # secretEncoding must be "BASE32" so that OTPCredentialModel.getDecodedSecret() calls
    # Base32.decode(value) instead of value.getBytes(UTF-8).
    credential = {
        "type": "otp",
        "userLabel": args.label,
        "credentialData": json.dumps(
            {
                "subType": "totp",
                "digits": args.digits,
                "counter": 0,
                "period": args.period,
                "algorithm": args.algorithm,
                "secretEncoding": "BASE32",
            }
        ),
        "secretData": json.dumps(
            {
                "value": args.secret,
            }
        ),
    }
    api(
        args.url,
        "PUT",
        token,
        f"/admin/realms/{args.realm}/users/{user_id}",
        {"credentials": [credential]},
    )
    print(f"TOTP credential seeded for {args.username!r} in realm {args.realm!r}")


if __name__ == "__main__":
    main()
