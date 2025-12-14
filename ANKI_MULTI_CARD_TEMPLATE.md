# Anki Multi-Card Variation Template

## Overview
The Anki card generation system now supports **multi-card variation templates** that create multiple card types per concept, with automatic media generation (images and audio).

## Changes Implemented

### 1. Updated Prompt Templates
All Anki transformation prompts now include multi-card variation instructions:

- **`anki_transformation_dutch_a2.jinja`**: 2-4 variations per word (10-20 cards total)
- **`anki_transformation_dutch_b1.jinja`**: 3-5 variations per concept (15-25 cards)
- **`anki_transformation_dutch_b2.jinja`**: 3-5 variations per concept (15-25 cards)
- **`anki_transformation_dutch_c1.jinja`**: 3-5 variations per concept (15-25 cards)
- **`anki_transformation_dutch_c2.jinja`**: 3-5 variations per concept (15-25 cards)
- **`anki_card_generation.jinja`**: General template with variation strategy

### 2. Card Variation Types

Each concept can be explored through multiple angles:

#### Core Variations (All Levels)
1. **Translation Card**: Direct Dutch ↔ English translation
   - Tag: `"translation"`
   - Example: *"Wat betekent 'verhuizen' in het Engels?"* → *"to move (house), to relocate"*

2. **Visual Context Card**: Scenario-based word recognition
   - Tag: `"visual-context"`
   - Example: *"Je ziet dozen, een verhuiswagen... Welk werkwoord?"* → *"verhuizen"*
   - Media: `image_query` field for relevant images

3. **Word Family Card**: Related words and derivatives
   - Tag: `"word-family"`
   - Example: *"Verwante woorden van 'verhuizen'?"* → *"de verhuizing, de verhuizer, het verhuisbedrijf..."*

4. **Conversation Card**: Fill-in-the-blank or dialogue
   - Tag: `"conversation"`
   - Example: *"Wanneer ben je ___?"* → *"aan het verhuizen"*
   - Media: `audio_text` for natural pronunciation

5. **Collocations Card**: Correct prepositions/articles
   - Tag: `"collocations"`
   - Example: *"verhuizen ___ een nieuwe stad"* → *"naar"*

#### Advanced Variations (B2+)
6. **False Friends Card**: Warn about misleading similarities
   - Tag: `"false-friends"`
   - Example: *"'verhuizen' betekent NIET 'to house'..."*

7. **Synonyms/Register Card**: Formality levels and alternatives
   - Tag: `"synonyms"` or `"register"`
   - Example: *"Formeler synoniem voor 'verhuizen'?"* → *"verplaatsen, domicilie verplaatsen"*

8. **Homonyms/Confusables Card**: Sound-alike distinctions
   - Tag: `"homonyms"` or `"confusables"`
   - Example: *"Verschil tussen 'verhuizen' en 'verhuren'?"*

#### Specialized Variations (C1/C2)
- **Professional Context**: Field-specific usage (legal, medical, academic)
- **Historical Context**: Etymology and semantic evolution
- **Regional Variation**: Belgian vs Netherlands Dutch

### 3. Media Enhancement Fields

Each card can now include:

```json
{
  "front": "Question or prompt",
  "back": "Answer",
  "notes": "Additional context",
  "suggested_tags": ["dutch", "B2", "translation", "housing"],
  "image_query": "moving house boxes truck",  // ← Search term for Unsplash/Pexels/Pixabay
  "audio_text": "verhuizen",                   // ← Text to synthesize with Piper TTS
  "audio_language": "nl"                       // ← Language code (nl, nl-BE, en, etc.)
}
```

### 4. Automatic Media Generation

When cards are created from insights via `/decks/{deck_id}/insights/{insight_id}/create-cards`:

1. **Image Generation**:
   - If `image_query` field present → calls `ImageService.search_image()`
   - Fetches from Unsplash (default), Pexels, or Pixabay
   - Caches image with attribution
   - Attaches `ImageMetadata` to card

