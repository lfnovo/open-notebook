import os
import json
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from open_notebook.plugins.podcasts import PodcastConfig

load_dotenv()

# Set environment variables for SurrealDB connection
os.environ["SURREAL_ADDRESS"] = os.getenv("SURREAL_ADDRESS", "localhost")
os.environ["SURREAL_PORT"] = os.getenv("SURREAL_PORT", "8000")
os.environ["SURREAL_USER"] = os.getenv("SURREAL_USER", "root")
os.environ["SURREAL_PASS"] = os.getenv("SURREAL_PASS", "root")
os.environ["SURREAL_NAMESPACE"] = os.getenv("SURREAL_NAMESPACE", "open_notebook")
os.environ["SURREAL_DATABASE"] = os.getenv("SURREAL_DATABASE", "open_notebook")

def update_existing_podcast_config(config_id, config_data):
    try:
        podcast_config = PodcastConfig.get(config_id)
        if not podcast_config:
            raise ValueError(f"PodcastConfig with ID {config_id} not found.")

        # Update fields from config_data
        for key, value in config_data.items():
            if hasattr(podcast_config, key):
                # Special handling for list fields that might come as comma-separated strings
                if key in ["person1_role", "person2_role", "conversation_style", "engagement_technique", "dialogue_structure"]:
                    if isinstance(value, str):
                        setattr(podcast_config, key, [item.strip() for item in value.split(',') if item.strip()])
                    elif isinstance(value, list):
                        setattr(podcast_config, key, value)
                    else:
                        setattr(podcast_config, key, []) # Default to empty list if unexpected type
                else:
                    setattr(podcast_config, key, value)
        
        podcast_config.save()
        print(json.dumps(json.loads(podcast_config.model_dump_json())))
        sys.stdout.flush()
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.stdout.flush()
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        config_id = sys.argv[1]
        input_data = sys.stdin.read()
        try:
            config_data = json.loads(input_data)
            update_existing_podcast_config(config_id, config_data)
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"Invalid JSON input: {e}"}))
            sys.stdout.flush()
            sys.exit(1)
        except Exception as e:
            print(json.dumps({"error": str(e)}))
            sys.stdout.flush()
            sys.exit(1)
    else:
        print(json.dumps({"error": "PodcastConfig ID not provided."}))
        sys.stdout.flush()
        sys.exit(1)
