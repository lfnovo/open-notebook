"""Loopback-only speech adapter: MLX Whisper + installed macOS Turkish voice."""
import asyncio
import hmac
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
import imageio_ffmpeg
import numpy as np
from pydantic import BaseModel, Field

ROOT = Path(os.environ.get('LOCAL_AUDIO_ROOT', Path(__file__).resolve().parent))
KEY = (ROOT / '.audio-key').read_text().strip()
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
STT_MODEL = ROOT / 'models/whisper-small'
LIMIT = 100 * 1024 * 1024
STT_LOCK = threading.Lock()
TTS_LOCK = threading.Semaphore(2)
app = FastAPI(docs_url=None, redoc_url=None)
VOICES = {'default': 175, 'alloy': 175, 'nova': 175, 'echo': 155, 'onyx': 155,
          'fable': 190, 'shimmer': 190, 'yelda': 175, 'yelda-sakin': 155, 'yelda-hizli': 190}


@app.middleware('http')
async def authenticate(request: Request, call_next):
    if request.url.path != '/health' and not hmac.compare_digest(
            request.headers.get('authorization', ''), 'Bearer ' + KEY):
        return Response(json.dumps({'error': {'message': 'Local audio authentication required'}}),
                        status_code=401, media_type='application/json')
    length = request.headers.get('content-length')
    if length and (not length.isdigit() or int(length) > LIMIT):
        return Response(status_code=413)
    return await call_next(request)


@app.get('/health')
def health():
    return {'status': 'healthy', 'stt_model_ready': (STT_MODEL / 'config.json').exists(),
            'stt_active': STT_LOCK.locked(), 'tts_voice': 'Yelda', 'local_only': True}


@app.get('/v1/models')
def models():
    return {'object': 'list', 'data': [
        {'id': 'whisper-small-local', 'object': 'model', 'owned_by': 'local', 'created': 0},
        {'id': 'macos-turkish-tts', 'object': 'model', 'owned_by': 'local', 'created': 0}]}


@app.get('/v1/audio/voices')
def voices():
    return {'voices': [{'voice_id': v, 'name': v, 'language': 'tr-TR'}
                       for v in ('yelda', 'yelda-sakin', 'yelda-hizli')]}


class SpeechRequest(BaseModel):
    model: str
    input: str = Field(min_length=1, max_length=20000)
    voice: str = 'yelda'
    response_format: str = 'mp3'
    speed: float = Field(default=1, ge=0.5, le=2)


@app.post('/v1/audio/speech')
def speech(body: SpeechRequest):
    if body.model != 'macos-turkish-tts':
        raise HTTPException(404, 'Unknown local speech model')
    if body.voice not in VOICES:
        raise HTTPException(400, 'Supported voices: yelda, yelda-sakin, yelda-hizli')
    formats = {'mp3': ('mp3', 'audio/mpeg'), 'wav': ('wav', 'audio/wav'),
               'flac': ('flac', 'audio/flac'), 'opus': ('opus', 'audio/ogg'),
               'aac': ('adts', 'audio/aac'), 'pcm': ('s16le', 'audio/pcm')}
    if body.response_format not in formats:
        raise HTTPException(400, 'Unsupported audio format')
    if not TTS_LOCK.acquire(timeout=240):
        raise HTTPException(503, 'Local speech queue timed out')
    try:
        with tempfile.TemporaryDirectory(prefix='speech-', dir=ROOT / 'tmp') as folder:
            aiff = Path(folder) / 'speech.aiff'
            subprocess.run(['/usr/bin/say', '-v', 'Yelda', '-r',
                            str(round(VOICES[body.voice] * body.speed)), '-o', str(aiff), '-f', '-'],
                           input=body.input, text=True, check=True, capture_output=True, timeout=240)
            fmt, media = formats[body.response_format]
            data = subprocess.run([FFMPEG, '-nostdin', '-v', 'error', '-i', str(aiff),
                                   '-ac', '1', '-ar', '24000', '-f', fmt, 'pipe:1'],
                                  capture_output=True, check=True, timeout=60).stdout
            if not data:
                raise RuntimeError('Empty speech output')
            return Response(data, media_type=media)
    except (subprocess.SubprocessError, RuntimeError):
        raise HTTPException(502, 'Local speech generation failed')
    finally:
        TTS_LOCK.release()


def transcribe_file(path, language):
    if not STT_LOCK.acquire(timeout=240):
        raise HTTPException(503, 'Local transcription queue timed out')
    try:
        import mlx_whisper
        decoded = subprocess.run([FFMPEG, '-nostdin', '-v', 'error', '-i', str(path),
                                  '-f', 'f32le', '-ac', '1', '-ar', '16000', 'pipe:1'],
                                 capture_output=True, check=True, timeout=120).stdout
        audio = np.frombuffer(decoded, dtype=np.float32).copy()
        if not len(audio) or len(audio) > 16000 * 1800:
            raise HTTPException(400, 'Audio must be nonempty and at most 30 minutes per request')
        result = mlx_whisper.transcribe(audio, path_or_hf_repo=str(STT_MODEL),
                                        language=language or None, verbose=False,
                                        condition_on_previous_text=False)
        return {'text': result['text'].strip(), 'language': result.get('language', language),
                'duration': len(audio) / 16000,
                'segments': [{k: s[k] for k in ('id', 'start', 'end', 'text')}
                             for s in result.get('segments', [])]}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, 'Local transcription failed')
    finally:
        STT_LOCK.release()


@app.post('/v1/audio/transcriptions')
async def transcription(file: UploadFile = File(...), model: str = Form(...),
                        language: str = Form(''), response_format: str = Form('json')):
    if model != 'whisper-small-local':
        raise HTTPException(404, 'Unknown local transcription model')
    if response_format not in ('json', 'verbose_json', 'text'):
        raise HTTPException(400, 'Supported transcription formats: json, verbose_json, text')
    if language and (len(language) > 5 or not language.replace('-', '').isalpha()):
        raise HTTPException(400, 'Invalid language code')
    with tempfile.TemporaryDirectory(prefix='transcription-', dir=ROOT / 'tmp') as folder:
        path = Path(folder) / 'input.audio'
        size = 0
        with path.open('wb') as stream:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > LIMIT:
                    raise HTTPException(413, 'Audio file too large')
                stream.write(chunk)
        result = await asyncio.to_thread(transcribe_file, path, language)
    if response_format == 'text':
        return Response(result['text'], media_type='text/plain')
    return result if response_format == 'verbose_json' else {'text': result['text']}


if __name__ == '__main__':
    import uvicorn
    (ROOT / 'tmp').mkdir(exist_ok=True, mode=0o700)
    uvicorn.run(app, host='127.0.0.1', port=8318, access_log=False, log_level='warning')
