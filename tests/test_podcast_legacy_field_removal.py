"""
Tests for migration 22: legacy provider/model strings dropped from podcast
profiles (#1107).

The migration maps still-unresolved profiles to `model` records (best effort,
no auto-create) and then drops the 6 legacy fields. The startup data
migration (open_notebook/podcasts/migration.py) that used to retry this
mapping on every boot is gone - its job now lives in the migration.
"""

from pathlib import Path

import pytest

MIGRATIONS_DIR = Path("open_notebook/database/migrations")

EPISODE_LEGACY_FIELDS = (
    "outline_provider",
    "outline_model",
    "transcript_provider",
    "transcript_model",
)
SPEAKER_LEGACY_FIELDS = ("tts_provider", "tts_model")


class TestMigration22Registration:
    """Migration files exist and are registered in AsyncMigrationManager
    (migrations are hard-coded, not auto-discovered)."""

    def test_migration_files_exist(self):
        assert (MIGRATIONS_DIR / "22.surrealql").is_file()
        assert (MIGRATIONS_DIR / "22_down.surrealql").is_file()

    def test_manager_registers_migration_22(self):
        from open_notebook.database.async_migrate import AsyncMigrationManager

        manager = AsyncMigrationManager()
        assert len(manager.up_migrations) >= 22
        assert len(manager.up_migrations) == len(manager.down_migrations)
        assert "REMOVE FIELD IF EXISTS outline_provider" in manager.up_migrations[21].sql


class TestMigration22Content:
    def test_up_maps_before_dropping(self):
        """Best-effort mapping (provider + name + type against `model`) must
        appear for all three reference fields, guarded so already-migrated
        rows are untouched."""
        sql = (MIGRATIONS_DIR / "22.surrealql").read_text()

        assert 'type = "language"' in sql
        assert 'type = "text_to_speech"' in sql
        # Mapping only fills EMPTY references - never overwrites a resolved one.
        assert "WHERE outline_llm = NONE" in sql
        assert "WHERE transcript_llm = NONE" in sql
        assert "WHERE voice_model = NONE" in sql
        # Mapping matches on the legacy strings of the row being updated.
        assert "$parent.outline_provider" in sql
        assert "$parent.transcript_provider" in sql
        assert "$parent.tts_provider" in sql
        # Mapping must run BEFORE the values are cleared/dropped.
        assert sql.index("outline_llm = (SELECT") < sql.index(
            "UPDATE episode_profile UNSET"
        )

    def test_up_clears_values_then_drops_all_six_fields(self):
        sql = (MIGRATIONS_DIR / "22.surrealql").read_text()

        # Stored values are cleared while the fields are still defined...
        assert "UPDATE episode_profile UNSET outline_provider" in sql
        assert "UPDATE speaker_profile UNSET tts_provider" in sql
        # ...then every legacy definition is removed.
        for field in EPISODE_LEGACY_FIELDS:
            assert f"REMOVE FIELD IF EXISTS {field} ON TABLE episode_profile" in sql
        for field in SPEAKER_LEGACY_FIELDS:
            assert f"REMOVE FIELD IF EXISTS {field} ON TABLE speaker_profile" in sql
        # No auto-create: a migration must not touch credentials.
        assert "CREATE model" not in sql

    def test_down_redefines_fields_as_optional_strings(self):
        """Rollback is a documented best effort: the schema shape returns
        (option<string>, the state migration 14 left) but the data does not."""
        sql = (MIGRATIONS_DIR / "22_down.surrealql").read_text()

        for field in EPISODE_LEGACY_FIELDS:
            assert (
                f"DEFINE FIELD OVERWRITE {field} ON TABLE episode_profile"
                f" TYPE option<string>" in sql
            )
        for field in SPEAKER_LEGACY_FIELDS:
            assert (
                f"DEFINE FIELD OVERWRITE {field} ON TABLE speaker_profile"
                f" TYPE option<string>" in sql
            )


class TestLegacyFieldsGone:
    def test_pydantic_models_dropped_legacy_fields(self):
        from open_notebook.podcasts.models import EpisodeProfile, SpeakerProfile

        for field in EPISODE_LEGACY_FIELDS:
            assert field not in EpisodeProfile.model_fields
            assert field not in EpisodeProfile.nullable_fields
        for field in SPEAKER_LEGACY_FIELDS:
            assert field not in SpeakerProfile.model_fields
            assert field not in SpeakerProfile.nullable_fields

    def test_startup_data_migration_module_is_gone(self):
        with pytest.raises(ImportError):
            import open_notebook.podcasts.migration  # noqa: F401

    def test_api_lifespan_no_longer_calls_podcast_migration(self):
        source = Path("api/main.py").read_text()
        assert "migrate_podcast_profiles" not in source
