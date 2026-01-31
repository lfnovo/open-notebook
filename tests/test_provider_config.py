"""
Unit tests for the ProviderConfig domain model.

This test suite focuses on validation logic, business rules, and data structures
that can be tested without database mocking.
"""

from unittest.mock import AsyncMock, patch

import pytest
from pydantic import SecretStr

from open_notebook.domain.provider_config import ProviderConfig, ProviderCredential


# =============================================================================
# TEST SUITE 1: ProviderCredential
# =============================================================================


class TestProviderCredential:
    """Test suite for ProviderCredential data model."""

    def setup_method(self):
        """Clear ProviderConfig singleton before each test."""
        ProviderConfig._clear_for_test()

    def test_create_basic_credential(self):
        """Test creating a basic credential with required fields."""
        cred = ProviderCredential(
            id="openai:test1",
            name="Test Config",
            provider="openai",
            api_key=SecretStr("sk-test-key"),
        )

        assert cred.id == "openai:test1"
        assert cred.name == "Test Config"
        assert cred.provider == "openai"
        assert cred.is_default is False
        assert cred.api_key.get_secret_value() == "sk-test-key"
        assert cred.base_url is None
        assert cred.model is None

    def test_create_full_credential(self):
        """Test creating a credential with all fields."""
        cred = ProviderCredential(
            id="azure:prod",
            name="Production",
            provider="azure",
            is_default=True,
            api_key=SecretStr("azure-key"),
            base_url="https://openai.azure.com/",
            model="gpt-4",
            api_version="2024-02-15-preview",
            endpoint="https://openai.azure.com/",
            endpoint_llm="https://llm.openai.azure.com/",
            endpoint_embedding="https://embedding.openai.azure.com/",
            project="my-project",
            location="eastus",
        )

        assert cred.id == "azure:prod"
        assert cred.name == "Production"
        assert cred.provider == "azure"
        assert cred.is_default is True
        assert cred.api_key.get_secret_value() == "azure-key"
        assert cred.base_url == "https://openai.azure.com/"
        assert cred.model == "gpt-4"
        assert cred.api_version == "2024-02-15-preview"
        assert cred.endpoint == "https://openai.azure.com/"
        assert cred.endpoint_llm == "https://llm.openai.azure.com/"
        assert cred.endpoint_embedding == "https://embedding.openai.azure.com/"
        assert cred.project == "my-project"
        assert cred.location == "eastus"

    def test_credential_timestamps(self):
        """Test that timestamps are auto-generated."""
        cred = ProviderCredential(
            id="test:id",
            name="Test",
            provider="test",
        )

        assert cred.created is not None
        assert cred.updated is not None
        assert cred.created == cred.updated  # Initially same

    def test_credential_to_dict(self):
        """Test converting credential to dictionary."""
        cred = ProviderCredential(
            id="test:id",
            name="Test",
            provider="test",
            api_key=SecretStr("secret-key"),
            base_url="https://example.com/",
        )

        # Without encryption
        data = cred.to_dict(encrypted=False)
        assert data["id"] == "test:id"
        assert data["name"] == "Test"
        assert data["provider"] == "test"
        assert data["api_key"] == "secret-key"  # Plain text when encrypted=False
        assert data["base_url"] == "https://example.com/"

    def test_credential_from_dict(self):
        """Test creating credential from dictionary."""
        data = {
            "id": "test:id",
            "name": "From Dict",
            "provider": "test",
            "is_default": True,
            "api_key": SecretStr("dict-key"),
            "base_url": "https://from-dict.com/",
            "model": "gpt-3.5",
        }

        cred = ProviderCredential.from_dict(data)

        assert cred.id == "test:id"
        assert cred.name == "From Dict"
        assert cred.provider == "test"
        assert cred.is_default is True
        assert cred.api_key.get_secret_value() == "dict-key"
        assert cred.base_url == "https://from-dict.com/"
        assert cred.model == "gpt-3.5"


# =============================================================================
# TEST SUITE 2: ProviderConfig
# =============================================================================


