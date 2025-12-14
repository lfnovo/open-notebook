"""
Anki domain models for flashcard generation and management.
"""
from datetime import datetime, timedelta
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator
from loguru import logger

from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.base import ObjectModel
from open_notebook.exceptions import DatabaseOperationError, InvalidInputError


class ImageMetadata(BaseModel):
    """Metadata for card images from external APIs or uploads"""
    url: Optional[str] = None
    source: Optional[str] = None  # "unsplash", "pexels", "pixabay", "upload"
    license: Optional[str] = None
    attribution_text: Optional[str] = None
    cached_path: Optional[str] = None
    cache_expiry: Optional[datetime] = None


class SourceCitation(BaseModel):
    """Citation information for cards generated from sources"""
    source_id: str
    page: Optional[int] = None
    context: Optional[str] = None  # Text snippet from source
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CEFRVote(BaseModel):
    """Individual model vote for CEFR classification"""
    model_id: str
    level: str  # A1, A2, B1, B2, C1, C2
    confidence: float  # 0.0-1.0
    reasoning: Optional[str] = None


class AudioMetadata(BaseModel):
    """Audio pronunciation reference and recordings"""
    reference_mp3: Optional[str] = None  # Path to reference audio file
    audio_expires_at: Optional[datetime] = None  # 30-day expiry
    user_recordings: List[str] = Field(default_factory=list)  # Paths to user recordings
    phonetic_scores: List[float] = Field(default_factory=list)  # Scores for each recording
    ipa_transcriptions: List[str] = Field(default_factory=list)  # IPA for reference + recordings


class AnkiCard(ObjectModel):
    """
    Anki flashcard with support for images, audio, CEFR levels, and source citations.
    """
    table_name: ClassVar[str] = "anki_card"
    
    # Core card fields
    front: str
    back: str
    notes: Optional[str] = None
    
    # Relationships
    deck_id: Optional[str] = None  # Reference to AnkiDeck
    export_session_id: Optional[str] = None  # Reference to AnkiExportSession
    
    # Enhanced features
    source_citation: Optional[SourceCitation] = None
    cefr_level: Optional[str] = None  # A1, A2, B1, B2, C1, C2
    cefr_confidence: Optional[float] = None  # 0.0-1.0
    cefr_votes: List[CEFRVote] = Field(default_factory=list)
    
    image_metadata: Optional[ImageMetadata] = None
    audio_metadata: Optional[AudioMetadata] = None
    
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator("front", "back")
    @classmethod
    def fields_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise InvalidInputError("Card front and back cannot be empty")
        return v
    
    @field_validator("cefr_level")
    @classmethod
    def validate_cefr_level(cls, v):
        if v is not None:
            valid_levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
            if v.upper() not in valid_levels:
                raise InvalidInputError(f"CEFR level must be one of {valid_levels}")
            return v.upper()
        return v
    
    async def get_deck(self) -> Optional["AnkiDeck"]:
        """Get the deck this card belongs to"""
        if not self.deck_id:
            return None
        try:
            return await AnkiDeck.get(self.deck_id)
        except Exception as e:
            logger.error(f"Error fetching deck for card {self.id}: {str(e)}")
            return None
    
    async def get_export_session(self) -> Optional["AnkiExportSession"]:
        """Get the export session this card is part of"""
        if not self.export_session_id:
            return None
        try:
            return await AnkiExportSession.get(self.export_session_id)
        except Exception as e:
            logger.error(f"Error fetching export session for card {self.id}: {str(e)}")
            return None
    
    async def add_edit_history(self, changes: Dict[str, Any], user_id: Optional[str] = None):
        """Add an edit to the card's history"""
        edit = AnkiCardEdit(
            card_id=str(self.id),
            changes=changes,
            edited_by=user_id
        )
        await edit.save()
    
    def is_audio_expired(self) -> bool:
        """Check if audio needs regeneration"""
        if not self.audio_metadata or not self.audio_metadata.audio_expires_at:
            return False
        return datetime.utcnow() > self.audio_metadata.audio_expires_at


