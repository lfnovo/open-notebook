# OSS-136 Epic: Podcast Engine + Background Infrastructure - Implementation Plan

## Overview

This plan breaks down the implementation of the new podcast engine and background infrastructure into manageable phases of approximately 3-4 hours each. Each phase is designed to be independent, testable, and builds upon the previous phase to create a competitive advantage against Google Notebook LM.

**Total Estimated Time**: 14-16 hours across 4 phases
**Risk Level**: Medium (new async architecture with proven libraries)
**Rollback Strategy**: Independent commits for each phase
**Dependencies**: surreal-commands, podcast-creator (both proven libraries)

**Strategic Goal**: Create 1-4 speaker flexibility vs Google's 2-host limitation with simplified Episode Profile workflow

---

## Phase 1: Async Foundation (OSS-137) - 4 hours

Surreal Commands Library: https://github.com/lfnovo/surreal-commands
Also available in Context7 and on /Users/luisnovo/dev/projetos/surreal-commands/surreal-commands

### 🎯 Goals
- Integrate surreal-commands for background job processing
- Create generic command infrastructure with example commands
- Set up worker process in existing container using supervisord
- Add Makefile command to start worker in dev environment
- Establish command-based architecture foundation for all future background processing

### 📁 Files to Create/Change
1. **NEW**: `commands/example_commands.py` - Generic command examples for testing (moved from /api/commands)
2. **NEW**: `commands/__init__.py` - Commands module initialization
3. **NEW**: `api/routers/commands.py` - Generic command execution endpoints
4. **NEW**: `api/command_service.py` - Generic service layer for command operations
5. **MODIFY**: `api/main.py` - Add commands router and import commands module
6. **MODIFY**: `supervisord.conf` - Add worker process
7. **MODIFY**: `pyproject.toml` - Add surreal-commands dependency
8. **MODIFY**: `Makefile` - Add worker start/stop/restart commands
9. **NEW**: `test_commands.sh` - Testing script for manual verification

### 🔧 Specific Implementation Steps

#### 1.1 Add Dependencies
```toml
# pyproject.toml - Add to dependencies array
dependencies = [
    # ... existing dependencies
    "surreal-commands>=1.0.7",
]
```

#### 1.2 Create Generic Command Infrastructure
```python
# commands/__init__.py
"""Surreal-commands integration for Open Notebook"""

# commands/example_commands.py
from surreal_commands import command
from pydantic import BaseModel
from typing import Optional, List
from loguru import logger
import asyncio
import time

class TextProcessingInput(BaseModel):
    text: str
    operation: str = "uppercase"  # uppercase, lowercase, word_count, reverse
    delay_seconds: Optional[int] = None  # For testing async behavior

class TextProcessingOutput(BaseModel):
    success: bool
    original_text: str
    processed_text: Optional[str] = None
    word_count: Optional[int] = None
    processing_time: float
    error_message: Optional[str] = None

class DataAnalysisInput(BaseModel):
    numbers: List[float]
    analysis_type: str = "basic"  # basic, detailed
    delay_seconds: Optional[int] = None

class DataAnalysisOutput(BaseModel):
    success: bool
    analysis_type: str
    count: int
    sum: Optional[float] = None
    average: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    processing_time: float
    error_message: Optional[str] = None

@command("process_text", app="open_notebook")
async def process_text_command(input_data: TextProcessingInput) -> TextProcessingOutput:
    """
    Example command for text processing. Tests basic command functionality
    and demonstrates different processing types.
    """
    start_time = time.time()
    
    try:
        logger.info(f"Processing text with operation: {input_data.operation}")
        
        # Simulate processing delay if specified
        if input_data.delay_seconds:
            await asyncio.sleep(input_data.delay_seconds)
        
        processed_text = None
        word_count = None
        
        if input_data.operation == "uppercase":
            processed_text = input_data.text.upper()
        elif input_data.operation == "lowercase":
            processed_text = input_data.text.lower()
        elif input_data.operation == "reverse":
            processed_text = input_data.text[::-1]
        elif input_data.operation == "word_count":
            word_count = len(input_data.text.split())
            processed_text = f"Word count: {word_count}"
        else:
            raise ValueError(f"Unknown operation: {input_data.operation}")
        
        processing_time = time.time() - start_time
        
        return TextProcessingOutput(
            success=True,
            original_text=input_data.text,
            processed_text=processed_text,
            word_count=word_count,
            processing_time=processing_time
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Text processing failed: {e}")
        return TextProcessingOutput(
            success=False,
            original_text=input_data.text,
            processing_time=processing_time,
            error_message=str(e)
        )

@command("analyze_data", app="open_notebook")
async def analyze_data_command(input_data: DataAnalysisInput) -> DataAnalysisOutput:
    """
    Example command for data analysis. Tests command with complex input/output
    and demonstrates error handling.
    """
    start_time = time.time()
    
    try:
        logger.info(f"Analyzing {len(input_data.numbers)} numbers with {input_data.analysis_type} analysis")
        
        # Simulate processing delay if specified
        if input_data.delay_seconds:
            await asyncio.sleep(input_data.delay_seconds)
        
        if not input_data.numbers:
            raise ValueError("No numbers provided for analysis")
        
        count = len(input_data.numbers)
        sum_value = sum(input_data.numbers)
        average = sum_value / count
        min_value = min(input_data.numbers)
        max_value = max(input_data.numbers)
        
        processing_time = time.time() - start_time
        
        return DataAnalysisOutput(
            success=True,
            analysis_type=input_data.analysis_type,
            count=count,
            sum=sum_value,
            average=average,
            min_value=min_value,
            max_value=max_value,
            processing_time=processing_time
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Data analysis failed: {e}")
        return DataAnalysisOutput(
            success=False,
            analysis_type=input_data.analysis_type,
            count=0,
            processing_time=processing_time,
            error_message=str(e)
        )
```

#### 1.3 Create Generic Command Service Layer
```python
# api/command_service.py
from typing import List, Optional, Dict, Any
from loguru import logger
from surreal_commands import submit_command, get_command_status
from api.models import ErrorResponse

class CommandService:
    """Generic service layer for command operations"""
    
    @staticmethod
    async def submit_command_job(
        module_name: str,
        command_name: str,
        command_args: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Submit a generic command job for background processing"""
        try:
            cmd_id = submit_command(
                module_name,
                command_name,
                command_args,
                context=context
            )
            logger.info(f"Submitted command job: {cmd_id} for {module_name}.{command_name}")
            return cmd_id
            
        except Exception as e:
            logger.error(f"Failed to submit command job: {e}")
            raise
    
    @staticmethod
    async def get_command_status(job_id: str) -> Dict[str, Any]:
        """Get status of any command job"""
        try:
            status = await get_command_status(job_id)
            return {
                "job_id": job_id,
                "status": status.status if status else "unknown",
                "result": status.result if status else None,
                "error_message": status.error_message if status else None,
                "created": str(status.created) if status and status.created else None,
                "updated": str(status.updated) if status and status.updated else None,
                "progress": status.progress if status else None
            }
        except Exception as e:
            logger.error(f"Failed to get command status: {e}")
            raise

    @staticmethod
    async def list_command_jobs(
        module_filter: Optional[str] = None,
        command_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List command jobs with optional filtering"""
        # This will be implemented with proper SurrealDB queries
        # For now, return empty list as this is foundation phase
        return []
    
    @staticmethod
    async def cancel_command_job(job_id: str) -> bool:
        """Cancel a running command job"""
        try:
            # Implementation depends on surreal-commands cancellation support
            # For now, just log the attempt
            logger.info(f"Attempting to cancel job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel command job: {e}")
            raise
```

