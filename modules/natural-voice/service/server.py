"""Local-only VoxCPM2 speech; synthetic references keep podcast speakers consistent."""
import os
os.environ.update(HF_HUB_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1', DO_NOT_TRACK='1')
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import hashlib
import hmac
import io
import json
import logging
from pathlib import Path
import re
import subprocess
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
import imageio_ffmpeg
import numpy as np
from pydantic import BaseModel, Field
import soundfile as sf

ROOT = Path(os.environ.get('NATURAL_VOICE_ROOT', Path(__file__).resolve().parent))
KEY = (ROOT / '.voice-key').read_text().strip()
MODEL_NAME = 'voxcpm2-turkish-local'
MODEL_PATH = ROOT / 'models/voxcpm2'
VOICES = json.loads((ROOT / 'voices.json').read_text())
VOICES.pop('reference_text', None)
ALIASES = {'default':'deniz', 'alloy':'deniz', 'onyx':'deniz', 'echo':'emre',
           'fable':'emre', 'nova':'selin', 'shimmer':'selin'}
POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix='neural-voice')
MODEL = None
GATE = asyncio.Semaphore(1)
STATE = {'active':False, 'waiting':0, 'completed':0, 'last_generation_seconds':None}
FORMATS = {'mp3':('mp3','audio/mpeg'), 'wav':('wav','audio/wav'),
           'flac':('flac','audio/flac'), 'opus':('opus','audio/ogg'),
           'aac':('adts','audio/aac'), 'pcm':('s16le','audio/pcm')}


def split_text(text: str, limit: int = 350) -> list[str]:
    # Do not drop punctuation or change content; prefer complete sentences.
    text = re.sub(r'\s+', ' ', text).strip()
    units = re.split(r'(?<=[.!?;:])\s+', text)
    chunks, current = [], ''
    for unit in units:
        parts = [unit]
        if len(unit) > limit:
            parts, part = [], ''
            for word in unit.split():
                if part and len(part) + len(word) + 1 > limit:
                    parts.append(part); part = ''
                part = (part + ' ' + word).strip()
            if part: parts.append(part)
        for part in parts:
            if current and len(current) + len(part) + 1 > limit:
                chunks.append(current); current = ''
            current = (current + ' ' + part).strip()
    if current: chunks.append(current)
    return chunks


def load_model():
    global MODEL
    from mlx_audio.tts.utils import load
    for voice in VOICES:
        if not (ROOT / 'voices' / (voice + '.wav')).is_file():
            raise RuntimeError('Synthetic voice reference missing: ' + voice)
    MODEL = load(str(MODEL_PATH))
    MODEL.compile_model()


@asynccontextmanager
async def lifespan(app):
    await asyncio.get_running_loop().run_in_executor(POOL, load_model)
    yield
    POOL.shutdown(wait=True)


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)


@app.middleware('http')
async def authenticate(request: Request, call_next):
    if request.url.path != '/health' and not hmac.compare_digest(
            request.headers.get('authorization',''), 'Bearer ' + KEY):
        return Response(status_code=401)
    length = request.headers.get('content-length')
    if length and (not length.isdigit() or int(length) > 100000):
        return Response(status_code=413)
    return await call_next(request)


@app.get('/health')
async def health():
    return {'status':'healthy' if MODEL is not None else 'loading', 'model':MODEL_NAME,
            'model_loaded':MODEL is not None, 'local_only':True, 'sample_rate':48000,
            'voices':list(VOICES), **STATE}


@app.get('/v1/models')
async def models():
    return {'object':'list', 'data':[{'id':MODEL_NAME,'object':'model','owned_by':'local','created':0}]}


@app.get('/v1/audio/voices')
async def voices():
    return {'voices':[{'voice_id':v,'name':p['name'],'language':'tr-TR'} for v,p in VOICES.items()]}


class SpeechRequest(BaseModel):
    model: str
    input: str = Field(min_length=1, max_length=12000)
    voice: str = 'deniz'
    response_format: str = 'mp3'
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


def synthesize(body: SpeechRequest, voice: str) -> bytes:
    import mlx.core as mx
    start = time.monotonic()
    pieces = []
    for text in split_text(body.input):
        # Stable, distinct synthetic identities; no recording of a real person.
        seed = int.from_bytes(hashlib.sha256((voice + text).encode()).digest()[:4], 'big')
        mx.random.seed(seed)
        result = next(MODEL.generate(text=text, ref_audio=str(ROOT/'voices'/(voice+'.wav')),
                                    inference_timesteps=10, cfg_value=2.0, max_tokens=650))
        audio = np.asarray(result.audio).reshape(-1).astype(np.float32)
        sr = result.sample_rate
        duration = len(audio) / sr
        if not np.isfinite(audio).all() or duration < 0.2 or duration >= 103:
            raise RuntimeError('Invalid or truncated generated speech')
        if np.sqrt(np.mean(audio ** 2)) < 0.0001:
            raise RuntimeError('Silent speech output')
        if pieces: pieces.append(np.zeros(round(sr*0.16), dtype=np.float32))
        pieces.append(audio)
    combined = np.concatenate(pieces)
    buffer = io.BytesIO()
    sf.write(buffer, combined, sr, format='WAV', subtype='PCM_24')
    fmt, _ = FORMATS[body.response_format]
    filters = ['loudnorm=I=-19:TP=-1.5:LRA=9']
    if body.speed != 1.0: filters.append('atempo=' + str(body.speed))
    args = [imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin','-v','error','-i','pipe:0',
            '-af',','.join(filters),'-ac','1','-ar','48000']
    if fmt == 'mp3': args += ['-c:a','libmp3lame','-b:a','192k']
    elif fmt == 'wav': args += ['-c:a','pcm_s24le']
    elif fmt == 'adts': args += ['-b:a','192k']
    elif fmt == 'opus': args += ['-b:a','128k']
    args += ['-f',fmt,'pipe:1']
    data = subprocess.run(args,input=buffer.getvalue(),capture_output=True,check=True,timeout=90).stdout
    if not data: raise RuntimeError('Empty encoded audio')
    STATE['last_generation_seconds'] = round(time.monotonic()-start,2)
    STATE['completed'] += 1
    return data


async def run_speech(body, voice):
    try:
        async with GATE:
            STATE['waiting'] -= 1
            STATE['active'] = True
            try:
                return await asyncio.get_running_loop().run_in_executor(POOL, synthesize, body, voice)
            finally:
                STATE['active'] = False
    except Exception:
        logging.exception('Local neural speech failed')
        raise


@app.post('/v1/audio/speech')
async def speech(body: SpeechRequest):
    if body.model != MODEL_NAME: raise HTTPException(404, 'Unknown local speech model')
    voice = ALIASES.get(body.voice, body.voice)
    if voice not in VOICES: raise HTTPException(400, 'Supported voices: deniz, selin, emre')
    if body.response_format not in FORMATS: raise HTTPException(400, 'Unsupported audio format')
    if not body.input.strip(): raise HTTPException(400, 'Speech text is empty')
    if STATE['waiting'] >= 24: raise HTTPException(429, 'Local speech queue is full')
    STATE['waiting'] += 1
    task = asyncio.create_task(run_speech(body, voice))
    try:
        data = await asyncio.shield(task)
    except asyncio.CancelledError:
        # Complete the active Metal invocation before another request starts.
        task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
        raise
    except Exception:
        raise HTTPException(502, 'Local neural speech generation failed')
    return Response(data,media_type=FORMATS[body.response_format][1])


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8319,access_log=False,log_level='warning')
