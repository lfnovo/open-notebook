import os

import yaml
from loguru import logger

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