#### 1.4 Create Generic Command Endpoints
```python
# api/routers/commands.py
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from loguru import logger

from api.command_service import CommandService
from api.models import ErrorResponse

router = APIRouter()

class CommandExecutionRequest(BaseModel):
    command: str = Field(..., description="Command function name (e.g., 'process_text')")
    app: str = Field(..., description="Application name (e.g., 'open_notebook')")
    input: Dict[str, Any] = Field(..., description="Arguments to pass to the command")

class CommandJobResponse(BaseModel):
    job_id: str
    status: str
    message: str

class CommandJobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created: Optional[str] = None
    updated: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None

@router.post("/commands/jobs", response_model=CommandJobResponse)
async def execute_command(request: CommandExecutionRequest):
    """
    Submit a command for background processing.
    Returns immediately with job ID for status tracking.
    """
    # parameters
    "command": "generate_podcast",
    "app": "open_notebook", 
    "input": { "notebook_id": "123", "episode_profile": "tech" }


@router.get("/commands/{job_id}", response_model=CommandJobStatusResponse)
async def get_command_job_status(job_id: str):
    """Get the status of a specific command job"""
    try:
        status_data = await CommandService.get_command_status(job_id)
        return CommandJobStatusResponse(**status_data)
        
    except Exception as e:
        logger.error(f"Error fetching job status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch job status: {str(e)}"
        )

@router.get("/commands/jobs", response_model=List[Dict[str, Any]])
async def list_command_jobs(
    command_filter: Optional[str] = Query(None, description="Filter by command name"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Maximum number of jobs to return")
):
    """List command jobs with optional filtering"""
    try:
        jobs = await CommandService.list_command_jobs(
            command_filter=command_filter,
            status_filter=status_filter,
            limit=limit
        )
        return jobs
        
    except Exception as e:
        logger.error(f"Error listing command jobs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list command jobs: {str(e)}"
        )

@router.delete("/commands/jobs/{job_id}")
async def cancel_command_job(job_id: str):
    """Cancel a running command job"""
    try:
        success = await CommandService.cancel_command_job(job_id)
        return {"job_id": job_id, "cancelled": success}
        
    except Exception as e:
        logger.error(f"Error cancelling command job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel command job: {str(e)}"
        )

```

#### 1.5 Add Router to Main App
```python
# api/main.py - Add import and router
from api.routers import notebooks, search, models, transformations, notes, embedding, settings, context, sources, insights
from api.routers import commands as commands_router

# Import commands to register them in the API process
try:
    import commands.example_commands
    from loguru import logger
    logger.info("Commands imported in API process")
except Exception as e:
    from loguru import logger
    logger.error(f"Failed to import commands in API process: {e}")

# Add to router includes (after line 31)
app.include_router(commands_router.router, prefix="/api", tags=["commands"])
```

#### 1.6 Configure Worker Process
```bash
# supervisord.conf - Add after [program:api] section
[program:worker]
command=uv run --env-file .env surreal-commands-worker --import-modules commands.example_commands
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
autorestart=true
```

#### 1.7 Add Makefile Commands
```makefile
# Makefile - Add worker management commands
.PHONY: worker worker-start worker-stop worker-restart

worker: worker-start

worker-start:
	@echo "Starting surreal-commands worker..."
	uv run --env-file .env surreal-commands-worker --import-modules commands.example_commands

worker-stop:
	@echo "Stopping surreal-commands worker..."
	pkill -f "surreal-commands-worker" || true

worker-restart: worker-stop
	@sleep 2
	@$(MAKE) worker-start

```

### ✅ Testing Strategy
1. **Dependencies**: Verify surreal-commands installs correctly
2. **Worker Process**: Test worker starts and registers example commands successfully
3. **API Endpoints**: Test generic command submission and status retrieval
4. **Command Execution**: Verify example commands execute and return expected results
5. **Error Handling**: Test error scenarios and proper error responses
6. **Async Behavior**: Test commands with delays to verify non-blocking execution

### 🧪 Manual Testing Commands
```bash
# 1. Install dependencies
uv sync

# 2. Start SurrealDB
make database

# 3. Start API and worker separately for testing
# Terminal 1: Start API
make api

# Terminal 2: Start worker
make worker

# 4. Test example command endpoints (shortcuts)
curl -X POST "http://localhost:5055/api/commands/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    params
    }
  }'


# 6. Check job status (use job_id from responses)
curl "http://localhost:5055/api/commands/jobs/{job_id}"

# 7. List all command jobs
curl "http://localhost:5055/api/commands/jobs"

# 8. Test worker with supervisord (production mode)
docker compose up

# 9. Test Makefile commands
make worker-start
make worker-stop
make worker-restart
```

### ⚠️ Critical Notes
- **Worker Process**: Single worker only (surreal-commands current limitation)
- **Environment Setup**: Ensure SurrealDB is running before starting worker
- **Testing Required**: Thoroughly test async job submission and status tracking
- **🛑 STOP**: Request human approval before proceeding to Phase 2

---

## Phase 2: Engine Integration (OSS-138) - 4 hours

### 📚 Dependencies
- Surreal Commands Library: https://github.com/lfnovo/surreal-commands
- Available in Context7 and on /Users/luisnovo/dev/projetos/surreal-commands/surreal-commands
- Podcast Creator Library: https://github.com/lfnovo/podcast-creator
- Available in Context7 and on /Users/luisnovo/dev/projetos/podcast-creator/podcast-creator

### 🎯 Goals
- Integrate podcast-creator library with Episode Profiles
- Create domain models for Episode and Speaker profiles
- Implement real podcast generation with LangGraph workflow
- Replace placeholder implementation with production-ready engine

### 📁 Files to Create/Change
1. **NEW**: `open_notebook/domain/podcast.py` - Episode, Speaker, PodcastEpisode models
2. **NEW**: `api/routers/episode_profiles.py` - Episode profile management endpoints
3. **NEW**: `api/routers/speaker_profiles.py` - Speaker profile management endpoints
4. **MODIFY**: `commands/podcast_commands.py` - Real podcast generation implementation
5. **MODIFY**: `api/main.py` - Add new routers
6. **DELETE AT THE END**: `plugins/podcasts.py` - Old Podcast module that we are replacing 


### 🔧 Before you start

Database models have already been created

Referer to the file 7.surrealql to see that has already been created. 


### 🔧 Specific Implementation Steps


