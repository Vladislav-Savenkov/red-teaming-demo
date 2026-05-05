import re
from pathlib import Path

import chromadb
import numpy as np
from openai import OpenAI

from app.config import settings

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

_chroma_client = None
_openai_client = None
_ef = None


def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )
    return _openai_client


class _EmbeddingFunction:
    def name(self) -> str:
        return "openrouter"

    def __call__(self, input: list[str]) -> list[list[float]]:
        response = _get_openai_client().embeddings.create(
            model=settings.openrouter_embed_model,
            input=input,
        )
        return [item.embedding for item in response.data]

    def embed_query(self, input: list[str]):
        return [np.array(e, dtype=np.float32) for e in self(input)]


def _get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.HttpClient(  # type: ignore[attr-defined]
            host=settings.chromadb_host,
            port=settings.chromadb_port,
        )
    return _chroma_client


def _get_ef() -> _EmbeddingFunction:
    global _ef
    if _ef is None:
        _ef = _EmbeddingFunction()
    return _ef


def _read_knowledge_base() -> list[dict]:
    chunks = []
    kb_path = Path(settings.kb_path)

    for layer in ("public", "private"):
        layer_path = kb_path / layer
        if not layer_path.exists():
            continue
        for md_file in sorted(layer_path.glob("*.md")):
            text = md_file.read_text(encoding="utf-8")
            file_chunks = _split_markdown(text)
            for chunk in file_chunks:
                chunks.append({
                    "text": chunk,
                    "metadata": {"file": md_file.name, "layer": layer},
                })

    return chunks


def _split_markdown(text: str) -> list[str]:
    # Режем по заголовкам ## — каждая секция становится отдельным чанком
    sections = re.split(r'\n(?=## )', text)
    chunks = []
    for section in sections:
        stripped = section.strip()
        if not stripped:
            continue
        if len(stripped) <= CHUNK_SIZE:
            chunks.append(stripped)
        else:
            # Секция слишком большая — дополнительно режем по символам
            chunks.extend(_split_text(stripped, CHUNK_SIZE, CHUNK_OVERLAP))
    return chunks


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start + chunk_size])
        start += chunk_size - overlap
    return chunks


def build_vectorstore() -> int:
    client = _get_chroma_client()
    ef = _get_ef()

    try:
        client.delete_collection(settings.chromadb_collection)
    except Exception:
        pass

    collection = client.create_collection(
        name=settings.chromadb_collection,
        embedding_function=ef,  # type: ignore[arg-type]
        metadata={"hnsw:space": "cosine"},
    )

    chunks = _read_knowledge_base()
    if not chunks:
        return 0

    collection.add(
        ids=[str(i) for i in range(len(chunks))],
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
    )

    return len(chunks)


def get_collection() -> chromadb.Collection:
    client = _get_chroma_client()
    ef = _get_ef()
    return client.get_collection(
        name=settings.chromadb_collection,
        embedding_function=ef,  # type: ignore[arg-type]
    )
