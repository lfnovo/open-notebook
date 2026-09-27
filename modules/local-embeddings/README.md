# Local embeddings

This installation profile uses a local Ollama embedding model. It contains no
downloaded model weights and never changes the active notebook's embedding space.

1. Install/start Ollama on the host and pull `nomic-embed-text`.
2. In Open Notebook → Models, add the Ollama embedding model using the host URL
   reachable from the API process (`http://host.lima.internal:11434` with Colima;
   `http://127.0.0.1:11434` for a host API).
3. Select it as the default embedding model. Preserve the currently selected
   model for existing installations; changing it requires rebuilding embeddings.

The module manager records that this profile is installed. Ollama remains an
independently managed local service. No API subscription is required.