class AnkiDeck(ObjectModel):
    """
    Collection of Anki cards organized by topic/session.
    """
    table_name: ClassVar[str] = "anki_deck"
    
    name: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise InvalidInputError("Deck name cannot be empty")
        return v
    
    async def get_cards(self) -> List[AnkiCard]:
        """Get all cards in this deck"""
        try:
            cards = await repo_query(
                "SELECT * FROM anki_card WHERE deck_id = $deck_id ORDER BY created DESC",
                {"deck_id": self.id}  # Use string ID directly, not RecordID
            )
            return [AnkiCard(**card) for card in cards] if cards else []
        except Exception as e:
            logger.error(f"Error fetching cards for deck {self.id}: {str(e)}")
            raise DatabaseOperationError(e)
    
    async def get_card_count(self) -> int:
        """Get the number of cards in this deck"""
        try:
            result = await repo_query(
                "SELECT count() as count FROM anki_card WHERE deck_id = $deck_id GROUP ALL",
                {"deck_id": self.id}  # Use string ID directly, not RecordID
            )
            return result[0]["count"] if result else 0
        except Exception as e:
            logger.error(f"Error counting cards for deck {self.id}: {str(e)}")
            return 0
    
    async def get_expired_audio_cards(self) -> List[AnkiCard]:
        """Get cards with expired audio in this deck"""
        try:
            cards = await self.get_cards()
            return [card for card in cards if card.is_audio_expired()]
        except Exception as e:
            logger.error(f"Error fetching expired audio cards for deck {self.id}: {str(e)}")
            return []


class AnkiExportSession(ObjectModel):
    """
    Named export session for organizing card exports with timestamp-based uniqueness.
    """
    table_name: ClassVar[str] = "anki_export_session"
    
    name: str  # Auto-timestamped like "Dutch Vocabulary (2025-12-09 14:30)"
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    # Export settings
    export_format: str = "apkg"  # "apkg" or "json"
    include_audio: bool = True
    include_images: bool = True
    
    # Status tracking
    status: str = "draft"  # "draft", "exporting", "completed", "failed"
    exported_at: Optional[datetime] = None
    export_path: Optional[str] = None
    error_message: Optional[str] = None
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @classmethod
    def generate_timestamped_name(cls, base_name: str) -> str:
        """Generate unique name with timestamp suffix"""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        return f"{base_name} ({timestamp})"
    
    async def get_cards(self) -> List[AnkiCard]:
        """Get all cards in this export session"""
        try:
            cards = await repo_query(
                "SELECT * FROM anki_card WHERE export_session_id = $session_id ORDER BY created DESC",
                {"session_id": ensure_record_id(self.id)}
            )
            return [AnkiCard(**card) for card in cards] if cards else []
        except Exception as e:
            logger.error(f"Error fetching cards for export session {self.id}: {str(e)}")
            raise DatabaseOperationError(e)
    
    async def get_card_count(self) -> int:
        """Get the number of cards in this session"""
        try:
            result = await repo_query(
                "SELECT count() as count FROM anki_card WHERE export_session_id = $session_id GROUP ALL",
                {"session_id": ensure_record_id(self.id)}
            )
            return result[0]["count"] if result else 0
        except Exception as e:
            logger.error(f"Error counting cards for export session {self.id}: {str(e)}")
            return 0


class AnkiCardEdit(ObjectModel):
    """
    Diff-based edit history for cards (last 10 versions).
    """
    table_name: ClassVar[str] = "anki_card_edit_history"
    
    card_id: str  # Reference to AnkiCard
    changes: Dict[str, Any]  # Diff of what changed
    edited_by: Optional[str] = None
    
    @classmethod
    async def get_card_history(cls, card_id: str, limit: int = 10) -> List["AnkiCardEdit"]:
        """Get edit history for a card (last N versions)"""
        try:
            edits = await repo_query(
                "SELECT * FROM anki_card_edit_history WHERE card_id = $card_id ORDER BY created DESC LIMIT $limit",
                {"card_id": ensure_record_id(card_id), "limit": limit}
            )
            return [AnkiCardEdit(**edit) for edit in edits] if edits else []
        except Exception as e:
            logger.error(f"Error fetching edit history for card {card_id}: {str(e)}")
            raise DatabaseOperationError(e)
    
    @classmethod
    async def cleanup_old_history(cls, card_id: str, keep_count: int = 10):
        """Remove old edit history beyond keep_count versions"""
        try:
            await repo_query(
                """
                DELETE FROM anki_card_edit_history 
                WHERE card_id = $card_id 
                AND created < (
                    SELECT created FROM anki_card_edit_history 
                    WHERE card_id = $card_id 
                    ORDER BY created DESC 
                    LIMIT 1 START $keep_count
                )[0].created
                """,
                {"card_id": ensure_record_id(card_id), "keep_count": keep_count}
            )
        except Exception as e:
            logger.warning(f"Error cleaning up old history for card {card_id}: {str(e)}")


