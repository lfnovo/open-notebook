import os
from math import ceil

from loguru import logger
from pydub import AudioSegment

from open_notebook.domain.models import model_manager
from open_notebook.graphs.content_processing.state import SourceState

# todo: remove reference to model_manager
# future: parallelize the transcription process


def split_audio(input_file, segment_length_minutes=15, output_prefix=None):
    """
    Split an audio file into segments of specified length.

    Args:
        input_file (str): Path to the input audio file
        segment_length_minutes (int): Length of each segment in minutes
        output_dir (str): Directory to save the segments (defaults to input file's directory)
        output_prefix (str): Prefix for output files (defaults to input filename)

    Returns:
        list: List of paths to the created segment files
    """
    # Convert input file to absolute path
    input_file = os.path.abspath(input_file)

    output_dir = os.path.dirname(input_file)
    os.makedirs(output_dir, exist_ok=True)

    # Set up output prefix
    if output_prefix is None:
        output_prefix = os.path.splitext(os.path.basename(input_file))[0]

    # Load the audio file
    audio = AudioSegment.from_file(input_file)

    # Calculate segment length in milliseconds
    segment_length_ms = segment_length_minutes * 60 * 1000

    # Calculate number of segments
    total_segments = ceil(len(audio) / segment_length_ms)
    logger.debug(f"Splitting file: {input_file} into {total_segments} segments")

    # List to store output file paths
    output_files = []

    # Split the audio into segments
    for i in range(total_segments):
        # Calculate start and end times for this segment
        start_time = i * segment_length_ms
        end_time = min((i + 1) * segment_length_ms, len(audio))

        # Extract segment
        segment = audio[start_time:end_time]

        # Generate output filename
        # Format: prefix_001.mp3 (padding with zeros ensures correct ordering)
        output_filename = f"{output_prefix}_{str(i+1).zfill(3)}.mp3"
        output_path = os.path.join(output_dir, output_filename)

        # Export segment
        segment.export(output_path, format="mp3")

        output_files.append(output_path)

        # Optional progress indication
        logger.debug(f"Exported segment {i+1}/{total_segments}: {output_filename}")

    return output_files


def extract_audio(data: SourceState):
    SPEECH_TO_TEXT_MODEL = model_manager.speech_to_text

    input_audio_path = data.get("file_path")
    audio_files = []

    try:
        audio_files = split_audio(input_audio_path)
        transcriptions = []

        for audio_file in audio_files:
            transcriptions.append(SPEECH_TO_TEXT_MODEL.transcribe(audio_file))

        return {"content": " ".join(transcriptions)}

    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        logger.exception(e)
        raise  # Re-raise the exception after logging

    finally:
        for file in audio_files:
            try:
                os.remove(file)
            except OSError as e:
                logger.error(f"Error removing temporary file {file}: {str(e)}")
