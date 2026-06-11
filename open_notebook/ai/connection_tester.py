"""
Connection testing for AI providers.

This module provides functionality to test if a provider's API key is valid
by making minimal API calls to each provider, and to test individual model
configurations end-to-end.
"""
import io
import os
import struct
from typing import Optional, Tuple

import httpx
from loguru import logger

# Test models for each provider - uses minimal/cheapest models for testing
# Format: (model_name, model_type)
TEST_MODELS = {
    "openai": ("gpt-3.5-turbo", "language"),
    "anthropic": ("claude-3-haiku-20240307", "language"),
    "google": ("gemini-2.0-flash", "language"),
    "groq": ("llama-3.1-8b-instant", "language"),
    "mistral": ("mistral-small-latest", "language"),
    "deepseek": ("deepseek-chat", "language"),
    "xai": ("grok-beta", "language"),
    "openrouter": ("openai/gpt-3.5-turbo", "language"),
    "voyage": ("voyage-3-lite", "embedding"),
    "elevenlabs": ("eleven_multilingual_v2", "text_to_speech"),
    "deepgram": ("aura-2-thalia-en", "text_to_speech"),
    "ollama": (None, "language"),  # Dynamic - will use first available model
    # Complex providers with additional configuration
    "vertex": ("gemini-2.0-flash", "language"),  # Uses Google Vertex AI
    "azure": ("gpt-35-turbo", "language"),  # Azure OpenAI deployment name
    "openai_compatible": (None, "language"),  # Dynamic - will use first available model
    "dashscope": ("qwen-plus", "language"),
    "minimax": ("MiniMax-M2.5", "language"),
}


async def _test_azure_connection(
    endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
    api_version: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Test Azure OpenAI connectivity by listing models.

    Azure requires deployment names which vary per user, so instead of
    invoking a model, we list available models to validate credentials.
    """
    test_endpoint = endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT")
    test_api_key = api_key or os.environ.get("AZURE_OPENAI_API_KEY")
    test_api_version = api_version or os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21")

    if not test_endpoint:
        return False, "No Azure endpoint configured"
    if not test_api_key:
        return False, "No Azure API key configured"

    # Strip trailing slash to avoid double-slash in URL
    test_endpoint = test_endpoint.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{test_endpoint}/openai/models?api-version={test_api_version}",
                headers={"api-key": test_api_key},
            )

            if response.status_code == 200:
                data = response.json()
                models = data.get("data", [])
                count = len(models)
                if count > 0:
                    names = [m.get("id", "unknown") for m in models[:3]]
                    name_list = ", ".join(names)
                    if count > 3:
                        name_list += f" (+{count - 3} more)"
                    return True, f"Connected. {count} models: {name_list}"
                else:
                    return True, "Connected successfully (no models found)"
            elif response.status_code == 401:
                return False, "Invalid API key"
            elif response.status_code == 403:
                return False, "API key lacks required permissions"
            else:
                return False, f"Azure returned status {response.status_code}"

    except httpx.ConnectError:
        return False, "Cannot connect to Azure endpoint. Check the URL."
    except httpx.TimeoutException:
        return False, "Connection timed out. Check the endpoint URL."
    except Exception as e:
        return False, f"Connection error: {str(e)[:100]}"


async def _test_ollama_connection(base_url: str) -> Tuple[bool, str]:
    """Test Ollama server connectivity."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try /api/tags endpoint (standard Ollama)
            response = await client.get(f"{base_url}/api/tags")

            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                model_count = len(models)

                if model_count > 0:
                    model_names = [m.get("name", "unknown") for m in models[:3]]
                    model_list = ", ".join(model_names)
                    if model_count > 3:
                        model_list += f" (+{model_count - 3} more)"
                    return True, f"Connected. {model_count} models available: {model_list}"
                else:
                    return True, "Connected successfully (no models listed)"
            elif response.status_code == 401:
                return False, "Invalid API key"
            elif response.status_code == 403:
                return False, "API key lacks required permissions"
            else:
                return False, f"Server returned status {response.status_code}"

    except httpx.ConnectError:
        return False, "Cannot connect to Ollama. Check if Ollama server is running."
    except httpx.TimeoutException:
        return False, "Connection timed out. Check if Ollama server is accessible."
    except Exception as e:
        return False, f"Connection error: {str(e)[:100]}"


async def _test_openai_compatible_connection(base_url: str, api_key: Optional[str] = None) -> Tuple[bool, str]:
    """Test OpenAI-compatible server connectivity."""
    try:
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try /models endpoint (standard OpenAI-compatible)
            response = await client.get(f"{base_url}/models", headers=headers)

            if response.status_code == 200:
                data = response.json()
                models = data.get("data", [])
                model_count = len(models)

                if model_count > 0:
                    model_names = [m.get("id", "unknown") for m in models[:3]]
                    model_list = ", ".join(model_names)
                    if model_count > 3:
                        model_list += f" (+{model_count - 3} more)"
                    return True, f"Connected. {model_count} models available: {model_list}"
                else:
                    return True, "Connected successfully (no models listed)"
            elif response.status_code == 401:
                return False, "Invalid API key"
            elif response.status_code == 403:
                return False, "API key lacks required permissions"
            else:
                return False, f"Server returned status {response.status_code}"

    except httpx.ConnectError:
        return False, "Cannot connect to server. Check the URL is correct."
    except httpx.TimeoutException:
        return False, "Connection timed out. Check if server is accessible."
    except Exception as e:
        return False, f"Connection error: {str(e)[:100]}"

# Default voices for TTS testing per provider
# ElevenLabs and Mistral excluded: voices looked up dynamically via available_voices
DEFAULT_TEST_VOICES = {
    "openai": "alloy",
    "azure": "alloy",
    "google": "Kore",
    "vertex": "Kore",
    "openai_compatible": "alloy",
    "deepgram": "aura-2-thalia-en",
    "xai": "eve",
}


def _generate_test_wav() -> io.BytesIO:
    """Generate a minimal 0.5s silence WAV file in memory (16kHz, 16-bit mono)."""
    sample_rate = 16000
    num_samples = sample_rate // 2  # 0.5 seconds
    bits_per_sample = 16
    num_channels = 1
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = num_samples * block_align

    buf = io.BytesIO()
    # RIFF header
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_size))
    buf.write(b"WAVE")
    # fmt chunk
    buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16))  # chunk size
    buf.write(struct.pack("<H", 1))  # PCM format
    buf.write(struct.pack("<H", num_channels))
    buf.write(struct.pack("<I", sample_rate))
    buf.write(struct.pack("<I", byte_rate))
    buf.write(struct.pack("<H", block_align))
    buf.write(struct.pack("<H", bits_per_sample))
    # data chunk
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    buf.write(b"\x00" * data_size)  # silence

    buf.seek(0)
    buf.name = "test.wav"
    return buf


