import os
import json
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from open_notebook.domain.notebook import Source
from open_notebook.config import UPLOADS_FOLDER # Assuming UPLOADS_FOLDER is defined here

load_dotenv()

# Set environment variables for SurrealDB connection
os.environ["SURREAL_ADDRESS"] = os.getenv("SURREAL_ADDRESS", "localhost")
os.environ["SURREAL_PORT"] = os.getenv("SURREAL_PORT", "8000")
os.environ["SURREAL_USER"] = os.getenv("SURREAL_USER", "root")
os.environ["SURREAL_PASS"] = os.getenv("SURREAL_PASS", "root")
os.environ["SURREAL_NAMESPACE"] = os.getenv("SURREAL_NAMESPACE", "open_notebook")
os.environ["SURREAL_DATABASE"] = os.getenv("SURREAL_DATABASE", "open_notebook")

def add_new_source(notebook_id, source_type, content=None, url=None, file_path=None):
    try:
        source_data = {}
        if source_type == "text":
            source_data["full_text"] = content
            source_data["title"] = content[:50] + "..." if content else "Text Source"
        elif source_type == "link":
            source_data["asset"] = {"url": url}
            source_data["title"] = url
            # In a real scenario, you'd fetch content from the URL here
            source_data["full_text"] = f"Content from URL: {url}" # Placeholder
        elif source_type == "upload":
            source_data["asset"] = {"file_path": file_path}
            source_data["title"] = os.path.basename(file_path) if file_path else "Uploaded File"
            # In a real scenario, you'd process the file content here
            source_data["full_text"] = f"Content from file: {file_path}" # Placeholder
        else:
            raise ValueError("Invalid source type provided.")

        source = Source(**source_data)
        source.save()
        source.add_to_notebook(notebook_id)
        print(json.dumps(json.loads(source.model_dump_json())))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    input_data = sys.stdin.read()
    try:
        data = json.loads(input_data)
        notebook_id = data.get("notebook_id")
        source_type = data.get("source_type")
        content = data.get("content")
        url = data.get("url")
        file_path = data.get("file_path") # This will be the path on the server after upload

        if not notebook_id:
            raise ValueError("Notebook ID is required.")

        add_new_source(notebook_id, source_type, content, url, file_path)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON input: {e}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
