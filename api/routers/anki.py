"""
API Router for Anki flashcard management.

Endpoints:
- Card CRUD operations
- Deck management
- Export sessions
- Audio generation and upload
- Image search and upload
- CEFR classification
"""

from pathlib import Path
from typing import List, Optional
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse
from loguru import logger
from pydantic import BaseModel, Field

from api.anki_service import AnkiService
from api.cefr_service import CEFRService
from api.image_service import ImageService
from api.audio_service import AudioService
from api.anki_insights_service import anki_insights_service
from open_notebook.domain.anki import (
    AnkiCard,
    AnkiDeck,
    AnkiExportSession,
    CEFRVote,
    ImageMetadata,
    AudioMetadata,
)
from open_notebook.exceptions import InvalidInputError

router = APIRouter(prefix="/anki", tags=["anki"])


# ============================================================================
# Request/Response Models
# ============================================================================


class CardCreateRequest(BaseModel):
    """Request to create a new card."""
    front: str
    back: str
    notes: Optional[str] = None
    deck_id: str
    tags: List[str] = []


class CardUpdateRequest(BaseModel):
    """Request to update an existing card."""
    front: Optional[str] = None
    back: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class DeckCreateRequest(BaseModel):
    """Request to create a new deck."""
    name: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class CEFRClassifyRequest(BaseModel):
    """Request to classify text CEFR level."""
    text: str


class CEFRClassifyResponse(BaseModel):
    """Response from CEFR classification."""
    level: str
    confidence: float
    votes: List[CEFRVote]


class ImageSearchRequest(BaseModel):
    """Request to search for an image."""
    query: str
    context: Optional[str] = None


class ExportSessionCreateRequest(BaseModel):
    """Request to create an export session."""
    deck_ids: List[str]
    export_format: str = "apkg"
    include_audio: bool = True
    include_images: bool = True


# ============================================================================
# Card Endpoints
# ============================================================================


@router.post("/cards", response_model=AnkiCard)
async def create_card(request: CardCreateRequest):
    """Create a new flashcard."""
    try:
        service = AnkiService()
        
        created_card = await service.create_card(
            front=request.front,
            back=request.back,
            notes=request.notes,
            deck_id=request.deck_id,
            tags=request.tags,
        )
        logger.info(f"Created card: {created_card.id}")
        
        return created_card
        
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create card: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cards/{card_id}", response_model=AnkiCard)
async def get_card(card_id: str):
    """Get a card by ID."""
    try:
        service = AnkiService()
        card = await service.get_card_by_id(card_id)
        
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        
        return card
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get card: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/cards/{card_id}", response_model=AnkiCard)
async def update_card(card_id: str, request: CardUpdateRequest):
    """Update an existing card."""
    try:
        service = AnkiService()
        
        # Get existing card
        card = await service.get_card_by_id(card_id)
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        
        # Update fields
        if request.front is not None:
            card.front = request.front
        if request.back is not None:
            card.back = request.back
        if request.notes is not None:
            card.notes = request.notes
        if request.tags is not None:
            card.tags = request.tags
        
        updated_card = await service.update_card(card)
        logger.info(f"Updated card: {card_id}")
        
        return updated_card
        
    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update card: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cards/{card_id}")
async def delete_card(card_id: str):
    """Delete a card."""
    try:
        service = AnkiService()
        await service.delete_card(card_id)
        logger.info(f"Deleted card: {card_id}")
        
        return {"success": True, "message": "Card deleted"}
        
    except Exception as e:
        logger.error(f"Failed to delete card: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/decks/{deck_id}/cards", response_model=List[AnkiCard])
