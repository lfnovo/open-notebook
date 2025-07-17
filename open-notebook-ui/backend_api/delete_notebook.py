import os
import json
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from open_notebook.domain.notebook import Notebook
from loguru import logger

# Configure loguru to write to stderr
logger.remove()
logger.add(sys.stderr, level="DEBUG")

load_dotenv()

# Set environment variables for SurrealDB connection
os.environ["SURREAL_ADDRESS"] = os.getenv("SURREAL_ADDRESS", "localhost")
os.environ["SURREAL_PORT"] = os.getenv("SURREAL_PORT", "8000")
os.environ["SURREAL_USER"] = os.getenv("SURREAL_USER", "root")
os.environ["SURREAL_PASS"] = os.getenv("SURREAL_PASS", "root")
os.environ["SURREAL_NAMESPACE"] = os.getenv("SURREAL_NAMESPACE", "open_notebook")
os.environ["SURREAL_DATABASE"] = os.getenv("SURREAL_DATABASE", "open_notebook")

def delete_existing_notebook(notebook_id):
    try:
        notebook = Notebook.get(notebook_id)
        if not notebook:
            raise ValueError(f"Notebook with ID {notebook_id} not found.")
        
        success = notebook.delete()
        print(json.dumps({"success": success}))
        sys.stdout.flush() # Explicitly flush stdout
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.stdout.flush() # Explicitly flush stdout for error output too
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        notebook_id = sys.argv[1]
        delete_existing_notebook(notebook_id)
    else:
        print(json.dumps({"error": "Notebook ID not provided."}))
        sys.exit(1)
