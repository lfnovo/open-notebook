import os
import json
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from open_notebook.domain.notebook import Note

load_dotenv()

# Set environment variables for SurrealDB connection
os.environ["SURREAL_ADDRESS"] = os.getenv("SURREAL_ADDRESS", "localhost")
os.environ["SURREAL_PORT"] = os.getenv("SURREAL_PORT", "8000")
os.environ["SURREAL_USER"] = os.getenv("SURREAL_USER", "root")
os.environ["SURREAL_PASS"] = os.getenv("SURREAL_PASS", "root")
os.environ["SURREAL_NAMESPACE"] = os.getenv("SURREAL_NAMESPACE", "open_notebook")
os.environ["SURREAL_DATABASE"] = os.getenv("SURREAL_DATABASE", "open_notebook")

def get_note_details(note_id):
    try:
        note = Note.get(note_id)
        if not note:
            raise ValueError(f"Note with ID {note_id} not found.")
        
        # Use model_dump_json() for proper datetime serialization
        note_data = json.loads(note.model_dump_json())
        
        print(json.dumps(note_data))
        sys.stdout.flush()
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.stdout.flush()
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        note_id = sys.argv[1]
        get_note_details(note_id)
    else:
        print(json.dumps({"error": "Note ID not provided."}))
        sys.stdout.flush()
        sys.exit(1)
