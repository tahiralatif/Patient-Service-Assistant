"""Loads knowledge-base documents from the knowledge/ folder and splits them
into chunks. Each chunk keeps its source doc_id and section title, so every
answer can point back to exactly where it came from.
"""
from dataclasses import dataclass
from pathlib import Path

import frontmatter

KB_DIR = Path(__file__).resolve().parent.parent / "knowledge"


@dataclass(frozen=True)
class Chunk:
    chunk_id: str       # e.g. "preparation_instructions#Cardiology"
    doc_id: str
    title: str
    section: str
    text: str
    owner: str
    last_reviewed: str


def _split_sections(body: str) -> list[tuple[str, str]]:
    """Split a markdown body on '## ' headings into (section, text) pairs."""
    sections: list[tuple[str, str]] = []
    current_title = "General"
    current_lines: list[str] = []

    for line in body.splitlines():
        if line.startswith("## "):
            if current_lines:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = line.removeprefix("## ").strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, "\n".join(current_lines).strip()))

    return [(title, text) for title, text in sections if text]


def load_chunks() -> list[Chunk]:
    chunks: list[Chunk] = []

    for path in sorted(KB_DIR.glob("*.md")):
        post = frontmatter.load(path)
        if not post.get("searchable", True):
            continue

        doc_id = post.get("doc_id", path.stem)
        title = post.get("title", doc_id)
        owner = post.get("owner", "unknown")
        last_reviewed = post.get("last_reviewed", "unknown")

        for section, text in _split_sections(post.content):
            chunks.append(Chunk(
                chunk_id=f"{doc_id}#{section}",
                doc_id=doc_id,
                title=title,
                section=section,
                text=text,
                owner=owner,
                last_reviewed=str(last_reviewed),
            ))

    return chunks