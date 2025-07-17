# OSS-136 Epic: Podcast Engine + Background Infrastructure - Context

## 🎯 Project Vision
Create a proprietary podcast generation engine that serves as Open Notebook's competitive differentiator against Google Notebook LM, while establishing the foundation for all background processing using proven open-source libraries.

## 📋 Current Implementation Analysis

### Existing System (to be replaced)
- **Technology**: Uses `podcastfy` library (synchronous)
- **Database**: `podcast_config` (complex 15+ fields) and `podcast_episode` tables
- **UI**: Complex Streamlit forms with manual field configuration
- **Processing**: Synchronous - blocks UI during generation
- **Location**: `open_notebook/plugins/podcasts.py` and `pages/5_🎙️_Podcasts.py`

### Key Current Features
- Multiple TTS providers (OpenAI, Anthropic, Google, ElevenLabs)
- Detailed speaker configuration (roles, personalities, voices)
- Conversation styles and dialogue structures
- Episode management and audio playback

## 🚀 Strategic Value & Competitive Advantages

### Democratization Impact
- **User Choice**: Flexible 1-4 speakers vs Google's fixed 2-host format
- **Model Freedom**: User selects LLM + TTS providers via Esperanto integration
- **Local Privacy**: Complete support for local audio models and processing
- **Customization**: Rich speaker personalities, backstories, and editable prompts

### Technical Foundation
- **Battle-tested Infrastructure**: Proven surreal-commands for background processing
- **Professional Engine**: Production-ready podcast-creator library with advanced features
- **Ecosystem Consistency**: LangChain Runnable patterns across all async operations
- **Scalable Architecture**: Foundation for Content Composer, Deep Research, and future workflows

## 🔄 Implementation Strategy (Updated Based on Clarifications)

### Phase 1: Async Foundation (OSS-137)
- **Technology**: Surreal-commands integration in same container
- **Worker**: Single worker using existing supervisord.conf
- **Processing**: Async job queue with SurrealDB backend
- **Status**: Simple status via podcast_episode → command relationship

### Phase 2: Engine Integration (OSS-138)
- **Technology**: Podcast-creator library with Episode Profiles
- **Migration**: From 15+ fields to simplified 3-click workflow
- **Compatibility**: Translation of old fields into new system (briefing concatenation)
- **Profiles**: Default Episode and Speaker profiles for common use cases

### Phase 3: UI Modernization (OSS-139)
- **Focus**: Simplified Episode Profile selector + basic job status
- **Approach**: Build UI after async foundation is ready
- **No**: Real-time updates, WebSockets, complex status tracking
- **Yes**: Simple page refresh for status updates, preparing for React migration

### Phase 4: Data Migration (OSS-141)
- **Timing**: Last phase, handled in parallel by Luis
- **Strategy**: Automatic translation of existing configs to Episode Profiles
- **Compatibility**: Heavy customizations handled by migration script
- **Database**: New tables for episode_profile and speaker_profile

## 🔧 Technical Architecture

### New Database Schema (Migration 7)
```sql
-- episode_profile table
DEFINE TABLE episode_profile SCHEMAFULL;
DEFINE FIELD name ON TABLE episode_profile TYPE string;
DEFINE FIELD description ON TABLE episode_profile TYPE option<string>;
DEFINE FIELD speaker_config ON TABLE episode_profile TYPE string;
DEFINE FIELD outline_provider ON TABLE episode_profile TYPE string;
DEFINE FIELD outline_model ON TABLE episode_profile TYPE string;
DEFINE FIELD transcript_provider ON TABLE episode_profile TYPE string;
DEFINE FIELD transcript_model ON TABLE episode_profile TYPE string;
DEFINE FIELD default_briefing ON TABLE episode_profile TYPE string;
DEFINE FIELD num_segments ON TABLE episode_profile TYPE int;

-- speaker_profile table
DEFINE TABLE speaker_profile SCHEMAFULL;
DEFINE FIELD name ON TABLE speaker_profile TYPE string;
DEFINE FIELD tts_provider ON TABLE speaker_profile TYPE string;
DEFINE FIELD tts_model ON TABLE speaker_profile TYPE string;
DEFINE FIELD speakers ON TABLE speaker_profile TYPE array;
```

### Component Integration
- **Surreal-Commands**: Async job processing with SurrealDB LIVE queries
- **Podcast-Creator**: Episode Profiles with LangGraph workflow
- **FastAPI**: New async endpoints for podcast generation
- **Streamlit**: Simplified UI with Episode Profile selection

### Worker Architecture
- **Container**: Same container as main app
- **Supervisor**: Existing supervisord.conf with new worker service
- **Scalability**: Single worker only (surreal-commands current limitation)
- **Processing**: Background job queue with status tracking

## 🎯 Success Metrics

### Technical Metrics
- **Generation Time**: ~2-3 minutes for professional quality
- **Concurrency**: Non-blocking UI during generation
- **Flexibility**: 1-4 speaker support vs Google's 2-host limit
- **Quality**: Professional podcast output with rich speaker personalities

### User Experience Metrics
- **Simplicity**: 3-click workflow (profile → name → generate)
- **Accessibility**: Episode Profiles for non-technical users
- **Transparency**: Clear job status without complex real-time updates
- **Flexibility**: Custom profiles for advanced users

## 📝 Implementation Notes

### Constraints
- **No Tests**: Testing will be handled in separate epic
- **No Real-time**: Simple refresh-based status updates in Streamlit
- **Single Worker**: Current surreal-commands limitation
- **Migration**: Luis will handle DB schema and migration scripts

### Dependencies
- **Libraries**: surreal-commands and podcast-creator already proven
- **Integration**: Esperanto for multi-provider support
- **Infrastructure**: Existing SurrealDB and supervisord setup
- **Migration**: Database schema changes handled in parallel

### Key Files to Modify/Create
- `api/routers/podcasts.py` - New FastAPI endpoints
- `api/podcast_service.py` - Service layer for async operations
- `pages/5_🎙️_Podcasts.py` - Simplified UI with Episode Profiles
- `open_notebook/plugins/podcasts.py` - Updated models and logic
- `supervisord.conf` - Worker process configuration
- Migration scripts (handled by Luis)

This implementation will establish Open Notebook as a superior alternative to Google Notebook LM while creating a robust foundation for future async processing features.