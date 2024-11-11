import re
import ssl

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger
from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
from youtube_transcript_api.formatters import TextFormatter  # type: ignore

from open_notebook.config import CONFIG
from open_notebook.exceptions import NoTranscriptFound
from open_notebook.graphs.content_processing.state import ContentState

ssl._create_default_https_context = ssl._create_unverified_context


async def get_video_title(video_id):
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                html = await response.text()

        # BeautifulSoup doesn't support async operations
        soup = BeautifulSoup(html, "html.parser")

        # YouTube stores title in a meta tag
        title = soup.find("meta", property="og:title")["content"]
        return title

    except Exception as e:
        logger.error(f"Failed to get video title: {e}")
        return None


def _extract_youtube_id(url):
    """
    Extract the YouTube video ID from a given URL using regular expressions.

    Args:
    url (str): The YouTube URL from which to extract the video ID.

    Returns:
    str: The extracted YouTube video ID or None if no valid ID is found.
    """
    # Define a regular expression pattern to capture the YouTube video ID
    youtube_regex = (
        r"(?:https?://)?"  # Optional scheme
        r"(?:www\.)?"  # Optional www.
        r"(?:"
        r"youtu\.be/"  # Shortened URL
        r"|youtube\.com"  # Main URL
        r"(?:"  # Group start
        r"/embed/"  # Embed URL
        r"|/v/"  # Older video URL
        r"|/watch\?v="  # Standard watch URL
        r"|/watch\?.+&v="  # Other watch URL
        r")"  # Group end
        r")"  # End main group
        r"([\w-]{11})"  # 11 characters (YouTube video ID)
    )

    # Search the URL for the pattern
    match = re.search(youtube_regex, url)

    # Return the video ID if a match is found
    return match.group(1) if match else None


async def get_best_transcript(video_id, preferred_langs=["en", "es", "pt"]):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # First try: Manual transcripts in preferred languages
        manual_transcripts = []
        try:
            for transcript in transcript_list:
                if not transcript.is_generated and not transcript.is_translatable:
                    manual_transcripts.append(transcript)

            if manual_transcripts:
                # Sort based on preferred language order
                for lang in preferred_langs:
                    for transcript in manual_transcripts:
                        if transcript.language_code == lang:
                            return transcript.fetch()
                # If no preferred language found, return first manual transcript
                return manual_transcripts[0].fetch()
        except NoTranscriptFound:
            pass

        # Second try: Auto-generated transcripts in preferred languages
        generated_transcripts = []
        try:
            for transcript in transcript_list:
                if transcript.is_generated and not transcript.is_translatable:
                    generated_transcripts.append(transcript)

            if generated_transcripts:
                # Sort based on preferred language order
                for lang in preferred_langs:
                    for transcript in generated_transcripts:
                        if transcript.language_code == lang:
                            return transcript.fetch()
                # If no preferred language found, return first generated transcript
                return generated_transcripts[0].fetch()
        except NoTranscriptFound:
            pass

        # Last try: Translated transcripts in preferred languages
        translated_transcripts = []
        try:
            for transcript in transcript_list:
                if transcript.is_translatable:
                    translated_transcripts.append(transcript)

            if translated_transcripts:
                # Sort based on preferred language order
                for lang in preferred_langs:
                    for transcript in translated_transcripts:
                        if transcript.language_code == lang:
                            return transcript.fetch()
                # If no preferred language found, return translation to first preferred language
                translation = translated_transcripts[0].translate(preferred_langs[0])
                return translation.fetch()
        except NoTranscriptFound:
            pass

        raise Exception("No suitable transcript found")

    except Exception as e:
        logger.error(f"Failed to get transcript for video {video_id}: {e}")
        return None


async def extract_youtube_transcript(state: ContentState):
    """
    Parse the text file and print its content.
    """

    languages = CONFIG.get("youtube_transcripts", {}).get(
        "preferred_languages", ["en", "es", "pt"]
    )

    video_id = _extract_youtube_id(state.get("url"))
    transcript = await get_best_transcript(video_id, languages)

    logger.debug(f"Found transcript: {transcript}")
    formatter = TextFormatter()
    try:
        title = await get_video_title(video_id)
    except Exception as e:
        logger.critical(f"Failed to get video title for video_id: {video_id}")
        logger.exception(e)
        title = None
    return {
        "content": formatter.format_transcript(transcript),
        "title": title,
    }