#### 2.1 Create Domain Models
```python
# open_notebook/domain/podcast.py
from typing import ClassVar, Optional, List, Dict, Any
from pydantic import Field, validator
from open_notebook.domain.base import ObjectModel

class EpisodeProfile(ObjectModel):
    """
    Episode Profile - Simplified podcast configuration.
    Replaces complex 15+ field configuration with user-friendly profiles.
    """
    table_name: ClassVar[str] = "episode_profile"
    
    name: str = Field(..., description="Unique profile name")
    description: Optional[str] = Field(None, description="Profile description")
    speaker_config: str = Field(..., description="Reference to speaker profile name")
    outline_provider: str = Field(..., description="AI provider for outline generation")
    outline_model: str = Field(..., description="AI model for outline generation")
    transcript_provider: str = Field(..., description="AI provider for transcript generation")
    transcript_model: str = Field(..., description="AI model for transcript generation")
    default_briefing: str = Field(..., description="Default briefing template")
    num_segments: int = Field(default=5, description="Number of podcast segments")
    
    @validator('num_segments')
    def validate_segments(cls, v):
        if not 3 <= v <= 20:
            raise ValueError('Number of segments must be between 3 and 20')
        return v
    
    @classmethod
    async def get_by_name(cls, name: str) -> Optional['EpisodeProfile']:
        """Get episode profile by name"""
        from open_notebook.database.repository import repo_query, ensure_record_id
        result = await repo_query(
            "SELECT * FROM episode_profile WHERE name = $name",
            {"name": name}
        )
        if result:
            return cls(**result[0])
        return None

class SpeakerProfile(ObjectModel):
    """
    Speaker Profile - Voice and personality configuration.
    Supports 1-4 speakers for flexible podcast formats.
    """
    table_name: ClassVar[str] = "speaker_profile"
    
    name: str = Field(..., description="Unique profile name")
    description: Optional[str] = Field(None, description="Profile description")
    tts_provider: str = Field(..., description="TTS provider (openai, elevenlabs, etc.)")
    tts_model: str = Field(..., description="TTS model name")
    speakers: List[Dict[str, Any]] = Field(..., description="Array of speaker configurations")
    
    @validator('speakers')
    def validate_speakers(cls, v):
        if not 1 <= len(v) <= 4:
            raise ValueError('Must have between 1 and 4 speakers')
        
        required_fields = ['name', 'voice_id', 'backstory', 'personality']
        for speaker in v:
            for field in required_fields:
                if field not in speaker:
                    raise ValueError(f'Speaker missing required field: {field}')
        return v
    
    @classmethod
    async def get_by_name(cls, name: str) -> Optional['SpeakerProfile']:
        """Get speaker profile by name"""
        from open_notebook.database.repository import repo_query
        result = await repo_query(
            "SELECT * FROM speaker_profile WHERE name = $name",
            {"name": name}
        )
        if result:
            return cls(**result[0])
        return None

from surrealdb import RecordID

class PodcastEpisode(ObjectModel):
    """Enhanced PodcastEpisode with job tracking and metadata"""
    table_name: ClassVar[str] = "episode"
    
    name: str
    episode_profile: str = Field(..., description="Episode profile used")
    generation_metadata: Dict[str, Any] = Field(default_factory=dict, description="Generation parameters")
    briefing: str = Field(..., description="Full briefing used for generation")
    text: str = Field(..., description="Source content")
    audio_file: Optional[str] = Field(None, description="Path to generated audio file")
    transcript_file: Optional[str] = Field(None, description="Path to transcript file")
    outline_file: Optional[str] = Field(None, description="Path to outline file")
    command: Optional[Union[str, RecordID]] = Field(None, description="Link to surreal-commands job")
    
    async def get_job_status(self) -> Optional[str]:
        """Get the status of the associated command"""
        if not self.command:
            return None
        
        from surreal_commands import get_command_status
        try:
            status = await get_command_status(self.command)
            return status.status if status else "unknown"
        except Exception:
            return "unknown"
```

#### 2.2 - Load the episode_profile and speaker_profile objects from SurrealDB into podcast-creator using its configure methods and Create the command

Look for a reference on commands/example_commands.py or look in the surreal-commands documentation for more details on how to create a command

Your command will get the speaker_profile, episode_profile, episode_name, additional_briefing and content as input and will generate the podcast episode
set output_dir as os.environ.get("DATA_DIR", "/podcasts")

The command will call the generate_podcast method from podcast_creator with the following parameters:

- output_dir
- episode_profile
- episode_name
- additional_briefing
- content

```python

# commands/podcast_commands.py
from podcast_creator import configure

# get the profiles
episode_profiles = await repo_query("select * from episode_profile")
speaker_profiles = await repo_query("select * from speaker_profile")

# transform the surrealdb array into a dictionary so you can pass them to config like this: 

episode_profiles_dict = {profile["name"]: profile for profile in episode_profiles}
speaker_profiles_dict = {profile["name"]: profile for profile in speaker_profiles}

# Define custom episode profiles
configure("episode_config", {
    "profiles": episode_profiles_dict
})

configure("speaker_config", {
    "profiles": speaker_profiles_dict
})


# commands/podcast_commands.py - Replace placeholder with real implementation
from podcast_creator import create_podcast, configure
from open_notebook.domain.podcast import EpisodeProfile, SpeakerProfile, PodcastEpisode
from open_notebook.domain.notebook import Notebook
from pathlib import Path
import json

@command("generate_podcast")
async def generate_podcast_command(
    input_data: PodcastGenerationInput
) -> PodcastGenerationOutput:
    """
    Real podcast generation using podcast-creator library with Episode Profiles
    """
    try:
        logger.info(f"Starting podcast generation for episode: {input_data.episode_name}")
        
        # 1. Load Episode and Speaker profiles
        episode_profile = await EpisodeProfile.get_by_name(input_data.episode_profile_name)
        speaker_profile = await SpeakerProfile.get_by_name(episode_profile.speaker_config)
        
        # 4. Generate briefing
        briefing = episode_profile.default_briefing
        if input_data.briefing_suffix:
            briefing += f"\n\nAdditional instructions: {input_data.briefing_suffix}"
        
        # 5. Create output directory
        output_dir = Path(f"{os.environ.get('DATA_DIR', '/podcasts')}/episodes/{input_data.episode_name}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 6. Generate podcast using podcast-creator
        result = await create_podcast(
            content=input_data.content,
            briefing=briefing,
            episode_name=input_data.episode_name,
            output_dir=str(output_dir),
            speaker_profile=speaker_profile.name,
            podcast_profile=episode_profile.name,
            
        )
        
        # 7. Save episode record
        episode = PodcastEpisode(
            name=input_data.episode_name,
            episode_profile=episode_profile.model_dump(),
            speaker_profile=speaker_profile.model_dump(),
            briefing=briefing,
            content=str(context),
            audio_file=result.get("final_output_file_path"),
            transcript=result.get("transcript"),
            outline=result.get("outline")
        )
        await episode.save()
        
        logger.info(f"Successfully generated podcast episode: {episode.id}")
        
        return PodcastGenerationOutput(
            success=True,
            episode_id=str(episode.id),
            audio_file_path=result.get("final_output_file_path"),
        )
        
    except Exception as e:
        logger.error(f"Podcast generation failed: {e}")
        return PodcastGenerationOutput(
            success=False,
            error_message=str(e)
        )

```

#### 2.3 - Create the API endpoint for podcast generation and the esrvice that will service the API and submit the command to surreal-commands

POST /podcast/episode



