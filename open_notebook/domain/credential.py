"""
Credential domain model for storing individual provider credentials.

Each credential is a standalone record in the 'credential' table, replacing
the old ProviderConfig singleton. Credentials store API keys (encrypted at
rest) and provider-specific configuration fields.

Usage:
    cred = Credential(
        name="Production",
        provider="openai",
        modalities=["language", "embedding"],
        api_key=SecretStr("sk-..."),
    )
    await cred.save()
"""

from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional

from loguru import logger
from pydantic import SecretStr

from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.base import ObjectModel
from open_notebook.utils.encryption import decrypt_value, encrypt_value


class Credential(ObjectModel):
    """
    Individual credential record for an AI provider.

    Each record stores authentication and configuration for a single provider
    account. Models link to credentials via the credential field.
    """

    table_name: ClassVar[str] = "credential"
    nullable_fields: ClassVar[set[str]] = {
        "api_key",
        "base_url",
        "endpoint",
        "api_version",
        "endpoint_llm",
        "endpoint_embedding",
        "endpoint_stt",
        "endpoint_tts",
        "project",
        "location",
        "credentials_path",
    }

    name: str
    provider: str
    modalities: List[str] = []
    api_key: Optional[SecretStr] = None
    base_url: Optional[str] = None
    endpoint: Optional[str] = None
    api_version: Optional[str] = None
    endpoint_llm: Optional[str] = None
    endpoint_embedding: Optional[str] = None
    endpoint_stt: Optional[str] = None
    endpoint_tts: Optional[str] = None
    project: Optional[str] = None
    location: Optional[str] = None
    credentials_path: Optional[str] = None

    def to_esperanto_config(self) -> Dict[str, Any]:
        """
        Build config dict for AIFactory.create_*() calls.

        Returns a dict that can be passed as the 'config' parameter to
        Esperanto's AIFactory methods, overriding env var lookup.
        """
        config: Dict[str, Any] = {}
        if self.api_key:
            config["api_key"] = self.api_key.get_secret_value()
        if self.base_url:
            config["base_url"] = self.base_url
        if self.endpoint:
            config["endpoint"] = self.endpoint
        if self.api_version:
            config["api_version"] = self.api_version
        if self.endpoint_llm:
            config["endpoint_llm"] = self.endpoint_llm
        if self.endpoint_embedding:
            config["endpoint_embedding"] = self.endpoint_embedding
        if self.endpoint_stt:
            config["endpoint_stt"] = self.endpoint_stt
        if self.endpoint_tts:
            config["endpoint_tts"] = self.endpoint_tts
        if self.project:
            config["project"] = self.project
        if self.location:
            config["location"] = self.location
        if self.credentials_path:
            config["credentials_path"] = self.credentials_path
        return config

    @classmethod
    async def get_by_provider(cls, provider: str) -> List["Credential"]:
        """Get all credentials for a provider."""
        results = await repo_query(
            "SELECT * FROM credential WHERE string::lowercase(provider) = string::lowercase($provider) ORDER BY created ASC",
            {"provider": provider},
        )
        credentials = []
        for row in results:
            try:
                cred = cls._from_db_row(row)
                credentials.append(cred)
            except Exception as e:
                logger.warning(f"Skipping invalid credential: {e}")
        return credentials

    @classmethod
    async def get(cls, id: str) -> "Credential":
        """Override get() to handle api_key decryption."""
        instance = await super().get(id)
        # Pydantic auto-wraps the raw DB string in SecretStr, so we need
        # to extract, decrypt, and re-wrap regardless of type.
        if instance.api_key:
            raw = (
                instance.api_key.get_secret_value()
                if isinstance(instance.api_key, SecretStr)
                else instance.api_key
            )
            decrypted = decrypt_value(raw)
            object.__setattr__(instance, "api_key", SecretStr(decrypted))
        return instance

    @classmethod
    async def get_all(cls, order_by=None) -> List["Credential"]:
        """Override get_all() to handle api_key decryption."""
        instances = await super().get_all(order_by=order_by)
        for instance in instances:
            if instance.api_key:
                raw = (
                    instance.api_key.get_secret_value()
                    if isinstance(instance.api_key, SecretStr)
                    else instance.api_key
                )
                decrypted = decrypt_value(raw)
                object.__setattr__(instance, "api_key", SecretStr(decrypted))
        return instances

    async def get_linked_models(self) -> list:
        """Get all models linked to this credential."""
        if not self.id:
            return []
        from open_notebook.ai.models import Model

        results = await repo_query(
            "SELECT * FROM model WHERE credential = $cred_id",
            {"cred_id": ensure_record_id(self.id)},
        )
        return [Model(**row) for row in results]

    def _prepare_save_data(self) -> Dict[str, Any]:
        """Override to encrypt api_key before storage."""
        data = {}
        for key, value in self.model_dump().items():
            if key == "api_key":
                # Handle SecretStr: extract, encrypt, store
                if self.api_key:
                    secret_value = self.api_key.get_secret_value()
                    data["api_key"] = encrypt_value(secret_value)
                else:
                    data["api_key"] = None
            elif value is not None or key in self.__class__.nullable_fields:
                data[key] = value

        return data

    async def save(self) -> None:
        """Save credential, handling api_key re-hydration after DB round-trip."""
        # Remember the original SecretStr before save
        original_api_key = self.api_key

        await super().save()

        # After save, the api_key field may be set to the encrypted string
        # from the DB result. Restore the original SecretStr.
        if original_api_key:
            object.__setattr__(self, "api_key", original_api_key)
        elif self.api_key and isinstance(self.api_key, str):
            # Decrypt if DB returned an encrypted string
            decrypted = decrypt_value(self.api_key)
            object.__setattr__(self, "api_key", SecretStr(decrypted))

    @classmethod
    def _from_db_row(cls, row: dict) -> "Credential":
        """Create a Credential from a database row, decrypting api_key."""
        api_key_val = row.get("api_key")
        if api_key_val and isinstance(api_key_val, str):
            decrypted = decrypt_value(api_key_val)
            row["api_key"] = SecretStr(decrypted)
        elif api_key_val is None:
            row["api_key"] = None
        return cls(**row)
