# Open Notebook Desktop (Linux)

Native Linux desktop launcher for Open Notebook. The app manages the Docker Compose stack in the background and opens the web UI in a dedicated window.

## Features

- Guided onboarding for Docker and encryption key setup
- Auto-start stack on launch (configurable)
- Splash screen with progress while the stack becomes ready
- Start, stop, restart, and view logs for the Open Notebook stack
- Optional automatic Docker installation via `pkexec` (Engine or Docker Desktop)
- Embedded WebView at `http://127.0.0.1:8502`
- Data directory: `~/.local/share/open-notebook-desktop`
- In-app updates for AppImage users

## Requirements

### Build dependencies (Ubuntu/Debian/Linux Mint)

```bash
sudo apt install libwebkit2gtk-4.1-dev build-essential curl wget \
  libssl-dev libayatana-appindicator3-dev librsvg2-dev pkg-config
```

### Runtime

- Docker Engine or Docker Desktop
- Docker Compose plugin
- User in the `docker` group (re-login after install if needed)

## Development

```bash
cd desktop
npm install
npm run tauri dev
```

## Production build

```bash
cd desktop
npm run tauri build
```

Artifacts:

- `desktop/src-tauri/target/release/bundle/deb/`
- `desktop/src-tauri/target/release/bundle/appimage/`

## Documentation

See [Desktop Launcher installation guide](../docs/1-INSTALLATION/desktop-launcher.md).