class TestProviderConfig:
    """Test suite for ProviderConfig data model."""

    def setup_method(self):
        """Clear ProviderConfig singleton before each test."""
        ProviderConfig._clear_for_test()

    def test_create_empty_config(self):
        """Test creating an empty ProviderConfig."""
        config = ProviderConfig()

        assert config.credentials == {}
        assert config.record_id == "open_notebook:provider_configs"

    def test_get_default_config_empty(self):
        """Test getting default config when provider has no configs."""
        config = ProviderConfig()

        default = config.get_default_config("openai")
        assert default is None

    def test_get_default_config_first(self):
        """Test that first config becomes default when no explicit default."""
        cred1 = ProviderCredential(
            id="openai:1", name="First", provider="openai", is_default=False
        )
        cred2 = ProviderCredential(
            id="openai:2", name="Second", provider="openai", is_default=False
        )

        config = ProviderConfig()
        config.credentials = {"openai": [cred1, cred2]}

        # First one should be returned as default
        default = config.get_default_config("openai")
        assert default is not None
        assert default.id == "openai:1"

    def test_get_default_config_explicit(self):
        """Test getting default config when one is explicitly marked."""
        cred1 = ProviderCredential(
            id="openai:1", name="First", provider="openai", is_default=False
        )
        cred2 = ProviderCredential(
            id="openai:2", name="Second", provider="openai", is_default=True
        )

        config = ProviderConfig()
        config.credentials = {"openai": [cred1, cred2]}

        default = config.get_default_config("openai")
        assert default is not None
        assert default.id == "openai:2"

    def test_get_config_by_id(self):
        """Test getting a specific config by ID."""
        cred1 = ProviderCredential(id="openai:1", name="First", provider="openai")
        cred2 = ProviderCredential(id="openai:2", name="Second", provider="openai")

        config = ProviderConfig()
        config.credentials = {"openai": [cred1, cred2]}

        found = config.get_config("openai", "openai:2")
        assert found is not None
        assert found.name == "Second"

    def test_get_config_not_found(self):
        """Test getting a non-existent config."""
        config = ProviderConfig()
        config.credentials = {"openai": []}

        found = config.get_config("openai", "nonexistent")
        assert found is None

    def test_add_config_first(self):
        """Test adding first config for a provider."""
        config = ProviderConfig()
        cred = ProviderCredential(
            id="openai:new", name="New", provider="openai", is_default=False
        )

        config.add_config("openai", cred)

        assert len(config.credentials["openai"]) == 1
        assert config.credentials["openai"][0].is_default is True  # First becomes default

    def test_add_config_sets_default(self):
        """Test adding a config with is_default=True unsets others."""
        config = ProviderConfig()
        cred1 = ProviderCredential(
            id="openai:1", name="First", provider="openai", is_default=True
        )
        cred2 = ProviderCredential(
            id="openai:2", name="Second", provider="openai", is_default=False
        )

        config.credentials = {"openai": [cred1]}

        # Add second with is_default=True
        config.add_config("openai", cred2)

        assert len(config.credentials["openai"]) == 2
        assert config.credentials["openai"][0].is_default is False  # First unset
        assert config.credentials["openai"][1].is_default is True  # Second set

    def test_delete_config_success(self):
        """Test deleting a non-default config."""
        cred1 = ProviderCredential(id="openai:1", name="First", provider="openai")
        cred2 = ProviderCredential(id="openai:2", name="Second", provider="openai")

        config = ProviderConfig()
        config.credentials = {"openai": [cred1, cred2]}

        result = config.delete_config("openai", "openai:1")

        assert result is True
        assert len(config.credentials["openai"]) == 1
        assert config.credentials["openai"][0].id == "openai:2"

    def test_delete_default_config_fails(self):
        """Test that deleting default config fails when others exist."""
        cred1 = ProviderCredential(
            id="openai:1", name="First", provider="openai", is_default=True
        )
        cred2 = ProviderCredential(
            id="openai:2", name="Second", provider="openai", is_default=False
        )

        config = ProviderConfig()
        config.credentials = {"openai": [cred1, cred2]}

        result = config.delete_config("openai", "openai:1")

        assert result is False
        assert len(config.credentials["openai"]) == 2  # Still has both

    def test_delete_only_config_succeeds(self):
        """Test that deleting the only config succeeds."""
        cred = ProviderCredential(id="openai:1", name="Only", provider="openai")

        config = ProviderConfig()
        config.credentials = {"openai": [cred]}

        result = config.delete_config("openai", "openai:1")

        assert result is True
        assert len(config.credentials["openai"]) == 0

    def test_delete_nonexistent_fails(self):
        """Test that deleting non-existent config fails."""
        config = ProviderConfig()
        config.credentials = {"openai": []}

        result = config.delete_config("openai", "nonexistent")

        assert result is False

    def test_set_default_config(self):
        """Test setting a config as default."""
        cred1 = ProviderCredential(
            id="openai:1", name="First", provider="openai", is_default=True
        )
        cred2 = ProviderCredential(
            id="openai:2", name="Second", provider="openai", is_default=False
        )

        config = ProviderConfig()
        config.credentials = {"openai": [cred1, cred2]}

        result = config.set_default_config("openai", "openai:2")

        assert result is True
        assert config.credentials["openai"][0].is_default is False
        assert config.credentials["openai"][1].is_default is True

    def test_set_default_config_not_found(self):
        """Test setting non-existent config as default fails."""
        config = ProviderConfig()
        config.credentials = {"openai": []}

        result = config.set_default_config("openai", "nonexistent")

        assert result is False

    def test_multiple_providers(self):
        """Test config with multiple providers."""
        openai_cred = ProviderCredential(id="openai:1", name="OpenAI", provider="openai")
        anthropic_cred = ProviderCredential(
            id="anthropic:1", name="Anthropic", provider="anthropic"
        )

        config = ProviderConfig()
        config.credentials = {
            "openai": [openai_cred],
            "anthropic": [anthropic_cred],
        }

        assert len(config.credentials) == 2
        assert len(config.credentials["openai"]) == 1
        assert len(config.credentials["anthropic"]) == 1

        # Each provider has its own default
        assert config.get_default_config("openai").name == "OpenAI"
        assert config.get_default_config("anthropic").name == "Anthropic"


