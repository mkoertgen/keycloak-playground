# Keycloak Playground

Local Keycloak 26 development environment for testing OIDC integrations.

**What's included:**

- **Keycloak 26** — with observability (Prometheus + Grafana), custom theme starter (Keycloakify), and OpenTofu provisioning
- **Test Client** — FastAPI OIDC demo with Back-Channel Logout as onboarding reference for dev teams
- **Automation** — User lifecycle management (CLI + webhook server) demonstrating workarounds for OIDC limitations

## Documentation

📖 **[Full Documentation](docs/index.md)** — organized using [Diátaxis](https://diataxis.fr/)

| Category               | Description                       |
| ---------------------- | --------------------------------- |
| 📘 **[Tutorials]**     | Step-by-step learning guides      |
| 📖 **[How-to Guides]** | Task-oriented solutions           |
| 📚 **[Reference]**     | Technical specifications          |
| 💡 **[Explanation]**   | Design decisions and architecture |

[Tutorials]: docs/tutorials/
[How-to Guides]: docs/how-to-guides/
[Reference]: docs/reference/
[Explanation]: docs/explanation/

## Services

| Service     | URL                   | Credentials |
| ----------- | --------------------- | ----------- |
| Keycloak    | http://localhost:8080 | admin/admin |
| Test Client | http://localhost:3000 | —           |
| Grafana     | http://localhost:3001 | admin/admin |
| Prometheus  | http://localhost:9090 | —           |

## Quick Start

```bash
# Clone and start
git clone https://github.com/mkoertgen/keycloak-playground.git
cd keycloak-playground
docker compose up -d

# Provision demo realm
cd tofu && tofu init && tofu apply
```

See **[Getting Started Tutorial](docs/tutorials/getting-started.md)** for full walkthrough.

For architecture overview and component details, see **[Architecture Reference](docs/reference/architecture.md)**.

## Warning

This setup is for local development only. Not suitable for production:

- H2 in-memory database
- Default credentials (admin/admin, Password123!)
- No TLS
- `start-dev` mode