# A short bundled clip of speech ("Hello there") used to validate STT models.
# Real speech (vs. silence) makes the test transcription non-empty, so a passing
# test visibly returns text instead of a blank result.
_TEST_SPEECH_PATH = os.path.join(os.path.dirname(__file__), "assets", "test_speech.mp3")


def _get_test_audio() -> io.BytesIO:
    """Return a short speech clip for STT testing, or silence as a fallback."""
    try:
        with open(_TEST_SPEECH_PATH, "rb") as f:
            buf = io.BytesIO(f.read())
        buf.name = "test_speech.mp3"
        buf.seek(0)
        return buf
    except OSError:
        # Fall back to a silent WAV if the bundled clip is missing
        return _generate_test_wav()


def _normalize_error_message(error_msg: str) -> Tuple[bool, str]:
    """Normalize common error patterns into user-friendly messages."""
    lower = error_msg.lower()

    if "401" in error_msg or "unauthorized" in lower:
        return False, "Invalid API key"
    elif "403" in error_msg or "forbidden" in lower:
        return False, "API key lacks required permissions"
    elif "rate" in lower and "limit" in lower:
        return True, "Rate limited - but connection works"
    elif "not found" in lower and "model" in lower:
        return False, "Model not found on this provider"
    elif "connection" in lower or "network" in lower:
        return False, "Connection error - check network/endpoint"
    elif "timeout" in lower:
        return False, "Connection timed out - check network/endpoint"

    return False, error_msg


async def test_individual_model(model) -> Tuple[bool, str]:
    """
    Test a specific model configuration end-to-end by making a real API call.

    Args:
        model: A Model instance (from open_notebook.ai.models)

    Returns:
        Tuple of (success: bool, message: str)
    """
    from open_notebook.ai.models import ModelManager

    try:
        manager = ModelManager()
        esp_model = await manager.get_model(model.id)

        if esp_model is None:
            return False, "Could not create model instance"

        if model.type == "language":
            response = await esp_model.achat_complete(
                messages=[{"role": "user", "content": "Hi!"}]
            )
            text = response.content[:100] if response.content else "(empty response)"
            return True, f"Response: {text}"

        elif model.type == "embedding":
            result = await esp_model.aembed(["This is a test."])
            if result and len(result) > 0:
                dims = len(result[0])
                return True, f"Embedding dimensions: {dims}"
            return True, "Embedding successful"

        elif model.type == "text_to_speech":
            # For ElevenLabs, look up first available voice (API uses voice_id, not name)
            voice = DEFAULT_TEST_VOICES.get(model.provider)
            if not voice and hasattr(esp_model, "available_voices"):
                try:
                    voices = esp_model.available_voices
                    if voices:
                        voice = next(iter(voices.keys()))
                except Exception:
                    pass
            if not voice:
                voice = "alloy"  # fallback

            result = await esp_model.agenerate_speech(
                text="Hello from SAI Notebook", voice=voice
            )
            if result and hasattr(result, "content"):
                size = len(result.content)
                return True, f"Audio generated: {size} bytes"
            return True, "Speech generation successful"

        elif model.type == "speech_to_text":
            audio_file = _get_test_audio()
            result = await esp_model.atranscribe(
                audio_file=audio_file, language="en"
            )
            text = str(result.text).strip() if hasattr(result, "text") else str(result).strip()
            if not text:
                return True, "Connection successful (test clip produced no transcription)"
            return True, f"Transcription: {text[:100]}"

        else:
            return False, f"Unsupported model type: {model.type}"

    except Exception as e:
        error_msg = str(e)
        success, normalized = _normalize_error_message(error_msg)
        if success:
            return True, normalized
        logger.debug(f"Test individual model error for {model.id}: {e}")
        return False, normalized
