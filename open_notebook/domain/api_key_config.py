"""
API Key Configuration domain model for storing provider credentials.

This singleton model stores API keys and configuration for all supported
AI providers. Keys are stored as SecretStr for in-memory protection (values
masked in logs/repr) and encrypted using Fernet before database storage.

Encryption is enabled when OPEN_NOTEBOOK_ENCRYPTION_KEY environment variable
is set. If not set, keys are stored as plain text with a warning logged.
"""

from typing import ClassVar, Optional

from pydantic import Field, SecretStr

from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.base import RecordModel
from open_notebook.utils.encryption import decrypt_value, encrypt_value


class APIKeyConfig(RecordModel):
    """
    Singleton configuration for API keys and provider credentials.

    Uses RecordModel pattern with a fixed record_id. All API key fields
    use Pydantic's SecretStr for basic protection (values are masked in
    logs and repr). URL and path fields are regular strings.

    Usage:
        config = await APIKeyConfig.get_instance()
        if config.openai_api_key:
            # Use the key (call .get_secret_value() to extract)
            key = config.openai_api_key.get_secret_value()
    """

    record_id: ClassVar[str] = "open_notebook:api_key_config"

    # ==========================================================================
    # Simple Providers (just API key)
    # ==========================================================================

    openai_api_key: Optional[SecretStr] = Field(
        default=None, description="OpenAI API Key"
    )
    anthropic_api_key: Optional[SecretStr] = Field(
        default=None, description="Anthropic API Key"
    )
    google_api_key: Optional[SecretStr] = Field(
        default=None, description="Google AI / Gemini API Key"
    )
    groq_api_key: Optional[SecretStr] = Field(
        default=None, description="Groq API Key"
    )
    mistral_api_key: Optional[SecretStr] = Field(
        default=None, description="Mistral API Key"
    )
    deepseek_api_key: Optional[SecretStr] = Field(
        default=None, description="DeepSeek API Key"
    )
    xai_api_key: Optional[SecretStr] = Field(
        default=None, description="xAI (Grok) API Key"
    )
    openrouter_api_key: Optional[SecretStr] = Field(
        default=None, description="OpenRouter API Key"
    )
    voyage_api_key: Optional[SecretStr] = Field(
        default=None, description="Voyage AI API Key"
    )
    elevenlabs_api_key: Optional[SecretStr] = Field(
        default=None, description="ElevenLabs API Key"
    )

    # ==========================================================================
    # URL-based Providers
    # ==========================================================================

    ollama_api_base: Optional[str] = Field(
        default=None, description="Ollama API Base URL (e.g., http://localhost:11434)"
    )

    # ==========================================================================
    # Google Vertex AI
    # ==========================================================================

    vertex_project: Optional[str] = Field(
        default=None, description="Google Cloud Project ID for Vertex AI"
    )
    vertex_location: Optional[str] = Field(
        default=None, description="Google Cloud Region for Vertex AI (e.g., us-central1)"
    )
    google_application_credentials: Optional[str] = Field(
        default=None,
        description="Path to Google Cloud service account JSON credentials file",
    )

    # ==========================================================================
    # Azure OpenAI
    # ==========================================================================

    azure_openai_api_key: Optional[SecretStr] = Field(
        default=None, description="Azure OpenAI API Key"
    )
    azure_openai_api_version: Optional[str] = Field(
        default=None,
        description="Azure OpenAI API Version (e.g., 2024-02-15-preview)",
    )
    azure_openai_endpoint: Optional[str] = Field(
        default=None,
        description="Azure OpenAI generic endpoint URL",
    )
    azure_openai_endpoint_llm: Optional[str] = Field(
        default=None,
        description="Azure OpenAI endpoint URL for LLM deployments",
    )
    azure_openai_endpoint_embedding: Optional[str] = Field(
        default=None,
        description="Azure OpenAI endpoint URL for embedding deployments",
    )
    azure_openai_endpoint_stt: Optional[str] = Field(
        default=None,
        description="Azure OpenAI endpoint URL for speech-to-text deployments",
    )
    azure_openai_endpoint_tts: Optional[str] = Field(
        default=None,
        description="Azure OpenAI endpoint URL for text-to-speech deployments",
    )

    # ==========================================================================
    # OpenAI-Compatible Providers (Generic)
    # ==========================================================================

    openai_compatible_api_key: Optional[SecretStr] = Field(
        default=None, description="Generic OpenAI-compatible provider API Key"
    )
    openai_compatible_base_url: Optional[str] = Field(
        default=None, description="Generic OpenAI-compatible provider base URL"
    )

    # ==========================================================================
    # OpenAI-Compatible Providers (Service-Specific: LLM)
    # ==========================================================================

    openai_compatible_api_key_llm: Optional[SecretStr] = Field(
        default=None, description="OpenAI-compatible API Key for LLM service"
    )
    openai_compatible_base_url_llm: Optional[str] = Field(
        default=None, description="OpenAI-compatible base URL for LLM service"
    )

    # ==========================================================================
    # OpenAI-Compatible Providers (Service-Specific: Embedding)
    # ==========================================================================

    openai_compatible_api_key_embedding: Optional[SecretStr] = Field(
        default=None, description="OpenAI-compatible API Key for embedding service"
    )
    openai_compatible_base_url_embedding: Optional[str] = Field(
        default=None, description="OpenAI-compatible base URL for embedding service"
    )

    # ==========================================================================
    # OpenAI-Compatible Providers (Service-Specific: STT)
    # ==========================================================================

    openai_compatible_api_key_stt: Optional[SecretStr] = Field(
        default=None,
        description="OpenAI-compatible API Key for speech-to-text service",
    )
    openai_compatible_base_url_stt: Optional[str] = Field(
        default=None,
        description="OpenAI-compatible base URL for speech-to-text service",
    )

    # ==========================================================================
    # OpenAI-Compatible Providers (Service-Specific: TTS)
    # ==========================================================================

    openai_compatible_api_key_tts: Optional[SecretStr] = Field(
        default=None,
        description="OpenAI-compatible API Key for text-to-speech service",
    )
    openai_compatible_base_url_tts: Optional[str] = Field(
        default=None,
        description="OpenAI-compatible base URL for text-to-speech service",
    )

    @classmethod
    async def get_instance(cls) -> "APIKeyConfig":
        """
        Always fetch fresh configuration from database.

        Overrides parent caching behavior to ensure we always get the latest
        configuration values, similar to DefaultModels pattern.

        Returns:
            APIKeyConfig: Fresh instance with current database values
        """
        result = await repo_query(
            "SELECT * FROM ONLY $record_id",
            {"record_id": ensure_record_id(cls.record_id)},
        )

        if result:
            if isinstance(result, list) and len(result) > 0:
                data = result[0]
            elif isinstance(result, dict):
                data = result
            else:
                data = {}
        else:
            data = {}

        # Convert string values back to SecretStr for API key fields
        secret_fields = {
            "openai_api_key",
            "anthropic_api_key",
            "google_api_key",
            "groq_api_key",
            "mistral_api_key",
            "deepseek_api_key",
            "xai_api_key",
            "openrouter_api_key",
            "voyage_api_key",
            "elevenlabs_api_key",
            "azure_openai_api_key",
            "openai_compatible_api_key",
            "openai_compatible_api_key_llm",
            "openai_compatible_api_key_embedding",
            "openai_compatible_api_key_stt",
            "openai_compatible_api_key_tts",
        }

        for field_name in secret_fields:
            if field_name in data and data[field_name] is not None:
                # If it's already a string (from DB), decrypt and wrap in SecretStr
                if isinstance(data[field_name], str):
                    decrypted = decrypt_value(data[field_name])
                    data[field_name] = SecretStr(decrypted)

        # Create new instance with fresh data (bypass singleton cache)
        instance = object.__new__(cls)
        object.__setattr__(instance, "__dict__", {})
        super(APIKeyConfig, instance).__init__(**data)
        return instance

    def _prepare_save_data(self) -> dict:
        """
        Prepare data for database storage.

        SecretStr values are extracted, encrypted, and stored as strings.
        Encryption is performed using Fernet symmetric encryption if
        OPEN_NOTEBOOK_ENCRYPTION_KEY is configured.
        """
        data = {}
        for field_name, field_info in self.model_fields.items():
            value = getattr(self, field_name, None)
            if value is not None:
                # Convert SecretStr to encrypted string for storage
                if isinstance(value, SecretStr):
                    data[field_name] = encrypt_value(value.get_secret_value())
                else:
                    data[field_name] = value
            # Skip None values (don't store them)
        return data

    async def save(self) -> "APIKeyConfig":
        """
        Save the configuration to the database.

        Uses _prepare_save_data() to properly handle SecretStr conversion.
        """
        from open_notebook.database.repository import repo_upsert

        data = self._prepare_save_data()
        await repo_upsert("open_notebook", self.record_id, data)
        return self
