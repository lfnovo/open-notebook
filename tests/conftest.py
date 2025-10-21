"""
Pytest configuration file.

This file ensures that the project root is in the Python path,
allowing tests to import from the api and open_notebook modules.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Ensure password auth is disabled for tests
# The PasswordAuthMiddleware skips auth when this env var is not set
if "OPEN_NOTEBOOK_PASSWORD" in os.environ:
    del os.environ["OPEN_NOTEBOOK_PASSWORD"]
