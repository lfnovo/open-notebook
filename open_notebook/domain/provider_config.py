"""
Provider Configuration domain model for storing multiple credentials per provider.

This module provides the ProviderConfig singleton model that stores multiple
API key configurations per provider. Each ProviderCredential contains a complete
set of configuration options for a provider (api_key, base_url, model, etc.).

Encryption is enabled when OPEN_NOTEBOOK_ENCRYPTION_KEY environment variable
is set. If not set, keys are stored as plain text with a warning logged.
"""

from datetime import datetime
from typing import ClassVar, Dict, List, Optional

from pydantic import Field, SecretStr, field_validator

from open_notebook.database.repository import ensure_record_id, repo_query, repo_upsert
from open_notebook.domain.base import RecordModel
from open_notebook.utils.encryption import decrypt_value, encrypt_value


class ProviderCredential:
    """
    A single provider configuration item containing api_key and related settings.

    This class represents one complete configuration for an AI provider.
    Multiple configurations can exist for the same provider, allowing users
    to have different credentials for different environments (dev, prod, etc.).

    Attributes:
        id: Unique identifier for this configuration
        name: Human-readable name for this configuration
        provider: Provider name (e.g., "openai", "anthropic")
        is_default: Whether this is the default configuration for the provider
        api_key: The API key (stored as SecretStr for in-memory protection)
        base_url: Base URL for the provider API
        model: Default model to use for this provider
        api_version: API version string (for providers that need it)
        endpoint: Generic endpoint URL
        endpoint_llm: Endpoint URL for LLM service
        endpoint_embedding: Endpoint URL for embedding service
        endpoint_stt: Endpoint URL for speech-to-text service
        endpoint_tts: Endpoint URL for text-to-speech service
        project: Project ID (for Vertex AI)
        location: Location/region (for Vertex AI)
        credentials_path: Path to credentials file (for Vertex AI)
        created: Timestamp when this config was created
        updated: Timestamp when this config was last updated
    """

    def __init__(
        self,
        id: str,
        name: str,
        provider: str,
        is_default: bool = False,
        api_key: Optional[SecretStr] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_version: Optional[str] = None,
        endpoint: Optional[str] = None,
        endpoint_llm: Optional[str] = None,
        endpoint_embedding: Optional[str] = None,
        endpoint_stt: Optional[str] = None,
        endpoint_tts: Optional[str] = None,
        project: Optional[str] = None,
        location: Optional[str] = None,
        credentials_path: Optional[str] = None,
        created: Optional[str] = None,
        updated: Optional[str] = None,
    ):
        self.id = id
        self.name = name
        self.provider = provider
        self.is_default = is_default
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.api_version = api_version
        self.endpoint = endpoint
        self.endpoint_llm = endpoint_llm
        self.endpoint_embedding = endpoint_embedding
        self.endpoint_stt = endpoint_stt
        self.endpoint_tts = endpoint_tts
        self.project = project
        self.location = location
        self.credentials_path = credentials_path
        self.created = created or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.updated = updated or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self, encrypted: bool = False) -> dict:
        """
        Convert the credential to a dictionary for storage.

        Args:
            encrypted: If True, api_key is encrypted; otherwise it's a SecretStr

        Returns:
            Dictionary representation of the credential
        """
        data = {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "is_default": self.is_default,
            "base_url": self.base_url,
            "model": self.model,
            "api_version": self.api_version,
            "endpoint": self.endpoint,
            "endpoint_llm": self.endpoint_llm,
            "endpoint_embedding": self.endpoint_embedding,
            "endpoint_stt": self.endpoint_stt,
            "endpoint_tts": self.endpoint_tts,
            "project": self.project,
            "location": self.location,
            "credentials_path": self.credentials_path,
            "created": self.created,
            "updated": self.updated,
        }

        if self.api_key:
            if encrypted:
                data["api_key"] = encrypt_value(self.api_key.get_secret_value())
            else:
                data["api_key"] = self.api_key.get_secret_value()

        return data

    @classmethod
    def from_dict(cls, data: dict, decrypted: bool = False) -> "ProviderCredential":
        """
        Create a ProviderCredential from a dictionary.

        Args:
            data: Dictionary containing credential data
            decrypted: If True, api_key is already decrypted; otherwise wrap in SecretStr

        Returns:
            ProviderCredential instance
        """
        api_key = None
        if "api_key" in data and data["api_key"]:
            if isinstance(data["api_key"], SecretStr):
                # Already a SecretStr - use as-is
                api_key = data["api_key"]
            elif decrypted:
                # Decrypted string from DB - wrap in SecretStr
                api_key = SecretStr(data["api_key"])
            else:
                # Encrypted string from DB - wrap in SecretStr (will be decrypted later)
                api_key = SecretStr(data["api_key"])

        return cls(
            id=data["id"],
            name=data["name"],
            provider=data["provider"],
            is_default=data.get("is_default", False),
            api_key=api_key,
            base_url=data.get("base_url"),
            model=data.get("model"),
            api_version=data.get("api_version"),
            endpoint=data.get("endpoint"),
            endpoint_llm=data.get("endpoint_llm"),
            endpoint_embedding=data.get("endpoint_embedding"),
            endpoint_stt=data.get("endpoint_stt"),
            endpoint_tts=data.get("endpoint_tts"),
            project=data.get("project"),
            location=data.get("location"),
            credentials_path=data.get("credentials_path"),
            created=data.get("created"),
            updated=data.get("updated"),
        )