#### 2.4 Create Profile Management Endpoints
```python
# api/routers/episode_profiles.py
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from open_notebook.domain.podcast import EpisodeProfile
from api.models import ErrorResponse

router = APIRouter()

class EpisodeProfileResponse(BaseModel):
    id: str
    name: str
    description: str
    speaker_config: str
    outline_provider: str
    outline_model: str
    transcript_provider: str
    transcript_model: str
    default_briefing: str
    num_segments: int

@router.get("/episode-profiles", response_model=List[EpisodeProfileResponse])
async def list_episode_profiles():
    """List all available episode profiles"""
    try:
        profiles = await EpisodeProfile.get_all(order_by="name asc")
        return [
            EpisodeProfileResponse(
                id=profile.id,
                name=profile.name,
                description=profile.description or "",
                speaker_config=profile.speaker_config,
                outline_provider=profile.outline_provider,
                outline_model=profile.outline_model,
                transcript_provider=profile.transcript_provider,
                transcript_model=profile.transcript_model,
                default_briefing=profile.default_briefing,
                num_segments=profile.num_segments
            )
            for profile in profiles
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch episode profiles: {str(e)}"
        )

# api/routers/speaker_profiles.py  
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from open_notebook.domain.podcast import SpeakerProfile

router = APIRouter()

class SpeakerProfileResponse(BaseModel):
    id: str
    name: str
    description: str
    tts_provider: str
    tts_model: str
    speakers: List[Dict[str, Any]]

@router.get("/speaker-profiles", response_model=List[SpeakerProfileResponse])
async def list_speaker_profiles():
    """List all available speaker profiles"""
    try:
        profiles = await SpeakerProfile.get_all(order_by="name asc")
        return [
            SpeakerProfileResponse(
                id=profile.id,
                name=profile.name,
                description=profile.description or "",
                tts_provider=profile.tts_provider,
                tts_model=profile.tts_model,
                speakers=profile.speakers
            )
            for profile in profiles
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch speaker profiles: {str(e)}"
        )
```

### ✅ Testing Strategy
1. **Profile Management**: Test episode and speaker profile CRUD operations
2. **Real Generation**: Test end-to-end podcast generation through the API -> surreal-commands -> podcast-creator
3. **Error Handling**: Test various failure scenarios (missing profiles, invalid content)
4. **Integration**: Verify podcast-creator integration with Episode Profiles


### 🧪 Manual Testing Commands
```bash

# 2. List available profiles  
curl "http://localhost:5055/api/episode-profiles"
curl "http://localhost:5055/api/speaker-profiles"

# 3. Generate real podcast
curl -X POST "http://localhost:5055/api/podcasts/episodes" \
  -H "Content-Type: application/json" \
  -d '{
    "episode_profile_name": "tech_discussion", 
    "content": "My first episode",
    "episode_name": "my_first_episode"
    "briefing_suffix": "Additional instructions blabla"
    "speaker_profile_name": "tech_experts"
  }'

# 4. Monitor job progress
curl "http://localhost:5055/api/commands/jobs/{job_id}"
```

### ⚠️ Critical Notes
- **Real Audio Generation**: This phase produces actual podcast audio files (~2-3 minutes)
- **Error Recovery**: Implement proper cleanup on generation failure
- **🛑 STOP**: Request human approval before proceeding to Phase 3

---

## Phase 3: UI Modernization (OSS-139) - 3 hours

### 🎯 Goals
- Simplify Streamlit UI from 15+ fields to 3-click workflow (Profile → Name → Generate)
- Display podcast episodes with job status via database relationships
- Implement non-blocking podcast generation UX
- Prepare UI foundation for future React migration

### 📁 Files to Create/Change
1. **MODIFY**: `pages/5_🎙️_Podcasts.py` - Complete UI overhaul (make a backup before starting)
2. **NEW**: `pages/components/episode_profile_selector.py` - Profile selection component
3. **NEW**: `pages/components/podcast_status_display.py` - Status display component
4. **MODIFY**: `pages/stream_app/chat.py` - Update podcast tab integration

### 🔧 Specific Implementation Steps

#### 3.1 Create Profile Selection Component
```python
# pages/components/episode_profile_selector.py
import asyncio
import streamlit as st
from typing import List, Optional
from open_notebook.domain.podcast import EpisodeProfile, SpeakerProfile

class EpisodeProfileSelector:
    """Component for selecting episode profiles with preview"""
    
    @staticmethod
    async def render() -> Optional[str]:
        """Render episode profile selector and return selected profile name"""
        
        # Load available profiles
        profiles = asyncio.run(EpisodeProfile.get_all(order_by="name asc"))
        
        if not profiles:
            st.error("No episode profiles available. Please contact administrator.")
            return None
        
        # Create profile options with descriptions
        profile_options = {}
        for profile in profiles:
            display_name = f"{profile.name} - {profile.description}" if profile.description else profile.name
            profile_options[display_name] = profile.name
        
        # Profile selection
        selected_display = st.selectbox(
            "Choose Episode Profile",
            options=list(profile_options.keys()),
            help="Select a pre-configured podcast style"
        )
        
        if selected_display:
            selected_name = profile_options[selected_display]
            selected_profile = next(p for p in profiles if p.name == selected_name)
            
            # Show profile preview
            with st.expander("📝 Profile Details", expanded=False):
                st.write(f"**Description:** {selected_profile.description or 'No description'}")
                st.write(f"**Speaker Configuration:** {selected_profile.speaker_config}")
                st.write(f"**Segments:** {selected_profile.num_segments}")
                st.write(f"**AI Models:** {selected_profile.outline_provider}/{selected_profile.outline_model} (outline), {selected_profile.transcript_provider}/{selected_profile.transcript_model} (transcript)")
                
                # Show speaker preview
                speaker_profile = asyncio.run(SpeakerProfile.get_by_name(selected_profile.speaker_config))
                if speaker_profile:
                    st.write(f"**Speakers ({len(speaker_profile.speakers)}):**")
                    for speaker in speaker_profile.speakers:
                        st.write(f"- **{speaker['name']}**: {speaker['personality']}")
                
                with st.container():
                    st.text_area(
                        "Default Briefing:",
                        value=selected_profile.default_briefing,
                        height=100,
                        disabled=True
                    )
            
            return selected_name
        
        return None
```