# =============================================================================
# TEST SUITE 3: ProviderCredential Serialization
# =============================================================================


class TestProviderCredentialSerialization:
    """Test suite for ProviderCredential serialization."""

    def setup_method(self):
        """Clear ProviderConfig singleton before each test."""
        ProviderConfig._clear_for_test()

    def test_to_dict_with_secret(self):
        """Test that SecretStr is properly handled in to_dict."""
        cred = ProviderCredential(
            id="test:id",
            name="Test",
            provider="test",
            api_key=SecretStr("secret-value"),
        )

        # encrypted=False should return plain text
        data = cred.to_dict(encrypted=False)
        assert data["api_key"] == "secret-value"

    def test_from_dict_with_secret(self):
        """Test that SecretStr is properly handled in from_dict."""
        data = {
            "id": "test:id",
            "name": "Test",
            "provider": "test",
            "api_key": SecretStr("plain-key"),
        }

        cred = ProviderCredential.from_dict(data)

        assert isinstance(cred.api_key, SecretStr)
        assert cred.api_key.get_secret_value() == "plain-key"


# =============================================================================
# TEST SUITE 4: Edge Cases
# =============================================================================


class TestProviderConfigEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    def setup_method(self):
        """Clear ProviderConfig singleton before each test."""
        ProviderConfig._clear_for_test()

    def test_empty_provider_name(self):
        """Test that empty provider name is stored correctly."""
        cred = ProviderCredential(
            id=":test", name="Test", provider="", api_key=SecretStr("key")
        )

        assert cred.provider == ""

    def test_special_characters_in_name(self):
        """Test that special characters in config name are handled."""
        cred = ProviderCredential(
            id="test:id",
            name="Config with spaces & symbols!",
            provider="test",
        )

        assert cred.name == "Config with spaces & symbols!"

    def test_multiple_configs_same_name(self):
        """Test that multiple configs can have the same name."""
        cred1 = ProviderCredential(id="test:1", name="Same Name", provider="test")
        cred2 = ProviderCredential(id="test:2", name="Same Name", provider="test")

        config = ProviderConfig()
        config.credentials = {"test": [cred1, cred2]}

        assert len(config.credentials["test"]) == 2
        # Both can have the same name
        assert config.credentials["test"][0].name == config.credentials["test"][1].name

    def test_credential_order_preserved(self):
        """Test that credential order is preserved when adding."""
        creds = [
            ProviderCredential(id=f"test:{i}", name=f"Config {i}", provider="test")
            for i in range(5)
        ]

        config = ProviderConfig()
        for cred in creds:
            config.add_config("test", cred)

        stored = config.credentials["test"]
        assert len(stored) == 5
        for i, cred in enumerate(stored):
            assert cred.id == f"test:{i}"

    def test_provider_name_case_handling(self):
        """Test that provider names are handled case-insensitively where appropriate."""
        cred = ProviderCredential(id="OPENAI:test", name="Test", provider="openai")

        # Provider name is stored as-is
        assert cred.provider == "openai"
