import os

import yaml
from loguru import logger

from open_notebook.domain.models import DefaultModels
from open_notebook.models.embedding_models import get_embedding_model
from open_notebook.models.speech_to_text_models import get_speech_to_text_model

# todo: enable config file overwrite with env vars
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
config_path = os.path.join(project_root, "open_notebook_config.yaml")

try:
    with open(config_path, "r") as file:
        CONFIG = yaml.safe_load(file)
except Exception:
    logger.critical("Config file not found, using empty defaults")
    logger.debug(f"Looked in {config_path}")
    CONFIG = {}

# ROOT DATA FOLDER
# todo: make this configurable once podcastfy supports it
DATA_FOLDER = "./data"

# LANGGRAPH CHECKPOINT FILE
sqlite_folder = f"{DATA_FOLDER}/sqlite-db"
os.makedirs(sqlite_folder, exist_ok=True)
LANGGRAPH_CHECKPOINT_FILE = f"{sqlite_folder}/checkpoints.sqlite"

# UPLOADS FOLDER
UPLOADS_FOLDER = f"{DATA_FOLDER}/uploads"
os.makedirs(UPLOADS_FOLDER, exist_ok=True)

# PODCASTS FOLDER
PODCASTS_FOLDER = f"{DATA_FOLDER}/podcasts"
os.makedirs(PODCASTS_FOLDER, exist_ok=True)


DEFAULT_MODELS = DefaultModels.load()

EMBEDDING_MODEL = get_embedding_model(DEFAULT_MODELS.default_embedding_model)

SPEECH_TO_TEXT_MODEL = get_speech_to_text_model(
    DEFAULT_MODELS.default_speech_to_text_model
)
