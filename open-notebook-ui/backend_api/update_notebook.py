import os
import json
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from open_notebook.domain.notebook import Notebook

load_dotenv()

# Set environment variables for SurrealDB connection
os.environ["SURREAL_ADDRESS"] = os.getenv("SURREAL_ADDRESS", "localhost")
os.environ["SURREAL_PORT"] = os.getenv("SURREAL_PORT", "8000")
os.environ["SURREAL_USER"] = os.getenv("SURREAL_USER", "root")
os.environ["SURREAL_PASS"] = os.getenv("SURREAL_PASS", "root")
os.environ["SURREAL_NAMESPACE"] = os.getenv("SURREAL_NAMESPACE", "open_notebook")
os.environ["SURREAL_DATABASE"] = os.getenv("SURREAL_DATABASE", "open_notebook")

def update_existing_notebook(notebook_id, name, description, archived):
    try:
        notebook = Notebook.get(notebook_id)
        if not notebook:
            raise ValueError(f"Notebook with ID {notebook_id} not found.")

        notebook.name = name
        notebook.description = description
        notebook.archived = archived
        notebook.save()
        print(json.dumps(json.loads(notebook.model_dump_json()))) # Ensure it's a dict for JSON
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        notebook_id = sys.argv[1]
        input_data = sys.stdin.read()
        try:
            data = json.loads(input_data)
            notebook_name = data.get("name")
            notebook_description = data.get("description")
            notebook_archived = data.get("archived")
            update_existing_notebook(notebook_id, notebook_name, notebook_description, notebook_archived)
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"Invalid JSON input: {e}"}))
            sys.exit(1)
        except Exception as e:
            print(json.dumps({"error": str(e)}))
            sys.exit(1)
    else:
        print(json.dumps({"error": "Notebook ID not provided."}))
        sys.exit(1)
