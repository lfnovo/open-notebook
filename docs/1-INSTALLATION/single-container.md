# Single Container Installation (Deprecated)

> **Deprecated:** the single-container image (`v1-latest-single`) will be removed in v2. It still receives updates until then, but new features and documentation target [Docker Compose](docker-compose.md). Use Docker Compose for new installs.

The single image bundles SurrealDB, the API, the background worker and the web UI in one container. It is mostly useful on hosting platforms that run exactly one container per app.

> **Images:** `lfnovo/open_notebook:v1-latest-single` on Docker Hub, `ghcr.io/lfnovo/open-notebook:v1-latest-single` on GitHub Container Registry.

## What the container needs

Whatever runs it (Docker on your machine or a hosting platform) must provide:

| Need | Value |
|---|---|
| **Port** | `8502` (web UI). Port `5055` (API) too, unless you set `API_URL` (below). |
| **Persistent storage** | Two paths: `/app/data` (uploads, app data) **and** `/mydata` (the database). Without `/mydata` on persistent storage the database is lost every time the container is recreated, including on every image update. |
| **`OPEN_NOTEBOOK_ENCRYPTION_KEY`** | Required. A long random secret; keep it, or saved API keys can't be decrypted. |
| **`SURREAL_URL`** | `ws://localhost:8000/rpc` (the database runs inside the same container). |
| **`SURREAL_USER`, `SURREAL_PASSWORD`** | Both `root` (see below). |
| **`OPEN_NOTEBOOK_PASSWORD`** | Required on anything reachable from a network. Authentication is off when it's unset. |
| **`API_URL`** | Set it to the public URL of the app (for example `https://notebook.example.com`) when only one port is reachable. The browser then sends API calls through the UI server instead of to port 5055. |

The embedded database always starts with user `root` and password `root`, so set `SURREAL_USER=root` and `SURREAL_PASSWORD=root`. Any other value breaks the connection. Don't publish port `8000`; nothing outside the container needs it.

## Run it locally with Docker

```yaml
# docker-compose.yml
services:
  open_notebook:
    image: lfnovo/open_notebook:v1-latest-single
    pull_policy: always
    ports:
      - "8502:8502"  # Web UI
      - "5055:5055"  # API
    environment:
      - OPEN_NOTEBOOK_ENCRYPTION_KEY=change-me-to-a-secret-string
      - SURREAL_URL=ws://localhost:8000/rpc
      - SURREAL_USER=root
      - SURREAL_PASSWORD=root
      - SURREAL_NAMESPACE=open_notebook
      - SURREAL_DATABASE=open_notebook
    volumes:
      - ./notebook_data:/app/data   # app data
      - ./surreal_data:/mydata      # database
    restart: always
```

Change the encryption key, then:

```bash
docker compose up -d
```

Open **http://localhost:8502** and follow [Connect a provider](../4-AI-PROVIDERS/index.md#connect-a-provider). Chat works once the default models are set.

Settings go in the `environment:` block and are applied with `docker compose up -d` (not `restart`). Logs: `docker compose logs -f open_notebook`.

## Hosting platforms

Use the table above to fill in your platform's form: the image, port `8502`, persistent storage for **both** `/app/data` and `/mydata`, and the environment variables. Platforms that can't give you persistent storage at both paths will lose data on redeploy; use a platform or VPS that runs Docker Compose instead.

After deploying, open the app's URL and follow [Connect a provider](../4-AI-PROVIDERS/index.md#connect-a-provider).

### EasyPanel

Open Notebook ships an EasyPanel template in [`examples/easypanel/`](https://github.com/lfnovo/open-notebook/tree/main/examples/easypanel). Unlike the single image, the template provisions **two services** (the Open Notebook app and a separate SurrealDB) and generates the database password, encryption key and, optionally, the app password for you.

- **One-click:** once the template is published to the official [EasyPanel template gallery](https://github.com/easypanel-io/templates), create a new service from "Open Notebook", set an app password (or leave it blank to auto-generate one), and deploy.
- **Manual:** copy `examples/easypanel/` into `templates/open-notebook` in a checkout of [`easypanel-io/templates`](https://github.com/easypanel-io/templates), run the templates playground (`npm run dev`), and create the template from the generated JSON in your EasyPanel instance.

See [`examples/easypanel/README.md`](https://github.com/lfnovo/open-notebook/blob/main/examples/easypanel/README.md) for details.

## Moving to Docker Compose

1. Stop the single container and copy its two data folders.
2. Set up [Docker Compose](docker-compose.md) with the **same** `OPEN_NOTEBOOK_ENCRYPTION_KEY`.
3. Before the first start, put the old database files in `surreal_data/` and the old app data in `notebook_data/`.

The single image's database uses `root:root`, which matches the compose default. The database path inside both setups is `/mydata/mydatabase.db`.

---

**Need help?** [Discord](https://discord.gg/37XJPXfz2w) · [GitHub Issues](https://github.com/lfnovo/open-notebook/issues)
