# OSS-136 Epic: Podcast Engine + Background Infrastructure - Architecture

## 🏗️ High-Level System Architecture

### Current State (Before Changes)
```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                Current System                                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Streamlit UI (pages/5_🎙️_Podcasts.py)                                              │
│ ├─ Complex 15+ field forms                                                         │
│ ├─ Synchronous processing (blocks UI)                                              │
│ └─ Direct podcast generation call                                                  │
│                                                                                     │
│ Domain Layer (open_notebook/plugins/podcasts.py)                                   │
│ ├─ PodcastConfig (complex model)                                                   │
│ ├─ PodcastEpisode (simple model)                                                   │
│ └─ Direct podcastfy library usage                                                  │
│                                                                                     │
│ Database (SurrealDB)                                                               │
│ ├─ podcast_config (schemaless, complex)                                            │
│ └─ podcast_episode (basic fields)                                                  │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Target State (After Implementation)
```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           New Podcast Engine System                                │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Streamlit UI (Simplified)                                                          │
│ ├─ Episode Profile selector (3-click workflow)                                     │
│ ├─ Basic job status display                                                        │
│ └─ Non-blocking async submission                                                   │
│                                                                                     │
│ FastAPI Layer (New)                                                                │
│ ├─ POST /api/podcasts/generate                                                     │
│ ├─ GET /api/podcasts/jobs/{job_id}                                                 │
│ ├─ GET /api/episode-profiles                                                       │
│ └─ GET /api/speaker-profiles                                                       │
│                                                                                     │
│ Service Layer (New)                                                                │
│ ├─ PodcastService (async operations)                                               │
│ ├─ EpisodeProfileService (profile management)                                      │
│ └─ SpeakerProfileService (speaker management)                                      │
│                                                                                     │
│ Background Processing (New)                                                        │
│ ├─ Surreal-Commands Worker                                                         │
│ ├─ Podcast-Creator Integration                                                     │
│ └─ LangGraph Workflow                                                              │
│                                                                                     │
│ Database (Enhanced)                                                                │
│ ├─ episode_profile (new schema)                                                    │
│ ├─ speaker_profile (new schema)                                                    │
│ ├─ podcast_episode (enhanced)                                                      │
│ ├─ command (surreal-commands)                                                      │
│ └─ podcast_config (legacy, for migration)                                          │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## 🔄 Phase-by-Phase Architecture

### Phase 1: Async Foundation (OSS-137)

#### 1.1 Surreal-Commands Integration
```python
# New: api/commands/podcast_commands.py
from surreal_commands import command
from pydantic import BaseModel
from typing import Optional

class PodcastGenerationInput(BaseModel):
    notebook_id: str
    episode_profile_name: str
    episode_name: str
    briefing_suffix: Optional[str] = None

class PodcastGenerationOutput(BaseModel):
    success: bool
    episode_id: str
    audio_file_path: Optional[str]
    error_message: Optional[str]

@command("generate_podcast")
async def generate_podcast_command(
    input_data: PodcastGenerationInput
) -> PodcastGenerationOutput:
    # Integration with podcast-creator library
    # Return structured results
    pass
```

#### 1.2 Worker Process Integration
```bash
# supervisord.conf addition
[program:worker]
command=uv run --env-file .env python -m surreal_commands.worker
environment=SURREAL_COMMANDS_MODULES="api.commands.podcast_commands"
stdout_logfile=/dev/stdout
stderr_logfile=/dev/stderr
autorestart=true
```

#### 1.3 FastAPI Job Management
```python
# New: api/routers/podcasts.py
from fastapi import APIRouter, HTTPException
from surreal_commands import submit_command, get_command_status

router = APIRouter()

@router.post("/podcasts/generate")
async def generate_podcast(request: PodcastGenerationRequest):
    cmd_id = submit_command(
        "api.commands.podcast_commands",
        "generate_podcast",
        request.model_dump()
    )
    return {"job_id": cmd_id, "status": "submitted"}

@router.get("/podcasts/jobs/{job_id}")
async def get_podcast_job_status(job_id: str):
    status = await get_command_status(job_id)
    return {"job_id": job_id, "status": status.status, "result": status.result}
```

### Phase 2: Engine Integration (OSS-138)