#### 3.2 Create Status Display Component
```python
# pages/components/podcast_status_display.py
import asyncio
import streamlit as st
from typing import List
from datetime import datetime
from open_notebook.domain.podcast import PodcastEpisode
import humanize

class PodcastStatusDisplay:
    """Component for displaying podcast episodes with job status"""
    
    @staticmethod
    async def render(notebook_id: Optional[str] = None):
        """Render podcast episodes with status"""
        
        # Get episodes with job status
        episodes = await PodcastStatusDisplay._get_episodes_with_status(notebook_id)
        
        if not episodes:
            st.info("No podcast episodes found. Generate your first episode above!")
            return
        
        st.subheader(f"📻 Podcast Episodes ({len(episodes)})")
        
        # Group by status for better organization
        status_groups = {
            "completed": [],
            "running": [], 
            "failed": [],
            "pending": []
        }
        
        for episode in episodes:
            status = episode.get("job_status", "unknown")
            if status == "completed":
                status_groups["completed"].append(episode)
            elif status in ["running", "processing"]:
                status_groups["running"].append(episode)
            elif status == "failed":
                status_groups["failed"].append(episode)
            else:
                status_groups["pending"].append(episode)
        
        # Display running jobs first
        if status_groups["running"]:
            st.write("🔄 **Currently Processing**")
            for episode in status_groups["running"]:
                PodcastStatusDisplay._render_episode_card(episode, show_audio=False)
        
        # Display completed episodes
        if status_groups["completed"]:
            st.write("✅ **Completed Episodes**")
            for episode in status_groups["completed"]:
                PodcastStatusDisplay._render_episode_card(episode, show_audio=True)
        
        # Display failed jobs
        if status_groups["failed"]:
            st.write("❌ **Failed Episodes**")
            for episode in status_groups["failed"]:
                PodcastStatusDisplay._render_episode_card(episode, show_audio=False)
        
        # Display pending jobs
        if status_groups["pending"]:
            st.write("⏳ **Pending Episodes**")
            for episode in status_groups["pending"]:
                PodcastStatusDisplay._render_episode_card(episode, show_audio=False)
    
    @staticmethod
    def _render_episode_card(episode_data: dict, show_audio: bool = True):
        """Render individual episode card"""
        with st.container():
            st.markdown("---")
            
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                status_emoji = {
                    "completed": "✅",
                    "running": "🔄", 
                    "failed": "❌",
                    "pending": "⏳"
                }.get(episode_data.get("job_status", "unknown"), "❓")
                
                st.write(f"{status_emoji} **{episode_data['name']}**")
                st.caption(f"Profile: {episode_data.get('episode_profile', 'Unknown')}")
            
            with col2:
                if episode_data.get("created"):
                    created_date = datetime.fromisoformat(episode_data["created"].replace('Z', '+00:00'))
                    st.caption(f"Created: {humanize.naturaltime(created_date)}")
            
            with col3:
                # Refresh button for non-completed episodes
                if episode_data.get("job_status") not in ["completed", "failed"]:
                    if st.button("🔄", key=f"refresh_{episode_data['id']}", help="Refresh status"):
                        st.rerun()
            
            # Show audio player for completed episodes
            if show_audio and episode_data.get("audio_file"):
                try:
                    st.audio(episode_data["audio_file"], format="audio/mpeg")
                except Exception:
                    st.error("Audio file not found or corrupted")
            
            # Show error message for failed episodes
            if episode_data.get("job_status") == "failed" and episode_data.get("error_message"):
                st.error(f"Error: {episode_data['error_message']}")
            
            # Show metadata in expander
            with st.expander(f"Details - {episode_data['name']}", expanded=False):
                metadata = episode_data.get("generation_metadata", {})
                if metadata:
                    st.json(metadata)
                
                if episode_data.get("briefing"):
                    st.text_area(
                        "Briefing Used:",
                        value=episode_data["briefing"],
                        height=100,
                        disabled=True,
                        key=f"briefing_{episode_data['id']}"
                    )
    
    @staticmethod
    async def _get_episodes_with_status(notebook_id: Optional[str] = None) -> List[dict]:
        """Get episodes with their job status"""
        from open_notebook.database.repository import repo_query
        
        # Query episodes with command status
        if notebook_id:
            query = """
            SELECT *,
                command.status AS job_status,
                command.error_message AS error_message
            FROM podcast_episode
            WHERE notebook_id = $notebook_id
            ORDER BY created DESC
            """
            params = {"notebook_id": notebook_id}
        else:
            query = """
            SELECT *,
                command.status AS job_status,
                command.error_message AS error_message  
            FROM podcast_episode
            ORDER BY created DESC
            """
            params = {}
        
        result = await repo_query(query, params)
        return result
```

#### 3.3 Modernize Main Podcast Page
```python
# pages/5_🎙️_Podcasts.py - Complete rewrite
import asyncio
import streamlit as st
import nest_asyncio
from pages.stream_app.utils import setup_page
from pages.components.episode_profile_selector import EpisodeProfileSelector
from pages.components.podcast_status_display import PodcastStatusDisplay
from api.podcast_service import PodcastService, DefaultProfiles

nest_asyncio.apply()

setup_page("🎙️ Podcasts", only_check_mandatory_models=False)

# Page title and description
st.title("🎙️ Podcast Generator")
st.markdown("""
Create professional podcasts from your notebook content using AI-powered Episode Profiles.
Choose from pre-configured styles or create custom profiles for your unique podcast format.
""")

# Initialize default profiles if needed
if st.button("🔧 Initialize Default Profiles", help="Create default episode and speaker profiles"):
    with st.spinner("Creating default profiles..."):
        try:
            asyncio.run(DefaultProfiles.create_default_episode_profiles())
            asyncio.run(DefaultProfiles.create_default_speaker_profiles())
            st.success("✅ Default profiles created successfully!")
        except Exception as e:
            st.error(f"Failed to create default profiles: {e}")

st.markdown("---")

# Main podcast generation section
st.subheader("🎬 Generate New Episode")

# Check if we have a current notebook
current_notebook_id = st.session_state.get("current_notebook_id")
if not current_notebook_id:
    st.warning("⚠️ Please select a notebook first from the main page.")
    st.stop()

col1, col2 = st.columns([2, 1])

with col1:
    # Episode Profile Selection (3-click workflow starts here)
    selected_profile = asyncio.run(EpisodeProfileSelector.render())
    
    if selected_profile:
        # Episode Name Input
        episode_name = st.text_input(
            "Episode Name",
            placeholder="e.g., Tech Discussion on AI Trends",
            help="Choose a descriptive name for your podcast episode"
        )
        
        # Optional briefing suffix
        briefing_suffix = st.text_area(
            "Additional Instructions (Optional)",
            placeholder="Add specific instructions for this episode...",
            height=100,
            help="Customize the briefing for this specific episode"
        )

with col2:
    st.markdown("### 📋 Generation Checklist")
    st.markdown(f"""
    - {'✅' if selected_profile else '⏳'} **Episode Profile**: {selected_profile or 'Not selected'}
    - {'✅' if episode_name else '⏳'} **Episode Name**: {'Set' if episode_name else 'Required'}
    - {'✅' if current_notebook_id else '❌'} **Notebook Content**: {'Available' if current_notebook_id else 'Missing'}
    """)

# Generate button (3-click workflow completion)
if selected_profile and episode_name and current_notebook_id:
    st.markdown("---")
    
    # Estimated generation time
    st.info("⏱️ **Estimated generation time**: 2-3 minutes for professional quality podcast")
    
    if st.button("🚀 Generate Podcast", type="primary", use_container_width=True):
        with st.spinner("🎙️ Starting podcast generation..."):
            try:
                job_id = asyncio.run(PodcastService.submit_generation_job(
                    notebook_id=current_notebook_id,
                    episode_profile_name=selected_profile,
                    episode_name=episode_name,
                    briefing_suffix=briefing_suffix if briefing_suffix.strip() else None
                ))
                
                st.success(f"""
                ✅ **Podcast generation started!**
                
                **Job ID**: `{job_id}`
                
                Your podcast is being generated in the background. You can continue using Open Notebook while it processes.
                The episode will appear in the list below when completed.
                """)
                
                # Auto-refresh to show the new job
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Failed to start podcast generation: {e}")

st.markdown("---")

# Episodes display section
asyncio.run(PodcastStatusDisplay.render(current_notebook_id))

# Footer with helpful information
st.markdown("---")
with st.expander("ℹ️ How it works", expanded=False):
    st.markdown("""
    ### 🎯 3-Click Podcast Generation
    
    1. **Choose Profile**: Select from pre-configured episode styles
    2. **Name Episode**: Give your podcast a descriptive name  
    3. **Generate**: Click generate and continue using Open Notebook
    
    ### 🎨 Episode Profiles
    - **Tech Discussion**: 2 experts discussing technical topics
    - **Solo Expert**: Single expert explaining complex concepts
    - **Business Analysis**: Business-focused panel discussion
    
    ### 🔄 Background Processing
    - Podcasts generate in the background (2-3 minutes)
    - No need to wait - continue your research
    - Refresh the page to see updates
    
    ### 🎧 Professional Quality
    - Multiple AI models for outline and transcript generation
    - High-quality text-to-speech with personality-rich speakers
    - Support for 1-4 speakers (vs Google's 2-speaker limit)
    """)
```

