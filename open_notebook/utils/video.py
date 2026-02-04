"""Video processing utilities using FFmpeg."""
import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from loguru import logger


async def get_video_duration(video_path: str) -> float:
    """
    Get video duration in seconds using ffprobe.

    Args:
        video_path: Path to the video file

    Returns:
        Duration in seconds

    Raises:
        RuntimeError: If ffprobe fails
    """
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {stderr.decode()}")

    return float(stdout.decode().strip())


def calculate_frame_params(duration: float) -> Tuple[float, int]:
    """
    Calculate optimal fps and max_frames based on video duration.

    Dynamically adjusts frame sampling to ensure full video coverage
    while keeping total frames reasonable for API costs.

    | Duration   | Sample Rate | Max Frames | Coverage         |
    |------------|-------------|------------|------------------|
    | ≤ 60s      | 1 fps       | 60         | Every second     |
    | 61s - 5min | 0.5 fps     | 150        | Every 2 seconds  |
    | 5min - 15m | 0.2 fps     | 180        | Every 5 seconds  |
    | > 15min    | 0.1 fps     | 180        | Every 10 seconds |

    Args:
        duration: Video duration in seconds

    Returns:
        Tuple of (fps, max_frames)
    """
    if duration <= 60:
        # Short videos: 1 frame per second, max 60 frames
        return (1.0, 60)
    elif duration <= 300:  # 5 minutes
        # Medium videos: 1 frame per 2 seconds, max 150 frames
        return (0.5, 150)
    elif duration <= 900:  # 15 minutes
        # Long videos: 1 frame per 5 seconds, max 180 frames
        return (0.2, 180)
    else:
        # Very long videos: 1 frame per 10 seconds, max 180 frames
        return (0.1, 180)


async def extract_frames(
    video_path: str,
    fps: float = 1.0,
    max_frames: int = 60,
    output_dir: Optional[str] = None,
) -> List[Tuple[str, float]]:
    """
    Extract frames from video at specified FPS.

    Args:
        video_path: Path to the video file
        fps: Frames per second to extract (default 1.0)
        max_frames: Maximum number of frames to extract (default 60)
        output_dir: Directory to save frames (creates temp dir if None)

    Returns:
        List of (frame_path, timestamp_seconds) tuples
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="video_frames_")

    output_pattern = os.path.join(output_dir, "frame_%04d.jpg")

    # Extract frames at specified FPS
    cmd = [
        "ffmpeg",
        "-i",
        video_path,
        "-vf",
        f"fps={fps}",
        "-frames:v",
        str(max_frames),
        "-q:v",
        "2",  # High quality JPEG
        output_pattern,
        "-y",  # Overwrite existing files
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        logger.warning(f"FFmpeg stderr: {stderr.decode()}")

    # Collect extracted frames with timestamps
    frames = []
    for i, frame_file in enumerate(sorted(Path(output_dir).glob("frame_*.jpg"))):
        timestamp = i / fps  # Calculate timestamp based on FPS
        frames.append((str(frame_file), timestamp))
        if len(frames) >= max_frames:
            break

    logger.info(f"Extracted {len(frames)} frames from video at {fps} fps")
    return frames


async def extract_audio(video_path: str, output_path: Optional[str] = None) -> str:
    """
    Extract audio track from video as WAV file.

    Args:
        video_path: Path to the video file
        output_path: Path for output WAV file (creates temp file if None)

    Returns:
        Path to the extracted audio file

    Raises:
        RuntimeError: If audio extraction fails
    """
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".wav", prefix="video_audio_")
        os.close(fd)

    cmd = [
        "ffmpeg",
        "-i",
        video_path,
        "-vn",  # No video
        "-acodec",
        "pcm_s16le",  # WAV format
        "-ar",
        "16000",  # 16kHz sample rate (good for speech)
        "-ac",
        "1",  # Mono
        output_path,
        "-y",  # Overwrite existing files
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(f"Audio extraction failed: {stderr.decode()}")

    logger.info(f"Extracted audio to {output_path}")
    return output_path


def cleanup_temp_files(paths: List[str]) -> None:
    """
    Remove temporary files and directories.

    Args:
        paths: List of file or directory paths to remove
    """
    for path in paths:
        if path is None:
            continue
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
                logger.debug(f"Removed temp directory: {path}")
            elif os.path.isfile(path):
                os.unlink(path)
                logger.debug(f"Removed temp file: {path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {path}: {e}")
