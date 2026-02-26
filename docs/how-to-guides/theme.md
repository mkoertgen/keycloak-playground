# Custom Theme (Keycloakify)

The playground ships a [Keycloakify 11](https://www.keycloakify.dev/) starter in
[`keycloak/theme/`](../keycloak/theme/) — Vite + React + TypeScript.

## Gallery

|                 Default theme                 |                Custom theme                 |
| :-------------------------------------------: | :-----------------------------------------: |
| ![Default login](img/theme-login-default.png) | ![Custom login](img/theme-login-custom.png) |

<p align="center">
  <strong>Account Console – 2FA enrollment</strong><br>
  <img src="img/theme-account-2fa.png" alt="2FA enrollment" width="600">
</p>

## Quick dev workflow

Live-inject the theme into Keycloak without building a jar first:

```bash
cd keycloak/theme
npm install
npm run dev          # serves at http://localhost:5173
```

<!-- asciinema cast placeholder — upload and replace the link below
[![asciicast](https://asciinema.org/a/REPLACE_ME.svg)](https://asciinema.org/a/REPLACE_ME)
Record with: bash docs/casts/record-theme-dev.sh
-->

Keycloak must already be running (`docker compose up -d keycloak`). The dev server
proxies the Keycloak UI and hot-reloads your React components on every save.

## Storybook

Preview components in isolation without running Keycloak:

```bash
cd keycloak/theme
npm run storybook    # http://localhost:6006
```

## Build & deploy

```bash
# 1. Build the theme jar
cd keycloak/theme
npm run build-keycloak-theme
# → dist_keycloak/keycloak-theme-*.jar
# → Auto-copied to ../providers/keycloak-theme.jar

# 2. Restart Keycloak to pick up the new provider
cd ../..
docker compose restart keycloak

# 3. Activate in terraform.tfvars (if not already set)
cd tofu
# Edit terraform.tfvars:
#   login_theme   = "keycloak-theme"
#   account_theme = "keycloak-theme"
#   email_theme   = "keycloak-theme"
tofu apply
```

The jar is volume-mounted from `keycloak/providers/` into the container — no image
rebuild needed.

## File layout

```
keycloak/
  providers/              ← Built jar staged here (git-ignored)
    keycloak-theme.jar    ← Auto-copied from theme/dist_keycloak/
  theme/
    src/
      login/              ← Login page components (React)
      account/            ← Account console components (Single-Page App)
      email/              ← Email templates (FreeMarker)
    dist_keycloak/        ← Build output (git-ignored)
    vite.config.ts
    package.json
    README.md             ← Detailed Keycloakify docs
```

## Theme variables

Edit `tofu/terraform.tfvars` to activate/deactivate themes:

| Variable        | Default | Options                                                   |
| --------------- | ------- | --------------------------------------------------------- |
| `login_theme`   | `null`  | `"keycloak-theme"`, `"keycloak"`, `"keycloak.v2"`, `null` |
| `account_theme` | `null`  | `"keycloak-theme"`, `"keycloak.v3"`, `null`               |
| `email_theme`   | `null`  | `"keycloak-theme"`, `"keycloak"`, `null`                  |

Set to `null` or omit to use Keycloak's built-in defaults.

## Resources

- [Keycloakify docs](https://docs.keycloakify.dev/)
- [keycloak/theme/README.md](../keycloak/theme/README.md)
- Storybook preview: `npm run storybook` → http://localhost:6006
