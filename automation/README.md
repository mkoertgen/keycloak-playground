# Keycloak-GitLab Automation

Automated user lifecycle management: onboarding and offboarding for Keycloak and GitLab.

**TL;DR:** GitLab doesn't support OIDC backchannel logout, so disabled users stay logged in. This tool bridges that gap by calling APIs directly when users are offboarded.

## Quick Start

```bash
# 1. Install dependencies
cd automation
uv sync

# 2. Configure
cp .env.example .env
# Edit .env with your Keycloak and GitLab credentials
# Set GROUP_SYNC_CRON for desired interval (default: every minute for demo)

# 3. CLI Usage
uv run ./automate.py onboard-user john.doe
uv run ./automate.py offboard-user john.doe
uv run ./automate.py list-onboarding-status

# 4. Start webhook server with scheduled group sync
uv run ./server.py
# or for auto-reload: uv run uvicorn server:app --reload

# 5. Check status
curl http://localhost:8000/health
curl http://localhost:8000/api/sync-status

# 6. Trigger manual group sync
curl -X POST http://localhost:8000/api/sync-groups
```

See [Usage](#usage) section below for detailed examples.

---

## Problem Statements

### Offboarding Gap

When a user is disabled in Keycloak, their sessions are **not** automatically terminated, and GitLab does **not** support OIDC backchannel logout. This means:

1. Disabling a user in Keycloak doesn't log them out of GitLab
2. GitLab's OIDC client ignores the `backchannel_logout_url` configuration
3. Manual intervention is required to terminate sessions

**Why GitLab doesn't support backchannel logout:**

- **GitLab Issue:** [gitlab#449119](https://gitlab.com/gitlab-org/gitlab/-/issues/449119) - Open since March 2024, no implementation planned
- **OmniAuth Issue:** [omniauth_openid_connect#177](https://github.com/omniauth/omniauth_openid_connect/issues/177) - Underlying Ruby gem lacks support
- **Frontchannel logout** is mentioned as alternative, but requires browser redirect (cannot be automated via API)

**Security Risk:** Disabled users remain logged into GitLab until session expires (up to 7 days by default).

### Onboarding Automation

New users need consistent onboarding (password setup, 2FA enrollment, email verification). Manual configuration is error-prone and time-consuming.

This tool integrates with **Keycloak Workflows** (`UserCreatedWorkflowEvent`, `AddRequiredActionStepProvider`) to automate onboarding.

## Solution

This automation service provides:

1. **CLI tool** for manual user lifecycle operations (onboarding & offboarding)
2. **Webhook server** for automated responses to GitLab and Keycloak events
3. Proper session termination across Keycloak and GitLab
4. Automated onboarding with required actions

## Features

### Offboarding

- ✅ Disable users in Keycloak
- ✅ Revoke all Keycloak sessions (including backchannel logout to other clients)
- ✅ Terminate GitLab sessions via API (`POST /users/:id/logout`)
- ✅ Batch offboarding for multiple users
- ✅ GitLab webhook integration for automatic offboarding

### Onboarding

- ✅ Set required actions (password, 2FA, email verification)
- ✅ Batch onboarding for multiple users
- ✅ Keycloak Workflow integration (`UserCreatedWorkflowEvent`)
- ✅ Track onboarding status and completion

### Group Synchronization

- ✅ **Scheduled sync** of Keycloak groups to GitLab groups
- ✅ Configurable cron schedule (every minute to hourly)
- ✅ Managed groups: `gitlab-admins`, `gitlab-developers`, `gitlab-external`, `demo-team-alpha`, `demo-team-beta`
- ✅ Manual sync trigger via API
- ✅ Automatic membership updates (add/remove users)
- ⚠️ **Note:** OIDC doesn't support auto-assignment of groups (would require SAML), so scheduled sync is needed

### General

- ✅ Batch onboarding for multiple users
- ✅ Keycloak Workflow integration (`UserCreatedWorkflowEvent`)
- ✅ Track onboarding status and completion

### General

- ✅ CLI and webhook server modes
- ✅ Dry-run mode for testing
- ✅ Health checks and monitoring

## Setup

### 1. Install Dependencies

```bash
cd /path/to/keycloak-playground/automation

# Install dependencies with uv (creates venv + installs from pyproject.toml)
uv sync
```

### 2. Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
# Keycloak
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_ADMIN_USER=admin
KEYCLOAK_ADMIN_PASSWORD=admin
KEYCLOAK_REALM=demo

# GitLab (optional, for GitLab integration)
GITLAB_URL=http://localhost:8929
GITLAB_ADMIN_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx

# GitLab Webhook (optional)
GITLAB_WEBHOOK_SECRET=$(openssl rand -hex 32)
```

**Getting GitLab Admin Token:**

1. GitLab → Admin Area → Settings → Access Tokens
2. Create token with scope: `api` (full API access)
3. Save the token in `.env`

### 3. Make CLI Executable

```bash
chmod +x automate.py
```

## Usage

### CLI Commands

#### Onboard a User

Set required actions for new users (password setup, 2FA):

```bash
./automate.py onboard-user USERNAME
```

Example:

```bash
# Default: UPDATE_PASSWORD + CONFIGURE_TOTP
uv run ./automate.py onboard-user john.doe

# Custom required actions
uv run ./automate.py onboard-user john.doe -a UPDATE_PASSWORD -a VERIFY_EMAIL
```

**Onboard Multiple Users:**

```bash
uv run ./automate.py onboard-users user1 user2 user3
uv run ./automate.py onboard-users user1 user2 -a UPDATE_PASSWORD -a CONFIGURE_TOTP
```

**Check Onboarding Status:**

```bash
# List users with incomplete onboarding
uv run ./automate.py list-onboarding-status

# List all users
uv run ./automate.py list-onboarding-status --filter all

# JSON output
uv run ./automate.py list-onboarding-status --format json
```

#### Offboard a User

Disable user in Keycloak and logout from GitLab:

```bash
uv run ./automate.py offboard-user USERNAME
```

Example:

```bash
uv run ./automate.py offboard-user marcel.koertgen
```

Options:

- `--skip-gitlab`: Skip GitLab logout (only disable in Keycloak)
- `--dry-run, -n`: Show what would happen without making changes
- `--yes`: Skip confirmation prompt

**Offboard Multiple Users:**

```bash
uv run ./automate.py offboard-users user1 user2 user3
```

**Check User Sessions:**

Show active Keycloak sessions for a user:

```bash
uv run ./automate.py check-sessions USERNAME
```

### Webhook Server

Start the FastAPI webhook server to handle GitLab events automatically:

```bash
uv run ./server.py
# or for development with auto-reload
uv run uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

The server provides:

- `GET /` - Health check
- `GET /health` - Detailed health status (Keycloak + GitLab)
- `POST /webhook/gitlab/user` - GitLab user event handler
- `POST /webhook/gitlab/test` - Test endpoint (no signature verification)

#### Configure GitLab System Hooks

1. Go to GitLab → **Admin Area** → **System Hooks**
2. Add new hook:
   - **URL**: `http://your-server:8000/webhook/gitlab/user`
   - **Secret Token**: Value of `GITLAB_WEBHOOK_SECRET` from `.env`
   - **Trigger**: Enable **User events**
   - **SSL verification**: Enable if using HTTPS

3. Test the webhook:
   ```bash
   curl -X POST http://localhost:8000/webhook/gitlab/test \
     -H "Content-Type: application/json" \
     -d '{"event_name": "user_block", "username": "testuser"}'
   ```

#### Supported Events

**GitLab System Hooks:**

- `user_create`: User created → onboard in Keycloak (set required actions)
- `user_destroy`: User deleted → offboard from Keycloak
- `user_block`: User blocked → offboard from Keycloak
- `user_failed_login`: Failed login attempts (logged, not processed)

**Keycloak Workflows:**

- `USER_CREATED`: Triggered by `UserCreatedWorkflowEvent` → onboard user

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────┐
│   GitLab        │  Event  │   Webhook        │  API    │  Keycloak   │
│                 ├────────►│   Server         ├────────►│             │
│ • User Create   │         │   (FastAPI)      │  Calls  │ Onboarding: │
│ • User Block    │         │                  │         │ • Set req.  │
│ • User Delete   │         │  Handlers:       │         │   actions   │
└─────────────────┘         │  • Onboarding    │         │             │
                            │  • Offboarding   │         │ Offboarding:│
┌─────────────────┐         │                  │         │ • Disable   │
│   Keycloak      │  Event  │                  │         │ • Revoke    │
│   Workflows     ├────────►│                  │         │   Sessions  │
│                 │         │                  │         └─────────────┘
│ UserCreated     │         └────────┬─────────┘
│ WorkflowEvent   │                  │
└─────────────────┘                  │ API Calls
                                     ▼
                             ┌──────────────┐
                             │   GitLab     │
                             │              │
                             │ POST /users/ │
                             │  {id}/logout │
                             └──────────────┘
```

### Why This Is Needed

#### 1. Keycloak Limitation: No Automatic Session Revocation

Disabling a user (`user.setEnabled(false)`) does **NOT** automatically revoke sessions:

- Source: [UserResource.java#L681](../keycloak/services/src/main/java/org/keycloak/services/resources/admin/UserResource.java#L681)
- Manual call to `user_logout()` is required
- Sessions remain active until they expire naturally

#### 2. GitLab Limitation: No OIDC Backchannel Logout Support

GitLab does **NOT** support OIDC backchannel logout, despite Keycloak sending logout notifications:

**Root Cause - Two Issues:**

1. **GitLab Core Issue:** [gitlab#449119](https://gitlab.com/gitlab-org/gitlab/-/issues/449119)
   - Status: Open since March 2024, labeled "backlog to-be-closed"
   - GitLab ignores `backchannel_logout_url` in OIDC client configuration
   - No implementation of OIDC Back-Channel Logout spec

2. **OmniAuth Gem Issue:** [omniauth_openid_connect#177](https://github.com/omniauth/omniauth_openid_connect/issues/177)
   - OmniAuth OIDC gem (used by GitLab) lacks backchannel logout support
   - Even if GitLab wanted to support it, the underlying library doesn't

**What About Frontchannel Logout?**

The OmniAuth issue mentions frontchannel logout as a potential workaround, but:

- ❌ Requires browser redirect (GET request to logout endpoint)
- ❌ Cannot be triggered headless (no API/script support)
- ❌ User must be actively using the application
- ❌ Not suitable for admin-initiated logouts or automation

**Conclusion:** Only manual API-based logout works: `POST /users/{id}/logout`

#### 3. Security Gap: Active Sessions After Account Disable

Without automated logout:

- ✗ Disabled users remain logged into GitLab for hours/days
- ✗ Session lifetime depends on GitLab's session timeout (default: 7 days)
- ✗ Offboarded employees can still access repositories
- ✗ Security compliance violation (immediate access revocation required)

**This automation bridges the gap** by calling GitLab's admin API to terminate sessions immediately.

## Deployment

### Systemd Service (Production)

Create `/etc/systemd/system/keycloak-gitlab-automation.service`:

```ini
[Unit]
Description=Keycloak-GitLab Automation Webhook Server
After=network.target

[Service]
Type=simple
User=automation
WorkingDirectory=/path/to/keycloak-playground/automation
Environment="PATH=/path/to/keycloak-playground/automation/venv/bin"
ExecStart=/path/to/keycloak-playground/automation/venv/bin/python server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable keycloak-gitlab-automation
sudo systemctl start keycloak-gitlab-automation
sudo systemctl status keycloak-gitlab-automation
```

### Docker (Alternative)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies from pyproject.toml
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy application code
COPY . .

CMD ["python", "server.py"]
```

```bash
docker build -t keycloak-gitlab-automation .
docker run -d -p 8000:8000 --env-file .env keycloak-gitlab-automation
```

## Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

Response:

```json
{
  "keycloak": "healthy",
  "gitlab": "healthy",
  "overall": "healthy"
}
```

### Logs

CLI operations print to console with rich formatting.

Webhook server logs to stdout/stderr:

```bash
# Follow logs (systemd)
journalctl -u keycloak-gitlab-automation -f

# Docker
docker logs -f <container-id>
```

## Testing

### Dry-Run Mode

Test without making changes:

```bash
./automate.py offboard-user testuser --dry-run
```

### Manual Test

1. Create test user in Keycloak
2. Login to GitLab with test user
3. Run offboarding:
   ```bash
   ./automate.py offboard-user testuser
   ```
4. Verify:
   - User disabled in Keycloak
   - Sessions terminated in Keycloak
   - Logged out from GitLab (refresh page → redirected to login)

## Troubleshooting

### "User not found in Keycloak"

- Check username spelling (case-sensitive)
- Verify user exists: `./automate.py check-sessions USERNAME`

### "Failed to disable user in Keycloak"

- Check admin credentials in `.env`
- Verify admin has realm management permissions
- Check Keycloak logs: `/var/log/keycloak/`

### "Failed to logout user from GitLab"

- Check GitLab admin token has `api` scope
- Verify user exists in GitLab
- Check GitLab logs: `/var/log/gitlab/`

### Webhook not triggering

- Verify GitLab system hook is configured and enabled
- Check webhook secret matches `.env`
- Test endpoint: `curl http://your-server:8000/webhook/gitlab/test`
- Check GitLab → Admin Area → System Hooks → Recent Deliveries

## Security Considerations

1. **Secrets Management**:
   - Never commit `.env` to git
   - Use secret management tools (Vault, AWS Secrets Manager) in production
   - Rotate webhook secrets periodically

2. **Network**:
   - Run webhook server on internal network only
   - Use HTTPS with valid certificates
   - Consider mTLS for GitLab → Webhook communication

3. **Access Control**:
   - Limit Keycloak admin scope to minimum required
   - Use dedicated service account for GitLab token
   - Audit log all offboarding operations

## Related Documentation

### GitLab OIDC Logout Issues

- **GitLab Core:** [gitlab#449119 - Support OIDC backchannel logout](https://gitlab.com/gitlab-org/gitlab/-/issues/449119)
  - Status: Open since March 2024, labeled "backlog to-be-closed" (low priority)
  - Impact: GitLab ignores `backchannel_logout_url` in OIDC client configuration
  - No ETA for implementation

- **OmniAuth Gem:** [omniauth_openid_connect#177 - OIDC Back-Channel Logout Support](https://github.com/omniauth/omniauth_openid_connect/issues/177)
  - Underlying Ruby gem used by GitLab for OIDC
  - Also lacks backchannel logout implementation
  - Discusses frontchannel logout alternative (requires browser, not API-driven)

### API Documentation

- **Keycloak:** [User Logout API](https://www.keycloak.org/docs-api/latest/rest-api/index.html#_users_resource)
- **GitLab:** [User Session Termination API](https://docs.gitlab.com/ee/api/users.html#user-session-termination)

### OIDC Standards

- **OIDC Spec:** [Back-Channel Logout 1.0](https://openid.net/specs/openid-connect-backchannel-1_0.html) - Server-to-server logout (not supported by GitLab)
- **OIDC Spec:** [Front-Channel Logout 1.0](https://openid.net/specs/openid-connect-frontchannel-1_0.html) - Browser-based logout (requires user session, cannot be automated)

## License

Same as parent project.
