import os
import json
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from open_notebook.domain.transformation import Transformation, DefaultPrompts

load_dotenv()

# Set environment variables for SurrealDB connection
os.environ["SURREAL_ADDRESS"] = os.getenv("SURREAL_ADDRESS", "localhost")
os.environ["SURREAL_PORT"] = os.getenv("SURREAL_PORT", "8000")
os.environ["SURREAL_USER"] = os.getenv("SURREAL_USER", "root")
os.environ["SURREAL_PASS"] = os.getenv("SURREAL_PASS", "root")
os.environ["SURREAL_NAMESPACE"] = os.getenv("SURREAL_NAMESPACE", "open_notebook")
os.environ["SURREAL_DATABASE"] = os.getenv("SURREAL_DATABASE", "open_notebook")

def get_all_transformations():
    try:
        transformations = Transformation.get_all(order_by="name asc")
        return [json.loads(t.model_dump_json()) for t in transformations]
    except Exception as e:
        return {"error": str(e)}

def get_default_prompts():
    try:
        default_prompts = DefaultPrompts()
        return json.loads(default_prompts.model_dump_json())
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else None

    if action == "all":
        result = get_all_transformations()
    elif action == "defaults":
        result = get_default_prompts()
    else:
        result = {"error": "Invalid action provided. Use 'all' or 'defaults'."}
    
    print(json.dumps(result))
    sys.stdout.flush()
