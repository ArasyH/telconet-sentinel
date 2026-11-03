"""Tests for RAG chunking and retrieval. [REQ-3.1–3.4]"""

import pytest

from telconet_sentinel.data_gen.sop import write_sop_docs
from telconet_sentinel.rag.chunking import chunk_dir
from telconet_sentinel.rag.ingest import ingest
from telconet_sentinel.rag.retriever import retrieve


@pytest.fixture
def sop_and_chroma(tmp_path):
    sop_dir = tmp_path / "sop"
    sop_dir.mkdir()
    chroma_dir = str(tmp_path / "chroma")
    write_sop_docs(sop_dir, overwrite=True)
    ingest(sop_dir=str(sop_dir), chroma_dir=chroma_dir)
    return str(sop_dir), chroma_dir


def test_chunk_count_stable(tmp_path):
    """Same dir → same chunk count on repeated calls."""
    sop_dir = tmp_path / "sop"
    sop_dir.mkdir()
    write_sop_docs(sop_dir, overwrite=True)
    c1 = chunk_dir(sop_dir)
    c2 = chunk_dir(sop_dir)
    assert len(c1) == len(c2)
    assert len(c1) > 0


def test_chunk_ids_deterministic(tmp_path):
    sop_dir = tmp_path / "sop"
    sop_dir.mkdir()
    write_sop_docs(sop_dir, overwrite=True)
    c1 = chunk_dir(sop_dir)
    c2 = chunk_dir(sop_dir)
    assert [c["id"] for c in c1] == [c["id"] for c in c2]


def test_chunks_have_required_metadata(tmp_path):
    sop_dir = tmp_path / "sop"
    sop_dir.mkdir()
    write_sop_docs(sop_dir, overwrite=True)
    for chunk in chunk_dir(sop_dir):
        for key in ("sop_id", "domain", "section", "source_file"):
            assert key in chunk["metadata"]


def test_ingest_idempotent(sop_and_chroma):
    sop_dir, chroma_dir = sop_and_chroma
    n1 = ingest(sop_dir=sop_dir, chroma_dir=chroma_dir)
    n2 = ingest(sop_dir=sop_dir, chroma_dir=chroma_dir)
    assert n1 == n2


def test_retrieve_ont_returns_ftth_chunks(sop_and_chroma):
    _, chroma_dir = sop_and_chroma
    results = retrieve("rx power drop", "ONT", k=4, chroma_dir=chroma_dir)
    assert len(results) > 0
    for r in results:
        assert r["metadata"]["domain"] == "FTTH"


def test_retrieve_core_router_returns_core_chunks(sop_and_chroma):
    _, chroma_dir = sop_and_chroma
    results = retrieve("high latency congestion", "CORE_ROUTER", k=4, chroma_dir=chroma_dir)
    assert len(results) > 0
    for r in results:
        assert r["metadata"]["domain"] == "CORE"


def test_retrieve_olt_returns_ftth_or_olt_chunks(sop_and_chroma):
    _, chroma_dir = sop_and_chroma
    results = retrieve("cpu high temperature", "OLT", k=4, chroma_dir=chroma_dir)
    assert len(results) > 0
    for r in results:
        assert r["metadata"]["domain"] in ("FTTH", "OLT")
