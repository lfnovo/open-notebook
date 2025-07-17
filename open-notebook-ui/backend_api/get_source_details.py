import os
import json
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from open_notebook.domain.notebook import Source

load_dotenv()

# Set environment variables for SurrealDB connection
os.environ["SURREAL_ADDRESS"] = os.getenv("SURREAL_ADDRESS", "localhost")
os.environ["SURREAL_PORT"] = os.getenv("SURREAL_PORT", "8000")
os.environ["SURREAL_USER"] = os.getenv("SURREAL_USER", "root")
os.environ["SURREAL_PASS"] = os.getenv("SURREAL_PASS", "root")
os.environ["SURREAL_NAMESPACE"] = os.getenv("SURREAL_NAMESPACE", "open_notebook")
os.environ["SURREAL_DATABASE"] = os.getenv("SURREAL_DATABASE", "open_notebook")

def get_source_details(source_id):
    try:
        source = Source.get(source_id)
        if not source:
            raise ValueError(f"Source with ID {source_id} not found.")
        
        # Use model_dump_json() for proper datetime serialization
        source_data = json.loads(source.model_dump_json())
        
        # Optionally include insights if needed for display
        # source_data['insights'] = [json.loads(i.model_dump_json()) for i in source.insights]

        print(json.dumps(source_data))
        sys.stdout.flush()
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.stdout.flush()
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        source_id = sys.argv[1]
        get_source_details(source_id)
    else:
        print(json.dumps({"error": "Source ID not provided."}))
        sys.stdout.flush()
        sys.exit(1)
