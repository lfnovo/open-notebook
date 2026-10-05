# Docker Compose Installation (Recommended)

This is the standard way to run Open Notebook. It uses the [`docker-compose.yml`](../../docker-compose.yml) in the root of the repository, which starts two services:

| Service | What it runs | Ports | Data folder |
|---|---|---|---|
| `surrealdb` | The database | `8000` (bound to `127.0.0.1` only) | `./surreal_data` |
| `open_notebook` | Web UI, REST API and the background worker | `8502` (UI), `5055` (API) | `./notebook_data` |

The background worker runs inside the `open_notebook` container, so source processing, embeddings and podcasts work without extra services.

> **Alternative registry:** images are published to Docker Hub (`lfnovo/open_notebook`) and GitHub Container Registry (`ghcr.io/lfnovo/open-notebook`). Swap the `image:` line if Docker Hub is blocked for you.

## Prerequisites

- **Docker with Compose v2.** On macOS and Windows install [Docker Desktop](https://www.docker.com/products/docker-desktop/). On Linux install Docker Engine and the Compose plugin. Check with `docker compose version`.
- **4 GB of free RAM** or more.
- **An AI provider**: an API key from a cloud provider, or a local model server such as Ollama. You add it in the UI after installing.

---

## Step 1: Download the compose file

Create a folder for Open Notebook and download the compose file into it:

```bash
mkdir open-notebook
cd open-notebook
curl -o docker-compose.yml https://raw.githubusercontent.com/lfnovo/open-notebook/main/docker-compose.yml
```

On Windows PowerShell, type `curl.exe` instead of `curl`. You can also open the [file on GitHub](https://github.com/lfnovo/open-notebook/blob/main/docker-compose.yml) and save it as `docker-compose.yml`.

## Step 2: Set your encryption key

Open `docker-compose.yml` and find this line in the `open_notebook` service:

```yaml
      - OPEN_NOTEBOOK_ENCRYPTION_KEY=change-me-to-a-secret-string
```

Replace `change-me-to-a-secret-string` with a long random string of your own (for example the output of `openssl rand -hex 32`). Open Notebook uses it to encrypt the provider API keys it stores.

> **Keep this key.** If it changes later, the keys you saved can no longer be decrypted and you have to enter them again.

## Step 3: Start Open Notebook

```bash
docker compose up -d
```

Check that both services are running:

```bash
docker compose ps
```

The API runs database migrations when it starts. After 20–30 seconds it should answer:

```bash
curl http://localhost:5055/health
# {"status":"healthy"}
```

## Step 4: Open the UI and connect a provider

Open **http://localhost:8502**.

Then follow [Connect a provider](../4-AI-PROVIDERS/index.md#connect-a-provider): add a configuration, test it, add models and set the default models. It ends with a test chat. Chat won't work until the default models are set.

---

## Changing settings

Every Open Notebook setting is an environment variable on the **`open_notebook`** service. Add it to that service's `environment:` block and apply it with:

```bash
docker compose up -d
```

`up -d` recreates the container when its configuration changed. `docker compose restart` does **not** apply new settings.

For example, to require a password:

```yaml
  open_notebook:
    environment:
      # ...existing lines...
      - OPEN_NOTEBOOK_PASSWORD=choose-a-password
```

A few things to know:

- **`.env` is not loaded into the container.** The shipped compose file has no `env_file:`. A `.env` file next to `docker-compose.yml` only fills the `${...}` placeholders in the file (the shipped file uses it for `SURREAL_USER` and `SURREAL_PASSWORD`). Anything else you put in `.env` is ignored.
- **Database credentials** default to `root:root`, and the database port is only reachable from the same machine. To use other credentials, put `SURREAL_USER=...` and `SURREAL_PASSWORD=...` in a `.env` file before the first start; both services read them. See [`.env.example`](../../.env.example).
- **Optional extraction engines** (Docling, Crawl4AI) are commented out in the compose file. When enabled they are installed on the next start, which then takes several minutes. See the [Environment Reference](../5-CONFIGURATION/environment-reference.md).
- **Keep your changes in an override file (optional).** Docker Compose automatically merges a `docker-compose.override.yml` in the same folder. Putting your additions there leaves `docker-compose.yml` untouched, so you can download a newer one later. The variants below use this file.

The full list of settings is in the [Environment Reference](../5-CONFIGURATION/environment-reference.md).

---

## Variants

### Ollama in Docker (local models)

Create `docker-compose.override.yml` next to `docker-compose.yml`:

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    volumes:
      - ./ollama_models:/root/.ollama
    restart: always
```

Start it and download a chat model and an embedding model:

```bash
docker compose up -d
docker compose exec ollama ollama pull qwen3
docker compose exec ollama ollama pull nomic-embed-text
```

When you [connect a provider](../4-AI-PROVIDERS/index.md#connect-a-provider), pick **Ollama** and set **Base URL** to `http://ollama:11434`. GPU setup, model choices and timeouts are in the [Ollama guide](../5-CONFIGURATION/ollama.md).

### Ollama installed on the host

Open Notebook runs in a container, so `localhost` there is the container, not your computer. Use `host.docker.internal` instead.

1. Create `docker-compose.override.yml` so that name resolves on every platform (Docker Desktop already provides it; Docker Engine on Linux needs this line):

   ```yaml
   services:
     open_notebook:
       extra_hosts:
         - "host.docker.internal:host-gateway"
   ```

2. **Linux only:** Ollama listens on `127.0.0.1` by default, which containers can't reach. Make it listen on all interfaces. For the systemd service:

   Run `sudo systemctl edit ollama`, add these lines, save, then run `sudo systemctl restart ollama`:

   ```ini
   [Service]
   Environment="OLLAMA_HOST=0.0.0.0:11434"
   ```

   If you start Ollama by hand, use `OLLAMA_HOST=0.0.0.0:11434 ollama serve`. This also exposes Ollama to your network, so firewall port 11434 if the machine is reachable from outside.

3. Run `docker compose up -d`.
4. When you [connect a provider](../4-AI-PROVIDERS/index.md#connect-a-provider), pick **Ollama** and set **Base URL** to `http://host.docker.internal:11434`.

### Single container

An all-in-one image also exists but is deprecated. See [Single Container](single-container.md).

---

## Access from another machine

By default the browser loads the UI from port `8502` and then calls the API directly on port `5055` of the same host name. So for access from another machine, either:

- make **both** ports `8502` and `5055` reachable, or
- set `API_URL` to the address you open the UI with (for example `- API_URL=http://192.168.1.50:8502`). The browser then sends API calls through the UI server, and only port `8502` needs to be reachable.

Authentication is off unless you set `OPEN_NOTEBOOK_PASSWORD`. Set it before exposing Open Notebook to any network. For HTTPS and domains, see [Reverse Proxy](../5-CONFIGURATION/reverse-proxy.md) and [Security](../5-CONFIGURATION/security.md).

---

## Common tasks

### View logs

```bash
docker compose logs -f open_notebook   # UI, API and worker
docker compose logs -f surrealdb       # database
```

### Stop and start

```bash
docker compose down    # stops and removes the containers; data folders stay
docker compose up -d
```

### Back up

Your data lives in the `surreal_data/` and `notebook_data/` folders. Stop the services and copy both:

```bash
docker compose down
tar czf open-notebook-backup.tgz surreal_data notebook_data
docker compose up -d
```

On Linux the folders are owned by root (the database runs as root for the bind mount), so you may need `sudo tar ...`.

### Update

Back up first, then:

```bash
docker compose pull
docker compose up -d
```

Since v1.15.0, API keys saved (or migrated) by Open Notebook use an encryption format that older versions can't read. If you need to roll back after updating, restore the backup you made before the update.

### Delete everything

`docker compose down -v` does **not** delete your data: the shipped compose file uses bind-mounted folders, not named volumes. To wipe the installation, stop it and delete the folders:

```bash
docker compose down
rm -rf surreal_data notebook_data   # permanent; use sudo on Linux
```

---

## Troubleshooting

**The UI loads but can't reach the API.** The API may still be starting; check `docker compose logs -f open_notebook`. If you open the UI from another machine, see [Access from another machine](#access-from-another-machine).

**Port already in use.** Change the host side of the mapping, for example `"8503:8502"`, run `docker compose up -d` and open `http://localhost:8503`.

**`Permission denied` or `Failed to create RocksDB directory` in the database logs (Linux).** The `surrealdb` service needs `user: root` to write to the bind-mounted folder. The shipped file has it; add it if your compose file is older, then run `docker compose up -d`.

**Sources stay queued.** The worker runs inside `open_notebook`; look for errors in `docker compose logs open_notebook`.

**Chat fails right after installing.** The default models aren't set. See step 4 of [Connect a provider](../4-AI-PROVIDERS/index.md#4-set-default-models).

More: [Quick Fixes](../6-TROUBLESHOOTING/quick-fixes.md) · [Connection Issues](../6-TROUBLESHOOTING/connection-issues.md).

---

## Other examples

The [`examples/`](../../examples/) folder has complete compose files for other setups, including Ollama, a fully local stack and a speech server. They are maintained separately from this guide; compare them with the root `docker-compose.yml` before using one.

## Next steps

- [User Guide](../3-USER-GUIDE/index.md)
- [Security](../5-CONFIGURATION/security.md) and [Reverse Proxy](../5-CONFIGURATION/reverse-proxy.md) before exposing it to a network

**Need help?** [Discord](https://discord.gg/37XJPXfz2w) · [GitHub Issues](https://github.com/lfnovo/open-notebook/issues)
