import json
import time
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.agent import ask
from app.vectorstore import build_vectorstore, get_collection

app = FastAPI(title="HR Agent", version="0.1.0")


class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None


@app.post("/chat")
def chat(req: ChatRequest):
    start = time.time()
    result = ask(req.question)
    latency_ms = int((time.time() - start) * 1000)

    retrieved_files = [s["file"] for s in result["sources"]]
    retrieved_private = any(s["layer"] == "private" for s in result["sources"])

    log = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": req.question,
        "retrieved_files": retrieved_files,
        "retrieved_private": retrieved_private,
        "answer_length": len(result["answer"]),
        "latency_ms": latency_ms,
    }
    print(json.dumps(log, ensure_ascii=False))

    return result


@app.get("/health")
def health():
    chroma_status = "disconnected"
    try:
        get_collection()
        chroma_status = "connected"
    except Exception:
        pass

    return {
        "status": "ok",
        "chromadb": chroma_status,
    }


@app.post("/admin/reload-kb")
def reload_kb():
    try:
        chunks_indexed = build_vectorstore()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "reloaded", "chunks_indexed": chunks_indexed}
