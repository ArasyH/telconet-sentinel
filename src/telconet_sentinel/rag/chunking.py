"""SOP document chunking — splits per section and per numbered Step. [REQ-3.1, 3.2]"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TypedDict


class SopChunk(TypedDict):
    id: str
    text: str
    metadata: dict[str, str]


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return (frontmatter_dict, body) from Markdown with YAML frontmatter."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    fm: dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    return fm, parts[2].strip()


def _deterministic_id(sop_id: str, section: str, step: str) -> str:
    key = f"{sop_id}::{section}::{step}"
    return key  # human-readable; unique per chunk within a SOP


def chunk_file(path: Path) -> list[SopChunk]:
    """Parse one SOP Markdown file into chunks (one per section, steps as sub-chunks)."""
    text = path.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(text)
    sop_id = fm.get("sop_id", path.stem)
    domain = fm.get("domain", "UNKNOWN")

    chunks: list[SopChunk] = []
    current_section = "header"
    current_lines: list[str] = []

    def _flush(section: str, lines: list[str]) -> None:
        content = "\n".join(lines).strip()
        if not content:
            return
        # Split section into per-step sub-chunks if it contains "Step N:"
        step_blocks = re.split(r"(?=^Step \d+:)", content, flags=re.MULTILINE)
        if len(step_blocks) <= 1:
            chunk_id = _deterministic_id(sop_id, section, "")
            chunks.append(SopChunk(
                id=chunk_id,
                text=f"[{sop_id}] {section}\n{content}",
                metadata={
                    "sop_id": sop_id,
                    "domain": domain,
                    "section": section,
                    "source_file": path.name,
                    "step": "",
                },
            ))
        else:
            for block in step_blocks:
                block = block.strip()
                if not block:
                    continue
                step_match = re.match(r"^(Step \d+):", block)
                step_label = step_match.group(1) if step_match else ""
                chunk_id = _deterministic_id(sop_id, section, step_label)
                chunks.append(SopChunk(
                    id=chunk_id,
                    text=f"[{sop_id}] {section} — {step_label}\n{block}",
                    metadata={
                        "sop_id": sop_id,
                        "domain": domain,
                        "section": section,
                        "source_file": path.name,
                        "step": step_label,
                    },
                ))

    for line in body.splitlines():
        if line.startswith("## "):
            _flush(current_section, current_lines)
            current_section = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    _flush(current_section, current_lines)
    return chunks


def chunk_dir(sop_dir: str | Path) -> list[SopChunk]:
    """Chunk all *.md files in sop_dir."""
    sop_dir = Path(sop_dir)
    all_chunks: list[SopChunk] = []
    for path in sorted(sop_dir.glob("*.md")):
        all_chunks.extend(chunk_file(path))
    return all_chunks
