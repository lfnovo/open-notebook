"""
Audio service for Anki flashcards.

This service handles:
1. Text-to-speech generation using Piper
2. Speech-to-text transcription using Whisper
3. IPA phonetic transcription using phonemizer
4. Phonetic distance scoring for pronunciation practice
"""

import asyncio
import hashlib
import httpx
import os
from datetime import datetime, timedelta
from loguru import logger
from pathlib import Path
from phonemizer import phonemize
from phonemizer.backend import EspeakBackend
from typing import Optional

from open_notebook.domain.anki import AnkiCard, AudioMetadata
from open_notebook.config import UPLOADS_FOLDER


class AudioService:
    """Service for audio generation, transcription, and phonetic analysis."""
    
    # Service URLs from environment or defaults
    WHISPER_URL = os.getenv("WHISPER_API_URL", "http://whisper:9000")
    PIPER_URL = os.getenv("PIPER_API_URL", "http://piper:10200")
    
    # Audio settings
    AUDIO_FORMAT = "mp3"
    AUDIO_BITRATE = "128k"
    AUDIO_EXPIRY_DAYS = 30
    
    def __init__(self):
        """Initialize audio service."""
        logger.info("Initializing Audio service")
        self.audio_dir = Path(UPLOADS_FOLDER) / "anki_data" / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize phonemizer backend
        self.phonemizer_backend = EspeakBackend(
            language="nl",  # Dutch
            with_stress=True,
            preserve_punctuation=False,
        )
    
    async def generate_reference_audio(
        self,
        text: str,
        card_id: str,
        language: str = "nl",
        voice: str = "nl_NL-rdh-medium"
    ) -> AudioMetadata:
        """Generate reference audio using Piper TTS.
        
        Args:
            text: Text to synthesize
            card_id: ID of the card this audio is for
            language: Language code (default: Dutch)
            voice: Piper voice model to use
            
        Returns:
            AudioMetadata with reference audio path and IPA transcription
        """
        logger.info(f"Generating reference audio for card {card_id}")
        
        # Generate IPA transcription
        ipa = self._transcribe_to_ipa(text, language)
        
        # Generate audio file using Piper
        audio_path = await self._generate_piper_audio(text, card_id, voice)
        
        # Create audio metadata
        metadata = AudioMetadata(
            reference_mp3=str(audio_path),
            audio_expires_at=datetime.utcnow() + timedelta(days=self.AUDIO_EXPIRY_DAYS),
            ipa_transcriptions=[ipa],
            user_recordings=[],
            phonetic_scores=[]
        )
        
        logger.info(f"Reference audio generated: {audio_path}")
        return metadata
    
    async def _generate_piper_audio(
        self,
        text: str,
        card_id: str,
        voice: str
    ) -> Path:
        """Generate audio using Piper TTS service.
        
        Args:
            text: Text to synthesize
            card_id: Card ID for filename
            voice: Piper voice model
            
        Returns:
            Path to generated audio file
        """
        # Create filename based on card ID and content hash
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        filename = f"{card_id}_{text_hash}.mp3"
        output_path = self.audio_dir / filename
        
        # If file already exists and is recent, return it
        if output_path.exists():
            logger.debug(f"Using cached audio: {output_path}")
            return output_path
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Piper API expects JSON with text and voice
                response = await client.post(
                    f"{self.PIPER_URL}/api/tts",
                    json={
                        "text": text,
                        "voice": voice,
                        "output_format": "mp3"
                    }
                )
                response.raise_for_status()
                
                # Save audio file
                output_path.write_bytes(response.content)
                logger.debug(f"Generated audio via Piper: {output_path}")
                
        except httpx.HTTPError as e:
            logger.error(f"Piper TTS failed: {e}")
            raise RuntimeError(f"Failed to generate audio: {e}")
        
        return output_path
    
    async def transcribe_user_recording(
        self,
        audio_file: Path,
        card_id: str,
        reference_text: str
    ) -> tuple[str, str, float]:
        """Transcribe user recording and calculate phonetic score.
        
        Args:
            audio_file: Path to user's audio recording
            card_id: Card ID for saving
            reference_text: Expected text for comparison
            
        Returns:
            Tuple of (transcribed_text, ipa_transcription, phonetic_score)
        """
        logger.info(f"Transcribing user recording for card {card_id}")
        
        # Transcribe using Whisper
        transcribed_text = await self._whisper_transcribe(audio_file)
        
        # Generate IPA for user's transcription
        user_ipa = self._transcribe_to_ipa(transcribed_text)
        
        # Generate IPA for reference text
        reference_ipa = self._transcribe_to_ipa(reference_text)
        
        # Calculate phonetic distance (similarity score)
        score = self._calculate_phonetic_score(user_ipa, reference_ipa)
        
        logger.info(f"Transcription: '{transcribed_text}' | Score: {score:.2f}")
        return transcribed_text, user_ipa, score
    
    async def _whisper_transcribe(self, audio_file: Path) -> str:
        """Transcribe audio using Whisper service.
        
        Args:
            audio_file: Path to audio file
            
        Returns:
            Transcribed text
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                with open(audio_file, "rb") as f:
                    files = {"audio_file": (audio_file.name, f, "audio/mpeg")}
                    response = await client.post(
                        f"{self.WHISPER_URL}/asr",
                        files=files,
                        data={"language": "nl"}  # Dutch
                    )
                    response.raise_for_status()
                    
                    result = response.json()
                    return result.get("text", "").strip()
                    
        except httpx.HTTPError as e:
            logger.error(f"Whisper transcription failed: {e}")
            raise RuntimeError(f"Failed to transcribe audio: {e}")
    
    def _transcribe_to_ipa(self, text: str, language: str = "nl") -> str:
        """Convert text to IPA phonetic transcription.
        
        Args:
            text: Text to transcribe
            language: Language code (default: Dutch)
            
        Returns:
            IPA transcription string
        """
        try:
            # Use phonemizer to convert text to IPA
            ipa = phonemize(
                text,
                language=language,
                backend="espeak",
                strip=True,
                preserve_punctuation=False,
                with_stress=True
            )
            return ipa.strip()
            
        except Exception as e:
            logger.error(f"IPA transcription failed: {e}")
            # Return original text as fallback
            return text
    
    def _calculate_phonetic_score(
        self,
        user_ipa: str,
        reference_ipa: str
    ) -> float:
        """Calculate phonetic similarity score using Levenshtein distance.
        
        Args:
            user_ipa: User's IPA transcription
            reference_ipa: Reference IPA transcription
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not user_ipa or not reference_ipa:
            return 0.0
        
        # Calculate Levenshtein distance
        distance = self._levenshtein_distance(user_ipa, reference_ipa)
        
        # Convert to similarity score (0.0 to 1.0)
        max_len = max(len(user_ipa), len(reference_ipa))
        if max_len == 0:
            return 1.0
        
        similarity = 1.0 - (distance / max_len)
        return max(0.0, min(1.0, similarity))  # Clamp to [0, 1]
    
    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings.
        
        Args:
            s1: First string
            s2: Second string
            
        Returns:
            Edit distance
        """
        if len(s1) < len(s2):
            return AudioService._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # Cost of insertions, deletions, or substitutions
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    async def regenerate_expired_audio(
        self,
        deck_id: Optional[str] = None,
        all_decks: bool = False
    ) -> int:
        """Regenerate expired audio for cards in a deck or all decks.
        
        Args:
            deck_id: Specific deck ID to regenerate audio for
            all_decks: If True, regenerate for all decks
            
        Returns:
            Number of audio files regenerated
        """
        logger.info(f"Regenerating expired audio (deck_id={deck_id}, all_decks={all_decks})")
        
        anki_service = AnkiService()
        
        if all_decks:
            # Get all decks
            decks = await anki_service.get_all_decks()
            cards = []
            for deck in decks:
                deck_cards = await anki_service.get_expired_audio_cards(deck.id)
                cards.extend(deck_cards)
        elif deck_id:
            # Get cards from specific deck
            cards = await anki_service.get_expired_audio_cards(deck_id)
        else:
            logger.warning("No deck specified for audio regeneration")
            return 0
        
        # Regenerate audio for each card
        regenerated_count = 0
        for card in cards:
            try:
                # Generate new audio
                audio_metadata = await self.generate_reference_audio(
                    text=card.front,  # Use front of card as audio text
                    card_id=card.id
                )
                
                # Update card with new audio
                await anki_service.set_card_audio(card.id, audio_metadata)
                regenerated_count += 1
                
            except Exception as e:
                logger.error(f"Failed to regenerate audio for card {card.id}: {e}")
                continue
        
        logger.info(f"Regenerated {regenerated_count} audio files")
        return regenerated_count
    
    async def cleanup_expired_audio(self) -> int:
        """Delete expired audio files from disk.
        
        Returns:
            Number of files deleted
        """
        logger.info("Cleaning up expired audio files")
        
        deleted_count = 0
        expiry_threshold = datetime.utcnow()
        
        # Iterate through all audio files
        for audio_file in self.audio_dir.glob("*.mp3"):
            # Check if file is old enough to be expired (older than expiry days)
            file_age = datetime.utcnow() - datetime.fromtimestamp(audio_file.stat().st_mtime)
            
            if file_age > timedelta(days=self.AUDIO_EXPIRY_DAYS):
                try:
                    audio_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted expired audio: {audio_file}")
                except Exception as e:
                    logger.error(f"Failed to delete {audio_file}: {e}")
        
        logger.info(f"Deleted {deleted_count} expired audio files")
        return deleted_count
