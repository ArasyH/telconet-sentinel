"""Ingest SOP chunks into ChromaDB (idempotent). [REQ-3.1–3.3]

Run:
    python -m telconet_sentinel.rag.ingest
"""

from __future__ import annotations

import sys

import chromadb
from chromadb.config import Settings as ChromaSettings

from telconet_sentinel.config import settings
from telconet_sentinel.rag.chunking import chunk_dir


def get_collection(chroma_dir: str | None = None):
    path = chroma_dir or str(settings.chroma_dir)
    client = chromadb.PersistentClient(
        path=path,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(
        name=settings.chroma_collection,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def ingest(sop_dir: str | None = None, chroma_dir: str | None = None) -> int:
    sop_dir = sop_dir or str(settings.sop_dir)
    collection = get_collection(chroma_dir)
    chunks = chunk_dir(sop_dir)
    if not chunks:
        print("ERROR: No SOP chunks found. Run data_gen.sop first.", file=sys.stderr)
        sys.exit(1)

    collection.upsert(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
    )
    n = collection.count()
    print(f"ChromaDB collection '{settings.chroma_collection}': {n} chunks total (upserted {len(chunks)})")
    return n


def main() -> None:
    ingest()


if __name__ == "__main__":
    main()
