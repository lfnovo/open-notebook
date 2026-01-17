"""
Unit tests for the open_notebook.domain module.

This test suite focuses on validation logic, business rules, and data structures
that can be tested without database mocking.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from open_notebook.ai.models import ModelManager
from open_notebook.domain.base import RecordModel
from open_notebook.domain.content_settings import ContentSettings
from open_notebook.domain.notebook import Asset, Note, Notebook, Source
from open_notebook.domain.transformation import Transformation
from open_notebook.exceptions import InvalidInputError
from open_notebook.podcasts.models import EpisodeProfile, SpeakerProfile

# ============================================================================
# TEST SUITE 1: RecordModel Singleton Pattern
# ============================================================================


class TestRecordModelSingleton:
    """Test suite for RecordModel singleton behavior."""

    def test_recordmodel_singleton_behavior(self):
        """Test that same instance is returned for same record_id."""

        class TestRecord(RecordModel):
            record_id = "test:singleton"
            value: int = 0

        # Clear any existing instance
        TestRecord.clear_instance()

        # Create first instance
        instance1 = TestRecord(value=42)
        assert instance1.value == 42

        # Create second instance - should return same object
        instance2 = TestRecord(value=99)
        assert instance1 is instance2
        assert instance2.value == 99  # Value was updated

        # Cleanup
        TestRecord.clear_instance()


# ============================================================================
# TEST SUITE 2: ModelManager Instance Isolation
# ============================================================================


class TestModelManager:
    """Test suite for ModelManager instance behavior."""

    def test_model_manager_instance_isolation(self):
        """Test that each ModelManager instance is independent (not a singleton)."""
        manager1 = ModelManager()
        manager2 = ModelManager()

        # Each instance should be independent (not a singleton)
        assert manager1 is not manager2
        assert id(manager1) != id(manager2)


# ============================================================================
# TEST SUITE 3: Notebook Domain Logic
# ============================================================================


class TestNotebookDomain:
    """Test suite for Notebook validation and business rules."""

    def test_notebook_name_validation(self):
        """Test empty/whitespace names are rejected."""
        # Empty name should raise error
        with pytest.raises(InvalidInputError, match="Notebook name cannot be empty"):
            Notebook(name="", description="Test")

        # Whitespace-only name should raise error
        with pytest.raises(InvalidInputError, match="Notebook name cannot be empty"):
            Notebook(name="   ", description="Test")

        # Valid name should work
        notebook = Notebook(name="Valid Name", description="Test")
        assert notebook.name == "Valid Name"

    def test_notebook_archived_flag(self):
        """Test archived flag defaults to False."""
        notebook = Notebook(name="Test", description="Test")
        assert notebook.archived is False

        notebook_archived = Notebook(name="Test", description="Test", archived=True)
        assert notebook_archived.archived is True


# ============================================================================
# TEST SUITE 4: Source Domain
# ============================================================================


class TestSourceDomain:
    """Test suite for Source domain model."""

    def test_source_command_field_parsing(self):
        """Test RecordID parsing for command field."""
        # Test with string command
        source = Source(title="Test", command="command:123")
        assert source.command is not None

        # Test with None command
        source2 = Source(title="Test", command=None)
        assert source2.command is None

        # Test command is included in save data prep
        source3 = Source(id="source:123", title="Test", command="command:456")
        save_data = source3._prepare_save_data()
        assert "command" in save_data

    @pytest.mark.asyncio
    async def test_source_delete_cleans_up_file(self):
        """Test that deleting a source removes the associated file."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp_file:
            tmp_file.write(b"Test content")
            tmp_path = Path(tmp_file.name)

        try:
            # Create source with file asset
            source = Source(
                id="source:test_delete",
                title="Test Source",
                asset=Asset(file_path=str(tmp_path)),
            )

            # Verify file exists
            assert tmp_path.exists()

            # Mock the parent delete method to avoid database operations
            with patch.object(
                Source.__bases__[0], "delete", new_callable=AsyncMock
            ) as mock_delete:
                mock_delete.return_value = True

                # Delete the source
                result = await source.delete()

                # Verify parent delete was called
                mock_delete.assert_called_once()
                assert result is True

            # Verify file was deleted
            assert not tmp_path.exists()

        finally:
            # Cleanup in case test fails
            if tmp_path.exists():
                tmp_path.unlink()

    @pytest.mark.asyncio
    async def test_source_delete_without_file(self):
        """Test that deleting a source without a file doesn't fail."""
        # Create source without file asset
        source = Source(id="source:test_no_file", title="Test Source", asset=None)

        # Mock the parent delete method
        with patch.object(
            Source.__bases__[0], "delete", new_callable=AsyncMock
        ) as mock_delete:
            mock_delete.return_value = True

            # Delete should complete without error
            result = await source.delete()
            assert result is True
            mock_delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_source_delete_continues_on_file_error(self):
        """Test that source deletion continues even if file deletion fails."""
        # Create source with non-existent file
        source = Source(
            id="source:test_missing_file",
            title="Test Source",
            asset=Asset(file_path="/nonexistent/path/file.txt"),
        )

        # Mock the parent delete method
        with patch.object(
            Source.__bases__[0], "delete", new_callable=AsyncMock
        ) as mock_delete:
            mock_delete.return_value = True

            # Delete should complete even though file doesn't exist
            result = await source.delete()
            assert result is True
            mock_delete.assert_called_once()


