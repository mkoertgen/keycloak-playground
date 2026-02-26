# ADR-0001: Keycloak Security Architecture and IaC Best Practices

**Status:** Accepted  
**Date:** 2026-02-26
**Deciders:** Infrastructure Team

## Context

We are implementing a Keycloak infrastructure-as-code (IaC) setup for both development and production environments. Several architectural decisions needed to be made regarding:

1. **Security Hardening**: How to implement defense-in-depth security across multiple realms
2. **Two-Factor Authentication (2FA)**: Whether to require 2FA by default and how to handle IaC automation
3. **Master Realm Access**: How to minimize the attack surface of the master realm
4. **Destruction Prevention**: How to protect critical resources from accidental deletion
5. **Configuration Management**: How to organize and make security configurations reusable
6. **Email/SMTP**: Whether email should be required or optional
7. **Token and Session Lifespans**: How to configure secure token lifetimes while maintaining usability
8. **Audit Logging**: What events to track for compliance and security monitoring

### Forces at Play

- **Security vs. Convenience**: Stronger security measures can complicate automation and development workflows
- **IaC Bootstrapping Problem**: Terraform/OpenTofu authentication conflicts with 2FA requirements (Direct Access Grants don't support OTP)
- **Master Realm Necessity**: Keycloak's master realm cannot be disabled but should be minimally exposed
- **Configuration Flexibility**: Production needs different security postures than development environments
- **Lifecycle Block Limitations**: Terraform/OpenTofu doesn't allow variables in lifecycle blocks, requiring workarounds
- **Code Organization**: Balancing DRY principles with clarity and maintainability

## Decision

### 1. Conditional Two-Factor Authentication

**Decision**: Implement conditional 2FA via authentication flow that automatically adapts based on user credentials.

**Rationale**:

- Security best practice: 2FA significantly reduces credential compromise risk
- Flow automatically challenges users with configured 2FA credentials
- Users without 2FA can still authenticate (important for IaC service accounts)
- New users are prompted to set up TOTP on first login

### 2. IaC Bootstrapping Strategy

**Decision**: Use dedicated IaC service accounts without 2FA enrollment.

**Problem**: Terraform's Direct Access Grants authentication method doesn't support OTP.

**Solution**: Use dedicated IaC service accounts that are exempt from 2FA enrollment, while enforcing 2FA for human administrators. The conditional authentication flow handles both scenarios without configuration toggles.

### 3. Master Realm Security Strategy

**Decision**: Master realm stays enabled but minimized in exposure and usage.

**Rationale**:

- **Cannot Disable**: Keycloak's master realm is a fundamental architectural component
- **Attack Surface Minimization**: Reduce exposure through multiple layers:

**Implementation Strategy**:

1. **Always Protected**: Master realm has unconditional destruction prevention
2. **Hide Admin Console**: Separate hostname/port for admin access (not publicly exposed)
3. **Minimize User Access**: Per-realm admin permissions for operational users; master realm for break-glass only
4. **Strict Security Controls**: Stricter brute force detection, strong password policies, mandatory 2FA

### 4. Destruction Prevention Strategy

**Decision**: Use keeper pattern for variable-driven lifecycle management.

**Problem**: Terraform/OpenTofu doesn't allow variables in `lifecycle` blocks.

**Solution**: Conditional dependency pattern that blocks destruction when the dependency exists and allows it when the dependency is absent.

**Protected Resources**:

- **Master Realm**: Always protected (unconditional)
- **Demo Realm**: Conditionally protected
- **Master Admin Users**: Conditionally protected

### 5. Email/SMTP as Optional Feature

**Decision**: Email disabled by default with clear toggle via `email_enabled` variable.

**Rationale**:

- Development environments often don't have SMTP configured
- Email verification/notifications not essential for basic testing
- Production can enable with proper SMTP configuration

### 6. Token and Session Lifespans

**Decision**: Configure production-hardened token and session lifespans with security-first defaults.

**Rationale**:

- **Shorter is better**: Reduced window for token theft/misuse
- **Balance with UX**: Too short = user frustration, too long = security risk
- **Granular control**: Different lifespans for different token types and use cases

**Key Security Improvements**:

- Offline sessions reduced from 30-60 days to 1-24 hours (dramatically reduces long-term token theft risk)
- Password reset links expire in 10 minutes (tighter than default 30 minutes)
- Short access tokens (5 minutes) force regular refresh
- Extended SSO sessions (2 hours idle) balance UX with security

### 7. Realm Events and Audit Logging

**Decision**: Enable comprehensive event logging for both user actions and admin changes.

**Rationale**:

- **Audit trail**: Required for compliance (SOC2, ISO 27001, GDPR)
- **Incident response**: Critical for investigating security incidents
- **User events**: Track authentication attempts, failures, account changes
- **Admin events**: Track all configuration changes (who changed what when)

**Key Points**:

- 7-day retention balances audit needs with storage constraints
- Master realm: Admin events only (no user logins expected)
- Demo realm: Both user and admin events
- For longer retention, export to external SIEM/log aggregation system

## Consequences

### Positive

1. **Defense in Depth**: Multiple security layers protect against various attack vectors
2. **Production Ready**: Security-by-default configuration with conditional 2FA, strong passwords, brute force detection
3. **Safe by Default**: Destruction prevention protects critical resources
4. **Token Security**: Dramatically reduced token lifespans (offline sessions: days → hours) limit exposure
5. **Audit Trail**: Comprehensive event logging supports compliance and incident response

### Negative

1. **Workaround Required**: Lifecycle protection pattern is less elegant than native variable support
2. **Manual Coordination**: Admin hostname must be configured outside Terraform
3. **Master Realm Exposure**: Cannot fully eliminate master realm (inherent Keycloak limitation)
4. **Shorter Session UX Impact**: Reduced token lifespans may require more frequent re-authentication
5. **Event Storage**: 7-day event retention requires monitoring storage usage; longer retention needs external system

### Neutral

1. **Token Lifespan Tuning**: May need adjustment based on specific application requirements and user feedback

## References

- [Keycloak Security Guide](https://www.keycloak.org/docs/latest/server_admin/#_security_hardening)
- [RFC 3986 - URI Generic Syntax](https://www.rfc-editor.org/rfc/rfc3986#section-2.2) (Reserved Characters)
- [Terraform Lifecycle Meta-Arguments](https://www.terraform.io/language/meta-arguments/lifecycle)
- [Keycloak Organizations Feature](https://www.keycloak.org/docs/latest/server_admin/#_organizations) (KC 26+)
- [Diataxis Documentation Framework](https://diataxis.fr/) (Explanation Category)

## Related ADRs

- None yet (this is the first ADR)

## Future Considerations

1. **Service Account Implementation**: Create dedicated IaC service account with client credentials grant
2. **Per-Realm Admin Roles**: Implement fine-grained admin permissions for operational users
3. **Automated Master Realm Auditing**: Monitor and alert on master realm access
4. **KC_HOSTNAME_ADMIN Automation**: Integrate admin hostname configuration into deployment pipeline
5. **Secrets Management**: Consider external secrets management (Vault, AWS Secrets Manager) for SMTP credentials
6. **SIEM Integration**: Export Keycloak events to centralized logging (Elasticsearch, Splunk, Datadog)
7. **Token Lifespan Monitoring**: Track token refresh patterns and adjust lifespans based on real usage
8. **Session Analytics**: Monitor session duration metrics to optimize idle timeout settings
9. **Event Retention Policy**: Evaluate external archival for long-term compliance requirements (>7 days)
