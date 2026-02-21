"""
Reproduce issue #264: tiktoken crashes instead of falling back when offline.

Run: uv run python scripts/repro_264.py

Before fix: raises an unhandled exception (network error propagates out of token_count).
After fix:  prints a token count and a warning log.
"""

import urllib.error
from unittest.mock import patch

print("=== Testing tiktoken offline behavior ===")

# Simulate no internet access for tiktoken's encoding download.
# tiktoken calls urllib.request.urlopen internally when the encoding
# file is not already cached on disk.
with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("No network")):
    # Clear in-memory registry so tiktoken tries to re-download the encoding.
    try:
        import tiktoken.registry

        tiktoken.registry._encoding_registry.clear()
    except Exception:
        pass

    from open_notebook.utils.token_utils import token_count

    try:
        result = token_count("Hello world, this is a test string for token counting.")
        print(f"Result: {result} tokens (fallback worked!)")
    except Exception as e:
        print(f"FAILED (bug present): {type(e).__name__}: {e}")
