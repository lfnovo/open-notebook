import os

import yaml
from loguru import logger

from open_notebook.domain.models import DefaultModels
from open_notebook.models import get_model

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

if DEFAULT_MODELS.default_embedding_model:
    EMBEDDING_MODEL = get_model(
        DEFAULT_MODELS.default_embedding_model, model_type="embedding"
    )
else:
    EMBEDDING_MODEL = None

if DEFAULT_MODELS.default_speech_to_text_model:
    SPEECH_TO_TEXT_MODEL = get_model(
        DEFAULT_MODELS.default_speech_to_text_model, model_type="speech_to_text"
    )
else:
    SPEECH_TO_TEXT_MODEL = None
