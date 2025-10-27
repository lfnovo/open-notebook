"""
Pytest configuration file.

This file ensures that the project root is in the Python path,
allowing tests to import from the api and open_notebook modules.
"""

import os
import sys
from pathlib import Path

# Ensure password auth is disabled for tests BEFORE any imports
# The PasswordAuthMiddleware skips auth when this env var is not set
# Set to empty string instead of deleting to prevent it from being reloaded
os.environ["OPEN_NOTEBOOK_PASSWORD"] = ""

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