#### 3.4 Update Chat Integration
```python
# pages/stream_app/chat.py - Update podcast tab (lines 76-132)
with podcast_tab:
    st.markdown("### 🎙️ Quick Podcast Generation")
    
    # Simple profile selector for chat context
    episode_profiles = asyncio.run(EpisodeProfile.get_all())
    if episode_profiles:
        profile_names = [ep.name for ep in episode_profiles]
        selected_template = st.selectbox("Episode Profile", profile_names)
        
        episode_name = st.text_input("Episode Name", key="chat_episode_name")
        
        if episode_name and selected_template:
            if st.button("🚀 Generate from Chat Context"):
                try:
                    job_id = asyncio.run(PodcastService.submit_generation_job(
                        notebook_id=current_notebook.id,
                        episode_profile_name=selected_template,
                        episode_name=episode_name,
                        briefing_suffix="Generate podcast from current chat context"
                    ))
                    st.success(f"Podcast generation started! Job ID: {job_id}")
                except Exception as e:
                    st.error(f"Failed to generate podcast: {e}")
    else:
        st.warning("No episode profiles available. Please initialize default profiles.")
    
    st.page_link("pages/5_🎙️_Podcasts.py", label="🎙️ Go to Full Podcast Interface")
```

### ✅ Testing Strategy
1. **Profile Selection**: Test episode profile selection and preview
2. **3-Click Workflow**: Verify simplified generation process
3. **Status Display**: Test job status updates and refresh functionality
4. **Audio Playback**: Verify completed episodes play correctly
5. **Error Handling**: Test UI behavior with failed generations
6. **Chat Integration**: Test quick generation from chat context

### 🧪 Manual Testing Scenarios
```
# Test 3-Click Workflow:
1. Navigate to Podcasts page
2. Select "tech_discussion" profile
3. Enter episode name "Test Episode"
4. Click "Generate Podcast"
5. Verify job appears in status list
6. Wait for completion and test audio playback

# Test Status Updates:
1. Generate multiple episodes
2. Refresh page to see status updates
3. Test failed episode error display
4. Verify completed episodes show audio player

# Test Profile Management:
1. Initialize default profiles
2. Verify all profiles load correctly
3. Test profile preview information
4. Verify speaker configuration display
```

### ⚠️ Critical Notes
- **UI Simplification**: Massive reduction from 15+ fields to 3 clicks
- **Non-blocking UX**: Users can continue working while podcasts generate
- **No Real-time Updates**: Simple refresh-based status (preparing for React migration)
- **Profile Dependencies**: Ensure default profiles are created before first use
- **Audio Storage**: Verify audio files are accessible from Streamlit
- **🛑 STOP**: Request human approval before proceeding to Phase 4

---

## Phase 4: Data Migration (OSS-141) - 3 hours

### 🎯 Goals
- Create new database schema for Episode and Speaker profiles
- Migrate existing podcast_config data to new Episode Profile format
- Maintain backward compatibility during transition
- Enable smooth rollback if needed

### 📁 Files to Create/Change
1. **NEW**: `migrations/7.surrealql` - New schema creation
2. **NEW**: `migrations/7_down.surrealql` - Rollback script  
3. **NEW**: `api/migration_service.py` - Data migration utilities
4. **NEW**: `api/routers/migration.py` - Migration management endpoints
5. **MODIFY**: `api/main.py` - Add migration router

### 🔧 Specific Implementation Steps

#### 4.1 Create New Database Schema
```sql
-- migrations/7.surrealql
DEFINE TABLE IF NOT EXISTS episode_profile SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS name ON TABLE episode_profile TYPE string;
DEFINE FIELD IF NOT EXISTS description ON TABLE episode_profile TYPE option<string>;
DEFINE FIELD IF NOT EXISTS speaker_config ON TABLE episode_profile TYPE string;
DEFINE FIELD IF NOT EXISTS outline_provider ON TABLE episode_profile TYPE string;
DEFINE FIELD IF NOT EXISTS outline_model ON TABLE episode_profile TYPE string;
DEFINE FIELD IF NOT EXISTS transcript_provider ON TABLE episode_profile TYPE string;
DEFINE FIELD IF NOT EXISTS transcript_model ON TABLE episode_profile TYPE string;
DEFINE FIELD IF NOT EXISTS default_briefing ON TABLE episode_profile TYPE string;
DEFINE FIELD IF NOT EXISTS num_segments ON TABLE episode_profile TYPE int DEFAULT 5;
DEFINE FIELD IF NOT EXISTS migrated_from_podcast_config ON TABLE episode_profile TYPE option<string>;
DEFINE FIELD IF NOT EXISTS created ON TABLE episode_profile TYPE datetime DEFAULT time::now();
DEFINE FIELD IF NOT EXISTS updated ON TABLE episode_profile TYPE datetime DEFAULT time::now();

-- Create Speaker Profile table
DEFINE TABLE IF NOT EXISTS speaker_profile SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS name ON TABLE speaker_profile TYPE string;
DEFINE FIELD IF NOT EXISTS description ON TABLE speaker_profile TYPE option<string>;
DEFINE FIELD IF NOT EXISTS tts_provider ON TABLE speaker_profile TYPE string;
DEFINE FIELD IF NOT EXISTS tts_model ON TABLE speaker_profile TYPE string;
DEFINE FIELD IF NOT EXISTS speakers ON TABLE speaker_profile TYPE array;
DEFINE FIELD IF NOT EXISTS migrated_from_podcast_config ON TABLE speaker_profile TYPE option<string>;
DEFINE FIELD IF NOT EXISTS created ON TABLE speaker_profile TYPE datetime DEFAULT time::now();
DEFINE FIELD IF NOT EXISTS updated ON TABLE speaker_profile TYPE datetime DEFAULT time::now();

-- Enhance PodcastEpisode table
DEFINE TABLE IF NOT EXISTS episode SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS episode_profile ON TABLE episode TYPE string;
DEFINE FIELD IF NOT EXISTS generation_metadata ON TABLE episode TYPE object;
DEFINE FIELD IF NOT EXISTS briefing ON TABLE episode TYPE option<string>;
DEFINE FIELD IF NOT EXISTS transcript ON TABLE episode TYPE option<object>;
DEFINE FIELD IF NOT EXISTS outline ON TABLE episode TYPE option<object>;
DEFINE FIELD IF NOT EXISTS command ON TABLE episode TYPE record<command>;

-- Create indexes for better performance
DEFINE INDEX IF NOT EXISTS idx_episode_profile_name ON TABLE episode_profile COLUMNS name UNIQUE CONCURRENTLY;
DEFINE INDEX IF NOT EXISTS idx_speaker_profile_name ON TABLE speaker_profile COLUMNS name UNIQUE CONCURRENTLY;
DEFINE INDEX IF NOT EXISTS idx_episode_profile ON TABLE episode COLUMNS episode_profile CONCURRENTLY;
DEFINE INDEX IF NOT EXISTS idx_episode_command ON TABLE episode COLUMNS command CONCURRENTLY;

```

