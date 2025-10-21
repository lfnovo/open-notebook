"""
Unit tests for the open_notebook.domain module.

This test suite provides comprehensive coverage of domain models including:
- ObjectModel base class (CRUD, relationships, validation)
- RecordModel singleton pattern
- Model and ModelManager functionality
- Notebook, Source, Note domain logic
- Podcast domain validation
- Content settings and transformations
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from pydantic import ValidationError

from open_notebook.domain.base import ObjectModel, RecordModel
from open_notebook.domain.content_settings import ContentSettings
from open_notebook.domain.models import DefaultModels, Model, ModelManager
from open_notebook.domain.notebook import ChatSession, Note, Notebook, Source
from open_notebook.domain.podcast import EpisodeProfile, PodcastEpisode, SpeakerProfile
from open_notebook.domain.transformation import DefaultPrompts, Transformation
from open_notebook.exceptions import InvalidInputError, NotFoundError


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_repo_create():
    """Mock repo_create to return a standard response."""
    with patch("open_notebook.domain.base.repo_create") as mock:
        mock.return_value = [
            {
                "id": "test:123",
                "created": "2024-01-01 12:00:00",
                "updated": "2024-01-01 12:00:00",
            }
        ]
        yield mock


@pytest.fixture
def mock_repo_update():
    """Mock repo_update to return a standard response."""
    with patch("open_notebook.domain.base.repo_update") as mock:
        mock.return_value = [
            {
                "id": "test:123",
                "created": "2024-01-01 12:00:00",
                "updated": "2024-01-01 13:00:00",
            }
        ]
        yield mock


@pytest.fixture
def mock_repo_query():
    """Mock repo_query for various query operations."""
    with patch("open_notebook.domain.base.repo_query") as mock:
        mock.return_value = []
        yield mock


@pytest.fixture
def mock_repo_delete():
    """Mock repo_delete to return success."""
    with patch("open_notebook.domain.base.repo_delete") as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def mock_repo_relate():
    """Mock repo_relate to return a relationship."""
    with patch("open_notebook.domain.base.repo_relate") as mock:
        mock.return_value = {"id": "relates:123"}
        yield mock


@pytest.fixture
def mock_embedding_model():
    """Mock embedding model for vectorization tests."""
    mock_model = AsyncMock()
    mock_model.aembed = AsyncMock(return_value=[[0.1, 0.2, 0.3] * 100])
    return mock_model


@pytest.fixture
def sample_notebook():
    """Create a sample Notebook instance."""
    return Notebook(
        id="notebook:test123",
        name="Test Notebook",
        description="A test notebook",
        archived=False,
    )


@pytest.fixture
def sample_source():
    """Create a sample Source instance."""
    return Source(
        id="source:test456",
        title="Test Source",
        full_text="This is a test source with some content.",
        topics=["testing", "pytest"],
    )


@pytest.fixture
def sample_note():
    """Create a sample Note instance."""
    return Note(
        id="note:test789",
        title="Test Note",
        content="This is a test note content.",
        note_type="human",
    )


# ============================================================================
# TEST SUITE 1: ObjectModel Base Class
# ============================================================================


class TestObjectModelBase:
    """Test suite for ObjectModel base class functionality."""

    @pytest.mark.asyncio
    async def test_objectmodel_save_create_new(self, mock_repo_create):
        """Test creating a new object generates ID and timestamps."""

        class TestModel(ObjectModel):
            table_name = "test_table"
            name: str

        obj = TestModel(name="Test Object")
        assert obj.id is None
        assert obj.created is None

        await obj.save()

        # Verify repo_create was called
        mock_repo_create.assert_called_once()
        call_args = mock_repo_create.call_args
        assert call_args[0][0] == "test_table"
        assert "name" in call_args[0][1]
        assert "created" in call_args[0][1]
        assert "updated" in call_args[0][1]

        # Verify object was updated with response
        assert obj.id == "test:123"
        assert obj.created is not None

    @pytest.mark.asyncio
    async def test_objectmodel_save_update_existing(self, mock_repo_update):
        """Test updating existing object preserves creation time."""

        class TestModel(ObjectModel):
            table_name = "test_table"
            name: str

        original_created = datetime(2024, 1, 1, 10, 0, 0)
        obj = TestModel(
            id="test:123",
            name="Test Object",
            created=original_created,
        )

        await obj.save()

        # Verify repo_update was called (not repo_create)
        mock_repo_update.assert_called_once()
        call_args = mock_repo_update.call_args
        assert call_args[0][0] == "test_table"
        assert call_args[0][1] == "test:123"

        # Created timestamp should be preserved
        saved_data = call_args[0][2]
        assert "created" in saved_data

    @pytest.mark.asyncio
    async def test_objectmodel_get_by_id(self, mock_repo_query):
        """Test retrieval by ID with proper class resolution."""

        class TestModel(ObjectModel):
            table_name = "test"
            name: str

        mock_repo_query.return_value = [
            {
                "id": "test:123",
                "name": "Retrieved Object",
                "created": "2024-01-01T12:00:00",
                "updated": "2024-01-01T12:00:00",
            }
        ]

        obj = await TestModel.get("test:123")

        assert obj.id == "test:123"
        assert obj.name == "Retrieved Object"
        assert isinstance(obj, TestModel)

    @pytest.mark.asyncio
    async def test_objectmodel_delete_validation(self, mock_repo_delete):
        """Test delete requires valid ID and handles errors properly."""

        class TestModel(ObjectModel):
            table_name = "test"
            name: str

        # Test deletion without ID raises error
        obj = TestModel(name="Test")
        with pytest.raises(InvalidInputError, match="Cannot delete object without an ID"):
            await obj.delete()

        # Test successful deletion with ID
        obj.id = "test:123"
        result = await obj.delete()
        assert result is True
        mock_repo_delete.assert_called_once_with("test:123")

    @pytest.mark.asyncio
    async def test_objectmodel_relate_creates_relationship(self, mock_repo_relate):
        """Test relationship creation between objects."""

        class TestModel(ObjectModel):
            table_name = "test"
            name: str

        obj = TestModel(id="test:123", name="Test")
        result = await obj.relate("belongs_to", "notebook:456", data={"role": "member"})

        assert result is not None
        mock_repo_relate.assert_called_once_with(
            source="test:123",
            relationship="belongs_to",
            target="notebook:456",
            data={"role": "member"},
        )


# ============================================================================
# TEST SUITE 2: RecordModel Singleton Pattern
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

    @pytest.mark.asyncio
    async def test_recordmodel_async_load_from_db(self):
        """Test database loading on first access via get_instance."""

        class TestRecord(RecordModel):
            record_id = "test:db_load"
            value: int = 0

        TestRecord.clear_instance()

        with patch("open_notebook.domain.base.repo_query") as mock_query:
            mock_query.return_value = [{"value": 123}]

            instance = await TestRecord.get_instance()

            # Verify DB was queried
            mock_query.assert_called_once()
            assert instance.value == 123

        TestRecord.clear_instance()

    @pytest.mark.asyncio
    async def test_recordmodel_update_persists_changes(self):
        """Test update mechanism saves changes to database."""

        class TestRecord(RecordModel):
            record_id = "test:update"
            value: int = 0

        TestRecord.clear_instance()

        with patch("open_notebook.domain.base.repo_upsert") as mock_upsert, patch(
            "open_notebook.domain.base.repo_query"
        ) as mock_query:

            mock_query.return_value = [{"value": 456}]
            mock_upsert.return_value = None

            instance = TestRecord(value=42)
            instance.value = 100
            await instance.update()

            # Verify upsert was called with new value
            mock_upsert.assert_called_once()
            call_args = mock_upsert.call_args[0]
            assert call_args[2]["value"] == 100

        TestRecord.clear_instance()


# ============================================================================
# TEST SUITE 3: ModelManager & Model Domain
# ============================================================================


class TestModelManager:
    """Test suite for Model and ModelManager functionality."""

    def test_model_manager_singleton(self):
        """Test ModelManager implements singleton pattern correctly."""
        manager1 = ModelManager()
        manager2 = ModelManager()

        assert manager1 is manager2
        assert id(manager1) == id(manager2)

    @pytest.mark.asyncio
    async def test_model_manager_caching(self):
        """Test model instances are cached with same parameters."""
        manager = ModelManager()
        manager.clear_cache()

        mock_model_data = {
            "id": "model:test123",
            "name": "gpt-4",
            "provider": "openai",
            "type": "language",
        }

        # Create a proper mock that will pass the isinstance check
        from esperanto import LanguageModel

        mock_language_model = MagicMock(spec=LanguageModel)

        with patch("open_notebook.domain.models.Model.get") as mock_get, patch(
            "open_notebook.domain.models.AIFactory.create_language"
        ) as mock_factory:

            mock_get.return_value = Model(**mock_model_data)
            mock_factory.return_value = mock_language_model

            # First call should create model
            model1 = await manager.get_model("model:test123")
            assert mock_factory.call_count == 1

            # Second call with same params should use cache
            model2 = await manager.get_model("model:test123")
            assert mock_factory.call_count == 1  # Not called again
            assert model1 is model2

            # Different params should create new instance
            model3 = await manager.get_model("model:test123", temperature=0.5)
            assert mock_factory.call_count == 2  # Called again

    @pytest.mark.asyncio
    async def test_model_manager_get_defaults(self):
        """Test default model retrieval with fallbacks."""
        manager = ModelManager()

        with patch("open_notebook.domain.models.DefaultModels.get_instance") as mock_get_instance:
            mock_defaults = DefaultModels(
                default_chat_model="model:chat123",
                default_embedding_model="model:embed456",
            )
            mock_get_instance.return_value = mock_defaults

            defaults = await manager.get_defaults()

            assert defaults.default_chat_model == "model:chat123"
            assert defaults.default_embedding_model == "model:embed456"
            mock_get_instance.assert_called()


# ============================================================================
# TEST SUITE 4: Notebook Domain Logic
# ============================================================================


class TestNotebookDomain:
    """Test suite for Notebook domain model."""

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

    @pytest.mark.asyncio
    async def test_notebook_get_sources_relationship(self):
        """Test source retrieval via relationships."""
        notebook = Notebook(id="notebook:123", name="Test", description="Test")

        with patch("open_notebook.domain.notebook.repo_query") as mock_query:
            mock_query.return_value = [
                {
                    "source": {
                        "id": "source:456",
                        "title": "Test Source",
                        "topics": ["test"],
                    }
                }
            ]

            sources = await notebook.get_sources()

            assert len(sources) == 1
            assert sources[0].id == "source:456"
            assert sources[0].title == "Test Source"
            mock_query.assert_called_once()

    def test_notebook_archived_flag(self):
        """Test archived flag defaults to False."""
        notebook = Notebook(name="Test", description="Test")
        assert notebook.archived is False

        notebook_archived = Notebook(name="Test", description="Test", archived=True)
        assert notebook_archived.archived is True


# ============================================================================
# TEST SUITE 5: Source Domain & Vectorization
# ============================================================================


class TestSourceDomain:
    """Test suite for Source domain model and vectorization."""

    @pytest.mark.asyncio
    async def test_source_vectorize_splits_text(self, mock_embedding_model):
        """Test vectorization splits text into chunks and generates embeddings."""
        source = Source(
            id="source:123",
            title="Test",
            full_text="This is a long text. " * 100,  # Create text that will be chunked
        )

        with patch("open_notebook.domain.notebook.model_manager.get_embedding_model") as mock_get_model, patch(
            "open_notebook.domain.notebook.repo_query"
        ) as mock_query, patch("open_notebook.domain.notebook.split_text") as mock_split:

            mock_get_model.return_value = mock_embedding_model
            mock_query.return_value = []  # No existing embeddings
            mock_split.return_value = ["chunk1", "chunk2", "chunk3"]

            await source.vectorize()

            # Verify text was split
            mock_split.assert_called_once()

            # Verify embeddings were created for each chunk
            assert mock_embedding_model.aembed.call_count == 3

            # Verify database inserts happened
            assert mock_query.call_count >= 3  # Delete query + 3 inserts

    @pytest.mark.asyncio
    async def test_source_add_insight_validation(self):
        """Test insight creation with proper validation."""
        source = Source(id="source:123", title="Test")

        mock_embedding_model = AsyncMock()
        mock_embedding_model.aembed = AsyncMock(return_value=[[0.1, 0.2, 0.3] * 100])

        with patch("open_notebook.domain.notebook.model_manager.get_embedding_model") as mock_get_model:
            mock_get_model.return_value = mock_embedding_model

            # Test validation - empty insight_type
            with pytest.raises(InvalidInputError, match="Insight type and content must be provided"):
                await source.add_insight("", "Some content")

            # Test validation - empty content
            with pytest.raises(InvalidInputError, match="Insight type and content must be provided"):
                await source.add_insight("summary", "")

        # Test successful insight creation
        with patch("open_notebook.domain.notebook.model_manager.get_embedding_model") as mock_get_model, patch(
            "open_notebook.domain.notebook.repo_query"
        ) as mock_query:

            mock_get_model.return_value = mock_embedding_model
            mock_query.return_value = [{"id": "insight:456"}]

            result = await source.add_insight("summary", "Test insight content")

            mock_embedding_model.aembed.assert_called_once_with(["Test insight content"])
            mock_query.assert_called_once()

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


# ============================================================================
# TEST SUITE 6: Note Domain
# ============================================================================


class TestNoteDomain:
    """Test suite for Note domain model."""

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

    def test_note_embedding_enabled(self):
        """Test notes have embedding enabled by default."""
        note = Note(title="Test", content="Test content")

        assert note.needs_embedding() is True
        assert note.get_embedding_content() == "Test content"

        # Test with None content
        note2 = Note(title="Test", content=None)
        assert note2.get_embedding_content() is None


# ============================================================================
# TEST SUITE 7: Podcast Domain Validation
# ============================================================================


class TestPodcastDomain:
    """Test suite for Podcast domain models."""

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
                speakers=[{"name": "Speaker 1"}],  # Missing voice_id, backstory, personality
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
# ADDITIONAL DOMAIN TESTS
# ============================================================================


class TestChatSessionDomain:
    """Test suite for ChatSession domain model."""

    @pytest.mark.asyncio
    async def test_chat_session_relate_to_notebook(self, mock_repo_relate):
        """Test chat session can relate to notebook."""
        session = ChatSession(id="chat:123", title="Test Chat")

        with pytest.raises(InvalidInputError, match="Notebook ID must be provided"):
            await session.relate_to_notebook("")

        result = await session.relate_to_notebook("notebook:456")
        assert result is not None
        mock_repo_relate.assert_called_once()


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


class TestContentSettings:
    """Test suite for ContentSettings RecordModel."""

    def test_content_settings_defaults(self):
        """Test ContentSettings has proper defaults."""
        settings = ContentSettings()

        assert settings.record_id == "open_notebook:content_settings"
        assert settings.default_content_processing_engine_doc == "auto"
        assert settings.default_embedding_option == "ask"
        assert settings.auto_delete_files == "yes"
        assert len(settings.youtube_preferred_languages) > 0


class TestEpisodeProfile:
    """Test suite for EpisodeProfile validation."""

    def test_episode_profile_segment_validation(self):
        """Test segment count validation (3-20)."""
        # Test invalid - too few segments
        with pytest.raises(ValidationError, match="Number of segments must be between 3 and 20"):
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
        with pytest.raises(ValidationError, match="Number of segments must be between 3 and 20"):
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
