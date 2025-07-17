from typing import ClassVar, List, Optional

from loguru import logger
from podcastfy.client import generate_podcast
from pydantic import Field, field_validator, model_validator

from open_notebook.config import DATA_FOLDER
from open_notebook.domain.notebook import ObjectModel


class PodcastEpisode(ObjectModel):
    table_name: ClassVar[str] = "podcast_episode"
    name: str
    template: str
    instructions: str
    text: str
    audio_file: str


class PodcastConfig(ObjectModel):
    table_name: ClassVar[str] = "podcast_config"
    name: str
    podcast_name: str
    podcast_tagline: str
    output_language: str = Field(default="English")
    person1_role: List[str]
    person2_role: List[str]
    conversation_style: List[str]
    engagement_technique: List[str]
    dialogue_structure: List[str]
    transcript_model: Optional[str] = None
    transcript_model_provider: Optional[str] = None
    user_instructions: Optional[str] = None
    ending_message: Optional[str] = None
    creativity: float = Field(ge=0, le=1)
    provider: str = Field(default="openai")
    voice1: str
    voice2: str
    model: str

    # Backwards compatibility
    @field_validator("person1_role", "person2_role", mode="before")
    @classmethod
    def split_string_to_list(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",")]
        return value

    @model_validator(mode="after")
    def validate_voices(self) -> "PodcastConfig":
        if not self.voice1 or not self.voice2:
            raise ValueError("Both voice1 and voice2 must be provided")
        return self

    async def generate_episode(
        self,
        episode_name: str,
        text: str,
        instructions: str = "",
        longform: bool = False,
        chunks: int = 8,
        min_chunk_size=600,
    ):
        self.user_instructions = (
            instructions if instructions else self.user_instructions
        )
        conversation_config = {
            "max_num_chunks": chunks,
            "min_chunk_size": min_chunk_size,
            "conversation_style": self.conversation_style,
            "roles_person1": self.person1_role,
            "roles_person2": self.person2_role,
            "dialogue_structure": self.dialogue_structure,
            "podcast_name": self.podcast_name,
            "podcast_tagline": self.podcast_tagline,
            "output_language": self.output_language,
            "user_instructions": self.user_instructions,
            "engagement_techniques": self.engagement_technique,
            "creativity": self.creativity,
            "text_to_speech": {
                "output_directories": {
                    "transcripts": f"{DATA_FOLDER}/podcasts/transcripts",
                    "audio": f"{DATA_FOLDER}/podcasts/audio",
                },
                "temp_audio_dir": f"{DATA_FOLDER}/podcasts/audio/tmp",
                "ending_message": "Thank you for listening to this episode. Don't forget to subscribe to our podcast for more interesting conversations.",
                "default_tts_model": self.provider,
                self.provider: {
                    "default_voices": {
                        "question": self.voice1,
                        "answer": self.voice2,
                    },
                    "model": self.model,
                },
                "audio_format": "mp3",
            },
        }

        api_key_label = None
        llm_model_name = None
        tts_model = None

        if self.transcript_model_provider:
            if self.transcript_model_provider == "openai":
                api_key_label = "OPENAI_API_KEY"
                llm_model_name = self.transcript_model
            elif self.transcript_model_provider == "anthropic":
                api_key_label = "ANTHROPIC_API_KEY"
                llm_model_name = self.transcript_model
            elif self.transcript_model_provider == "gemini":
                api_key_label = "GOOGLE_API_KEY"
                llm_model_name = self.transcript_model

        if self.provider == "google":
            tts_model = "gemini"
        elif self.provider == "openai":
            tts_model = "openai"
        elif self.provider == "anthropic":
            tts_model = "anthropic"
        elif self.provider == "vertexai":
            tts_model = "geminimulti"
        elif self.provider == "elevenlabs":
            tts_model = "elevenlabs"

        logger.info(
            f"Generating episode {episode_name} with config {conversation_config} and using model {llm_model_name}, tts model {tts_model}"
        )

        try:
            audio_file = generate_podcast(
                conversation_config=conversation_config,
                text=text,
                tts_model=tts_model,
                llm_model_name=llm_model_name,
                api_key_label=api_key_label,
                longform=longform,
            )
            episode = PodcastEpisode(
                name=episode_name,
                template=self.name,
                instructions=instructions,
                text=str(text),
                audio_file=audio_file,
            )
            await episode.save()
        except Exception as e:
            logger.error(f"Failed to generate episode {episode_name}: {e}")
            raise

    @field_validator(
        "name", "podcast_name", "podcast_tagline", "output_language", "model"
    )
    @classmethod
    def validate_required_strings(cls, value: str, field) -> str:
        if value is None or value.strip() == "":
            raise ValueError(f"{field.field_name} cannot be None or empty string")
        return value.strip()

    @field_validator("creativity")
    def validate_creativity(cls, value):
        if not 0 <= value <= 1:
            raise ValueError("Creativity must be between 0 and 1")
        return value


