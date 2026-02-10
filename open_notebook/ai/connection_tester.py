"""
Connection testing for AI providers.

This module provides functionality to test if a provider's API key is valid
by making minimal API calls to each provider, and to test individual model
configurations end-to-end.
"""
import io
import os
import struct
from typing import List, Optional, Tuple

import httpx
from esperanto.factory import AIFactory
from loguru import logger

from open_notebook.domain.credential import Credential

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
    "ollama": (None, "language"),  # Dynamic - will use first available model
    # Complex providers with additional configuration
    "vertex": ("gemini-2.0-flash", "language"),  # Uses Google Vertex AI
    "azure": ("gpt-35-turbo", "language"),  # Azure OpenAI deployment name
    "openai_compatible": (None, "language"),  # Dynamic - will use first available model
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
    test_api_version = api_version or os.environ.get("AZURE_OPENAI_API_VERSION", "2024-06-01")

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

async def test_provider_connection(
    provider: str, model_type: str = "language", config_id: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Test if a provider's API key is valid by making a minimal API call.

    Args:
        provider: Provider name (openai, anthropic, etc.)
        model_type: Type of model to test (language, embedding, etc.)
                   Note: This is overridden by TEST_MODELS if provider is in that dict.
        config_id: Optional specific configuration ID to test (format: configId)
                   If provided, uses the configuration from ProviderConfig for this specific config.

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Get configuration - either specific config or default
        api_key: Optional[str] = None
        base_url: Optional[str] = None
        endpoint: Optional[str] = None
        api_version: Optional[str] = None
        model_name: Optional[str] = None

        if config_id:
            # Load specific credential from database
            try:
                cred = await Credential.get(config_id)
                config = cred.to_esperanto_config()
                api_key = config.get("api_key")
                base_url = config.get("base_url")
                endpoint = config.get("endpoint")
                api_version = config.get("api_version")
            except Exception:
                return False, f"Credential not found: {config_id}"

        # Normalize provider name (handle hyphenated aliases)
        normalized_provider = provider.replace("-", "_")

        # Special handling for URL-based providers (no API key, just connectivity)
        if normalized_provider == "ollama":
            # Use base_url from specific config, or environment variable
            test_base_url = base_url or os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")
            return await _test_ollama_connection(test_base_url)

        if normalized_provider == "openai_compatible":
            # Use base_url from specific config, or environment variable
            test_base_url = base_url or os.environ.get("OPENAI_COMPATIBLE_BASE_URL")
            test_api_key = api_key or os.environ.get("OPENAI_COMPATIBLE_API_KEY")
            if not test_base_url:
                return False, "No base URL configured for OpenAI-compatible provider"
            return await _test_openai_compatible_connection(test_base_url, test_api_key)

        if normalized_provider == "azure":
            return await _test_azure_connection(endpoint, api_key, api_version)

        # Get test model for provider
        if normalized_provider not in TEST_MODELS:
            return False, f"Unknown provider: {provider}"

        test_model, test_model_type = TEST_MODELS[normalized_provider]

        # Use model from config if provided, otherwise use TEST_MODELS default
        model_to_use = model_name if model_name else test_model

        # For providers with dynamic model detection
        if model_to_use is None:
            if normalized_provider == "openai_compatible":
                # OpenAI-compatible servers should already be tested via _test_openai_compatible_connection
                test_base_url = base_url or os.environ.get("OPENAI_COMPATIBLE_BASE_URL", "")
                test_api_key = api_key or os.environ.get("OPENAI_COMPATIBLE_API_KEY")
                return await _test_openai_compatible_connection(test_base_url, test_api_key)
            else:
                return False, f"No test model configured for {provider}"

        # If we have a specific API key, set it in environment for this test
        if api_key:
            os.environ[f"{provider.upper()}_API_KEY"] = api_key

        # Try to create the model and make a minimal call
        if test_model_type == "language":
            model = AIFactory.create_language(model_name=model_to_use, provider=provider)
            # Convert to LangChain and make a minimal call
            lc_model = model.to_langchain()
            await lc_model.ainvoke("Hi")
            return True, "Connection successful"

        elif test_model_type == "embedding":
            model = AIFactory.create_embedding(model_name=model_to_use, provider=provider)
            # Embed a single short test string
            await model.aembed(["test"])
            return True, "Connection successful"

        elif test_model_type == "text_to_speech":
            # For TTS, we just verify the model can be created
            # Making an actual TTS call would be more expensive
            # Most TTS providers validate the key on model creation
            AIFactory.create_text_to_speech(
                model_name=model_to_use, provider=provider
            )
            return True, "Connection successful (key format valid)"

        else:
            return False, f"Unsupported model type for testing: {test_model_type}"

    except Exception as e:
        error_msg = str(e)

        # Clean up common error messages for user-friendly display
        if "401" in error_msg or "unauthorized" in error_msg.lower():
            return False, "Invalid API key"
        elif "403" in error_msg or "forbidden" in error_msg.lower():
            return False, "API key lacks required permissions"
        elif "rate" in error_msg.lower() and "limit" in error_msg.lower():
            # Rate limit means the key is valid but we hit limits
            return True, "Rate limited - but connection works"
        elif "connection" in error_msg.lower() or "network" in error_msg.lower():
            return False, "Connection error - check network/endpoint"
        elif "timeout" in error_msg.lower():
            return False, "Connection timed out - check network/endpoint"
        elif "not found" in error_msg.lower() and "model" in error_msg.lower():
            # Model not found but auth worked - this is actually a success for connectivity
            return True, "API key valid (test model not available)"
        elif provider == "ollama" and "connection refused" in error_msg.lower():
            return False, "Ollama not running - check if Ollama server is started"
        else:
            logger.debug(f"Test connection error for {provider}: {e}")
            # Truncate long error messages
            truncated = error_msg[:100] + "..." if len(error_msg) > 100 else error_msg
            return False, f"Error: {truncated}"


# Default voices for TTS testing per provider
# ElevenLabs excluded: uses voice_id (not name), looked up dynamically
DEFAULT_TEST_VOICES = {
    "openai": "alloy",
    "azure": "alloy",
    "google": "Kore",
    "vertex": "Kore",
    "openai_compatible": "alloy",
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
                text="Hello from Open Notebook", voice=voice
            )
            if result and hasattr(result, "content"):
                size = len(result.content)
                return True, f"Audio generated: {size} bytes"
            return True, "Speech generation successful"

        elif model.type == "speech_to_text":
            audio_file = _generate_test_wav()
            result = await esp_model.atranscribe(
                audio_file=audio_file, language="en"
            )
            text = str(result.text) if hasattr(result, "text") else str(result)
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