2. **Audio Generation**:
   - If `audio_text` field present → calls `AudioService.generate_reference_audio()`
   - Uses Piper TTS with appropriate voice model
   - Generates IPA transcription
   - Saves MP3 file in `data/anki_data/audio/`
   - Attaches `AudioMetadata` to card

3. **Voice Model Mapping**:
   ```python
   {
       "nl": "nl_NL-rdh-medium",      # Netherlands Dutch
       "nl-BE": "nl_BE-rdh-medium",   # Belgian Dutch
       "en": "en_US-lessac-medium",   # English
       "es": "es_ES-mls-medium",      # Spanish
       "fr": "fr_FR-mls-medium",      # French
       "de": "de_DE-thorsten-medium"  # German
   }
   ```

## Example Output Structure

A transformation insight for the word "verhuizen" now generates:

```json
[
  {
    "front": "Wat betekent 'verhuizen' in het Engels?",
    "back": "to move (house), to relocate",
    "notes": "Common verb. Present: ik verhuis. Past: ik verhuisde.",
    "suggested_tags": ["dutch", "B2", "verbs", "housing", "translation"],
    "audio_text": "verhuizen",
    "audio_language": "nl"
  },
  {
    "front": "Je ziet dozen, een verhuiswagen en mensen die meubels dragen. Welk werkwoord past hierbij?",
    "back": "verhuizen",
    "notes": "Visual context: moving house scenario.",
    "suggested_tags": ["dutch", "B2", "visual-context", "housing"],
    "image_query": "moving house boxes truck furniture"
  },
  {
    "front": "Wat zijn verwante woorden van 'verhuizen'?",
    "back": "de verhuizing, de verhuizer, het verhuisbedrijf, de verhuiswagen",
    "notes": "Word family: verhuis- prefix.",
    "suggested_tags": ["dutch", "B2", "word-family", "housing"]
  },
  // ... 5-8 cards total per concept
]
```

## Benefits

1. **Comprehensive Learning**: Multiple angles of the same concept (recognition, production, context, usage)
2. **Rich Media**: Automatic images and audio for visual/auditory learners
3. **Scalability**: 15-25 cards per transformation (vs 3-5 before) = 3-5x content generation
4. **Better Retention**: Varied card types prevent memorization of card format
5. **Context-Rich**: Images reinforce meaning, audio supports pronunciation
6. **Flexible Tagging**: Variation type tags enable filtering by learning style

## Usage

### Creating Cards from Existing Insights
1. Go to deck detail page: `/anki/{deckId}`
2. Select a notebook with processed sources
3. View Anki transformation insights
4. Click "Create Cards" → System generates cards with media

### Testing Multi-Card Template
See [`create_dutch_cards.py`](./create_dutch_cards.py) for a manual example creating 8 variation types for "verhuizen".

### Next Steps
1. Process a source with updated Anki transformation (e.g., Dutch B2)
2. Review generated insights to verify 15-25 cards with media fields
3. Create cards from insight → verify images and audio are attached
4. Export to `.apkg` and test in Anki desktop/mobile

## Technical Details

### Services Used
- **`AnkiService`**: Card CRUD operations
- **`ImageService`**: Unsplash/Pexels/Pixabay API integration with 7-day cache
- **`AudioService`**: Piper TTS + Whisper STT + phonemizer (IPA transcription)
- **`AnkiInsightsService`**: Parses transformation insights into card data

### API Endpoint
```
POST /anki/decks/{deck_id}/insights/{insight_id}/create-cards
```

Enhanced to:
- Parse `image_query`, `audio_text`, `audio_language` from card data
- Call image/audio services asynchronously
- Attach media to cards via `set_card_image()` and `set_card_audio()`
- Log warnings if media generation fails (doesn't block card creation)

### Error Handling
- Media generation failures are non-fatal (logged as warnings)
- Cards still created even if image/audio fails
- Provides graceful degradation for API rate limits or service unavailability
