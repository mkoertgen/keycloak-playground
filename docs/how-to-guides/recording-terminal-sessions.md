# docs/casts – Asciinema Recording Guide

Shell scripts to record terminal sessions with [asciinema](https://asciinema.org/).

## Prerequisites

> **Windows users:** `asciinema rec` requires a Unix PTY (`termios`/`pty`) and does **not**
> work in PowerShell or Git Bash. Run all recording scripts inside **WSL** (Ubuntu/Debian).
> The repo is reachable from WSL at `/mnt/c/Users/<you>/git/oss/mkoertgen/keycloak-playground`.

```bash
# macOS
brew install asciinema

# Linux / WSL
sudo apt install asciinema   # or: pip install asciinema

# Verify
asciinema --version
```

## Recordings

| Cast file          | Script                  | Description                              |
| ------------------ | ----------------------- | ---------------------------------------- |
| `quickstart.cast`  | `record-quickstart.sh`  | `docker compose up -d` + health check    |
| `tofu-apply.cast`  | `record-tofu.sh`        | `tofu init` → `plan` → `apply` + outputs |
| `smoke-tests.cast` | `record-smoke-tests.sh` | pytest API tests (browser tests skipped) |
| `totp-watch.cast`  | `record-totp-watch.sh`  | TOTP code generator for alice            |
| `theme-dev.cast`   | `record-theme-dev.sh`   | Keycloakify `npm run dev` live-inject    |

## How to record

```bash
# Make scripts executable (once)
chmod +x docs/casts/record-*.sh

# Record individual cast (from repo root)
bash docs/casts/record-tofu.sh
bash docs/casts/record-smoke-tests.sh
# etc.
```

Each script drops a `.cast` file next to itself in `docs/casts/`.

## How to preview

Preview recordings locally before uploading:

```bash
# Play a cast in the terminal
asciinema play docs/casts/tofu-apply.cast

# Play all casts
for cast in docs/casts/*.cast; do
  echo "Playing: $cast"
  asciinema play "$cast"
done
```

Controls during playback:

- `Space` - pause/resume
- `.` - step forward (when paused)
- `Ctrl+C` - quit

## How to embed

### On asciinema.org

```bash
asciinema upload docs/casts/tofu-apply.cast
# → https://asciinema.org/a/<id>
```

Then embed with the badge pattern used in the docs pages:

```markdown
[![asciicast](https://asciinema.org/a/<id>.svg)](https://asciinema.org/a/<id>)
```

### Self-hosted / GitHub Pages

```bash
# Generate a standalone HTML player
asciinema convert docs/casts/tofu-apply.cast docs/casts/tofu-apply.html
```

Or embed the raw cast with [asciinema-player](https://github.com/asciinema/asciinema-player) in an HTML page.

### GitHub README (static fallback)

GitHub doesn't render asciinema inline. Use an SVG preview image or an animated GIF:

```bash
# Convert cast → GIF via agg (https://github.com/asciinema/agg)
agg docs/casts/tofu-apply.cast docs/img/cast-tofu-apply.gif
```

Then reference as a normal image.

## Tips

- Keep `--cols 120 --rows 35` for readable terminal output in players
- Run `asciinema play docs/casts/tofu-apply.cast` to preview locally
- Edit a cast with [`asciinema-edit`](https://github.com/cirocosta/asciinema-edit) to trim idle gaps:
  ```bash
  asciinema-edit quantize --range 2 docs/casts/tofu-apply.cast > docs/casts/tofu-apply-trimmed.cast
  ```
