# Test Webhook Payloads

> **Note:** These webhooks are necessary because GitLab doesn't support OIDC backchannel logout:
>
> - [gitlab#449119](https://gitlab.com/gitlab-org/gitlab/-/issues/449119) - GitLab core issue
> - [omniauth_openid_connect#177](https://github.com/omniauth/omniauth_openid_connect/issues/177) - OmniAuth gem issue
>
> Frontchannel logout (mentioned in these issues) requires browser redirect and cannot be automated via API.
> Therefore, we use GitLab's admin API (`POST /users/{id}/logout`) to terminate sessions manually.

## Onboarding Events

### GitLab user created event

```bash
curl -X POST http://localhost:8000/webhook/gitlab/user \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Token: your-webhook-secret" \
  -d '{
    "event_name": "user_create",
    "created_at": "2024-01-15T12:34:56Z",
    "username": "john.doe",
    "user_id": 456,
    "email": "john.doe@example.com"
  }'
```

### Keycloak Workflow user created event

```bash
curl -X POST http://localhost:8000/webhook/keycloak/user-created \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-webhook-secret" \
  -d '{
    "eventType": "USER_CREATED",
    "realmId": "demo",
    "userId": "uuid-1234-5678",
    "username": "john.doe",
    "email": "john.doe@example.com"
  }'
```

## Offboarding Events

### User blocked event

```bash
curl -X POST http://localhost:8000/webhook/gitlab/user \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Token: your-webhook-secret" \
  -d '{
    "event_name": "user_block",
    "created_at": "2024-01-15T12:34:56Z",
    "username": "testuser",
    "user_id": 123,
    "email": "testuser@example.com"
  }'
```

## User destroyed event

```bash
curl -X POST http://localhost:8000/webhook/gitlab/user \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Token: your-webhook-secret" \
  -d '{
    "event_name": "user_destroy",
    "created_at": "2024-01-15T12:34:56Z",
    "username": "testuser",
    "user_id": 123,
    "email": "testuser@example.com"
  }'
```

## Test endpoint (no signature verification)

```bash
curl -X POST http://localhost:8000/webhook/gitlab/test \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "user_block",
    "username": "testuser"
  }'
```

## Expected Responses

### Onboarding Success

```json
{
  "status": "success",
  "message": "User 'john.doe' onboarded",
  "actions": ["set_required_actions", "welcome_email_queued"],
  "required_actions": ["UPDATE_PASSWORD", "CONFIGURE_TOTP"],
  "trigger": "user_create"
}
```

### Offboarding Success

```json
{
  "status": "success",
  "message": "User 'testuser' offboarded",
  "actions": ["disabled_in_keycloak", "revoked_keycloak_sessions"],
  "trigger": "user_block"
}
```

### User not found

```json
{
  "status": "warning",
  "message": "User 'testuser' not found in Keycloak",
  "action": "none"
}
```

### Error

```json
{
  "status": "error",
  "message": "Failed to disable user in Keycloak",
  "user": "testuser"
}
```

## Full GitLab System Hook Payload Example

GitLab actually sends this structure:

```json
{
  "created_at": "2024-01-15T12:34:56Z",
  "updated_at": "2024-01-15T12:34:56Z",
  "event_name": "user_block",
  "username": "john.doe",
  "user_id": 123,
  "email": "john.doe@example.com",
  "name": "John Doe",
  "state": "blocked"
}
```

## Testing with Python

```python
import requests
import hmac
import hashlib
import json

url = "http://localhost:8000/webhook/gitlab/user"
secret = "your-webhook-secret"

payload = {
    "event_name": "user_block",
    "created_at": "2024-01-15T12:34:56Z",
    "username": "testuser",
    "user_id": 123,
    "email": "testuser@example.com"
}

payload_bytes = json.dumps(payload).encode()
signature = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()

response = requests.post(
    url,
    json=payload,
    headers={"X-Gitlab-Token": signature}
)

print(response.status_code)
print(response.json())
```
