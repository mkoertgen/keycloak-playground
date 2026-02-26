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

Add a bind-mount to the Keycloak service in `../docker-compose.yaml`:

```yaml
volumes:
  - keycloak-data:/opt/keycloak/data
  - ./keycloak/dist_keycloak/keycloak-theme-<version>.jar:/opt/keycloak/providers/keycloak-theme.jar
```

Then restart Keycloak and select the theme in the realm settings.

Docs: https://docs.keycloakify.dev/features/compiler-options/keycloakversiontargets
