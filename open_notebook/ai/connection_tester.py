"""
Connection testing for AI providers.

This module provides functionality to test if a provider's API key is valid
by making minimal API calls to each provider.
"""
import os
from typing import List, Optional, Tuple

import httpx
from esperanto import AIFactory
from loguru import logger

from open_notebook.ai.key_provider import provision_provider_keys


async def _get_azure_deployment() -> Optional[str]:
    """
    Attempt to get an Azure OpenAI deployment name.

    Azure requires a deployment name which varies by user configuration.
    This function tries to list available deployments via the API.

    Returns:
        Deployment name if found, None otherwise.
    """
    try:
        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2023-05-15")

        if not endpoint or not api_key:
            return None

        # Try to list deployments
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Azure OpenAI uses a different endpoint pattern for listing deployments
            response = await client.get(
                f"{endpoint}/openai/deployments?api-version={api_version}",
                headers={"Authorization": f"Bearer {api_key}"},
            )

            if response.status_code == 200:
                data = response.json()
                deployments = data.get("data", [])
                if deployments:
                    # Return the first deployment
                    return deployments[0].get("id")
    except Exception as e:
        logger.debug(f"Failed to get Azure deployments: {e}")

    return None


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
    provider: str, model_type: str = "language"
) -> Tuple[bool, str]:
    """
    Test if a provider's API key is valid by making a minimal API call.

    Args:
        provider: Provider name (openai, anthropic, etc.)
        model_type: Type of model to test (language, embedding, etc.)
                   Note: This is overridden by TEST_MODELS if provider is in that dict.

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Ensure keys are provisioned from DB (with env var fallback)
        await provision_provider_keys(provider)

        # Normalize provider name (handle hyphenated aliases)
        normalized_provider = provider.replace("-", "_")

        # Special handling for URL-based providers (no API key, just connectivity)
        if normalized_provider == "ollama":
            base_url = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")
            return await _test_ollama_connection(base_url)

        if normalized_provider == "openai_compatible":
            base_url = os.environ.get("OPENAI_COMPATIBLE_API_BASE")
            api_key = os.environ.get("OPENAI_COMPATIBLE_API_KEY")
            if not base_url:
                return False, "No base URL configured for OpenAI-compatible provider"
            return await _test_openai_compatible_connection(base_url, api_key)

        # Get test model for provider
        if normalized_provider not in TEST_MODELS:
            return False, f"Unknown provider: {provider}"

        model_name, test_model_type = TEST_MODELS[normalized_provider]

        # For providers with dynamic model detection (azure, openai_compatible)
        if model_name is None:
            if normalized_provider == "azure":
                # Try to list Azure deployments via the API
                deployment_name = await _get_azure_deployment()
                if not deployment_name:
                    return False, "Could not determine Azure deployment name. Please check your configuration."
                model_name = deployment_name
            elif normalized_provider == "openai_compatible":
                # OpenAI-compatible servers should already be tested via _test_openai_compatible_connection
                return await _test_openai_compatible_connection(
                    os.environ.get("OPENAI_COMPATIBLE_API_BASE", ""),
                    os.environ.get("OPENAI_COMPATIBLE_API_KEY")
                )
            else:
                return False, f"No test model configured for {provider}"

        # Try to create the model and make a minimal call
        if test_model_type == "language":
            model = AIFactory.create_language(model_name=model_name, provider=provider)
            # Convert to LangChain and make a minimal call
            lc_model = model.to_langchain()
            await lc_model.ainvoke("Hi")
            return True, "Connection successful"

        elif test_model_type == "embedding":
            model = AIFactory.create_embedding(model_name=model_name, provider=provider)
            # Embed a single short test string
            await model.aembed(["test"])
            return True, "Connection successful"

        elif test_model_type == "text_to_speech":
            # For TTS, we just verify the model can be created
            # Making an actual TTS call would be more expensive
            # This at least validates the API key format
            # For TTS, we just verify the model can be created
            # Making an actual TTS call would be more expensive
            # Most TTS providers validate the key on model creation
            # If we get here without exception, key is likely valid
            AIFactory.create_text_to_speech(
                model_name=model_name, provider=provider
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
