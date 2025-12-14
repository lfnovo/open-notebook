# Anki Feature Ideas & Enhancements

## Planned Features

### AI-Suggested Cards Panel in Notebooks
**Priority:** High  
**Description:** Add a collapsible sidebar panel within the notebook view that displays AI-suggested Anki cards based on the notebook content, with automatic deck recommendations.

**Requirements:**
- Collapsible side panel in notebook detail view
- AI analyzes notebook content and suggests potential flashcards
- Automatic deck recommendation based on:
  - Content difficulty (beginner/intermediate/advanced)
  - Topic/theme detection
  - Existing deck tags and metadata
- Card suggestion includes:
  - Proposed front/back content
  - Recommended deck(s)
  - Confidence score
  - Source reference (which part of notebook)
- User actions:
  - ✓ Add card to suggested deck (or choose different deck)
  - ✗ Dismiss suggestion
  - ✎ Edit before adding
  - 🔄 Request more suggestions
- Persistent suggestion queue per notebook
- Batch operations (add all, dismiss all)

**User Flow:**
1. User opens a notebook
2. Sidebar shows AI-generated card suggestions
3. Each suggestion displays:
   - Card preview (front/back)
   - Recommended deck with reasoning
   - Difficulty indicator
   - Source context
4. User can:
   - Quick-add to recommended deck
   - Edit card details before adding
   - Change target deck
   - Dismiss suggestion
   - Click "Suggest More" for additional cards
5. Suggestions update as notebook content changes

**Technical Considerations:**
- Use streaming/chunking for large notebooks
- Cache suggestions to avoid repeated API calls
- Real-time suggestion generation option
- Smart context window selection (relevant paragraphs)
- Difficulty detection using CEFR or custom model
- Theme/topic classification using embeddings
- Store suggestions temporarily (session or database)

**Related Components:**
- `/notebooks/[id]/page.tsx` - Add collapsible sidebar panel
- New component: `AnkiSuggestionsPanel.tsx`
- `api/anki_service.py` - New method for card suggestions
- `api/routers/anki.py` - New endpoint `/anki/suggestions/generate`
- Leverage existing notebook content retrieval
- Reuse transformation/LLM infrastructure

---

### AI-Assisted Card Creation from Sources
**Priority:** High  
**Description:** When viewing a deck, provide a feature to generate Anki flashcards from stored sources using AI models.

**Requirements:**
- Access source documents from the notebook/sources system
- Allow user to provide context/prompt for card generation
- Use configured language models to generate:
  - Front of card (question/term)
  - Back of card (answer/definition)
  - Optional notes
  - Suggested tags
- Support for multiple sources as context
- Review/edit generated cards before adding to deck
- Batch generation option (create multiple cards at once)

**User Flow:**
1. User is viewing a deck detail page
2. Clicks "Generate Card from Sources" button
3. Dialog opens with:
   - Source selector (from available sources/notebooks)
   - Text input for user prompt/context
   - Model selector (which AI model to use)
   - Preview of selected source content
4. AI generates card based on source + prompt
5. User reviews and can edit the generated card
6. Card is added to the current deck

**Technical Considerations:**
- Leverage existing chat/transformation endpoints
- Create new prompt template for card generation
- Consider CEFR level detection for language learning cards
- Cache frequently used source chunks for performance
- Add card generation history/tracking

**Related Components:**
- `/anki/[deckId]/page.tsx` - Add "Generate from Sources" button
- `api/anki_service.py` - New method for AI card generation
- `api/routers/anki.py` - New endpoint `/anki/decks/{deck_id}/generate-card`
- Reuse source content retrieval from chat system
- Reuse LLM integration from transformations

---

## Future Enhancements

### Spaced Repetition Improvements
- Better SM-2 algorithm implementation
- Custom scheduling preferences per deck
- Study statistics and progress tracking

### Bulk Operations
- Import cards from CSV/JSON
- Bulk edit tags and metadata
- Merge duplicate cards

### Multimedia Support
- Image generation for visual learning
- Audio pronunciation for language cards
- Video embedding support

### Collaboration
- Share decks with other users
- Community deck marketplace
- Collaborative editing

### Analytics
- Learning velocity metrics
- Card difficulty analysis
- Optimal study time recommendations
