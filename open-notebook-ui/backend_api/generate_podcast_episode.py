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

def generate_podcast_episode(config_id, episode_name, text, instructions, longform, chunks, min_chunk_size):
    try:
        podcast_config = PodcastConfig.get(config_id)
        if not podcast_config:
            raise ValueError(f"PodcastConfig with ID {config_id} not found.")
        
        podcast_config.generate_episode(
            episode_name=episode_name,
            text=text,
            instructions=instructions,
            longform=longform,
            chunks=chunks,
            min_chunk_size=min_chunk_size
        )
        print(json.dumps({"success": True, "message": "Episode generated successfully!"}))
        sys.stdout.flush()
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.stdout.flush()
        sys.exit(1)

if __name__ == "__main__":
    input_data = sys.stdin.read()
    try:
        data = json.loads(input_data)
        config_id = data.get("config_id")
        episode_name = data.get("episode_name")
        text = data.get("text")
        instructions = data.get("instructions", "")
        longform = data.get("longform", False)
        chunks = data.get("chunks")
        min_chunk_size = data.get("min_chunk_size")

        if not config_id or not episode_name or not text:
            raise ValueError("Config ID, episode name, and text are required.")

        generate_podcast_episode(config_id, episode_name, text, instructions, longform, chunks, min_chunk_size)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON input: {e}"}))
        sys.stdout.flush()
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.stdout.flush()
        sys.exit(1)
