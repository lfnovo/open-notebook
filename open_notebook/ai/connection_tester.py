"""
Connection testing for AI providers.

This module provides functionality to test if a provider's API key is valid
by making minimal API calls to each provider, and to test individual model
configurations end-to-end.
"""
import io
import json
import os
import struct
from typing import Optional, Tuple

import httpx
from loguru import logger

from open_notebook.utils.url_validation import validate_url


def _is_vertex_credentials_file_error(exc: Exception) -> bool:
    """
    True if `exc` came from loading a Vertex service-account file
    (credentials_path - free text, no path validation; see
    open_notebook/ai/key_provider.py).

    Google's auth library raises distinguishable exceptions for "file
    missing" (FileNotFoundError, an OSError), "not valid JSON"
    (json.JSONDecodeError), and "valid JSON but wrong shape"
    (google.auth.exceptions.GoogleAuthError) - confirmed by direct
    reproduction. Echoing any of these back to an API caller turns
    credential/model testing into a filesystem oracle: an attacker who can
    create/test a Vertex credential could probe for the existence and
    contents-shape of arbitrary files on the server. Callers should catch
    these and return one generic message instead of the raw exception text.

    Network failures are excluded even though they'd otherwise match
    (ConnectionError/TimeoutError are OSError subclasses, TransportError a
    GoogleAuthError subclass): they say nothing about the credentials file,
    and classifying them here would tell a user with a blocked network to
    go debug their file path. Letting them fall through reveals only the
    error's category ("connection error"), which keeps the oracle closed.
    """
    from google.auth.exceptions import GoogleAuthError, TransportError

    if isinstance(exc, (ConnectionError, TimeoutError, TransportError)):
        return False
    return isinstance(exc, (OSError, json.JSONDecodeError, GoogleAuthError))


