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

# PODCASTS FOLDER
# Matches the root that build_episode_output_dir() (commands/podcast_commands.py)
# creates episode directories under when called with DATA_FOLDER in production.
PODCASTS_FOLDER = f"{DATA_FOLDER}/podcasts"
os.makedirs(PODCASTS_FOLDER, exist_ok=True)

# TIKTOKEN CACHE FOLDER
# Reads TIKTOKEN_CACHE_DIR from the environment so Docker can redirect the cache
# to a path outside /data/ (which is typically volume-mounted and would hide the
# pre-baked encoding baked into the image at build time).
TIKTOKEN_CACHE_DIR = os.environ.get("TIKTOKEN_CACHE_DIR", "").strip() or f"{DATA_FOLDER}/tiktoken-cache"
os.makedirs(TIKTOKEN_CACHE_DIR, exist_ok=True)

# RDLens 嵌入式作用域（SPK-03）
# 启用后：禁用 Source/Note Embedding（REQ-DIS-01）、原生 Provider/原生 AI 路径
# （REQ-DIS-02），屏蔽全局页面与直接 API（REQ-SCOPE-03 / REQ-AUTH-03），
# 并把 AI 生成固定绑定 Research Gateway 的 OpenAI 兼容端点。
# 模块属性在调用时读取，便于测试注入；默认关闭保持上游行为。
RD_EMBEDDED_MODE = (
    os.environ.get("RD_EMBEDDED_MODE", "").strip().lower() in ("1", "true", "yes")
)
RD_EMBEDDED_NOTEBOOK_ID = os.environ.get("RD_EMBEDDED_NOTEBOOK_ID", "").strip()
RD_AI_GATEWAY_URL = os.environ.get("RD_AI_GATEWAY_URL", "").strip()
RD_AI_GATEWAY_MODEL = os.environ.get("RD_AI_GATEWAY_MODEL", "").strip()
RD_AI_GATEWAY_API_KEY = os.environ.get("RD_AI_GATEWAY_API_KEY", "").strip()