conversation_styles = [
    "Analytical",
    "Argumentative",
    "Informative",
    "Humorous",
    "Casual",
    "Formal",
    "Inspirational",
    "Debate-style",
    "Interview-style",
    "Storytelling",
    "Satirical",
    "Educational",
    "Philosophical",
    "Speculative",
    "Motivational",
    "Fun",
    "Technical",
    "Light-hearted",
    "Serious",
    "Investigative",
    "Debunking",
    "Didactic",
    "Thought-provoking",
    "Controversial",
    "Sarcastic",
    "Emotional",
    "Exploratory",
    "Fast-paced",
    "Slow-paced",
    "Introspective",
]

# Dialogue Structures
dialogue_structures = [
    "Topic Introduction",
    "Opening Monologue",
    "Guest Introduction",
    "Icebreakers",
    "Historical Context",
    "Defining Terms",
    "Problem Statement",
    "Overview of the Issue",
    "Deep Dive into Subtopics",
    "Pro Arguments",
    "Con Arguments",
    "Cross-examination",
    "Expert Interviews",
    "Case Studies",
    "Myth Busting",
    "Q&A Session",
    "Rapid-fire Questions",
    "Summary of Key Points",
    "Recap",
    "Key Takeaways",
    "Actionable Tips",
    "Call to Action",
    "Future Outlook",
    "Closing Remarks",
    "Resource Recommendations",
    "Trending Topics",
    "Closing Inspirational Quote",
    "Final Reflections",
]

# Podcast Participant Roles
participant_roles = [
    "Main Summarizer",
    "Questioner/Clarifier",
    "Optimist",
    "Skeptic",
    "Specialist",
    "Thesis Presenter",
    "Counterargument Provider",
    "Professor",
    "Student",
    "Moderator",
    "Host",
    "Co-host",
    "Expert Guest",
    "Novice",
    "Devil's Advocate",
    "Analyst",
    "Storyteller",
    "Fact-checker",
    "Comedian",
    "Interviewer",
    "Interviewee",
    "Historian",
    "Visionary",
    "Strategist",
    "Critic",
    "Enthusiast",
    "Mediator",
    "Commentator",
    "Researcher",
    "Reporter",
    "Advocate",
    "Debater",
    "Explorer",
]

# Engagement Techniques
engagement_techniques = [
    "Rhetorical Questions",
    "Anecdotes",
    "Analogies",
    "Humor",
    "Metaphors",
    "Storytelling",
    "Quizzes",
    "Personal Testimonials",
    "Quotes",
    "Jokes",
    "Emotional Appeals",
    "Provocative Statements",
    "Sarcasm",
    "Pop Culture References",
    "Thought Experiments",
    "Puzzles and Riddles",
    "Role-playing",
    "Debates",
    "Catchphrases",
    "Statistics and Facts",
    "Open-ended Questions",
    "Challenges to Assumptions",
    "Evoking Curiosity",
]
