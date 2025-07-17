import os
import json
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from open_notebook.plugins.podcasts import PodcastConfig, PodcastEpisode

load_dotenv()

# Set environment variables for SurrealDB connection
os.environ["SURREAL_ADDRESS"] = os.getenv("SURREAL_ADDRESS", "localhost")
os.environ["SURREAL_PORT"] = os.getenv("SURREAL_PORT", "8000")
os.environ["SURREAL_USER"] = os.getenv("SURREAL_USER", "root")
os.environ["SURREAL_PASS"] = os.getenv("SURREAL_PASS", "root")
os.environ["SURREAL_NAMESPACE"] = os.getenv("SURREAL_NAMESPACE", "open_notebook")
os.environ["SURREAL_DATABASE"] = os.getenv("SURREAL_DATABASE", "open_notebook")

def get_all_podcast_configs():
    try:
        configs = PodcastConfig.get_all(order_by="created desc")
        return [json.loads(c.model_dump_json()) for c in configs]
    except Exception as e:
        return {"error": str(e)}

def get_all_podcast_episodes():
    try:
        episodes = PodcastEpisode.get_all(order_by="created desc")
        return [json.loads(e.model_dump_json()) for e in episodes]
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else None

    if action == "configs":
        result = get_all_podcast_configs()
    elif action == "episodes":
        result = get_all_podcast_episodes()
    else:
        result = {"error": "Invalid action provided. Use 'configs' or 'episodes'."}
    
    print(json.dumps(result))
    sys.stdout.flush()
