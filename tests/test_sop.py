"""Tests for SOP generator. [REQ-0.1, REQ-1.7, 1.8, 1.9]"""

import pytest

from telconet_sentinel.data_gen.sop import SOP_DOCS, write_sop_docs


def test_writes_six_or_more_sops(tmp_path):
    write_sop_docs(tmp_path, overwrite=True)
    files = list(tmp_path.glob("*.md"))
    assert len(files) >= 6


def test_each_sop_has_unique_id(tmp_path):
    write_sop_docs(tmp_path, overwrite=True)
    ids = [doc["sop_id"] for doc in SOP_DOCS]
    assert len(ids) == len(set(ids))


def test_sop_file_contains_sop_id(tmp_path):
    write_sop_docs(tmp_path, overwrite=True)
    for doc in SOP_DOCS:
        content = (tmp_path / f"{doc['sop_id']}.md").read_text()
        assert doc["sop_id"] in content


def test_sop_contains_numbered_steps(tmp_path):
    write_sop_docs(tmp_path, overwrite=True)
    for doc in SOP_DOCS:
        content = (tmp_path / f"{doc['sop_id']}.md").read_text()
        assert "Step 1:" in content


def test_sop_contains_synthetic_disclaimer(tmp_path):
    write_sop_docs(tmp_path, overwrite=True)
    for doc in SOP_DOCS:
        content = (tmp_path / f"{doc['sop_id']}.md").read_text()
        assert "sintetis" in content.lower() or "synthetic" in content.lower()


def test_sop_has_frontmatter(tmp_path):
    write_sop_docs(tmp_path, overwrite=True)
    for doc in SOP_DOCS:
        content = (tmp_path / f"{doc['sop_id']}.md").read_text()
        assert content.startswith("---")
        assert "sop_id:" in content


def test_overwrite_protection(tmp_path):
    write_sop_docs(tmp_path, overwrite=True)
    with pytest.raises(SystemExit):
        write_sop_docs(tmp_path, overwrite=False)


def test_domain_coverage():
    domains = {doc["domain"] for doc in SOP_DOCS}
    assert "FTTH" in domains
    assert "OLT" in domains
    assert "CORE" in domains
