import asyncio
import os
from functools import partial
from math import ceil

from loguru import logger
from pydub import AudioSegment

from open_notebook.domain.models import model_manager
from open_notebook.graphs.content_processing.state import ContentState

# todo: remove reference to model_manager
# future: parallelize the transcription process


async def split_audio(input_file, segment_length_minutes=15, output_prefix=None):
    """
    Split an audio file into segments asynchronously.
    """

    def _split(input_file, segment_length_minutes, output_prefix):
        # Convert input file to absolute path
        input_file_abs = os.path.abspath(input_file)
        output_dir = os.path.dirname(input_file_abs)
        os.makedirs(output_dir, exist_ok=True)

        # Set up output prefix
        if output_prefix is None:
            output_prefix = os.path.splitext(os.path.basename(input_file_abs))[0]

        # Load the audio file
        audio = AudioSegment.from_file(input_file_abs)

        # Calculate segment length in milliseconds
        segment_length_ms = segment_length_minutes * 60 * 1000

        # Calculate number of segments
        total_segments = ceil(len(audio) / segment_length_ms)
        logger.debug(f"Splitting file: {input_file_abs} into {total_segments} segments")

        output_files = []

        # Split the audio into segments
        for i in range(total_segments):
            start_time = i * segment_length_ms
            end_time = min((i + 1) * segment_length_ms, len(audio))

            # Extract segment
            segment = audio[start_time:end_time]

            # Generate output filename
            output_filename = f"{output_prefix}_{str(i+1).zfill(3)}.mp3"
            output_path = os.path.join(output_dir, output_filename)

            # Export segment
            segment.export(output_path, format="mp3")
            output_files.append(output_path)

            logger.debug(f"Exported segment {i+1}/{total_segments}: {output_filename}")

        return output_files

    # Run CPU-bound audio processing in thread pool
    return await asyncio.get_event_loop().run_in_executor(
        None, partial(_split, input_file, segment_length_minutes, output_prefix)
    )


async def transcribe_audio_segment(audio_file, model):
    """Transcribe a single audio segment asynchronously"""

    def _transcribe(audio_file, model):
        return model.transcribe(audio_file)

    return await asyncio.get_event_loop().run_in_executor(
        None, partial(_transcribe, audio_file, model)
    )


async def extract_audio(data: ContentState):
    SPEECH_TO_TEXT_MODEL = model_manager.speech_to_text
    input_audio_path = data.get("file_path")
    audio_files = []

    try:
        # Split audio into segments
        audio_files = await split_audio(input_audio_path)

        # Transcribe all segments concurrently
        transcribe_tasks = [
            transcribe_audio_segment(audio_file, SPEECH_TO_TEXT_MODEL)
            for audio_file in audio_files
        ]
        transcriptions = await asyncio.gather(*transcribe_tasks)

        return {"content": " ".join(transcriptions)}

    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        logger.exception(e)
        raise

    finally:
        # Clean up temporary files
        def _cleanup(files):
            for file in files:
                try:
                    os.remove(file)
                except OSError as e:
                    logger.error(f"Error removing temporary file {file}: {str(e)}")

        await asyncio.get_event_loop().run_in_executor(
            None, partial(_cleanup, audio_files)
        )
