import os
import json
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from open_notebook.domain.notebook import vector_search
from open_notebook.domain.models import model_manager # Needed for embedding model

load_dotenv()

# Set environment variables for SurrealDB connection
os.environ["SURREAL_ADDRESS"] = os.getenv("SURREAL_ADDRESS", "localhost")
os.environ["SURREAL_PORT"] = os.getenv("SURREAL_PORT", "8000")
os.environ["SURREAL_USER"] = os.getenv("SURREAL_USER", "root")
os.environ["SURREAL_PASS"] = os.getenv("SURREAL_PASS", "root")
os.environ["SURREAL_NAMESPACE"] = os.getenv("SURREAL_NAMESPACE", "open_notebook")
os.environ["SURREAL_DATABASE"] = os.getenv("SURREAL_DATABASE", "open_notebook")

def perform_vector_search(keyword, results_limit, search_sources, search_notes, minimum_score):
    try:
        # Ensure embedding model is available
        if not model_manager.embedding_model:
            raise ValueError("No embedding model configured. Vector search is not available.")
            
        search_results = vector_search(keyword, results_limit, search_sources, search_notes, minimum_score)
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
        minimum_score = float(sys.argv[5]) if len(sys.argv) > 5 else 0.2
        perform_vector_search(keyword, results_limit, search_sources, search_notes, minimum_score)
    else:
        print(json.dumps({"error": "Search keyword not provided."}))
        sys.stdout.flush()
        sys.exit(1)
