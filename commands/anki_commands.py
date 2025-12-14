"""
Anki command module for async background jobs.

This module provides commands for:
- Generating flashcards from conversations/sources
- Regenerating expired audio
- Reclassifying CEFR levels with updated models
"""

import time
from typing import Optional, List
from loguru import logger
from pydantic import BaseModel
from surreal_commands import CommandInput, CommandOutput, command

from open_notebook.domain.anki import AnkiCard, AnkiDeck
from api.anki_service import AnkiService
from api.cefr_service import CEFRService
from api.image_service import ImageService
from api.audio_service import AudioService


# ============================================================================
# Card Generation Commands
# ============================================================================


class GenerateCardsInput(CommandInput):
    """Input for generating cards from content."""
    source_content: str
    source_id: Optional[str] = None
    deck_id: str
    target_language: str = "nl"  # Dutch by default
    include_audio: bool = True
    include_images: bool = True
    auto_cefr: bool = True


class GenerateCardsOutput(CommandOutput):
    """Output from card generation."""
    success: bool
    cards_created: int
    card_ids: List[str]
    processing_time: float
    error_message: Optional[str] = None


@command("generate_anki_cards", app="open_notebook")
async def generate_anki_cards(
    input_data: GenerateCardsInput,
) -> GenerateCardsOutput:
    """Generate Anki flashcards from content using LLM.
    
    This command:
    1. Uses LLM to extract vocabulary and create cards
    2. Optionally classifies CEFR levels
    3. Optionally searches for images
    4. Optionally generates reference audio
    """
    start_time = time.time()
    
    try:
        logger.info(f"Generating cards for deck {input_data.deck_id}")
        
        anki_service = AnkiService()
        cefr_service = CEFRService()
        image_service = ImageService()
        audio_service = AudioService()
        
        # TODO: Use LLM with card_generation.jinja prompt to extract cards
        # For now, this is a placeholder showing the structure
        
        # Example: Parse content and create cards
        # cards_data = await _extract_cards_from_content(input_data.source_content)
        
        card_ids = []
        cards_created = 0
        
        # Placeholder: Create one sample card to show the flow
        sample_card = AnkiCard(
            front="werken",
            back="to work",
            notes="Common verb for work-related activities",
            deck_id=input_data.deck_id,
            tags=["verb", "work"]
        )
        
        # Add CEFR classification if requested
        if input_data.auto_cefr:
            level, confidence, votes = await cefr_service.classify_text(
                sample_card.front
            )
            sample_card.cefr_level = level
            sample_card.cefr_confidence = confidence
            sample_card.cefr_votes = votes
        
        # Add image if requested
        if input_data.include_images:
            try:
                image_meta = await image_service.search_image(
                    query=sample_card.front,
                    context=sample_card.back
                )
                sample_card.image_metadata = image_meta
            except Exception as e:
                logger.warning(f"Failed to fetch image: {e}")
        
        # Add audio if requested
        if input_data.include_audio:
            try:
                audio_meta = await audio_service.generate_reference_audio(
                    text=sample_card.front,
                    card_id="temp",  # Will be updated after card creation
                    language=input_data.target_language
                )
                sample_card.audio_metadata = audio_meta
            except Exception as e:
                logger.warning(f"Failed to generate audio: {e}")
        
        # Create card in database
        created_card = await anki_service.create_card(sample_card)
        card_ids.append(created_card.id)
        cards_created += 1
        
        # If audio was generated, update the filename with actual card ID
        if input_data.include_audio and created_card.audio_metadata:
            try:
                # Regenerate with proper card ID
                audio_meta = await audio_service.generate_reference_audio(
                    text=created_card.front,
                    card_id=created_card.id,
                    language=input_data.target_language
                )
                await anki_service.set_card_audio(created_card.id, audio_meta)
            except Exception as e:
                logger.warning(f"Failed to update audio with card ID: {e}")
        
        processing_time = time.time() - start_time
        logger.info(f"Created {cards_created} cards in {processing_time:.2f}s")
        
        return GenerateCardsOutput(
            success=True,
            cards_created=cards_created,
            card_ids=card_ids,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Card generation failed: {e}")
        return GenerateCardsOutput(
            success=False,
            cards_created=0,
            card_ids=[],
            processing_time=time.time() - start_time,
            error_message=str(e)
        )


# ============================================================================
# Audio Regeneration Commands
# ============================================================================


class RegenerateAudioInput(CommandInput):
    """Input for audio regeneration."""
    deck_id: Optional[str] = None
    all_decks: bool = False
    force_regenerate: bool = False  # Regenerate even if not expired


class RegenerateAudioOutput(CommandOutput):
    """Output from audio regeneration."""
    success: bool
    files_regenerated: int
    processing_time: float
    error_message: Optional[str] = None


@command("regenerate_anki_audio", app="open_notebook")
async def regenerate_anki_audio(
    input_data: RegenerateAudioInput,
) -> RegenerateAudioOutput:
    """Regenerate expired audio files for Anki cards.
    
    This command:
    1. Finds cards with expired audio
    2. Regenerates reference audio using Piper TTS
    3. Updates audio metadata with new expiry dates
    """
    start_time = time.time()
    
    try:
        logger.info(
            f"Regenerating audio (deck_id={input_data.deck_id}, "
            f"all_decks={input_data.all_decks})"
        )
        
        audio_service = AudioService()
        
        files_regenerated = await audio_service.regenerate_expired_audio(
            deck_id=input_data.deck_id,
            all_decks=input_data.all_decks
        )
        
        processing_time = time.time() - start_time
        logger.info(
            f"Regenerated {files_regenerated} audio files in {processing_time:.2f}s"
        )
        
        return RegenerateAudioOutput(
            success=True,
            files_regenerated=files_regenerated,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Audio regeneration failed: {e}")
        return RegenerateAudioOutput(
            success=False,
            files_regenerated=0,
            processing_time=time.time() - start_time,
            error_message=str(e)
        )


# ============================================================================
# CEFR Reclassification Commands
# ============================================================================


class ReclassifyCEFRInput(CommandInput):
    """Input for CEFR reclassification."""
    deck_id: Optional[str] = None
    card_ids: Optional[List[str]] = None
    all_cards: bool = False


class ReclassifyCEFROutput(CommandOutput):
    """Output from CEFR reclassification."""
    success: bool
    cards_reclassified: int
    processing_time: float
    error_message: Optional[str] = None


@command("reclassify_cefr_levels", app="open_notebook")
async def reclassify_cefr_levels(
    input_data: ReclassifyCEFRInput,
) -> ReclassifyCEFROutput:
    """Reclassify CEFR levels for cards using updated models.
    
    This command:
    1. Gets cards to reclassify (specific IDs, deck, or all)
    2. Runs multi-model CEFR classification
    3. Updates cards with new CEFR levels and votes
    """
    start_time = time.time()
    
    try:
        logger.info("Starting CEFR reclassification")
        
        anki_service = AnkiService()
        cefr_service = CEFRService()
        
        # Determine which cards to reclassify
        cards = []
        
        if input_data.card_ids:
            # Specific card IDs
            for card_id in input_data.card_ids:
                card = await anki_service.get_card_by_id(card_id)
                if card:
                    cards.append(card)
                    
        elif input_data.deck_id:
            # All cards in a deck
            deck = await anki_service.get_deck_by_id(input_data.deck_id)
            if deck:
                cards = await deck.get_cards()
                
        elif input_data.all_cards:
            # All cards (expensive operation)
            all_decks = await anki_service.get_all_decks()
            for deck in all_decks:
                deck_cards = await deck.get_cards()
                cards.extend(deck_cards)
        
        # Reclassify each card
        cards_reclassified = 0
        
        for card in cards:
            try:
                # Classify the front text
                level, confidence, votes = await cefr_service.classify_text(
                    card.front
                )
                
                # Update card
                await anki_service.set_card_cefr(
                    card_id=card.id,
                    cefr_level=level,
                    cefr_confidence=confidence,
                    cefr_votes=votes
                )
                
                cards_reclassified += 1
                logger.debug(
                    f"Reclassified card {card.id}: {level} "
                    f"(confidence: {confidence:.2f})"
                )
                
            except Exception as e:
                logger.error(f"Failed to reclassify card {card.id}: {e}")
                continue
        
        processing_time = time.time() - start_time
        logger.info(
            f"Reclassified {cards_reclassified} cards in {processing_time:.2f}s"
        )
        
        return ReclassifyCEFROutput(
            success=True,
            cards_reclassified=cards_reclassified,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"CEFR reclassification failed: {e}")
        return ReclassifyCEFROutput(
            success=False,
            cards_reclassified=0,
            processing_time=time.time() - start_time,
            error_message=str(e)
        )


# ============================================================================
# Cleanup Commands
# ============================================================================


class CleanupInput(CommandInput):
    """Input for cleanup operations."""
    cleanup_audio: bool = True
    cleanup_images: bool = True


class CleanupOutput(CommandOutput):
    """Output from cleanup operations."""
    success: bool
    audio_files_deleted: int
    image_files_deleted: int
    processing_time: float
    error_message: Optional[str] = None


@command("cleanup_anki_files", app="open_notebook")
async def cleanup_anki_files(
    input_data: CleanupInput,
) -> CleanupOutput:
    """Clean up expired audio and image files.
    
    This command:
    1. Deletes audio files older than expiry date
    2. Deletes cached images based on LRU and expiry
    """
    start_time = time.time()
    
    try:
        logger.info("Starting Anki file cleanup")
        
        audio_deleted = 0
        image_deleted = 0
        
        if input_data.cleanup_audio:
            audio_service = AudioService()
            audio_deleted = await audio_service.cleanup_expired_audio()
        
        if input_data.cleanup_images:
            image_service = ImageService()
            image_deleted = await image_service.cleanup_expired_cache()
        
        processing_time = time.time() - start_time
        logger.info(
            f"Cleanup complete: {audio_deleted} audio files, "
            f"{image_deleted} image files deleted in {processing_time:.2f}s"
        )
        
        return CleanupOutput(
            success=True,
            audio_files_deleted=audio_deleted,
            image_files_deleted=image_deleted,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return CleanupOutput(
            success=False,
            audio_files_deleted=0,
            image_files_deleted=0,
            processing_time=time.time() - start_time,
            error_message=str(e)
        )
