# OpenAI-Compatible Providers

The **OpenAI Compatible** provider connects Open Notebook to any server that speaks the OpenAI API: LM Studio, vLLM, llama.cpp's server, LocalAI, Text Generation WebUI, Speaches and many hosted gateways. It supports language, embedding, speech-to-text and text-to-speech models.

For Ollama and oMLX, prefer their native providers: [Ollama](ollama.md), [oMLX](omlx.md).

---

## Setup

1. Start your server and note its address, including the API path (usually `/v1`).
2. Open **Manage → Models** and, in the **OpenAI Compatible** section, click **Add Configuration**.
3. Fill in:
   - **Configuration Name**, e.g. "LM Studio"
   - **API Key**: optional. Leave it empty if the server doesn't check keys; some servers want any non-empty value
   - **Base URL**: the server's API root, e.g. `http://host.docker.internal:1234/v1`
4. Click **Add Configuration**, then **Test** on the new configuration. The test asks the server for its model list.
5. Click **Models** to open **Discover Models**, choose the **Model Type**, tick the models and click **Add Selected**. If the server doesn't list a model, type its exact id in the search box and click **Add "…"**.
6. Assign the models under **Default Model Assignments**.

One configuration has one Base URL. To use different servers for different jobs (LM Studio for chat, Speaches for speech), add one OpenAI Compatible configuration per server. Each model you register remembers which configuration it came from.

---

## Base URL from inside Docker

`localhost` inside the Open Notebook container is the container itself.

| Your server runs | Base URL |
|------------------|----------|
| On the host, Docker Desktop (macOS/Windows) | `http://host.docker.internal:<port>/v1` |
| On the host, Linux | `http://host.docker.internal:<port>/v1` after adding `extra_hosts: ["host.docker.internal:host-gateway"]` to the `open_notebook` service, or the bridge IP `http://172.17.0.1:<port>/v1` |
| In the same compose file | `http://<service-name>:<container-port>/v1` |
| On another machine | `http://<server-ip>:<port>/v1` |
| Open Notebook from source, server on the same machine | `http://localhost:<port>/v1` |

The server must listen on an address the container can reach (often `0.0.0.0` rather than `127.0.0.1`).

Check from inside the container:

```bash
docker compose exec open_notebook curl -s http://host.docker.internal:1234/v1/models
```

---

## LM Studio

1. In LM Studio, load a model and start the local server (default port 1234). Enable "Serve on Local Network" if Open Notebook runs in Docker on Linux or on another machine.
2. Base URL: `http://host.docker.internal:1234/v1` (Open Notebook in Docker) or `http://localhost:1234/v1` (from source). No API key.

## vLLM

```bash
vllm serve meta-llama/Llama-3.1-8B-Instruct --port 8001
```

Base URL `http://host.docker.internal:8001/v1`. The model id is the Hugging Face path you served. Avoid port 8000 on the host if SurrealDB already uses it.

In the same compose file:

```yaml
services:
  vllm:
    image: vllm/vllm-openai:latest
    command: --model meta-llama/Llama-3.1-8B-Instruct
    volumes:
      - ~/.cache/huggingface:/root/.cache/huggingface
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

Base URL `http://vllm:8000/v1` (the container port; no host port needs to be published).

## llama.cpp server

```bash
llama-server -m model.gguf --host 0.0.0.0 --port 8080
```

Base URL `http://host.docker.internal:8080/v1`. If embeddings fail with null values on very short chunks, see `OPEN_NOTEBOOK_MIN_CHUNK_SIZE` in the [Environment Reference](environment-reference.md#embeddings-and-chunking).

## Text Generation WebUI

Start it with `--api --listen`; its OpenAI-compatible API listens on port 5000. Base URL `http://host.docker.internal:5000/v1`.

## Speech servers

For local text-to-speech and speech-to-text with Speaches, see [Local speech with Speaches](local-tts.md).

---

## Troubleshooting

| Message from **Test** | Cause | Fix |
|-----------------------|-------|-----|
| "Cannot connect to server. Check the URL is correct." | Nothing answers at that address, or TLS verification failed | Check the Base URL from inside the container (curl above). For HTTPS with a private CA, set `ESPERANTO_SSL_CA_BUNDLE` ([Advanced → SSL](advanced.md#ssl-for-self-signed-providers)) |
| "Connection timed out. Check if server is accessible." | Firewall, wrong IP, or the server is busy loading a model | Check reachability; retry once the model is loaded |
| "Invalid API key" | The server checks keys and the one saved doesn't match | Edit the configuration and set the key |
| "Server returned status 404" | Base URL is missing the API path | Add `/v1` (or whatever path your server uses) |

During use:

- **Model not found:** the id you registered doesn't match what the server serves. Compare with `curl <base-url>/models` and re-add the model with the exact id.
- **Slow answers fail after three minutes:** model calls are limited by `ESPERANTO_LLM_TIMEOUT` (180 s). The error reads "The AI provider took too long to respond. Try again, use a faster model, or raise ESPERANTO_LLM_TIMEOUT (180 seconds by default)." Raise it in the `open_notebook` environment, below 600, and set `OPEN_NOTEBOOK_WORKER_MAX_TASKS=1` if one GPU serves everything. Details in [Advanced → Model call timeout](advanced.md#model-call-timeout).

---

## Legacy environment variables

`OPENAI_COMPATIBLE_BASE_URL` / `OPENAI_COMPATIBLE_API_KEY` and their per-modality variants (`_LLM`, `_EMBEDDING`, `_STT`, `_TTS`) are a deprecated fallback. **Migrate to Database** copies only the generic pair. See the [Environment Reference](environment-reference.md#legacy-ai-provider-variables-deprecated).

---

## Related

- [AI Providers](ai-providers.md)
- [Local speech with Speaches](local-tts.md)
- [Ollama](ollama.md), [oMLX](omlx.md)
