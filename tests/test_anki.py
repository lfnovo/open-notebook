"""
Unit tests for Anki domain models and services.

This test suite covers:
- AnkiCard validation and business logic
- AnkiDeck card management
- AnkiExportSession naming and lifecycle
- CEFR classification logic
- Image caching and LRU eviction
- Dutch word frequency lookups
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from open_notebook.domain.anki import (
    AnkiCard,
    AnkiDeck,
    AnkiExportSession,
    AnkiCardEdit,
    DutchWordFrequency,
    ImageCache,
    ImageMetadata,
    AudioMetadata,
    SourceCitation,
    CEFRVote,
)
from open_notebook.exceptions import InvalidInputError


# ============================================================================
# TEST SUITE 1: AnkiCard Validation
# ============================================================================


class TestAnkiCardValidation:
    """Test suite for AnkiCard field validation."""

    def test_card_creation_with_valid_data(self):
        """Test creating a card with valid front and back."""
        card = AnkiCard(
            front="Hoe zeg je 'hello' in het Nederlands?",
            back="hallo"
        )
        assert card.front == "Hoe zeg je 'hello' in het Nederlands?"
        assert card.back == "hallo"
        assert card.notes is None
        assert card.tags == []

    def test_card_creation_with_all_fields(self):
        """Test creating a card with all optional fields."""
        citation = SourceCitation(
            source_id="source:123",
            page=42,
            context="Example context"
        )
        
        image_meta = ImageMetadata(
            url="https://example.com/image.jpg",
            source="unsplash",
            attribution_text="Photo by John Doe"
        )
        
        audio_meta = AudioMetadata(
            reference_mp3="/path/to/audio.mp3",
            audio_expires_at=datetime.utcnow() + timedelta(days=30)
        )
        
        votes = [
            CEFRVote(model_id="model1", level="B1", confidence=0.85),
            CEFRVote(model_id="model2", level="B1", confidence=0.90),
        ]
        
        card = AnkiCard(
            front="werken",
            back="to work",
            notes="Common verb for work-related activities",
            deck_id="deck:1",
            export_session_id="session:1",
            source_citation=citation,
            cefr_level="B1",
            cefr_confidence=0.875,
            cefr_votes=votes,
            image_metadata=image_meta,
            audio_metadata=audio_meta,
            tags=["verb", "work", "B1"],
        )
        
        assert card.front == "werken"
        assert card.cefr_level == "B1"
        assert len(card.cefr_votes) == 2
        assert card.source_citation.page == 42
        assert card.image_metadata.source == "unsplash"

    def test_empty_front_raises_error(self):
        """Test that empty front field raises validation error."""
        with pytest.raises(InvalidInputError, match="Card front and back cannot be empty"):
            AnkiCard(front="", back="answer")

    def test_empty_back_raises_error(self):
        """Test that empty back field raises validation error."""
        with pytest.raises(InvalidInputError, match="Card front and back cannot be empty"):
            AnkiCard(front="question", back="")

    def test_whitespace_only_front_raises_error(self):
        """Test that whitespace-only front raises validation error."""
        with pytest.raises(InvalidInputError, match="Card front and back cannot be empty"):
            AnkiCard(front="   ", back="answer")

    def test_cefr_level_normalization(self):
        """Test that CEFR levels are normalized to uppercase."""
        card = AnkiCard(front="test", back="test", cefr_level="b1")
        assert card.cefr_level == "B1"

    def test_invalid_cefr_level_raises_error(self):
        """Test that invalid CEFR level raises validation error."""
        with pytest.raises(InvalidInputError, match="CEFR level must be one of"):
            AnkiCard(front="test", back="test", cefr_level="D1")

    def test_valid_cefr_levels(self):
        """Test all valid CEFR levels."""
        valid_levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
        for level in valid_levels:
            card = AnkiCard(front="test", back="test", cefr_level=level.lower())
            assert card.cefr_level == level

    def test_audio_expiry_check_not_expired(self):
        """Test audio expiry check when audio is not expired."""
        future_date = datetime.utcnow() + timedelta(days=10)
        audio_meta = AudioMetadata(
            reference_mp3="/path/to/audio.mp3",
            audio_expires_at=future_date
        )
        card = AnkiCard(
            front="test",
            back="test",
            audio_metadata=audio_meta
        )
        assert card.is_audio_expired() is False

    def test_audio_expiry_check_expired(self):
        """Test audio expiry check when audio is expired."""
        past_date = datetime.utcnow() - timedelta(days=1)
        audio_meta = AudioMetadata(
            reference_mp3="/path/to/audio.mp3",
            audio_expires_at=past_date
        )
        card = AnkiCard(
            front="test",
            back="test",
            audio_metadata=audio_meta
        )
        assert card.is_audio_expired() is True

    def test_audio_expiry_check_no_audio(self):
        """Test audio expiry check when card has no audio."""
        card = AnkiCard(front="test", back="test")
        assert card.is_audio_expired() is False


# ============================================================================
# TEST SUITE 2: AnkiDeck Validation
# ============================================================================


class TestAnkiDeckValidation:
    """Test suite for AnkiDeck validation."""

    def test_deck_creation_with_valid_name(self):
        """Test creating a deck with valid name."""
        deck = AnkiDeck(name="Dutch Vocabulary")
        assert deck.name == "Dutch Vocabulary"
        assert deck.description is None
        assert deck.tags == []

    def test_deck_creation_with_all_fields(self):
        """Test creating a deck with all fields."""
        deck = AnkiDeck(
            name="Advanced Dutch",
            description="Advanced level vocabulary and grammar",
            tags=["dutch", "advanced", "C1"],
            metadata={"category": "language"}
        )
        assert deck.name == "Advanced Dutch"
        assert deck.description == "Advanced level vocabulary and grammar"
        assert len(deck.tags) == 3
        assert deck.metadata["category"] == "language"

    def test_empty_deck_name_raises_error(self):
        """Test that empty deck name raises validation error."""
        with pytest.raises(InvalidInputError, match="Deck name cannot be empty"):
            AnkiDeck(name="")

    def test_whitespace_only_deck_name_raises_error(self):
        """Test that whitespace-only deck name raises validation error."""
        with pytest.raises(InvalidInputError, match="Deck name cannot be empty"):
            AnkiDeck(name="   ")


# ============================================================================
# TEST SUITE 3: AnkiExportSession
# ============================================================================


class TestAnkiExportSession:
    """Test suite for AnkiExportSession."""

    def test_export_session_creation(self):
        """Test creating an export session."""
        session = AnkiExportSession(
            name="Dutch Vocabulary (2025-12-09 14:30)",
            export_format="apkg",
            status="draft"
        )
        assert session.name == "Dutch Vocabulary (2025-12-09 14:30)"
        assert session.export_format == "apkg"
        assert session.status == "draft"
        assert session.include_audio is True
        assert session.include_images is True

    def test_timestamped_name_generation(self):
        """Test automatic timestamped name generation."""
        base_name = "My Deck"
        timestamped = AnkiExportSession.generate_timestamped_name(base_name)
        
        # Should contain base name and timestamp format
        assert "My Deck" in timestamped
        assert "(" in timestamped
        assert ")" in timestamped
        # Should match format: "My Deck (YYYY-MM-DD HH:MM)"
        assert len(timestamped) > len(base_name)

    def test_export_session_with_settings(self):
        """Test export session with custom settings."""
        session = AnkiExportSession(
            name="Audio-only Export",
            export_format="json",
            include_audio=True,
            include_images=False,
        )
        assert session.include_audio is True
        assert session.include_images is False
        assert session.export_format == "json"


# ============================================================================
# TEST SUITE 4: CEFR Vote and Classification
# ============================================================================


class TestCEFRVote:
    """Test suite for CEFR voting system."""

    def test_cefr_vote_creation(self):
        """Test creating a CEFR vote."""
        vote = CEFRVote(
            model_id="gpt-4",
            level="B1",
            confidence=0.85,
            reasoning="Common intermediate vocabulary with standard grammar"
        )
        assert vote.model_id == "gpt-4"
        assert vote.level == "B1"
        assert vote.confidence == 0.85
        assert "intermediate" in vote.reasoning

    def test_cefr_vote_without_reasoning(self):
        """Test CEFR vote without reasoning (optional field)."""
        vote = CEFRVote(
            model_id="claude-3",
            level="C1",
            confidence=0.92
        )
        assert vote.reasoning is None


# ============================================================================
# TEST SUITE 5: Source Citation
# ============================================================================


class TestSourceCitation:
    """Test suite for source citation."""

    def test_citation_creation_with_page(self):
        """Test creating citation with page number."""
        citation = SourceCitation(
            source_id="source:ebook_123",
            page=42,
            context="This is the relevant passage from the book."
        )
        assert citation.source_id == "source:ebook_123"
        assert citation.page == 42
        assert "relevant passage" in citation.context

    def test_citation_timestamp_auto_generated(self):
        """Test that timestamp is automatically generated."""
        citation = SourceCitation(source_id="source:123")
        assert citation.timestamp is not None
        assert isinstance(citation.timestamp, datetime)

    def test_citation_without_optional_fields(self):
        """Test citation with only required source_id."""
        citation = SourceCitation(source_id="source:456")
        assert citation.source_id == "source:456"
        assert citation.page is None
        assert citation.context is None


# ============================================================================
# TEST SUITE 6: Image Metadata
# ============================================================================


class TestImageMetadata:
    """Test suite for image metadata."""

    def test_image_metadata_from_api(self):
        """Test image metadata from external API."""
        meta = ImageMetadata(
            url="https://images.unsplash.com/photo-123",
            source="unsplash",
            license="Unsplash License",
            attribution_text="Photo by John Doe on Unsplash",
            cached_path="/app/data/anki_data/images/cache/abc123.jpg",
            cache_expiry=datetime.utcnow() + timedelta(days=7)
        )
        assert meta.source == "unsplash"
        assert "John Doe" in meta.attribution_text
        assert meta.cached_path.endswith(".jpg")

    def test_image_metadata_from_upload(self):
        """Test image metadata from user upload."""
        meta = ImageMetadata(
            source="upload",
            cached_path="/app/data/anki_data/images/uploads/my_image.png"
        )
        assert meta.source == "upload"
        assert meta.url is None
        assert meta.attribution_text is None


# ============================================================================
# TEST SUITE 7: Audio Metadata
# ============================================================================


class TestAudioMetadata:
    """Test suite for audio metadata."""

    def test_audio_metadata_with_reference(self):
        """Test audio metadata with reference audio."""
        expires = datetime.utcnow() + timedelta(days=30)
        audio = AudioMetadata(
            reference_mp3="/app/data/anki_data/audio/card_123.mp3",
            audio_expires_at=expires,
            ipa_transcriptions=["ˈvɛrkən"]
        )
        assert audio.reference_mp3.endswith(".mp3")
        assert len(audio.ipa_transcriptions) == 1
        assert audio.user_recordings == []
        assert audio.phonetic_scores == []

    def test_audio_metadata_with_user_recordings(self):
        """Test audio metadata with user recordings."""
        audio = AudioMetadata(
            reference_mp3="/path/to/ref.mp3",
            user_recordings=["/path/to/rec1.mp3", "/path/to/rec2.mp3"],
            phonetic_scores=[0.85, 0.92],
            ipa_transcriptions=["ˈvɛrkən", "ˈvɛrkən", "ˈvɛrkən"]
        )
        assert len(audio.user_recordings) == 2
        assert len(audio.phonetic_scores) == 2
        assert len(audio.ipa_transcriptions) == 3  # reference + 2 recordings


# ============================================================================
# TEST SUITE 8: DutchWordFrequency
# ============================================================================


class TestDutchWordFrequency:
    """Test suite for Dutch word frequency."""

    def test_word_frequency_creation(self):
        """Test creating word frequency entry."""
        freq = DutchWordFrequency(
            word="werken",
            frequency=95000,
            rank=850
        )
        assert freq.word == "werken"
        assert freq.frequency == 95000
        assert freq.rank == 850

    def test_frequency_rank_correlation(self):
        """Test that high frequency = low rank (common words)."""
        common_word = DutchWordFrequency(word="de", frequency=5000000, rank=1)
        rare_word = DutchWordFrequency(word="epistemologisch", frequency=300, rank=35000)
        
        assert common_word.rank < rare_word.rank
        assert common_word.frequency > rare_word.frequency


# ============================================================================
# TEST SUITE 9: ImageCache
# ============================================================================


class TestImageCache:
    """Test suite for image cache."""

    def test_image_cache_creation(self):
        """Test creating image cache entry."""
        cache = ImageCache(
            url="cache_key_unsplash:house",
            cached_path="/app/data/anki_data/images/cache/abc123.jpg",
            source="unsplash",
            attribution="Photo by John Doe",
            file_size=1024000  # 1MB
        )
        assert cache.file_size == 1024000
        assert cache.access_count == 0
        assert cache.source == "unsplash"

    def test_cache_expiry_default(self):
        """Test that cache expiry defaults to 7 days from now."""
        cache = ImageCache(
            url="test",
            cached_path="/path",
            source="test",
            attribution="test",
            file_size=1000
        )
        
        # Check expiry is roughly 7 days from now (within 1 minute tolerance)
        expected_expiry = datetime.utcnow() + timedelta(days=7)
        time_diff = abs((cache.expires_at - expected_expiry).total_seconds())
        assert time_diff < 60  # Within 1 minute

    def test_access_tracking_fields(self):
        """Test access tracking fields."""
        cache = ImageCache(
            url="test",
            cached_path="/path",
            source="test",
            attribution="test",
            file_size=1000
        )
        
        assert cache.access_count == 0
        assert isinstance(cache.last_accessed, datetime)
        
        # Simulate access update
        cache.access_count += 1
        cache.last_accessed = datetime.utcnow()
        assert cache.access_count == 1


# ============================================================================
# TEST SUITE 10: AnkiCardEdit
# ============================================================================


class TestAnkiCardEdit:
    """Test suite for card edit history."""

    def test_card_edit_creation(self):
        """Test creating a card edit record."""
        changes = {
            "front": {"old": "old text", "new": "new text"},
            "tags": {"old": ["A1"], "new": ["A1", "verb"]}
        }
        
        edit = AnkiCardEdit(
            card_id="card:123",
            changes=changes,
            edited_by="user:456"
        )
        
        assert edit.card_id == "card:123"
        assert "front" in edit.changes
        assert edit.edited_by == "user:456"

    def test_card_edit_without_user(self):
        """Test card edit without user attribution."""
        edit = AnkiCardEdit(
            card_id="card:123",
            changes={"back": {"old": "a", "new": "b"}}
        )
        assert edit.edited_by is None


# ============================================================================
# TEST SUITE 11: Integration Tests
# ============================================================================


class TestAnkiIntegration:
    """Integration tests for Anki components working together."""

    def test_complete_card_workflow(self):
        """Test creating a complete card with all features."""
        # Create citation
        citation = SourceCitation(
            source_id="source:dutch_textbook",
            page=127,
            context="Chapter on work-related vocabulary"
        )
        
        # Create image metadata
        image = ImageMetadata(
            url="https://example.com/work.jpg",
            source="pexels",
            attribution_text="Photo by Jane Smith on Pexels",
            cached_path="/cache/work.jpg"
        )
        
        # Create audio metadata
        audio = AudioMetadata(
            reference_mp3="/audio/werken.mp3",
            audio_expires_at=datetime.utcnow() + timedelta(days=30),
            ipa_transcriptions=["ˈvɛrkən"]
        )
        
        # Create CEFR votes
        votes = [
            CEFRVote(model_id="fietje-2", level="B1", confidence=0.88),
            CEFRVote(model_id="gpt-4", level="B1", confidence=0.85),
            CEFRVote(model_id="claude-3", level="B1", confidence=0.90),
        ]
        
        # Create complete card
        card = AnkiCard(
            front="werken",
            back="to work",
            notes="Common verb. Used in work contexts.",
            deck_id="deck:intermediate",
            source_citation=citation,
            cefr_level="B1",
            cefr_confidence=0.876,
            cefr_votes=votes,
            image_metadata=image,
            audio_metadata=audio,
            tags=["verb", "work", "B1"]
        )
        
        # Verify all components
        assert card.front == "werken"
        assert card.source_citation.page == 127
        assert card.image_metadata.source == "pexels"
        assert card.audio_metadata.reference_mp3 == "/audio/werken.mp3"
        assert len(card.cefr_votes) == 3
        assert all(v.level == "B1" for v in card.cefr_votes)
        assert card.cefr_confidence == 0.876

    def test_deck_with_multiple_cefr_levels(self):
        """Test deck can contain cards of different CEFR levels."""
        cards = [
            AnkiCard(front="hallo", back="hello", cefr_level="A1"),
            AnkiCard(front="werken", back="to work", cefr_level="B1"),
            AnkiCard(front="epistemologisch", back="epistemological", cefr_level="C2"),
        ]
        
        levels = [card.cefr_level for card in cards]
        assert "A1" in levels
        assert "B1" in levels
        assert "C2" in levels
