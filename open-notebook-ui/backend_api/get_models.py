import os
import json
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from open_notebook.domain.models import Model, DefaultModels, ModelManager
from esperanto import AIFactory

load_dotenv()

# Set environment variables for SurrealDB connection
os.environ["SURREAL_ADDRESS"] = os.getenv("SURREAL_ADDRESS", "localhost")
os.environ["SURREAL_PORT"] = os.getenv("SURREAL_PORT", "8000")
os.environ["SURREAL_USER"] = os.getenv("SURREAL_USER", "root")
os.environ["SURREAL_PASS"] = os.getenv("SURREAL_PASS", "root")
os.environ["SURREAL_NAMESPACE"] = os.getenv("SURREAL_NAMESPACE", "open_notebook")
os.environ["SURREAL_DATABASE"] = os.getenv("SURREAL_DATABASE", "open_notebook")

def get_all_models():
    try:
        models = Model.get_all()
        return [json.loads(m.model_dump_json()) for m in models]
    except Exception as e:
        return {"error": str(e)}

def get_models_by_type(model_type):
    try:
        models = Model.get_models_by_type(model_type)
        return [json.loads(m.model_dump_json()) for m in models]
    except Exception as e:
        return {"error": str(e)}

def get_default_models():
    try:
        default_models = DefaultModels()
        return json.loads(default_models.model_dump_json())
    except Exception as e:
        return {"error": str(e)}

def get_available_providers():
    provider_status = {}
    provider_status["ollama"] = os.environ.get("OLLAMA_API_BASE") is not None
    provider_status["openai"] = os.environ.get("OPENAI_API_KEY") is not None
    provider_status["groq"] = os.environ.get("GROQ_API_KEY") is not None
    provider_status["xai"] = os.environ.get("XAI_API_KEY") is not None
    provider_status["vertexai"] = (
        os.environ.get("VERTEX_PROJECT") is not None
        and os.environ.get("VERTEX_LOCATION") is not None
        and os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") is not None
    )
    provider_status["gemini"] = os.environ.get("GOOGLE_API_KEY") is not None
    provider_status["openrouter"] = (
        os.environ.get("OPENROUTER_API_KEY") is not None
        and os.environ.get("OPENAI_API_KEY") is not None
        and os.environ.get("OPENROUTER_BASE_URL") is not None
    )
    provider_status["anthropic"] = os.environ.get("ANTHROPIC_API_KEY") is not None
    provider_status["elevenlabs"] = os.environ.get("ELEVENLABS_API_KEY") is not None
    provider_status["voyage"] = os.environ.get("VORAGE_API_KEY") is not None
    provider_status["azure"] = (
        os.environ.get("AZURE_OPENAI_API_KEY") is not None
        and os.environ.get("AZURE_OPENAI_ENDPOINT") is not None
        and os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME") is not None
        and os.environ.get("AZURE_OPENAI_API_VERSION") is not None
    )
    provider_status["mistral"] = os.environ.get("MISTRAL_API_KEY") is not None
    provider_status["deepseek"] = os.environ.get("DEEPSEEK_API_KEY") is not None

    available_providers = {
        "language": AIFactory.get_available_providers().get("language", []),
        "embedding": AIFactory.get_available_providers().get("embedding", []),
        "text_to_speech": AIFactory.get_available_providers().get("text_to_speech", []),
        "speech_to_text": AIFactory.get_available_providers().get("speech_to_text", []),
    }

    return {
        "provider_status": provider_status,
        "available_providers": available_providers
    }

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else None

    if action == "all":
        result = get_all_models()
    elif action == "by_type":
        model_type = sys.argv[2] if len(sys.argv) > 2 else None
        if not model_type:
            result = {"error": "Model type not provided for 'by_type' action."}
        else:
            result = get_models_by_type(model_type)
    elif action == "defaults":
        result = get_default_models()
    elif action == "providers":
        result = get_available_providers()
    else:
        result = {"error": "Invalid action provided. Use 'all', 'by_type <type>', 'defaults', or 'providers'."}
    
    print(json.dumps(result))
    sys.stdout.flush()
