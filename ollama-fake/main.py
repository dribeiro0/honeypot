import json
import os
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

LOG_FILE = os.environ.get("LOG_FILE", "ollama.json")

MODELS = [
    {
        "name": "llama3.1:8b",
        "model": "llama3.1:8b",
        "modified_at": "2026-09-14T10:22:31Z",
        "size": 4920753328,
        "digest": "46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e",
        "details": {
            "format": "gguf",
            "family": "llama",
            "parameter_size": "8.0B",
            "quantization_level": "Q4_K_M",
        },
    },

    {
        "name": "qwen2.5:7b",
        "model": "qwen2.5:7b",
        "modified_at": "2026-10-02T18:05:12Z",
        "size": 4683087332,
        "digest": "845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e",
        "details": {
            "format": "gguf",
            "family": "qwen2",
            "parameter_size": "7.6B",
            "quantization_level": "Q4_K_M",
        },
    },
]

CANNED = "I'm sorry, I can't help with that right now."

def now():
    return datetime.now(timezone.utc).isoformat()


async def get_json(request: Request):
    try:
        data = await request.json() 
        return data if isinstance(data, dict) else {}
    except Exception: 
        return {}


@app.middleware("http")
async def log_requests(request: Request, call_next):
    raw = await request.body()
    entry = {
        "timestamp": now(), 
        "src_ip": request.client.host if request.client else None,
        "method": request.method, 
        "path": request.url.path, 
        "query": request.url.query, 
        "headers": dict(request.headers), 
        "body": raw.decode("utf-8", errors="replace")[:20000],
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    
    return await call_next(request)


@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return PlainTextResponse("Ollama is running")


#get
@app.get("/api/version")
async def version():
    return {"version": "0.12.6"}


@app.get("/api/tags")
async def tags(): 
    return {"models": MODELS}


@app.get("/api/ps")
async def ps():
    return {"models": []}


@app.get("/v1/models")
async def openai_models():
    return {
        "object": "list",
        "data": [
            {"id": m["name"], "object": "model",
             "created": 1760000000, "owned_by": "library"}
            for m in MODELS
        ],
    }


#post 
@app.post("/api/generate")
async def generate(request: Request):
    data = await get_json(request)
    return {
        "model": data.get("model", "llama3.1:8b"),
        "created_at": now(),
        "response": CANNED,
        "done": True,
        "done_reason": "stop",
    }


@app.post("/api/chat")
async def chat(request: Request):
    data = await get_json(request)
    return {
        "model": data.get("model", "llama3.1:8b"),
        "created_at": now(),
        "message": {"role": "assistant", "content": CANNED},
        "done": True,
        "done_reason": "stop",
    }


@app.post("/api/pull")
async def pull():
    return {"status": "success"}


@app.post("/api/show")
async def show(request: Request):
    data = await get_json(request)
    return {
        "modelfile": f"FROM {data.get('model', 'llama3.1:8b')}",
        "details": MODELS[0]["details"],
    }


@app.post("/v1/chat/completions")
async def openai_chat(request: Request):
    data = await get_json(request)
    return {
        "id": "chatcmpl-482",
        "object": "chat.completion",
        "created": int(datetime.now(timezone.utc).timestamp()),
        "model": data.get("model", "llama3.1:8b"),
        "choices": [{
            "index": 0,
            "finish_reason": "stop",
            "message": {"role": "assistant", "content": CANNED},
        }],
    }