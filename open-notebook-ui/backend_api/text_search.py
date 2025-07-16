import os
import json
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from open_notebook.domain.notebook import text_search

load_dotenv()

# Set environment variables for SurrealDB connection
os.environ["SURREAL_ADDRESS"] = os.getenv("SURREAL_ADDRESS", "localhost")
os.environ["SURREAL_PORT"] = os.getenv("SURREAL_PORT", "8000")
os.environ["SURREAL_USER"] = os.getenv("SURREAL_USER", "root")
os.environ["SURREAL_PASS"] = os.getenv("SURREAL_PASS", "root")
os.environ["SURREAL_NAMESPACE"] = os.getenv("SURREAL_NAMESPACE", "open_notebook")
os.environ["SURREAL_DATABASE"] = os.getenv("SURREAL_DATABASE", "open_notebook")

def perform_text_search(keyword, results_limit, search_sources, search_notes):
    try:
        search_results = text_search(keyword, results_limit, search_sources, search_notes)
        # Convert any datetime objects within results to strings if necessary
        # (text_search should return JSON-serializable data, but double-check)
        print(json.dumps(search_results))
        sys.stdout.flush()
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.stdout.flush()
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        keyword = sys.argv[1]
        results_limit = int(sys.argv[2]) if len(sys.argv) > 2 else 100
        search_sources = sys.argv[3].lower() == 'true' if len(sys.argv) > 3 else True
        search_notes = sys.argv[4].lower() == 'true' if len(sys.argv) > 4 else True
        perform_text_search(keyword, results_limit, search_sources, search_notes)
    else:
        print(json.dumps({"error": "Search keyword not provided."}))
        sys.stdout.flush()
        sys.exit(1)
