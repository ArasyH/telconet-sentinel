"""SOP retriever with domain filter. [REQ-3.4]"""

from __future__ import annotations

from telconet_sentinel.config import settings
from telconet_sentinel.rag.ingest import get_collection

# Mapping device_type → applicable SOP domains (design.md §3.3)
DOMAIN_MAP: dict[str, list[str]] = {
    "ONT": ["FTTH"],
    "OLT": ["FTTH", "OLT"],
    "CORE_ROUTER": ["CORE"],
}


def retrieve(
    query: str,
    device_type: str,
    k: int | None = None,
    chroma_dir: str | None = None,
) -> list[dict]:
    """Return top-k SOP chunks filtered by device_type → domain."""
    k = k or settings.retrieval_k
    domains = DOMAIN_MAP.get(device_type, [])
    if not domains:
        return []

    collection = get_collection(chroma_dir)
    where = {"domain": {"$in": domains}} if len(domains) > 1 else {"domain": domains[0]}

    results = collection.query(
        query_texts=[query],
        n_results=min(k, collection.count()),
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text": doc,
            "metadata": meta,
            "distance": dist,
        })
    return chunks
