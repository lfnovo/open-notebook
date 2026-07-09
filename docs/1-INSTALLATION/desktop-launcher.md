# Linux Desktop Launcher

Native Linux desktop app that manages the Open Notebook Docker stack and embeds the web UI in its own window.

## Who is this for?

- Linux users who want a **desktop app experience** instead of opening a browser manually
- Users who prefer guided setup for Docker and the encryption key
- Anyone who wants start/stop/log controls without using the terminal

## Requirements

- Linux (Ubuntu, Debian, Linux Mint, Fedora, etc.)
- Docker Engine or Docker Desktop
- Docker Compose plugin
- Your user in the `docker` group

## Install from release (recommended)

Download from [GitHub Releases](https://github.com/lfnovo/open-notebook/releases):

- **AppImage** — portable, supports in-app updates
- **.deb** — for Debian/Ubuntu/Linux Mint

```bash
chmod +x Open\ Notebook\ Desktop_*.AppImage
./Open\ Notebook\ Desktop_*.AppImage
```

On first launch the app will:

1. Check Docker
2. Guide you through encryption key setup (if needed)
3. Pull official `lfnovo/open_notebook` images
4. Start the stack and open Open Notebook

Data is stored at `~/.local/share/open-notebook-desktop`.

## Build from source

```bash
sudo apt install libwebkit2gtk-4.1-dev build-essential curl wget \
  libssl-dev libayatana-appindicator3-dev librsvg2-dev pkg-config

cd desktop
npm install
npm run tauri dev
```

## Security notes

The desktop launcher uses a dedicated Compose file (`desktop/resources/docker-compose.yml`) that binds services to **localhost only** (`127.0.0.1`), unlike the default root `docker-compose.yml` which exposes ports on all interfaces.

## Troubleshooting

- **Stack not starting**: Open *Management* from the menu bar → check logs
- **Docker permission denied**: Add your user to the `docker` group and log out/in
- **Web UI not loading**: Wait for the splash screen to reach 100% before the notebook window opens

See also [Quick Fixes](../6-TROUBLESHOOTING/quick-fixes.md).
