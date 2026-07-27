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

from typing import Any, ClassVar, Dict, List, Optional

from loguru import logger
from pydantic import SecretStr, model_validator

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

    # Provider-specific tuning options that are exposed as top-level fields on
    # this model but persisted inside the flexible `config` object on the
    # `credential` table (migration 15). Adding a new such option only requires
    # declaring the Pydantic field below and listing it here — no DB migration.
    CONFIG_EXTRAS: ClassVar[set[str]] = {"num_ctx"}

    name: str
    provider: str
    modalities: List[str] = []
    api_key: Optional[SecretStr] = None
    decryption_error: Optional[str] = None
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
    # Flexible provider config bag, persisted as-is to the credential table's
    # `config` FLEXIBLE object (migration 15). This is the source of truth on
    # disk and holds both the keys this version maps (see CONFIG_EXTRAS) and any
    # keys written by a newer version, so a load/save round-trip never clobbers
    # options this version doesn't know about.
    config: Optional[Dict[str, Any]] = None

    # Ollama-only: overrides the context window (num_ctx). Esperanto defaults to
    # 8192; raise this if your hardware can handle a larger context window.
    # Exposed as a top-level field (and on the API) for convenience; it mirrors
    # config["num_ctx"].
    num_ctx: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def _mirror_config_to_fields(cls, data: Any) -> Any:
        """Mirror known keys from the persisted `config` bag onto their
        convenience fields on load. Done in `before` so the values flow through
        normal Pydantic field validation (e.g. `num_ctx` is coerced/validated as
        an int) instead of being set raw. Unknown keys stay in `config` untouched
        and are preserved on save."""
        if isinstance(data, dict) and isinstance(data.get("config"), dict):
            config = data["config"]
            data = dict(data)
            for key in cls.CONFIG_EXTRAS:
                if data.get(key) is None and config.get(key) is not None:
                    data[key] = config[key]
        return data

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
            # For Azure, base_url from the UI form maps to endpoint
            if self.provider and self.provider.lower() == "azure" and not self.endpoint:
                config["endpoint"] = self.base_url
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
        # Vertex esperanto providers accept `vertex_project`/`vertex_location`,
        # not the generic `project`/`location` keys (#1151). Emit the Vertex-
        # specific names so credential-linked (non-env) config actually
        # configures the provider instead of crashing on unexpected kwargs.
        is_vertex = bool(self.provider) and self.provider.lower() == "vertex"
        if self.project:
            config["vertex_project" if is_vertex else "project"] = self.project
        if self.location:
            config["vertex_location" if is_vertex else "location"] = self.location
        if self.credentials_path:
            config["credentials_path"] = self.credentials_path
        if self.num_ctx is not None:
            config["num_ctx"] = self.num_ctx
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
        """Override get_all() to handle api_key decryption with per-row error handling."""
        if order_by:
            validated_order_by = cls._validate_order_by(order_by)
            query = f"SELECT * FROM {cls.table_name} ORDER BY {validated_order_by}"
        else:
            query = f"SELECT * FROM {cls.table_name}"
        results = await repo_query(query, {})
        credentials = []
        for row in results:
            try:
                cred = cls._from_db_row(row)
                credentials.append(cred)
            except Exception as e:
                logger.warning(
                    f"Failed to decrypt credential {row.get('id', 'unknown')}: {e}"
                )
                # Create a minimal credential with error info from raw DB fields
                try:
                    error_cred = cls(
                        name=row.get("name", "Unknown"),
                        provider=row.get("provider", "unknown"),
                        modalities=row.get("modalities", []),
                        decryption_error="Failed to decrypt API key. The encryption key may have changed.",
                    )
                    # Preserve the DB id, created, updated from the raw row
                    if row.get("id"):
                        object.__setattr__(error_cred, "id", str(row["id"]))
                    if row.get("created"):
                        object.__setattr__(error_cred, "created", row["created"])
                    if row.get("updated"):
                        object.__setattr__(error_cred, "updated", row["updated"])
                    # Mark that it had an api_key (even though we can't decrypt it)
                    if row.get("api_key"):
                        object.__setattr__(
                            error_cred, "api_key", SecretStr("UNDECRYPTABLE")
                        )
                    credentials.append(error_cred)
                except Exception as inner_e:
                    logger.error(
                        f"Failed to create error credential for {row.get('id', 'unknown')}: {inner_e}"
                    )
        return credentials

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
        """Override to encrypt api_key and sync provider extras into `config`."""
        data: Dict[str, Any] = {}
        for key, value in self.model_dump().items():
            if key in ("decryption_error", "config"):
                # `config` is rebuilt below from the existing bag + convenience fields.
                continue
            if key == "api_key":
                # Handle SecretStr: extract, encrypt, store
                if self.api_key:
                    secret_value = self.api_key.get_secret_value()
                    data["api_key"] = encrypt_value(secret_value)
                else:
                    data["api_key"] = None
            elif value is not None or key in self.__class__.nullable_fields:
                data[key] = value

        # Sync the convenience fields (num_ctx, ...) into the flexible `config`
        # object so the SCHEMAFULL credential table doesn't drop them (migration
        # 15). Starting from the existing bag preserves any keys written by a
        # newer version, since repo_update MERGE replaces the whole object.
        # `config` is None only when the merged result is genuinely empty.
        config: Dict[str, Any] = dict(self.config or {})
        for key in self.__class__.CONFIG_EXTRAS:
            data.pop(key, None)  # not a top-level column; lives in `config`
            value = getattr(self, key, None)
            if value is not None:
                config[key] = value
            else:
                config.pop(key, None)
        data["config"] = config or None

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