#### 2.1 Episode Profile Models
```python
# New: open_notebook/domain/podcast.py
from typing import ClassVar, Optional
from pydantic import Field
from open_notebook.domain.base import ObjectModel

class EpisodeProfile(ObjectModel):
    table_name: ClassVar[str] = "episode_profile"
    name: str
    description: Optional[str] = None
    speaker_config: str  # Reference to speaker profile
    outline_provider: str
    outline_model: str
    transcript_provider: str
    transcript_model: str
    default_briefing: str
    num_segments: int = Field(default=5)
    migrated_from_podcast_config: Optional[str] = None

class SpeakerProfile(ObjectModel):
    table_name: ClassVar[str] = "speaker_profile"
    name: str
    description: Optional[str] = None
    tts_provider: str
    tts_model: str
    speakers: list  # Array of speaker objects
    migrated_from_podcast_config: Optional[str] = None

class PodcastEpisode(ObjectModel):
    table_name: ClassVar[str] = "podcast_episode"
    name: str
    episode_profile: str  # Reference to episode profile used
    generation_metadata: dict  # Store generation parameters
    text: str
    audio_file: str
    command: Optional[str] = None  # Link to surreal-commands job
```

#### 2.2 Podcast-Creator Integration
```python
# Enhanced: api/commands/podcast_commands.py
from podcast_creator import create_podcast, configure
from open_notebook.domain.podcast import EpisodeProfile, SpeakerProfile
from open_notebook.domain.notebook import Notebook

@command("generate_podcast")
async def generate_podcast_command(
    input_data: PodcastGenerationInput
) -> PodcastGenerationOutput:
    try:
        # Load episode profile
        episode_profile = await EpisodeProfile.get_by_name(input_data.episode_profile_name)
        speaker_profile = await SpeakerProfile.get_by_name(episode_profile.speaker_config)
        
        # Get notebook context
        notebook = await Notebook.get_by_id(input_data.notebook_id)
        context = await notebook.get_context()
        
        # Configure podcast-creator
        configure("speakers_config", {
            "profiles": {
                speaker_profile.name: {
                    "tts_provider": speaker_profile.tts_provider,
                    "tts_model": speaker_profile.tts_model,
                    "speakers": speaker_profile.speakers
                }
            }
        })
        
        # Generate briefing
        briefing = episode_profile.default_briefing
        if input_data.briefing_suffix:
            briefing += f"\n\n{input_data.briefing_suffix}"
        
        # Create podcast
        result = await create_podcast(
            content=str(context),
            briefing=briefing,
            episode_name=input_data.episode_name,
            output_dir=f"data/podcasts/episodes/{input_data.episode_name}",
            speaker_config=speaker_profile.name,
            outline_provider=episode_profile.outline_provider,
            outline_model=episode_profile.outline_model,
            transcript_provider=episode_profile.transcript_provider,
            transcript_model=episode_profile.transcript_model,
            num_segments=episode_profile.num_segments
        )
        
        # Save episode record
        episode = PodcastEpisode(
            name=input_data.episode_name,
            episode_profile=episode_profile.name,
            generation_metadata={
                "briefing": briefing,
                "context_size": len(str(context)),
                "num_segments": episode_profile.num_segments
            },
            text=str(context),
            audio_file=result["final_output_file_path"]
        )
        await episode.save()
        
        return PodcastGenerationOutput(
            success=True,
            episode_id=episode.id,
            audio_file_path=result["final_output_file_path"]
        )
        
    except Exception as e:
        return PodcastGenerationOutput(
            success=False,
            episode_id=None,
            error_message=str(e)
        )
```

### Phase 3: UI Modernization (OSS-139)

#### 3.1 Simplified Streamlit Interface
```python
# Enhanced: pages/5_🎙️_Podcasts.py
import asyncio
import streamlit as st
from open_notebook.domain.podcast import EpisodeProfile, SpeakerProfile, PodcastEpisode
from api.podcast_service import PodcastService

# Simple episode profile selector
episode_profiles = asyncio.run(EpisodeProfile.get_all())
profile_names = [ep.name for ep in episode_profiles]

selected_profile = st.selectbox("Choose Episode Profile", profile_names)
episode_name = st.text_input("Episode Name")
briefing_suffix = st.text_area("Additional Instructions (optional)")

if st.button("Generate Podcast"):
    # Submit async job
    job_id = await PodcastService.submit_generation_job(
        notebook_id=st.session_state.current_notebook_id,
        episode_profile_name=selected_profile,
        episode_name=episode_name,
        briefing_suffix=briefing_suffix
    )
    st.success(f"Podcast generation started. Job ID: {job_id}")

# Display episodes with job status
episodes = asyncio.run(PodcastEpisode.get_all_with_job_status())
for episode in episodes:
    with st.container():
        st.write(f"**{episode.name}** - Status: {episode.job_status}")
        if episode.job_status == "completed":
            st.audio(episode.audio_file)
```