class DutchWordFrequency(ObjectModel):
    """
    Dutch word frequency data from OpenSubtitles for CEFR classification.
    """
    table_name: ClassVar[str] = "dutch_word_frequency"
    
    word: str
    frequency: int  # Occurrence count
    rank: int  # Frequency rank (1 = most common)
    
    @classmethod
    async def get_word_frequency(cls, word: str) -> Optional["DutchWordFrequency"]:
        """Get frequency data for a specific word"""
        try:
            result = await repo_query(
                "SELECT * FROM dutch_word_frequency WHERE word = $word LIMIT 1",
                {"word": word.lower()}
            )
            return DutchWordFrequency(**result[0]) if result else None
        except Exception as e:
            logger.error(f"Error fetching frequency for word '{word}': {str(e)}")
            return None
    
    @classmethod
    async def bulk_insert(cls, words: List[Dict[str, Any]]):
        """Bulk insert word frequency data"""
        try:
            for word_data in words:
                word = cls(**word_data)
                await word.save()
        except Exception as e:
            logger.error(f"Error bulk inserting word frequencies: {str(e)}")
            raise DatabaseOperationError(e)


class ImageCache(ObjectModel):
    """
    Cache for external API images with 7-day expiry and 500MB LRU management.
    """
    table_name: ClassVar[str] = "image_cache"
    
    url: str  # Original URL from API
    cached_path: str  # Local path in notebook_data/anki_images/cache/
    source: str  # "unsplash", "pexels", "pixabay"
    attribution: str
    
    file_size: int  # Bytes
    access_count: int = 0
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(days=7))
    
    @classmethod
    async def get_by_url(cls, url: str) -> Optional["ImageCache"]:
        """Get cached image by URL"""
        try:
            result = await repo_query(
                "SELECT * FROM image_cache WHERE url = $url LIMIT 1",
                {"url": url}
            )
            if result:
                # Update access tracking
                cache_entry = ImageCache(**result[0])
                cache_entry.access_count += 1
                cache_entry.last_accessed = datetime.utcnow()
                await cache_entry.save()
                return cache_entry
            return None
        except Exception as e:
            logger.error(f"Error fetching cached image for URL '{url}': {str(e)}")
            return None
    
    @classmethod
    async def get_expired_entries(cls) -> List["ImageCache"]:
        """Get all expired cache entries"""
        try:
            result = await repo_query(
                "SELECT * FROM image_cache WHERE expires_at < $now",
                {"now": datetime.utcnow()}
            )
            return [ImageCache(**entry) for entry in result] if result else []
        except Exception as e:
            logger.error(f"Error fetching expired cache entries: {str(e)}")
            return []
    
    @classmethod
    async def get_total_cache_size(cls) -> int:
        """Get total size of cached images in bytes"""
        try:
            result = await repo_query(
                "SELECT math::sum(file_size) as total FROM image_cache GROUP ALL"
            )
            return result[0]["total"] if result and result[0].get("total") else 0
        except Exception as e:
            logger.error(f"Error calculating cache size: {str(e)}")
            return 0
    
    @classmethod
    async def cleanup_lru(cls, max_size_bytes: int = 500 * 1024 * 1024):
        """
        Cleanup cache using LRU eviction if over max_size (default 500MB).
        """
        try:
            total_size = await cls.get_total_cache_size()
            if total_size <= max_size_bytes:
                return
            
            # Get entries sorted by last access (oldest first)
            entries = await repo_query(
                "SELECT * FROM image_cache ORDER BY last_accessed ASC"
            )
            
            if not entries:
                return
            
            bytes_to_free = total_size - max_size_bytes
            freed_bytes = 0
            
            for entry_data in entries:
                if freed_bytes >= bytes_to_free:
                    break
                
                entry = ImageCache(**entry_data)
                freed_bytes += entry.file_size
                await entry.delete()
                logger.info(f"Evicted cache entry: {entry.cached_path} ({entry.file_size} bytes)")
            
            logger.info(f"Cache cleanup freed {freed_bytes} bytes")
        except Exception as e:
            logger.error(f"Error during LRU cache cleanup: {str(e)}")
