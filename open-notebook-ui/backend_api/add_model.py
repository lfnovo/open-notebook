import os
import json
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from open_notebook.domain.models import Model

load_dotenv()

# Set environment variables for SurrealDB connection
os.environ["SURREAL_ADDRESS"] = os.getenv("SURREAL_ADDRESS", "localhost")
os.environ["SURREAL_PORT"] = os.getenv("SURREAL_PORT", "8000")
os.environ["SURREAL_USER"] = os.getenv("SURREAL_USER", "root")
os.environ["SURREAL_PASS"] = os.getenv("SURREAL_PASS", "root")
os.environ["SURREAL_NAMESPACE"] = os.getenv("SURREAL_NAMESPACE", "open_notebook")
os.environ["SURREAL_DATABASE"] = os.getenv("SURREAL_DATABASE", "open_notebook")

def add_new_model(name, provider, model_type):
    try:
        model = Model(name=name, provider=provider, type=model_type)
        model.save()
        print(json.dumps(json.loads(model.model_dump_json())))
        sys.stdout.flush()
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.stdout.flush()
        sys.exit(1)

if __name__ == "__main__":
    input_data = sys.stdin.read()
    try:
        data = json.loads(input_data)
        model_name = data.get("name")
        model_provider = data.get("provider")
        model_type = data.get("type")

        if not model_name or not model_provider or not model_type:
            raise ValueError("Model name, provider, and type are required.")

        add_new_model(model_name, model_provider, model_type)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON input: {e}"}))
        sys.stdout.flush()
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.stdout.flush()
        sys.exit(1)
