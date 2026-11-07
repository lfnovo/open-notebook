# Quick Start - External Ollama

Run Open Notebook in Docker and connect it to an **Ollama you installed directly on your computer** (not in Docker). Useful when you already use Ollama, or want its native GPU support without Docker GPU passthrough.

If you don't have Ollama yet and want everything in Docker, use the [Local Quick Start](quick-start-local.md).

## Prerequisites

1. **Docker with Compose v2**: [Docker Desktop](https://www.docker.com/products/docker-desktop/) on macOS and Windows; Docker Engine with the Compose plugin on Linux.
2. **Ollama** installed from [ollama.com](https://ollama.com/download). Check with `ollama --version`.

## Step 1: Download models (2-5 min)

Open Notebook needs a chat model and an embedding model:

```bash
ollama pull qwen3
ollama pull nomic-embed-text
```

On a smaller machine, use `llama3.2` or `gemma3:1b` instead of `qwen3`.

## Step 2: Let containers reach Ollama

Open Notebook runs in a container, where `localhost` means the container itself. It reaches your computer's Ollama through the name `host.docker.internal`.

**macOS and Windows (Docker Desktop):** Docker Desktop forwards `host.docker.internal` to your computer, so Ollama's default setup usually works as is; try it first. If the connection test in Step 5 fails, make Ollama listen on all interfaces: on macOS run `launchctl setenv OLLAMA_HOST "0.0.0.0:11434"`, then quit and reopen the Ollama app (this setting is lost when you log out or reboot, so run it again after each login, or follow Ollama's FAQ for a permanent setup); on Windows add a user environment variable `OLLAMA_HOST` = `0.0.0.0:11434`, then quit and restart Ollama. See Ollama's [documentation](https://github.com/ollama/ollama/tree/main/docs) (FAQ, "How do I configure Ollama server?").

**Linux:** Ollama listens only on `127.0.0.1` by default, which containers can't reach. Make it listen on all interfaces. If Ollama runs as the systemd service (the default for the Linux installer):

```bash
sudo systemctl edit ollama
```

Add these lines, save, and restart:

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

```bash
sudo systemctl restart ollama
```

If you run Ollama by hand, start it with `OLLAMA_HOST=0.0.0.0:11434 ollama serve`.

**On any platform,** `OLLAMA_HOST=0.0.0.0` exposes Ollama's API, which has no authentication, on every network interface. Allow port 11434 only from this computer and its Docker networks (for example with your firewall), never from untrusted networks.

## Step 3: Download and configure Open Notebook (1 min)

```bash
mkdir open-notebook
cd open-notebook
curl -o docker-compose.yml https://raw.githubusercontent.com/lfnovo/open-notebook/main/docker-compose.yml
```

(On Windows PowerShell, use `curl.exe`.)

Open `docker-compose.yml` and replace `change-me-to-a-secret-string` in the `OPEN_NOTEBOOK_ENCRYPTION_KEY` line with a long random secret you generate yourself, for example with `openssl rand -hex 32` (Windows: see [Set your encryption key](../1-INSTALLATION/docker-compose.md#step-2-set-your-encryption-key)). Don't reuse an example value.

> **Shared network or server?** The shipped file publishes the UI (`8502`) and API (`5055`) on all network interfaces, and there is no password by default. If other devices can reach this machine, do one of these before starting: change the two `open_notebook` port lines to `"127.0.0.1:8502:8502"` and `"127.0.0.1:5055:5055"`, or add `- OPEN_NOTEBOOK_PASSWORD=your-password` to its `environment:` block.

Then create `docker-compose.override.yml` in the same folder. On Linux this is what makes `host.docker.internal` resolve; on Docker Desktop it's harmless:

```yaml
services:
  open_notebook:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

## Step 4: Start (1 min)

```bash
docker compose up -d
```

## Step 5: Connect Ollama and chat (3 min)

Open **http://localhost:8502** and follow **[Connect a provider](../4-AI-PROVIDERS/index.md#connect-a-provider)** with these values:

| Field | Value |
|---|---|
| Provider | **Ollama** |
| API Key | Leave empty |
| Base URL | `http://host.docker.internal:11434` |
| Models to add | Your chat model as **Language** (listed as `qwen3:latest`), then `nomic-embed-text:latest` as **Embedding** |
| Defaults | Click **Auto-assign Defaults** |

The last step of that page creates a notebook, adds a text source and sends a chat message.

## Verification checklist

- [ ] `ollama list` shows a chat model and `nomic-embed-text`
- [ ] `docker compose ps` shows `surrealdb` and `open_notebook` running
- [ ] **Test** on the Ollama configuration shows a green check
- [ ] **Default Model Assignments** has a Chat Model and an Embedding Model
- [ ] A chat message gets an answer

## Troubleshooting

**Test shows a red cross.** Check from inside the container:

```bash
docker compose exec open_notebook curl -s http://host.docker.internal:11434/api/version
```

- *Could not resolve host*: the `extra_hosts` override is missing, or you didn't run `docker compose up -d` after adding it.
- *Connection refused*: Ollama is still listening on `127.0.0.1` only. Redo Step 2 (on macOS and Windows, apply the `OLLAMA_HOST` fallback). On Linux, check with `ss -ltn | grep 11434`; it should show `*:11434` or `0.0.0.0:11434`.
- No answer at all: a firewall is blocking port 11434 between Docker and the host.

**Responses are slow or time out.** See the timeouts section of the [Ollama guide](../5-CONFIGURATION/ollama.md).

**Adding more models later.** Run `ollama pull <model>`, then click **Models** on the Ollama configuration again (it opens the **Discover Models** dialog) and add it.

## Ollama in Docker or on the host?

| | Ollama in Docker ([Local Quick Start](quick-start-local.md)) | Ollama on the host (this guide) |
|---|---|---|
| GPU | Needs Docker GPU setup | Uses the GPU natively (including Apple Silicon) |
| Managing models | `docker compose exec ollama ollama ...` | `ollama ...` |
| Networking | Works out of the box | Needs `extra_hosts`; Linux (and sometimes Docker Desktop) needs `OLLAMA_HOST` |

## Next steps

- [Ollama guide](../5-CONFIGURATION/ollama.md): model choices, networking, timeouts
- [Docker Compose guide](../1-INSTALLATION/docker-compose.md): settings, backups, updates
- [User Guide](../3-USER-GUIDE/index.md)

**Need help?** Join our [Discord community](https://discord.gg/37XJPXfz2w).
