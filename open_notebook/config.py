import os

# ROOT DATA FOLDER
DATA_FOLDER = "./data"

# LANGGRAPH CHECKPOINT FILE
sqlite_folder = f"{DATA_FOLDER}/sqlite-db"
os.makedirs(sqlite_folder, exist_ok=True)
LANGGRAPH_CHECKPOINT_FILE = f"{sqlite_folder}/checkpoints.sqlite"

# UPLOADS FOLDER
UPLOADS_FOLDER = f"{DATA_FOLDER}/uploads"
os.makedirs(UPLOADS_FOLDER, exist_ok=True)

# TIKTOKEN CACHE FOLDER
# Reads TIKTOKEN_CACHE_DIR from the environment so Docker can redirect the cache
# to a path outside /data/ (which is typically volume-mounted and would hide the
# pre-baked encoding baked into the image at build time).
TIKTOKEN_CACHE_DIR = os.environ.get("TIKTOKEN_CACHE_DIR", "").strip() or f"{DATA_FOLDER}/tiktoken-cache"
os.makedirs(TIKTOKEN_CACHE_DIR, exist_ok=True)

# REPO REVIEW ALLOWED ROOTS
# Colon-separated list of absolute directories the repo-review feature is allowed
# to read. This is the security boundary: the backend will refuse to scan any path
# outside these roots. Empty (the default) disables the feature with a clear error.
# Docker note: the repo must be volume-mounted into the container and its in-container
# path listed here (e.g. REPO_REVIEW_ALLOWED_ROOTS=/repos).
REPO_REVIEW_ALLOWED_ROOTS = [
    root.strip()
    for root in os.environ.get("REPO_REVIEW_ALLOWED_ROOTS", "").split(os.pathsep)
    if root.strip()
]
