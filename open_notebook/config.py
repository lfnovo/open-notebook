import os
from typing import MutableMapping

# ROOT DATA FOLDER
DATA_FOLDER = "./data"

# LANGGRAPH CHECKPOINT FILE
sqlite_folder = f"{DATA_FOLDER}/sqlite-db"
os.makedirs(sqlite_folder, exist_ok=True)
LANGGRAPH_CHECKPOINT_FILE = f"{sqlite_folder}/checkpoints.sqlite"

# UPLOADS FOLDER
UPLOADS_FOLDER = f"{DATA_FOLDER}/uploads"
os.makedirs(UPLOADS_FOLDER, exist_ok=True)

# PODCASTS FOLDER
# Matches the root that build_episode_output_dir() (commands/podcast_commands.py)
# creates episode directories under when called with DATA_FOLDER in production.
PODCASTS_FOLDER = f"{DATA_FOLDER}/podcasts"
os.makedirs(PODCASTS_FOLDER, exist_ok=True)

# TIKTOKEN CACHE FOLDER
# Reads TIKTOKEN_CACHE_DIR from the environment so Docker can redirect the cache
# to a path outside /data/ (which is typically volume-mounted and would hide the
# pre-baked encoding baked into the image at build time).
TIKTOKEN_CACHE_DIR = (
    os.environ.get("TIKTOKEN_CACHE_DIR", "").strip() or f"{DATA_FOLDER}/tiktoken-cache"
)
os.makedirs(TIKTOKEN_CACHE_DIR, exist_ok=True)

# LLM TIMEOUT
# Since esperanto 2.28, to_langchain() enforces ESPERANTO_LLM_TIMEOUT on every
# provider (default 60 s; before, most providers used their SDK default and
# Ollama waited forever). 60 s cuts off long answers and slow local models, so
# Open Notebook defaults it to 180 s, well below the web UI's 600 s request
# timeout (NEXT_PUBLIC_API_TIMEOUT_MS). An explicit value always wins. Both the API and
# the worker import this module before any model is created.
DEFAULT_LLM_TIMEOUT_SECONDS = 180


def ensure_llm_timeout_default(environ: MutableMapping[str, str] = os.environ) -> None:
    """Set ESPERANTO_LLM_TIMEOUT to Open Notebook's default when unset or blank."""
    if not environ.get("ESPERANTO_LLM_TIMEOUT", "").strip():
        environ["ESPERANTO_LLM_TIMEOUT"] = str(DEFAULT_LLM_TIMEOUT_SECONDS)


ensure_llm_timeout_default()