class ProviderConfig(RecordModel):
    """
    Singleton configuration for multiple provider credentials.

    Uses RecordModel pattern with a fixed record_id. Stores a dictionary
    of ProviderCredential objects organized by provider name.

    Usage:
        config = await ProviderConfig.get_instance()
        credentials = config.credentials.get("openai", [])
        default = config.get_default_config("openai")
    """

    record_id: ClassVar[str] = "open_notebook:provider_configs"

    # Store credentials organized by provider name
    # Structure: {"openai": [ProviderCredential, ...], "anthropic": [...], ...}
    credentials: Dict[str, List[ProviderCredential]] = Field(
        default_factory=dict,
        description="Provider credentials organized by provider name",
    )

    @classmethod
    async def get_instance(cls) -> "ProviderConfig":
        """
        Always fetch fresh configuration from database.

        Overrides parent caching behavior to ensure we always get the latest
        configuration values, similar to APIKeyConfig pattern.

        Returns:
            ProviderConfig: Fresh instance with current database values
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

        # Initialize credentials from database data
        credentials: Dict[str, List[ProviderCredential]] = {}
        creds_data = data.get("credentials")
        if creds_data and isinstance(creds_data, dict):
            for provider, provider_creds in creds_data.items():
                if isinstance(provider_creds, list):
                    credentials[provider] = []
                    for cred_data in provider_creds:
                        try:
                            # Decrypt api_key if it's a string
                            api_key_val = cred_data.get("api_key")
                            if api_key_val and isinstance(api_key_val, str):
                                decrypted = decrypt_value(api_key_val)
                                cred_data["api_key"] = SecretStr(decrypted)
                            else:
                                # Keep as SecretStr or None
                                if api_key_val:
                                    cred_data["api_key"] = SecretStr(api_key_val)
                                else:
                                    cred_data["api_key"] = None

                            credentials[provider].append(
                                ProviderCredential(
                                    id=cred_data.get("id", ""),
                                    name=cred_data.get("name", "Default"),
                                    provider=cred_data.get("provider", provider),
                                    is_default=cred_data.get("is_default", False),
                                    api_key=cred_data.get("api_key"),
                                    base_url=cred_data.get("base_url"),
                                    model=cred_data.get("model"),
                                    api_version=cred_data.get("api_version"),
                                    endpoint=cred_data.get("endpoint"),
                                    endpoint_llm=cred_data.get("endpoint_llm"),
                                    endpoint_embedding=cred_data.get(
                                        "endpoint_embedding"
                                    ),
                                    endpoint_stt=cred_data.get("endpoint_stt"),
                                    endpoint_tts=cred_data.get("endpoint_tts"),
                                    project=cred_data.get("project"),
                                    location=cred_data.get("location"),
                                    credentials_path=cred_data.get("credentials_path"),
                                    created=cred_data.get("created"),
                                    updated=cred_data.get("updated"),
                                )
                            )
                        except Exception:
                            # Skip invalid credentials
                            continue

        # Create instance using model_validate to properly initialize Pydantic model
        instance = cls.model_validate({"credentials": credentials})

        # Mark as loaded from database
        object.__setattr__(instance, "_db_loaded", True)

        return instance

    def get_default_config(self, provider: str) -> Optional[ProviderCredential]:
        """
        Get the default configuration for a provider.

        Args:
            provider: Provider name (e.g., "openai", "anthropic")

        Returns:
            The default ProviderCredential, or None if not found
        """
        provider_lower = provider.lower()
        credentials = self.credentials.get(provider_lower, [])

        # First, try to find explicitly marked default
        for cred in credentials:
            if cred.is_default:
                return cred

        # If no explicit default, return first config
        if credentials:
            return credentials[0]

        return None

    def get_config(
        self, provider: str, config_id: str
    ) -> Optional[ProviderCredential]:
        """
        Get a specific configuration by ID.

        Args:
            provider: Provider name
            config_id: Configuration ID

        Returns:
            The ProviderCredential if found, None otherwise
        """
        provider_lower = provider.lower()
        credentials = self.credentials.get(provider_lower, [])

        for cred in credentials:
            if cred.id == config_id:
                return cred

        return None

    def add_config(self, provider: str, credential: ProviderCredential) -> None:
        """
        Add a new configuration for a provider.

        If this is the first config for the provider, it becomes the default.
        When adding a new config to an existing provider, the new config becomes
        the default and previous default is unset.

        Args:
            provider: Provider name (normalized to lowercase)
            credential: ProviderCredential to add
        """
        provider_lower = provider.lower()
        credential.provider = provider_lower

        if provider_lower not in self.credentials:
            self.credentials[provider_lower] = []

        # When adding a new config to an existing provider, make it the default
        # and unset the previous default
        if self.credentials[provider_lower]:
            for cred in self.credentials[provider_lower]:
                cred.is_default = False
            credential.is_default = True

        # If this is the first config, make it default
        if not self.credentials[provider_lower]:
            credential.is_default = True

        self.credentials[provider_lower].append(credential)

    def delete_config(self, provider: str, config_id: str) -> bool:
        """
        Delete a configuration.

        Cannot delete the default configuration unless it's the only one.

        Args:
            provider: Provider name
            config_id: Configuration ID to delete

        Returns:
            True if deleted, False if not found
        """
        provider_lower = provider.lower()
        credentials = self.credentials.get(provider_lower, [])

        for i, cred in enumerate(credentials):
            if cred.id == config_id:
                # Cannot delete default if there are other configs
                if cred.is_default and len(credentials) > 1:
                    return False

                del credentials[i]
                return True

        return False

    def set_default_config(self, provider: str, config_id: str) -> bool:
        """
        Set a configuration as the default for a provider.

        Args:
            provider: Provider name
            config_id: Configuration ID to make default

        Returns:
            True if successful, False if config not found
        """
        provider_lower = provider.lower()
        credentials = self.credentials.get(provider_lower, [])

        for cred in credentials:
            if cred.id == config_id:
                # Unset all other defaults
                for other in credentials:
                    other.is_default = False

                # Set this one as default
                cred.is_default = True
                cred.updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return True

        return False

    def _prepare_save_data(self) -> dict:
        """
        Prepare data for database storage.

        SecretStr values are extracted, encrypted, and stored as strings.
        Encryption is performed using Fernet symmetric encryption if
        OPEN_NOTEBOOK_ENCRYPTION_KEY is configured.
        """
        data = {"credentials": {}}

        for provider, credentials in self.credentials.items():
            data["credentials"][provider] = []
            for cred in credentials:
                cred.updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                data["credentials"][provider].append(cred.to_dict(encrypted=True))

        return data

    async def save(self) -> "ProviderConfig":
        """
        Save the configuration to the database.

        Uses _prepare_save_data() to properly handle SecretStr conversion
        and encryption.
        """
        data = self._prepare_save_data()
        await repo_upsert("open_notebook", self.record_id, data)
        return self

    @classmethod
    def _clear_for_test(cls) -> None:
        """Clear the singleton instance for testing purposes."""
        if cls.record_id in cls._instances:
            del cls._instances[cls.record_id]
