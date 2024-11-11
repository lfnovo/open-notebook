import asyncio
import json
import os
import subprocess
from functools import partial

from loguru import logger

from open_notebook.graphs.content_processing.state import ContentState


async def extract_audio_from_video(input_file, output_file, stream_index):
    """
    Extract the specified audio stream to MP3 format asynchronously
    """

    def _extract(input_file, output_file, stream_index):
        try:
            cmd = [
                "ffmpeg",
                "-i",
                input_file,
                "-map",
                f"0:a:{stream_index}",  # Select specific audio stream
                "-codec:a",
                "libmp3lame",  # Use MP3 codec
                "-q:a",
                "2",  # High quality setting
                "-y",  # Overwrite output file if exists
                output_file,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"FFmpeg failed: {result.stderr}")

            return True

        except Exception as e:
            logger.error(f"Error extracting audio: {str(e)}")
            return False

    return await asyncio.get_event_loop().run_in_executor(
        None, partial(_extract, input_file, output_file, stream_index)
    )


async def get_audio_streams(input_file):
    """
    Analyze video file and return information about all audio streams asynchronously
    """

    def _analyze(input_file):
        logger.debug(f"Analyzing video file {input_file} for audio streams")
        try:
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_streams",
                "-select_streams",
                "a",
                input_file,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"FFprobe failed: {result.stderr}")

            data = json.loads(result.stdout)
            return data.get("streams", [])

        except Exception as e:
            logger.error(f"Error analyzing file: {str(e)}")
            return []

    return await asyncio.get_event_loop().run_in_executor(
        None, partial(_analyze, input_file)
    )


async def select_best_audio_stream(streams):
    """
    Select the best audio stream based on various quality metrics
    """

    def _select(streams):
        if not streams:
            logger.debug("No audio streams found")
            return None
        else:
            logger.debug(f"Found {len(streams)} audio streams")

        # Score each stream based on various factors
        scored_streams = []
        for stream in streams:
            score = 0

            # Prefer higher bit rates
            bit_rate = stream.get("bit_rate")
            if bit_rate:
                score += int(int(bit_rate) / 1000000)  # Convert to Mbps and ensure int

            # Prefer more channels (stereo over mono)
            channels = stream.get("channels", 0)
            score += channels * 10

            # Prefer higher sample rates
            sample_rate = stream.get("sample_rate", "0")
            score += int(int(sample_rate) / 48000)

            scored_streams.append((score, stream))

        # Return the stream with highest score
        return max(scored_streams, key=lambda x: x[0])[1]

    return await asyncio.get_event_loop().run_in_executor(
        None, partial(_select, streams)
    )


async def extract_best_audio_from_video(data: ContentState):
    """
    Main function to extract the best audio stream from a video file asynchronously
    """
    input_file = data.get("file_path")
    assert input_file is not None, "Input file path must be provided"

    def _check_file(path):
        return os.path.exists(path)

    file_exists = await asyncio.get_event_loop().run_in_executor(
        None, partial(_check_file, input_file)
    )

    if not file_exists:
        logger.critical(f"Input file not found: {input_file}")
        return False

    base_name = os.path.splitext(input_file)[0]
    output_file = f"{base_name}_audio.mp3"

    # Get all audio streams
    streams = await get_audio_streams(input_file)
    if not streams:
        logger.debug("No audio streams found in the file")
        return False

    # Select best stream
    best_stream = await select_best_audio_stream(streams)
    if not best_stream:
        logger.error("Could not determine best audio stream")
        return False

    # Extract the selected stream
    stream_index = streams.index(best_stream)
    success = await extract_audio_from_video(input_file, output_file, stream_index)

    if success:
        logger.debug(f"Successfully extracted audio to: {output_file}")
        logger.debug(f"- Channels: {best_stream.get('channels', 'unknown')}")
        logger.debug(f"- Sample rate: {best_stream.get('sample_rate', 'unknown')} Hz")
        logger.debug(f"- Bit rate: {best_stream.get('bit_rate', 'unknown')} bits/s")

    return {"file_path": output_file, "identified_type": "audio/mp3"}
