"""Local-only neural reranker. No API subscription or remote inference."""
from contextlib import asynccontextmanager
import asyncio
import hmac
import json
import os
from pathlib import Path
import time

import torch
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(os.environ['RERANKER_ROOT'])
CONFIG = json.loads((ROOT/'config.json').read_text())
KEY = (ROOT/'.key').read_text().strip()
MODEL = None
TOKENIZER = None
DEVICE = 'mps' if torch.backends.mps.is_available() else 'cpu'
LOCK = asyncio.Lock()


@asynccontextmanager
async def lifespan(app):
    global MODEL, TOKENIZER
    torch.set_num_threads(4)
    TOKENIZER = AutoTokenizer.from_pretrained(CONFIG['model_path'], local_files_only=True, trust_remote_code=False)
    MODEL = AutoModelForSequenceClassification.from_pretrained(CONFIG['model_path'], local_files_only=True, trust_remote_code=False, use_safetensors=True).to(DEVICE).eval()
    yield

app = FastAPI(lifespan=lifespan)


class Input(BaseModel):
    query: str = Field(min_length=1,max_length=4000)
    documents: list[str] = Field(min_length=1,max_length=80)


@app.get('/health')
async def health():
    return {'status':'healthy' if MODEL is not None else 'loading','model':'BAAI/bge-reranker-v2-m3','revision':CONFIG['revision'],'device':DEVICE}


def score(query, documents):
    scores=[]
    with torch.inference_mode():
        for start in range(0,len(documents),8):
            pairs=[[query,d] for d in documents[start:start+8]]
            inputs=TOKENIZER(pairs,padding=True,truncation=True,max_length=1024,return_tensors='pt').to(DEVICE)
            values=MODEL(**inputs,return_dict=True).logits.view(-1).float().sigmoid().cpu().tolist()
            scores.extend(values)
    return scores


@app.post('/rerank')
async def rerank(body:Input, authorization:str=Header(default='')):
    if not hmac.compare_digest(authorization,'Bearer '+KEY):
        raise HTTPException(401,'Authentication required')
    if any(len(d)>6000 for d in body.documents):
        raise HTTPException(413,'Passages must be bounded before reranking')
    # Bound the queue; client cancellation cannot spawn concurrent GPU inference.
    try:
        await asyncio.wait_for(LOCK.acquire(),timeout=15)
    except TimeoutError:
        raise HTTPException(503,'Reranker is busy')
    try:
        start=time.perf_counter()
        task=asyncio.create_task(asyncio.to_thread(score,body.query,body.documents))
        try:
            scores=await asyncio.shield(task)
        except asyncio.CancelledError:
            await task
            raise
        return {'scores':scores,'elapsed_ms':round((time.perf_counter()-start)*1000),'model':'BAAI/bge-reranker-v2-m3'}
    finally:
        LOCK.release()
