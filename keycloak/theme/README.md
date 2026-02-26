# Keycloak Custom Theme

Custom Keycloak login theme for the [keycloak-playground](../README.md), built with
[Keycloakify 11](https://keycloakify.dev) on Vite + React + TypeScript.

## Quick Start

```bash
cd keycloak
npm install
```

## Development

### Storybook (UI preview without Keycloak)

```bash
npm run storybook
# → http://localhost:6006
```

### Live preview against a running Keycloak

```bash
# 1. Start Keycloak (from repo root)
docker compose up -d keycloak

# 2. Launch the Keycloakify dev server
npm run dev
# → http://localhost:5173  (auto-injects into Keycloak's login flow)
```

Docs: https://docs.keycloakify.dev/testing-your-theme

## Customize

The login pages live in `src/login/`.

| File           | Purpose                                  |
| -------------- | ---------------------------------------- |
| `KcPage.tsx`   | Page router — add overrides per `pageId` |
| `KcContext.ts` | Extended Keycloak context types          |
| `i18n.ts`      | Translations / message overrides         |

CSS customization guide: https://docs.keycloakify.dev/css-customization

### Eject a page for full control

```bash
npx keycloakify eject-page
```

### Add an Account or Email theme

```bash
npx keycloakify initialize-account-theme
npx keycloakify initialize-email-theme
```

## Build & Deploy

> Requires Java + Maven (`choco install openjdk maven` on Windows).

```bash
npm run build-keycloak-theme
# → dist_keycloak/keycloak-theme-*.jar
```

### Mount into Docker Compose (local testing)

Running `npm run build-keycloak-theme` automatically copies the KC 26 jar to
`../providers/keycloak-theme.jar`. The `docker-compose.yaml` in the repo root already
mounts that directory:

```yaml
volumes:
    - ./keycloak/providers:/opt/keycloak/providers:ro
```

Restart Keycloak to pick up the new provider, then activate the theme via Tofu:

```bash
# From repo root
docker compose restart keycloak

cd tofu
tofu apply -var="custom_theme=true"
```

Docs: https://docs.keycloakify.dev/features/compiler-options/keycloakversiontargets