#### 4.3 Create Migration Service
```python
# api/migration_service.py
from typing import List, Dict, Any, Optional
from loguru import logger
from open_notebook.database.repository import repo_query, repo_create
from open_notebook.domain.podcast import EpisodeProfile, SpeakerProfile

class PodcastMigrationService:
    """Service for migrating podcast_config data to Episode Profiles"""
    
    @staticmethod
    async def analyze_existing_configs() -> Dict[str, Any]:
        """Analyze existing podcast_config records for migration planning"""
        try:
            configs = await repo_query("SELECT * FROM podcast_config")
            
            analysis = {
                "total_configs": len(configs),
                "unique_combinations": {},
                "tts_providers": set(),
                "models": set(),
                "languages": set(),
                "migration_candidates": []
            }
            
            for config in configs:
                # Analyze TTS usage
                analysis["tts_providers"].add(config.get("provider", "unknown"))
                analysis["models"].add(config.get("model", "unknown"))
                analysis["languages"].add(config.get("output_language", "unknown"))
                
                # Create combination signature for deduplication
                combo_key = f"{config.get('provider')}_{config.get('model')}_{len(config.get('person1_role', []))}_{len(config.get('person2_role', []))}"
                
                if combo_key not in analysis["unique_combinations"]:
                    analysis["unique_combinations"][combo_key] = {
                        "count": 0,
                        "example_config": config,
                        "suggested_profile_name": PodcastMigrationService._suggest_profile_name(config)
                    }
                
                analysis["unique_combinations"][combo_key]["count"] += 1
                
                # Add to migration candidates
                analysis["migration_candidates"].append({
                    "config_id": config.get("id"),
                    "name": config.get("name"),
                    "suggested_episode_profile": PodcastMigrationService._suggest_profile_name(config),
                    "suggested_speaker_profile": PodcastMigrationService._suggest_speaker_profile_name(config)
                })
            
            # Convert sets to lists for JSON serialization
            analysis["tts_providers"] = list(analysis["tts_providers"])
            analysis["models"] = list(analysis["models"])
            analysis["languages"] = list(analysis["languages"])
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze existing configs: {e}")
            raise
    
    @staticmethod
    def _suggest_profile_name(config: Dict[str, Any]) -> str:
        """Suggest an episode profile name based on config characteristics"""
        person1_roles = config.get("person1_role", [])
        person2_roles = config.get("person2_role", [])
        
        # Determine if it's solo or multi-speaker
        if not person2_roles or len(person2_roles) == 0:
            return f"solo_{config.get('name', 'custom').lower().replace(' ', '_')}"
        
        # Look for common role patterns
        all_roles = person1_roles + person2_roles
        if any("tech" in role.lower() or "engineer" in role.lower() for role in all_roles):
            return f"tech_{config.get('name', 'discussion').lower().replace(' ', '_')}"
        elif any("business" in role.lower() or "analyst" in role.lower() for role in all_roles):
            return f"business_{config.get('name', 'analysis').lower().replace(' ', '_')}"
        else:
            return f"custom_{config.get('name', 'discussion').lower().replace(' ', '_')}"
    
    @staticmethod  
    def _suggest_speaker_profile_name(config: Dict[str, Any]) -> str:
        """Suggest a speaker profile name based on config characteristics"""
        provider = config.get("provider", "openai")
        person2_roles = config.get("person2_role", [])
        
        if not person2_roles or len(person2_roles) == 0:
            return f"solo_{provider}"
        else:
            return f"dual_{provider}"
    
    @staticmethod
    async def migrate_config_to_profiles(config_id: str) -> Dict[str, str]:
        """Migrate a specific podcast_config to Episode and Speaker profiles"""
        try:
            # Get the config
            config_result = await repo_query(
                "SELECT * FROM podcast_config WHERE id = $id",
                {"id": config_id}
            )
            
            if not config_result:
                raise ValueError(f"Config not found: {config_id}")
            
            config = config_result[0]
            
            # Create speaker profile
            speaker_profile_name = PodcastMigrationService._suggest_speaker_profile_name(config)
            speakers = []
            
            # Add first speaker
            if config.get("person1_role"):
                speakers.append({
                    "name": "Speaker 1",
                    "voice_id": config.get("voice1", "nova"),
                    "backstory": f"Expert in: {', '.join(config.get('person1_role', []))}",
                    "personality": f"Role: {', '.join(config.get('person1_role', []))}"
                })
            
            # Add second speaker if exists
            if config.get("person2_role") and len(config.get("person2_role", [])) > 0:
                speakers.append({
                    "name": "Speaker 2", 
                    "voice_id": config.get("voice2", "alloy"),
                    "backstory": f"Expert in: {', '.join(config.get('person2_role', []))}",
                    "personality": f"Role: {', '.join(config.get('person2_role', []))}"
                })
            
            # Check if speaker profile already exists
            existing_speaker = await SpeakerProfile.get_by_name(speaker_profile_name)
            if not existing_speaker:
                speaker_profile = SpeakerProfile(
                    name=speaker_profile_name,
                    description=f"Migrated from podcast_config: {config.get('name')}",
                    tts_provider=config.get("provider", "openai"),
                    tts_model=config.get("model", "tts-1"),
                    speakers=speakers,
                    migrated_from_podcast_config=config_id
                )
                await speaker_profile.save()
            
            # Create episode profile
            episode_profile_name = PodcastMigrationService._suggest_profile_name(config)
            
            # Build briefing from old fields
            briefing_parts = [
                f"Podcast: {config.get('podcast_name', 'Unknown')}",
                f"Tagline: {config.get('podcast_tagline', '')}",
                f"Language: {config.get('output_language', 'English')}",
            ]
            
            if config.get("conversation_style"):
                briefing_parts.append(f"Conversation Style: {', '.join(config.get('conversation_style', []))}")
            
            if config.get("engagement_technique"):
                briefing_parts.append(f"Engagement Techniques: {', '.join(config.get('engagement_technique', []))}")
            
            if config.get("user_instructions"):
                briefing_parts.append(f"Special Instructions: {config.get('user_instructions')}")
            
            default_briefing = "\n".join(briefing_parts)
            
            # Determine number of segments from dialogue_structure
            num_segments = len(config.get("dialogue_structure", [])) if config.get("dialogue_structure") else 5
            num_segments = max(3, min(10, num_segments))  # Clamp between 3-10
            
            # Check if episode profile already exists
            existing_episode = await EpisodeProfile.get_by_name(episode_profile_name)
            if not existing_episode:
                episode_profile = EpisodeProfile(
                    name=episode_profile_name,
                    description=f"Migrated from podcast_config: {config.get('name')}",
                    speaker_config=speaker_profile_name,
                    outline_provider=config.get("transcript_model_provider", "openai"),
                    outline_model=config.get("transcript_model", "gpt-4o-mini"),
                    transcript_provider=config.get("transcript_model_provider", "openai"),
                    transcript_model=config.get("transcript_model", "gpt-4o-mini"),
                    default_briefing=default_briefing,
                    num_segments=num_segments,
                    migrated_from_podcast_config=config_id
                )
                await episode_profile.save()
            
            return {
                "episode_profile": episode_profile_name,
                "speaker_profile": speaker_profile_name
            }
            
        except Exception as e:
            logger.error(f"Failed to migrate config {config_id}: {e}")
            raise
    
    @staticmethod
    async def migrate_all_configs() -> Dict[str, Any]:
        """Migrate all podcast_config records to new format"""
        try:
            configs = await repo_query("SELECT * FROM podcast_config")
            
            results = {
                "total_configs": len(configs),
                "migrated": 0,
                "failed": 0,
                "skipped": 0,
                "episode_profiles_created": set(),
                "speaker_profiles_created": set(),
                "errors": []
            }
            
            for config in configs:
                try:
                    # Check if already migrated
                    episode_name = PodcastMigrationService._suggest_profile_name(config)
                    existing = await EpisodeProfile.get_by_name(episode_name)
                    
                    if existing and existing.migrated_from_podcast_config:
                        results["skipped"] += 1
                        continue
                    
                    # Migrate the config
                    profiles = await PodcastMigrationService.migrate_config_to_profiles(config["id"])
                    
                    results["migrated"] += 1
                    results["episode_profiles_created"].add(profiles["episode_profile"])
                    results["speaker_profiles_created"].add(profiles["speaker_profile"])
                    
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append({
                        "config_id": config.get("id"),
                        "config_name": config.get("name"),
                        "error": str(e)
                    })
            
            # Convert sets to lists for JSON serialization
            results["episode_profiles_created"] = list(results["episode_profiles_created"])
            results["speaker_profiles_created"] = list(results["speaker_profiles_created"])
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to migrate all configs: {e}")
            raise
```

