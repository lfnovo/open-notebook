"""Synthesize multi-stream video analysis into coherent content."""
from typing import List, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from open_notebook.utils.vision import format_timestamp


async def synthesize_video_content(
    frame_descriptions: List[Tuple[float, str]],  # (timestamp, description)
    transcript: Optional[str] = None,
    sound_events: Optional[List[Tuple[float, str]]] = None,  # Future use
    model=None,  # LangChain model for synthesis
) -> str:
    """
    Combine frame descriptions, transcript, and sound events into coherent content.

    Args:
        frame_descriptions: List of (timestamp_seconds, description) tuples
        transcript: Optional audio transcript text
        sound_events: Optional list of (timestamp_seconds, event) tuples (future use)
        model: Optional LangChain model for synthesizing narrative

    Returns:
        Combined analysis content as markdown
    """
    # Build structured content
    sections = []

    # Visual content section
    if frame_descriptions:
        visual_lines = ["## Visual Content\n"]
        for timestamp, desc in sorted(frame_descriptions, key=lambda x: x[0]):
            ts_str = format_timestamp(timestamp)
            visual_lines.append(f"**[{ts_str}]** {desc}\n")
        sections.append("\n".join(visual_lines))

    # Transcript section
    if transcript:
        sections.append(f"## Audio Transcript\n\n{transcript}")

    # Sound events section (future use)
    if sound_events:
        sound_lines = ["## Sound Events\n"]
        for timestamp, event in sorted(sound_events, key=lambda x: x[0]):
            ts_str = format_timestamp(timestamp)
            sound_lines.append(f"**[{ts_str}]** {event}")
        sections.append("\n".join(sound_lines))

    combined_content = "\n\n---\n\n".join(sections)

    # If no content at all, return placeholder
    if not combined_content.strip():
        return "# Video Analysis\n\nNo content could be extracted from this video."

    # Optional: Use LLM to synthesize into narrative
    if model and (frame_descriptions or transcript):
        try:
            synthesis_prompt = """You are analyzing a video. Given the visual descriptions, transcript, and sound events below, create a coherent summary that:
1. Describes what happens in the video chronologically
2. Integrates visual and audio information
3. Highlights key moments and themes

Keep the summary informative but concise."""

            messages = [
                SystemMessage(content=synthesis_prompt),
                HumanMessage(content=combined_content),
            ]

            logger.debug("Synthesizing video content with LLM")
            response = await model.ainvoke(messages)

            # Return both synthesis and raw analysis
            return f"# Video Analysis\n\n{response.content}\n\n---\n\n# Detailed Analysis\n\n{combined_content}"
        except Exception as e:
            logger.warning(f"LLM synthesis failed, returning raw analysis: {e}")
            return f"# Video Analysis\n\n{combined_content}"

    return f"# Video Analysis\n\n{combined_content}"