# ============================================================================
# TEST SUITE 5: Note Domain
# ============================================================================


class TestNoteDomain:
    """Test suite for Note validation."""

    def test_note_content_validation(self):
        """Test empty content is rejected."""
        # None content is allowed
        note = Note(title="Test", content=None)
        assert note.content is None

        # Non-empty content is valid
        note2 = Note(title="Test", content="Valid content")
        assert note2.content == "Valid content"

        # Empty string should raise error
        with pytest.raises(InvalidInputError, match="Note content cannot be empty"):
            Note(title="Test", content="")

        # Whitespace-only should raise error
        with pytest.raises(InvalidInputError, match="Note content cannot be empty"):
            Note(title="Test", content="   ")

    def test_note_content_for_embedding(self):
        """Test notes can hold content for embedding.

        Note: Embedding is now handled via command submission in Note.save(),
        not via needs_embedding() method. This test verifies basic content handling.
        """
        note = Note(title="Test", content="Test content")
        assert note.content == "Test content"

        # Test with None content - valid, no embedding will be submitted
        note2 = Note(title="Test", content=None)
        assert note2.content is None


# ============================================================================
# TEST SUITE 6: Podcast Domain Validation
# ============================================================================


class TestPodcastDomain:
    """Test suite for Podcast domain validation."""

    def test_speaker_profile_validation(self):
        """Test speaker profile validates count and required fields."""
        # Test invalid - no speakers
        with pytest.raises(ValidationError):
            SpeakerProfile(
                name="Test",
                tts_provider="openai",
                tts_model="tts-1",
                speakers=[],
            )

        # Test invalid - too many speakers (> 4)
        with pytest.raises(ValidationError):
            SpeakerProfile(
                name="Test",
                tts_provider="openai",
                tts_model="tts-1",
                speakers=[{"name": f"Speaker{i}"} for i in range(5)],
            )

        # Test invalid - missing required fields
        with pytest.raises(ValidationError):
            SpeakerProfile(
                name="Test",
                tts_provider="openai",
                tts_model="tts-1",
                speakers=[
                    {"name": "Speaker 1"}
                ],  # Missing voice_id, backstory, personality
            )

        # Test valid - single speaker with all fields
        profile = SpeakerProfile(
            name="Test",
            tts_provider="openai",
            tts_model="tts-1",
            speakers=[
                {
                    "name": "Host",
                    "voice_id": "voice123",
                    "backstory": "A friendly host",
                    "personality": "Enthusiastic and welcoming",
                }
            ],
        )
        assert len(profile.speakers) == 1
        assert profile.speakers[0]["name"] == "Host"


# ============================================================================
# TEST SUITE 7: Transformation Domain
# ============================================================================


class TestTransformationDomain:
    """Test suite for Transformation domain model."""

    def test_transformation_creation(self):
        """Test transformation model creation."""
        transform = Transformation(
            name="summarize",
            title="Summarize Content",
            description="Creates a summary",
            prompt="Summarize the following text: {content}",
            apply_default=True,
        )

        assert transform.name == "summarize"
        assert transform.apply_default is True


# ============================================================================
# TEST SUITE 8: Content Settings
# ============================================================================


class TestContentSettings:
    """Test suite for ContentSettings defaults."""

    def test_content_settings_defaults(self):
        """Test ContentSettings has proper defaults."""
        settings = ContentSettings()

        assert settings.record_id == "open_notebook:content_settings"
        assert settings.default_content_processing_engine_doc == "auto"
        assert settings.default_embedding_option == "ask"
        assert settings.auto_delete_files == "yes"
        assert len(settings.youtube_preferred_languages) > 0


# ============================================================================
# TEST SUITE 9: Episode Profile Validation
# ============================================================================


class TestEpisodeProfile:
    """Test suite for EpisodeProfile validation."""

    def test_episode_profile_segment_validation(self):
        """Test segment count validation (3-20)."""
        # Test invalid - too few segments
        with pytest.raises(
            ValidationError, match="Number of segments must be between 3 and 20"
        ):
            EpisodeProfile(
                name="Test",
                speaker_config="default",
                outline_provider="openai",
                outline_model="gpt-4",
                transcript_provider="openai",
                transcript_model="gpt-4",
                default_briefing="Test briefing",
                num_segments=2,
            )

        # Test invalid - too many segments
        with pytest.raises(
            ValidationError, match="Number of segments must be between 3 and 20"
        ):
            EpisodeProfile(
                name="Test",
                speaker_config="default",
                outline_provider="openai",
                outline_model="gpt-4",
                transcript_provider="openai",
                transcript_model="gpt-4",
                default_briefing="Test briefing",
                num_segments=21,
            )

        # Test valid segment count
        profile = EpisodeProfile(
            name="Test",
            speaker_config="default",
            outline_provider="openai",
            outline_model="gpt-4",
            transcript_provider="openai",
            transcript_model="gpt-4",
            default_briefing="Test briefing",
            num_segments=5,
        )
        assert profile.num_segments == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
