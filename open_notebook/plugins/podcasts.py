from typing import ClassVar, List, Literal, Optional

from loguru import logger
from podcastfy.client import generate_podcast
from pydantic import Field, field_validator

from open_notebook.domain import ObjectModel


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
    person1_role: str
    person2_role: str
    conversation_style: List[str]
    engagement_technique: List[str]
    dialogue_structure: List[str]
    user_instructions: Optional[str] = None
    ending_message: Optional[str] = None
    wordcount: int = Field(ge=400, le=10000)
    creativity: float = Field(ge=0, le=1)
    provider: Literal["openai", "elevenlabs", "edge"] = Field(default="openai")
    voice1: Optional[str] = None
    voice2: Optional[str] = None
    model: str

    def generate_episode(self, episode_name, text, instructions=None):
        self.user_instructions = (
            instructions if instructions else self.user_instructions
        )
        conversation_config = {
            "word_count": self.wordcount,
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
                # "temp_audio_dir": f"{PODCASTS_FOLDER}/tmp",
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

        logger.debug(
            f"Generating episode {episode_name} with config {conversation_config}"
        )

        audio_file = generate_podcast(
            conversation_config=conversation_config, text=text, tts_model=self.provider
        )
        episode = PodcastEpisode(
            name=episode_name,
            template=self.name,
            instructions=instructions,
            text=str(text),
            audio_file=audio_file,
        )
        episode.save()

    @field_validator(
        "name", "podcast_name", "podcast_tagline", "output_language", "model"
    )
    @classmethod
    def validate_required_strings(cls, value: str, field) -> str:
        if value is None or value.strip() == "":
            raise ValueError(f"{field.field_name} cannot be None or empty string")
        return value.strip()

    @field_validator("wordcount")
    def validate_wordcount(cls, value):
        if not 400 <= value <= 6000:
            raise ValueError("Wordcount must be between 400 and 10000")
        return value

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
    "Reflective",
    "Narrative",
    "Satirical",
    "Educational",
    "Conversational",
    "Critical",
    "Empathetic",
    "Philosophical",
    "Speculative",
    "Motivational",
    "Fun",
    "Technical",
    "Light-hearted",
    "Serious",
    "Investigative",
    "Debunking",
    "Collaborative",
    "Didactic",
    "Thought-provoking",
    "Controversial",
    "Skeptical",
    "Optimistic",
    "Pessimistic",
    "Objective",
    "Subjective",
    "Sarcastic",
    "Emotional",
    "Exploratory",
    "Friendly",
    "Fast-paced",
    "Slow-paced",
    "Introspective",
    "Open-ended",
    "Affirmative",
    "Dissenting",
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
    "Rebuttal",
    "Expert Interviews",
    "Panel Discussion",
    "Case Studies",
    "Myth Busting",
    "Debunking Misconceptions",
    "Audience Questions",
    "Q&A Session",
    "Listener Feedback",
    "Rapid-fire Questions",
    "Summary of Key Points",
    "Recap",
    "Key Takeaways",
    "Actionable Tips",
    "Call to Action",
    "Future Outlook",
    "Teaser for Next Episode",
    "Closing Remarks",
    "Thank You and Credits",
    "Outtakes or Bloopers",
    "Sponsor Messages",
    "Social Media Shout-outs",
    "Resource Recommendations",
    "Feedback Request",
    "Lightning Round",
    "Behind-the-Scenes Insights",
    "Ethical Considerations",
    "Fact-checking Segment",
    "Trending Topics",
    "Closing Inspirational Quote",
    "Final Reflections",
    "Debrief",
    "Farewell Messages",
    "Next Episode Preview",
    "Live Reactions",
    "Call-in Segment",
    "Acknowledgements",
    "Transition Segments",
    "Break Segments",
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
    "Influencer",
    "Observer",
    "Listener",
    "Facilitator",
    "Innovator",
    "Debater",
    "Educator",
    "Motivator",
    "Narrator",
    "Explorer",
    "Opponent",
    "Proponent",
    "Philosopher",
    "Engineer",
    "Doctor",
    "Psychologist",
    "Economist",
    "Politician",
    "Scientist",
    "Entrepreneur",
    "Artist",
    "Author",
    "Journalist",
    "Activist",
    "Challenger",
    "Supporter",
    "Mentor",
    "Mentee",
    "Panelist",
    "Audience Representative",
    "Case Study Presenter",
    "Data Analyst",
    "Ethicist",
    "Cultural Critic",
    "Technologist",
    "Environmentalist",
    "Legal Expert",
    "Healthcare Professional",
    "Financial Advisor",
    "Policy Maker",
    "Sociologist",
    "Anthropologist",
    "Myth Buster",
    "Trend Analyst",
    "Futurist",
    "Negotiator",
    "Community Leader",
    "Voice of Reason",
    "Conflict Resolver",
    "Emotional Support",
    "Pragmatist",
    "Idealist",
    "Realist",
    "Satirist",
    "Story Analyst",
    "Language Expert",
    "Historical Witness",
    "Survivor",
    "Inspirational Figure",
    "Cultural Ambassador",
    "Digital Nomad",
    "Remote Correspondent",
    "Field Reporter",
    "Data Scientist",
    "Gamer",
    "Musician",
    "Filmmaker",
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
    "Polls",
    "Contests/Giveaways",
    "Guest Appearances",
    "Sound Effects",
    "Music Interludes",
    "Shout-outs",
    "Interactive Challenges",
    "Personal Testimonials",
    "Quotes",
    "Jokes",
    "Surprise Elements",
    "Emotional Appeals",
    "Provocative Statements",
    "Irony",
    "Sarcasm",
    "Alliteration",
    "Repetition",
    "Foreshadowing",
    "Cliffhangers",
    "Audience Participation",
    "Sensory Descriptions",
    "Visual Aids (if applicable)",
    "Callbacks to Earlier Points",
    "Pop Culture References",
    "Hyperbole",
    "Parables",
    "Thought Experiments",
    "Puzzles and Riddles",
    "Role-playing",
    "Mock Scenarios",
    "Debates",
    "Sound Bites",
    "Catchphrases",
    "Voice Modulation",
    "Interactive Games",
    "Live Demos",
    "Behind-the-Scenes Insights",
    "Vivid Imagery",
    "Statistics and Facts",
    "Open-ended Questions",
    "Challenges to Assumptions",
    "Evoking Curiosity",
    "Memes (if visual components are included)",
    "Surveys",
    "Testimonials",
    "Provocations",
]