# Test models for each provider - uses minimal/cheapest models for testing
# Format: (model_name, model_type)
#
# Prefer a provider-maintained floating alias where one exists, so a model
# retirement doesn't silently break the connection test (see #970: Google
# hard-shuts-down Gemini model ids on a schedule). `gemini-flash-latest`
# is Google's alias for the current stable Flash model and moves forward on
# its own. The provider test also no longer treats a model-level failure as
# a connection failure (see `_connection_failure_reason`), so even if an
# alias ever breaks, the test still reports the credentials correctly.
TEST_MODELS = {
    "openai": ("gpt-3.5-turbo", "language"),
    "anthropic": ("claude-3-haiku-20240307", "language"),
    "google": ("gemini-flash-latest", "language"),
    "groq": ("llama-3.1-8b-instant", "language"),
    "mistral": ("mistral-small-latest", "language"),
    "deepseek": ("deepseek-chat", "language"),
    "xai": ("grok-beta", "language"),
    "openrouter": ("openai/gpt-3.5-turbo", "language"),
    "voyage": ("voyage-3-lite", "embedding"),
    "elevenlabs": ("eleven_multilingual_v2", "text_to_speech"),
    "deepgram": ("aura-2-thalia-en", "text_to_speech"),
    "ollama": (None, "language"),  # Dynamic - will use first available model
    "omlx": (None, "language"),  # Dynamic - OpenAI-compatible /models ping
    # Complex providers with additional configuration
    "vertex": ("gemini-flash-latest", "language"),  # Uses Google Vertex AI
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
        # Re-validate at request time: the endpoint may have been saved
        # against a hostname that only later resolved to an internal
        # address (DNS rebinding), so a save-time check alone isn't enough.
        await validate_url(test_endpoint, "azure")
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

    except ValueError as e:
        return False, str(e)
    except httpx.ConnectError:
        return False, "Cannot connect to Azure endpoint. Check the URL."
    except httpx.TimeoutException:
        return False, "Connection timed out. Check the endpoint URL."
    except Exception as e:
        return False, f"Connection error: {str(e)[:100]}"


async def _test_ollama_connection(base_url: str) -> Tuple[bool, str]:
    """Test Ollama server connectivity."""
    try:
        # Re-validate at request time (see _test_azure_connection for why).
        await validate_url(base_url, "ollama")
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

    except ValueError as e:
        return False, str(e)
    except httpx.ConnectError:
        return False, "Cannot connect to Ollama. Check if Ollama server is running."
    except httpx.TimeoutException:
        return False, "Connection timed out. Check if Ollama server is accessible."
    except Exception as e:
        return False, f"Connection error: {str(e)[:100]}"


async def _test_openai_compatible_connection(base_url: str, api_key: Optional[str] = None) -> Tuple[bool, str]:
    """Test OpenAI-compatible server connectivity."""
    try:
        # Re-validate at request time (see _test_azure_connection for why).
        await validate_url(base_url, "openai_compatible")
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        trimmed = base_url.rstrip("/")
        models_url = (
            trimmed if trimmed.endswith("/models") else f"{trimmed}/models"
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try /models endpoint (standard OpenAI-compatible)
            response = await client.get(models_url, headers=headers)

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

    except ValueError as e:
        return False, str(e)
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


def _connection_failure_reason(error_msg: str) -> Optional[str]:
    """Classify whether an error means the provider is genuinely unreachable
    or the credentials are rejected.

    Returns a user-facing failure message for the only errors that actually
    disprove a working provider connection — bad key (401), insufficient
    permissions (403), and network/timeout failures. Returns None for
    anything the provider itself returned *after* authenticating (a missing
    or retired model, an unsupported request, a rate limit): reaching the
    model layer at all proves the credentials and endpoint work, so those
    are not connection failures. This is what keeps a retired test model
    (see #970) from being misreported as a broken provider connection.
    """
    lower = error_msg.lower()

    if "401" in error_msg or "unauthorized" in lower:
        return "Invalid API key"
    if "403" in error_msg or "forbidden" in lower:
        return "API key lacks required permissions"
    if "timeout" in lower or "timed out" in lower:
        return "Connection timed out - check network/endpoint"
    if (
        "connection" in lower
        or "network" in lower
        or "getaddrinfo" in lower
        or "name resolution" in lower
        or "failed to establish" in lower
    ):
        return "Connection error - check network/endpoint"
    return None


def _is_rate_limit(error_msg: str) -> bool:
    """True if the error is a throttling/quota response. Being rate-limited
    proves the request authenticated, so callers treat this as connection-OK.
    Covers the common phrasings across providers (429, quota, resource
    exhausted) rather than just the literal words "rate limit"."""
    lower = error_msg.lower()
    return (
        ("rate" in lower and "limit" in lower)
        or "429" in error_msg
        or "quota" in lower
        or "resource has been exhausted" in lower
        or "resource exhausted" in lower
    )


def _normalize_error_message(error_msg: str) -> Tuple[bool, str]:
    """Normalize common error patterns into user-friendly messages.

    Used by the *individual model* test, where the user is validating one
    specific registered model — so a missing model IS a failure (unlike the
    provider-level test, which only cares that the credentials work).
    """
    reason = _connection_failure_reason(error_msg)
    if reason:
        return False, reason

    if _is_rate_limit(error_msg):
        return True, "Rate limited - but connection works"
    lower = error_msg.lower()
    if "not found" in lower and "model" in lower:
        return False, "Model not found on this provider"

    return False, error_msg


# Substrings that indicate the provider answered but the *test model* is
# missing/retired/unsupported - proof the credentials and endpoint work.
# Only consulted for fixed-endpoint API-key providers (URL-based providers
# are tested via their own handlers), so a "not found" here is about the
# model, never a user-supplied base URL.
_MODEL_UNAVAILABLE_MARKERS = (
    "not found",
    "not supported",
    "does not exist",
    "deprecated",
    "unavailable",
    "no longer available",
)


def classify_provider_test_error(error_msg: str) -> Tuple[bool, str]:
    """Classify a provider connection-test exception into (success, message).

    The provider test only asks "do these credentials reach a working
    provider?" - so the sole real failures are a rejected key (401),
    insufficient permissions (403), and an unreachable endpoint. Anything
    the provider returned after authenticating - a rate limit, or a
    missing/retired/unsupported test model - still proves the connection
    works, so it's reported as success. This is the durable half of the
    #970 fix: even if the hard-coded test model is retired, a valid key is
    never misreported as a broken connection.
    """
    reason = _connection_failure_reason(error_msg)
    if reason:
        return False, reason

    if _is_rate_limit(error_msg):
        return True, "Rate limited - but connection works"
    lower = error_msg.lower()
    if any(marker in lower for marker in _MODEL_UNAVAILABLE_MARKERS):
        return True, "API key valid (test model unavailable)"

    truncated = error_msg[:100] + "..." if len(error_msg) > 100 else error_msg
    return False, f"Error: {truncated}"


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
        if model.provider == "vertex" and _is_vertex_credentials_file_error(e):
            logger.debug(f"Vertex credentials file error for model {model.id}: {e}")
            return False, "Invalid or inaccessible credentials file"

        error_msg = str(e)
        success, normalized = _normalize_error_message(error_msg)
        if success:
            return True, normalized
        logger.debug(f"Test individual model error for {model.id}: {e}")
        return False, normalized