#### 3.2 Episode Profile Management
```python
# New: pages/components/episode_profile_manager.py
class EpisodeProfileManager:
    @staticmethod
    def create_default_profiles():
        """Create default episode profiles for common use cases"""
        profiles = [
            {
                "name": "tech_discussion",
                "description": "Technical discussion between experts",
                "speaker_config": "tech_experts",
                "default_briefing": "Create an engaging technical discussion about the provided content..."
            },
            {
                "name": "solo_expert",
                "description": "Single expert explaining complex topics",
                "speaker_config": "solo_expert",
                "default_briefing": "Explain the content in an accessible, educational way..."
            },
            # More profiles...
        ]
        return profiles
```

### Phase 4: Data Migration (OSS-141)

#### 4.1 Migration Strategy
```python
# New: migrations/7.surrealql (handled by Luis)
# Create new tables
DEFINE TABLE episode_profile SCHEMAFULL;
DEFINE TABLE speaker_profile SCHEMAFULL;
# ... field definitions

# Migration script (handled by Luis)
# Translate old podcast_config fields to new format
# Create default profiles based on common configurations
```

## 🔗 Component Dependencies & Relationships

### External Dependencies
```toml
# pyproject.toml additions
dependencies = [
    "surreal-commands>=1.0.0",
    "podcast-creator>=0.2.0",
    # ... existing dependencies
]
```

### Internal Component Flow
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit UI  │───▶│   FastAPI       │───▶│   Service       │
│   (3-click)     │    │   (async)       │    │   Layer         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   SurrealDB     │◀───│   Background    │◀───│   Surreal-      │
│   (job status)  │    │   Worker        │    │   Commands      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │   Podcast-      │
                        │   Creator       │
                        │   (LangGraph)   │
                        └─────────────────┘
```

## 🎯 Design Patterns & Best Practices

### 1. Async-First Architecture
- All new components use async/await patterns
- Consistent with existing codebase patterns
- Non-blocking UI experience

### 2. Domain-Driven Design
- Clear separation: Domain models, Service layer, API layer
- Follows existing `ObjectModel` patterns
- Consistent with current architecture

### 3. Command Pattern
- Surreal-commands for background processing
- Structured input/output models
- Error handling and status tracking

### 4. Configuration Management
- Episode Profiles for simplified user experience
- Speaker Profiles for reusable voice configurations
- Migration-friendly design

## 📁 File Structure & Modifications

### New Files to Create
```
api/
├── commands/
│   └── podcast_commands.py          # Surreal-commands integration
├── routers/
│   └── podcasts.py                  # FastAPI podcast endpoints
└── podcast_service.py               # Service layer for podcast operations

open_notebook/
└── domain/
    └── podcast.py                   # New domain models (Episode/Speaker Profiles)

supervisord.conf                     # Add worker process configuration
```

### Files to Modify
```
api/main.py                          # Add podcast router
pages/5_🎙️_Podcasts.py               # Simplified UI implementation
open_notebook/plugins/podcasts.py    # Enhanced with new models
```

### Files to Migrate (Phase 4)
```
migrations/7.surrealql               # New schema (handled by Luis)
migrations/7_down.surrealql          # Rollback script
```

## ⚡ Performance & Scalability

### Async Processing Benefits
- **Non-blocking UI**: Users can continue working while podcasts generate
- **Scalable Design**: Foundation for future background processing
- **Resource Management**: Worker process isolation

### Database Optimization
- **Structured Schema**: Move from schemaless to schemafull for better performance
- **Efficient Queries**: Profile-based lookups vs complex configuration parsing
- **Status Tracking**: Simple relationship-based job status

## 🛡️ Error Handling & Monitoring

### Command Error Handling
```python
@command("generate_podcast")
async def generate_podcast_command(input_data: PodcastGenerationInput):
    try:
        # ... podcast generation logic
        return PodcastGenerationOutput(success=True, ...)
    except ValidationError as e:
        return PodcastGenerationOutput(success=False, error_message=f"Invalid input: {e}")
    except Exception as e:
        logger.error(f"Podcast generation failed: {e}")
        return PodcastGenerationOutput(success=False, error_message=str(e))
```

### Status Monitoring
- Command status tracking via surreal-commands
- Simple UI updates through database relationships
- Structured error messages for debugging

## 🔄 Migration Strategy

### Backward Compatibility
- Existing `podcast_config` table remains during migration
- Gradual migration of user configurations
- Fallback mechanisms for legacy data

### Data Translation
- Old configuration fields mapped to new Episode Profile format
- Default profiles created for common use cases
- Migration script handles complex configurations

This architecture provides a solid foundation for the podcast engine while maintaining consistency with existing codebase patterns and ensuring a smooth migration path.