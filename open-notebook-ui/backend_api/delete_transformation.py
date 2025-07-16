import os
import json
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from open_notebook.domain.transformation import Transformation

load_dotenv()

# Set environment variables for SurrealDB connection
os.environ["SURREAL_ADDRESS"] = os.getenv("SURREAL_ADDRESS", "localhost")
os.environ["SURREAL_PORT"] = os.getenv("SURREAL_PORT", "8000")
os.environ["SURREAL_USER"] = os.getenv("SURREAL_USER", "root")
os.environ["SURREAL_PASS"] = os.getenv("SURREAL_PASS", "root")
os.environ["SURREAL_NAMESPACE"] = os.getenv("SURREAL_NAMESPACE", "open_notebook")
os.environ["SURREAL_DATABASE"] = os.getenv("SURREAL_DATABASE", "open_notebook")

def delete_existing_transformation(transformation_id):
    try:
        transformation = Transformation.get(transformation_id)
        if not transformation:
            raise ValueError(f"Transformation with ID {transformation_id} not found.")
        
        success = transformation.delete()
        print(json.dumps({"success": success}))
        sys.stdout.flush()
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.stdout.flush()
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        transformation_id = sys.argv[1]
        delete_existing_transformation(transformation_id)
    else:
        print(json.dumps({"error": "Transformation ID not provided."}))
        sys.stdout.flush()
        sys.exit(1)
