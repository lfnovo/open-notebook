# Anki Backend Test Coverage

## Test File Created
- `tests/test_anki.py` - 569 lines of comprehensive unit tests for Anki domain models

## Test Coverage Summary

### 1. AnkiCard Validation (11 tests)
- ✅ Valid card creation with minimal fields
- ✅ Valid card creation with all optional fields
- ✅ Empty front/back validation errors
- ✅ Whitespace-only front/back validation errors
- ✅ CEFR level normalization (lowercase → uppercase)
- ✅ Invalid CEFR level validation (must be A1-C2)
- ✅ All valid CEFR levels accepted
- ✅ Audio expiry check (not expired)
- ✅ Audio expiry check (expired)
- ✅ Audio expiry check (no audio metadata)

### 2. AnkiDeck Validation (4 tests)
- ✅ Valid deck creation
- ✅ Deck creation with all fields (description, tags, metadata)
- ✅ Empty deck name validation error
- ✅ Whitespace-only deck name validation error

### 3. AnkiExportSession (3 tests)
- ✅ Export session creation with all fields
- ✅ Timestamped name generation format
- ✅ Export session with custom settings (audio/images toggles)

### 4. CEFR Vote (2 tests)
- ✅ CEFR vote creation with reasoning
- ✅ CEFR vote without reasoning (optional)

### 5. Source Citation (3 tests)
- ✅ Citation creation with page number and context
- ✅ Automatic timestamp generation
- ✅ Citation with only required source_id

### 6. Image Metadata (2 tests)
- ✅ Image metadata from external API (Unsplash/Pexels)
- ✅ Image metadata from user upload

### 7. Audio Metadata (2 tests)
- ✅ Audio metadata with reference MP3 and IPA
- ✅ Audio metadata with user recordings and phonetic scores

### 8. Dutch Word Frequency (2 tests)
- ✅ Word frequency entry creation
- ✅ Frequency/rank correlation (high freq = low rank)

### 9. Image Cache (4 tests)
- ✅ Image cache entry creation
- ✅ Default cache expiry (7 days)
- ✅ Access tracking fields (count, last_accessed)
- ✅ LRU access count increment

### 10. AnkiCardEdit (2 tests)
- ✅ Card edit history creation with changes
- ✅ Card edit without user attribution (optional)

### 11. Integration Tests (2 tests)
- ✅ Complete card workflow with all features (citation, image, audio, CEFR votes)
- ✅ Deck with multiple CEFR levels (A1, B1, C2)

## Total Test Count: 37 tests

## Running the Tests

Since the project uses Docker for development, tests should be run inside the container:

```bash
# Using docker-compose
docker-compose -f docker-compose.dev.yml run --rm api pytest tests/test_anki.py -v

# Or if using single container
docker-compose -f docker-compose.single.yml run --rm open-notebook pytest tests/test_anki.py -v
```

For local development with dependencies installed:
```bash
pip install -e ".[dev]"
pytest tests/test_anki.py -v
```

## Test Coverage Notes

### What's Tested
- **Domain model validation**: All Pydantic validators and business logic
- **Field constraints**: Empty/whitespace checks, CEFR level normalization
- **Business logic**: Audio expiry, cache expiry defaults, timestamp generation
- **Integration**: Complete workflows with multiple related models

### What's NOT Tested (requires mocking/integration tests)
- Database operations (CRUD via SurrealDB)
- External API calls (Unsplash, Pexels, Pixabay)
- LLM model calls (CEFR classification voting)
- Audio generation (Whisper, Piper services)
- File system operations (cache management)
- Phonemizer/espeak-ng integration

### Next Steps for Testing
1. Add service layer tests with mocked database
2. Add CEFR service tests with mocked LLM responses
3. Add image service tests with mocked HTTP calls
4. Add integration tests with test database
5. Add API endpoint tests with FastAPI TestClient