#### 4.4 Create Migration Endpoints
```python
# api/routers/migration.py
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from api.migration_service import PodcastMigrationService
from loguru import logger

router = APIRouter()

@router.get("/migration/podcast-analysis")
async def analyze_podcast_configs() -> Dict[str, Any]:
    """Analyze existing podcast_config records for migration planning"""
    try:
        analysis = await PodcastMigrationService.analyze_existing_configs()
        return {
            "success": True,
            "analysis": analysis
        }
    except Exception as e:
        logger.error(f"Failed to analyze podcast configs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze podcast configurations: {str(e)}"
        )

@router.post("/migration/podcast-config/{config_id}")
async def migrate_specific_config(config_id: str) -> Dict[str, Any]:
    """Migrate a specific podcast_config to Episode and Speaker profiles"""
    try:
        profiles = await PodcastMigrationService.migrate_config_to_profiles(config_id)
        return {
            "success": True,
            "message": f"Successfully migrated config {config_id}",
            "profiles": profiles
        }
    except Exception as e:
        logger.error(f"Failed to migrate config {config_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to migrate configuration: {str(e)}"
        )

@router.post("/migration/podcast-configs/all")
async def migrate_all_configs() -> Dict[str, Any]:
    """Migrate all podcast_config records to Episode and Speaker profiles"""
    try:
        results = await PodcastMigrationService.migrate_all_configs()
        return {
            "success": True,
            "message": "Migration completed",
            "results": results
        }
    except Exception as e:
        logger.error(f"Failed to migrate all configs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to migrate all configurations: {str(e)}"
        )

@router.get("/migration/status")
async def get_migration_status() -> Dict[str, Any]:
    """Get current migration status"""
    try:
        from open_notebook.database.repository import repo_query
        
        # Check migration version
        version_result = await repo_query("SELECT * FROM open_notebook:migration_version")
        current_version = version_result[0]["version"] if version_result else 0
        
        # Count records
        configs = await repo_query("SELECT count() as count FROM podcast_config")
        episode_profiles = await repo_query("SELECT count() as count FROM episode_profile")
        speaker_profiles = await repo_query("SELECT count() as count FROM speaker_profile")
        
        return {
            "migration_version": current_version,
            "schema_ready": current_version >= 7,
            "podcast_configs": configs[0]["count"] if configs else 0,
            "episode_profiles": episode_profiles[0]["count"] if episode_profiles else 0,
            "speaker_profiles": speaker_profiles[0]["count"] if speaker_profiles else 0
        }
    except Exception as e:
        logger.error(f"Failed to get migration status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get migration status: {str(e)}"
        )
```

### ✅ Testing Strategy
1. **Schema Creation**: Verify new tables are created correctly
2. **Migration Analysis**: Test analysis of existing podcast_config records
3. **Single Migration**: Test migrating one podcast_config successfully
4. **Bulk Migration**: Test migrating all configs with error handling
5. **Rollback**: Verify rollback script works correctly
6. **Data Integrity**: Ensure migrated profiles work with podcast generation

### 🧪 Manual Testing Commands
```bash
# 1. Check migration status
curl "http://localhost:5055/api/migration/status"

# 2. Analyze existing configs
curl "http://localhost:5055/api/migration/podcast-analysis"

# 3. Migrate specific config
curl -X POST "http://localhost:5055/api/migration/podcast-config/{config_id}"

# 4. Migrate all configs
curl -X POST "http://localhost:5055/api/migration/podcast-configs/all"

# 5. Verify new profiles work
curl "http://localhost:5055/api/episode-profiles"
curl "http://localhost:5055/api/speaker-profiles"

# 6. Test generation with migrated profile
curl -X POST "http://localhost:5055/api/podcasts/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "notebook_id": "test_notebook",
    "episode_profile_name": "migrated_profile_name",
    "episode_name": "migration_test"
  }'
```

### ⚠️ Critical Notes
- **Data Preservation**: All existing podcast_config data is preserved
- **Backward Compatibility**: Old configs remain accessible during transition
- **Migration Tracking**: All profiles track their migration source
- **Rollback Safety**: Complete rollback script available if needed
- **Validation Required**: Test migrated profiles generate podcasts correctly
- **🛑 COMPLETE**: Epic implementation finished - request final review

---

## 📋 Implementation Summary & Progress Tracking

### Phase Completion Status
- [x] **Phase 1**: Async Foundation (OSS-137) - ✅ COMPLETED (4 hours actual)
- [ ] **Phase 2**: Engine Integration (OSS-138) - 4 hours estimated  
- [ ] **Phase 3**: UI Modernization (OSS-139) - 3 hours estimated
- [ ] **Phase 4**: Data Migration (OSS-141) - 3 hours estimated

### Session Tracking Template

```markdown
## Session [Date] - Phase [N] Progress

### Completed Tasks
- [ ] Task 1
- [ ] Task 2

### Testing Results
- [ ] Test scenario 1
- [ ] Test scenario 2

### Issues Encountered
- Issue description and resolution

### Next Session Plan
- What to tackle next
- Any blockers to address

### Human Approval Required
- [ ] Phase completion review
- [ ] Ready to proceed to next phase
```

### Key Success Metrics
- [x] **Async Foundation**: Background job processing working ✅ COMPLETED
- [x    ] **Episode Profiles**: 3-click workflow operational  ✅ COMPLETED PHASE 2
- [ ] **Professional Quality**: 2-3 minute generation time achieved
- [ ] **Competitive Advantage**: 1-4 speaker flexibility vs Google's 2-host limit
- [ ] **User Experience**: Non-blocking UI with status tracking
- [ ] **Data Migration**: All existing configs successfully migrated

### Final Deliverables
1. ✅ **Async Job Processing**: Surreal-commands integration ✅ COMPLETED PHASE 1
2. ✅ **Podcast Engine**: Podcast-creator with Episode Profiles ✅ COMPLETED PHASE 2
3. ⏳ **Simplified UI**: 3-click generation workflow
4. ⏳ **Professional Audio**: High-quality multi-speaker podcasts
5. ⏳ **Status Tracking**: Job monitoring without real-time updates
6. ⏳ **Data Migration**: Seamless transition from old system
7. ⏳ **Competitive Positioning**: Superior flexibility vs Google Notebook LM


---

**Total Epic Scope**: Professional podcast engine establishing Open Notebook as a superior alternative to Google Notebook LM with flexible speaker options, model choice, and 3-click user experience.