async def get_deck_cards(
    deck_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get all cards in a deck with pagination."""
    try:
        service = AnkiService()
        deck = await service.get_deck(deck_id)
        
        if not deck:
            raise HTTPException(status_code=404, detail="Deck not found")
        
        cards = await deck.get_cards()
        logger.info(f"Retrieved {len(cards)} cards for deck {deck_id}")
        
        # Simple pagination
        paginated_cards = cards[skip:skip + limit]
        logger.info(f"Returning {len(paginated_cards)} cards after pagination (skip={skip}, limit={limit})")
        return paginated_cards
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get deck cards: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Deck Endpoints
# ============================================================================


@router.post("/decks", response_model=AnkiDeck)
async def create_deck(request: DeckCreateRequest):
    """Create a new deck."""
    try:
        logger.info(f"Received deck creation request: name={request.name}, tags={request.tags}")
        service = AnkiService()
        
        created_deck = await service.create_deck(
            name=request.name,
            description=request.description,
            tags=request.tags
        )
        logger.info(f"Created deck: {created_deck.id}")
        
        return created_deck
        
    except InvalidInputError as e:
        logger.error(f"Invalid input error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to create deck: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/decks", response_model=List[AnkiDeck])
async def get_all_decks():
    """Get all decks."""
    try:
        service = AnkiService()
        decks = await service.get_all_decks()
        
        return decks
        
    except Exception as e:
        logger.error(f"Failed to get decks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/decks/{deck_id}", response_model=AnkiDeck)
async def get_deck(deck_id: str):
    """Get a deck by ID."""
    try:
        service = AnkiService()
        deck = await service.get_deck(deck_id)
        
        if not deck:
            raise HTTPException(status_code=404, detail="Deck not found")
        
        return deck
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get deck: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/decks/{deck_id}")
async def delete_deck(
    deck_id: str,
    delete_cards: bool = Query(False)
):
    """Delete a deck (optionally with all cards)."""
    try:
        service = AnkiService()
        await service.delete_deck(deck_id, delete_cards=delete_cards)
        logger.info(f"Deleted deck: {deck_id} (delete_cards={delete_cards})")
        
        return {"success": True, "message": "Deck deleted"}
        
    except Exception as e:
        logger.error(f"Failed to delete deck: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CEFR Classification Endpoints
# ============================================================================


@router.post("/cefr/classify", response_model=CEFRClassifyResponse)
async def classify_cefr(request: CEFRClassifyRequest):
    """Classify text CEFR level using multi-model voting."""
    try:
        service = CEFRService()
        
        level, confidence, votes = await service.classify_text(request.text)
        
        return CEFRClassifyResponse(
            level=level,
            confidence=confidence,
            votes=votes
        )
        
    except Exception as e:
        logger.error(f"CEFR classification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cards/{card_id}/cefr")
async def set_card_cefr(card_id: str, request: CEFRClassifyRequest):
    """Classify and set CEFR level for a card."""
    try:
        anki_service = AnkiService()
        cefr_service = CEFRService()
        
        # Check card exists
        card = await anki_service.get_card_by_id(card_id)
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        
        # Classify
        level, confidence, votes = await cefr_service.classify_text(request.text)
        
        # Update card
        await anki_service.set_card_cefr(
            card_id=card_id,
            cefr_level=level,
            cefr_confidence=confidence,
            cefr_votes=votes
        )
        
        logger.info(f"Set CEFR level for card {card_id}: {level}")
        
        return {
            "success": True,
            "level": level,
            "confidence": confidence,
            "votes": votes
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set CEFR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Image Endpoints
# ============================================================================


@router.post("/images/search", response_model=ImageMetadata)
async def search_image(request: ImageSearchRequest):
    """Search for an image using external APIs."""
    try:
        service = ImageService()
        
        image_meta = await service.search_image(
            query=request.query,
            context=request.context
        )
        
        return image_meta
        
    except Exception as e:
        logger.error(f"Image search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cards/{card_id}/image/upload")
async def upload_card_image(
    card_id: str,
    file: UploadFile = File(...)
):
    """Upload a custom image for a card."""
    try:
        anki_service = AnkiService()
        image_service = ImageService()
        
        # Check card exists
        card = await anki_service.get_card_by_id(card_id)
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        
        # Save uploaded image
        image_meta = await image_service.save_uploaded_image(
            file=file,
            card_id=card_id
        )
        
        # Update card
        await anki_service.set_card_image(card_id, image_meta)
        
        logger.info(f"Uploaded image for card {card_id}")
        
        return {"success": True, "image_metadata": image_meta}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Audio Endpoints
# ============================================================================


@router.post("/cards/{card_id}/audio/generate")
async def generate_card_audio(
    card_id: str,
    text: str = Query(...),
    language: str = Query("nl")
):
    """Generate reference audio for a card."""
    try:
        anki_service = AnkiService()
        audio_service = AudioService()
        
        # Check card exists
        card = await anki_service.get_card_by_id(card_id)
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        
        # Generate audio
        audio_meta = await audio_service.generate_reference_audio(
            text=text,
            card_id=card_id,
            language=language
        )
        
        # Update card
        await anki_service.set_card_audio(card_id, audio_meta)
        
        logger.info(f"Generated audio for card {card_id}")
        
        return {"success": True, "audio_metadata": audio_meta}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cards/{card_id}/audio/transcribe")
async def transcribe_user_recording(
    card_id: str,
    file: UploadFile = File(...),
    reference_text: str = Query(...)
):
    """Transcribe user recording and score pronunciation."""
    try:
        anki_service = AnkiService()
        audio_service = AudioService()
        
        # Check card exists
        card = await anki_service.get_card_by_id(card_id)
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        
        # Save uploaded file temporarily
        temp_path = Path(f"/tmp/{file.filename}")
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Transcribe and score
        transcribed_text, ipa, score = await audio_service.transcribe_user_recording(
            audio_file=temp_path,
            card_id=card_id,
            reference_text=reference_text
        )
        
        # Clean up temp file
        temp_path.unlink()
        
        return {
            "success": True,
            "transcribed_text": transcribed_text,
            "ipa_transcription": ipa,
            "phonetic_score": score
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Export Session Endpoints
# ============================================================================


@router.post("/export-sessions", response_model=AnkiExportSession)
async def create_export_session(request: ExportSessionCreateRequest):
    """Create a new export session."""
    try:
        service = AnkiService()
        
        # Get deck names for session naming
        deck_names = []
        for deck_id in request.deck_ids:
            deck = await service.get_deck(deck_id)
            if deck:
                deck_names.append(deck.name)
        
        # Generate session name
        base_name = ", ".join(deck_names) if deck_names else "Export"
        session_name = AnkiExportSession.generate_timestamped_name(base_name)
        
        # Create session
        session = AnkiExportSession(
            name=session_name,
            export_format=request.export_format,
            include_audio=request.include_audio,
            include_images=request.include_images,
            status="draft"
        )
        
        created_session = await service.create_export_session(session)
        
        # TODO: Link cards to session and generate export file
        
        logger.info(f"Created export session: {created_session.id}")
        
        return created_session
        
    except Exception as e:
        logger.error(f"Failed to create export session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export-sessions/{session_id}", response_model=AnkiExportSession)
async def get_export_session(session_id: str):
    """Get an export session by ID."""
    try:
        service = AnkiService()
        session = await service.get_export_session_by_id(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Export session not found")
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get export session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# AI Card Generation
# ============================================================================


class GenerateCardRequest(BaseModel):
    """Request model for AI card generation."""
    source_ids: List[str] = Field(..., description="List of source IDs to use as context")
    user_prompt: str = Field(..., description="User's prompt/instructions for card generation")
    model_id: Optional[str] = Field(None, description="Optional model override")
    num_cards: int = Field(1, min=1, max=10, description="Number of cards to generate")


class GeneratedCardPreview(BaseModel):
    """Preview of an AI-generated card before adding to deck."""
    front: str = Field(..., description="Card front (question/term)")
    back: str = Field(..., description="Card back (answer/definition)")
    notes: Optional[str] = Field(None, description="Additional notes")
    suggested_tags: List[str] = Field(default_factory=list, description="AI-suggested tags")
    source_references: List[str] = Field(default_factory=list, description="Source IDs used")


class GenerateCardResponse(BaseModel):
    """Response containing generated card previews."""
    cards: List[GeneratedCardPreview] = Field(..., description="Generated card previews")
    model_used: str = Field(..., description="Model used for generation")


@router.post("/decks/{deck_id}/generate-cards", response_model=GenerateCardResponse)
async def generate_cards_from_sources(
    deck_id: str,
    request: GenerateCardRequest
):
    """
    Generate Anki flashcards from sources using AI.
    
    This endpoint takes source documents and a user prompt, then uses an AI model
    to generate flashcard content. The generated cards are returned as previews
    for the user to review and edit before adding to the deck.
    """
    logger.info(f"RECEIVED generate-cards request for deck {deck_id}")
    logger.info(f"Request params: sources={request.source_ids}, num_cards={request.num_cards}")
    try:
        logger.info("Initializing AnkiService")
        service = AnkiService()
        logger.info("AnkiService initialized")
        
        # Verify deck exists
        deck = await service.get_deck(deck_id)
        if not deck:
            raise HTTPException(status_code=404, detail="Deck not found")
        
        # Generate cards using AI
        generated_cards = await service.generate_cards_with_ai(
            source_ids=request.source_ids,
            user_prompt=request.user_prompt,
            model_id=request.model_id,
            num_cards=request.num_cards
        )
        
        return GenerateCardResponse(
            cards=generated_cards["cards"],
            model_used=generated_cards["model_used"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate cards: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Anki Insights - Convert Transformation Insights to Cards
# ============================================================================

class InsightCardPreview(BaseModel):
    """Preview of a card from an insight."""
    front: str
    back: str
    notes: Optional[str] = None
    suggested_tags: List[str] = Field(default_factory=list)
    insight_id: str
    insight_type: str


class SourceAnkiInsightsResponse(BaseModel):
    """Response containing Anki card insights for a source."""
    source_id: str
    insights: List[dict]  # List of {insight_id, insight_type, cards: [...]}
    total_cards: int


class NotebookAnkiInsightsResponse(BaseModel):
    """Response containing Anki card insights for a notebook."""
    notebook_id: str
    sources: List[dict]  # List of {source_id, insights: [...], card_count: int}
    total_cards: int


class CreateCardsFromInsightRequest(BaseModel):
    """Request to create Anki cards from an insight."""
    card_indices: Optional[List[int]] = None  # If None, create all cards


@router.get("/sources/{source_id}/anki-insights", response_model=SourceAnkiInsightsResponse)
async def get_source_anki_insights(source_id: str):
    """
    Get all Anki card insights for a source with parsed cards.
    
    This endpoint retrieves transformation insights that contain Anki cards
    (e.g., from "Anki Cards - Dutch A2" transformations) and parses them
    into structured card data.
    """
    try:
        insights_with_cards = await anki_insights_service.get_anki_insights_for_source(source_id)
        
        insights_data = []
        total_cards = 0
        
        for insight, cards in insights_with_cards:
            insights_data.append({
                "insight_id": insight.id,
                "insight_type": insight.insight_type,
                "created": insight.created.isoformat() if insight.created else None,
                "cards": cards,
                "card_count": len(cards)
            })
            total_cards += len(cards)
        
        return SourceAnkiInsightsResponse(
            source_id=source_id,
            insights=insights_data,
            total_cards=total_cards
        )
    except Exception as e:
        logger.error(f"Failed to get Anki insights for source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notebooks/{notebook_id}/anki-insights", response_model=NotebookAnkiInsightsResponse)
async def get_notebook_anki_insights(notebook_id: str):
    """
    Get all Anki card insights for all sources in a notebook.
    
    This endpoint retrieves all transformation insights that contain Anki cards
    from all sources in the notebook, grouped by source.
    """
    try:
        insights_with_cards = await anki_insights_service.get_anki_insights_for_notebook(notebook_id)
        
        # Group by source
        sources_dict = {}
        for insight, source_id, cards in insights_with_cards:
            if source_id not in sources_dict:
                sources_dict[source_id] = {
                    "source_id": source_id,
                    "insights": [],
                    "card_count": 0
                }
            
            sources_dict[source_id]["insights"].append({
                "insight_id": insight.id,
                "insight_type": insight.insight_type,
                "created": insight.created.isoformat() if insight.created else None,
                "cards": cards,
                "card_count": len(cards)
            })
            sources_dict[source_id]["card_count"] += len(cards)
        
        sources_data = list(sources_dict.values())
        total_cards = sum(s["card_count"] for s in sources_data)
        
        return NotebookAnkiInsightsResponse(
            notebook_id=notebook_id,
            sources=sources_data,
            total_cards=total_cards
        )
    except Exception as e:
        logger.error(f"Failed to get Anki insights for notebook {notebook_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/decks/{deck_id}/insights/{insight_id}/create-cards")
async def create_cards_from_insight(
    deck_id: str,
    insight_id: str,
    request: CreateCardsFromInsightRequest
):
    """
    Create Anki cards in a deck from a transformation insight.
    
    This endpoint parses an Anki card insight and creates actual cards in the deck.
    You can optionally specify which cards to create by index.
    """
    try:
        from open_notebook.domain.notebook import SourceInsight
        
        # Get the insight
        insight = await SourceInsight.get(insight_id)
        if not insight:
            raise HTTPException(status_code=404, detail="Insight not found")
        
        # Check if it's an Anki insight
        if not anki_insights_service.is_anki_insight(insight.insight_type):
            raise HTTPException(
                status_code=400, 
                detail=f"Insight type '{insight.insight_type}' is not an Anki card insight"
            )
        
        # Parse cards from insight
        cards = anki_insights_service.parse_cards_from_insight(insight.content)
        if not cards:
            raise HTTPException(status_code=400, detail="No valid cards found in insight")
        
        # Filter by indices if specified
        if request.card_indices is not None:
            cards = [cards[i] for i in request.card_indices if 0 <= i < len(cards)]
        
        # Create the cards with media generation
        anki_service = AnkiService()
        from api.image_service import ImageService
        from api.audio_service import AudioService
        
        image_service = ImageService()
        audio_service = AudioService()
        created_cards = []
        
        for card_data in cards:
            # Create base card
            card = await anki_service.create_card(
                deck_id=deck_id,
                front=card_data.get("front", ""),
                back=card_data.get("back", ""),
                notes=card_data.get("notes"),
                tags=card_data.get("suggested_tags", [])
            )
            
            # Generate image if image_query is provided
            if card_data.get("image_query"):
                try:
                    image_meta = await image_service.search_image(
                        query=card_data["image_query"],
                        provider="unsplash"  # Can be made configurable
                    )
                    if image_meta:
                        await anki_service.set_card_image(str(card.id), image_meta)
                        card.image_metadata = image_meta
                except Exception as e:
                    logger.warning(f"Failed to fetch image for card {card.id}: {e}")
            
            # Generate audio if audio_text is provided
            if card_data.get("audio_text"):
                try:
                    audio_language = card_data.get("audio_language", "nl")
                    # Map language to appropriate voice
                    voice_map = {
                        "nl": "nl_NL-rdh-medium",
                        "nl-BE": "nl_BE-rdh-medium",
                        "en": "en_US-lessac-medium",
                        "es": "es_ES-mls-medium",
                        "fr": "fr_FR-mls-medium",
                        "de": "de_DE-thorsten-medium",
                    }
                    voice = voice_map.get(audio_language, "nl_NL-rdh-medium")
                    
                    audio_meta = await audio_service.generate_reference_audio(
                        text=card_data["audio_text"],
                        card_id=str(card.id),
                        language=audio_language,
                        voice=voice
                    )
                    if audio_meta:
                        await anki_service.set_card_audio(str(card.id), audio_meta)
                        card.audio_metadata = audio_meta
                except Exception as e:
                    logger.warning(f"Failed to generate audio for card {card.id}: {e}")
            
            created_cards.append(card)
        
        return {
            "success": True,
            "cards_created": len(created_cards),
            "cards": [{"id": c.id, "front": c.front} for c in created_cards]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create cards from insight: {e}")
        raise HTTPException(status_code=500, detail=str(e))
