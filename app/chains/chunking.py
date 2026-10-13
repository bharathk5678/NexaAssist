from __future__ import annotations

import re
from dataclasses import dataclass, field

from langchain_text_splitters import RecursiveCharacterTextSplitter
from unstructured.documents.elements import Element, NarrativeText, Table, Title

SECTION_TITLE = re.compile(r"^(\d+)\.\s")
CLAUSE = re.compile(r"^(\d+\.\d+)\s+(.+?)\.(?:\s|$)")


@dataclass(frozen=True)
class Chunk:
    """One citable child chunk: a numbered clause (or a piece of one) plus where it sits."""

    text: str
    section_number: int
    section: str
    clause: str | None
    clause_heading: str | None
    has_table: bool


@dataclass
class _Clause:
    section_number: int
    section: str
    clause: str | None
    clause_heading: str | None
    parts: list[tuple[str, bool]] = field(default_factory=list)


def chunk_by_clause(elements: list[Element], max_characters: int, overlap: int) -> list[Chunk]:
    """Hybrid chunking: structure rules first, size rules second.

    Structure: one chunk per numbered clause ("6.2 Processing fee. ..."). A table or
    continuation line stays with the clause that introduces it, and a table is never split.
    Size: only a clause longer than `max_characters` is split. Its tables become their own
    chunks and its narrative is split at sentence boundaries with `overlap` characters
    repeated. Text before section 1 is section 0, "Front matter".
    """
    section_number, section = 0, "Front matter"
    clauses: list[_Clause] = [_Clause(section_number, section, None, None)]
    for element in elements:
        is_table = isinstance(element, Table)
        text = (element.metadata.text_as_html or element.text) if is_table else element.text
        title = SECTION_TITLE.match(element.text) if isinstance(element, Title) else None
        clause = CLAUSE.match(element.text) if isinstance(element, NarrativeText) else None
        if title:
            section_number, section = int(title.group(1)), element.text
            clauses.append(_Clause(section_number, section, None, None))
        elif clause:
            clauses.append(
                _Clause(section_number, section, clause.group(1), clause.group(2), [(text, False)])
            )
        else:
            clauses[-1].parts.append((text, is_table))

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_characters,
        chunk_overlap=overlap,
        separators=["\n", ". ", " "],
        keep_separator="end",
    )
    chunks: list[Chunk] = []
    for item in clauses:
        if sum(len(text) for text, _ in item.parts) <= max_characters:
            pieces = [("\n".join(text for text, _ in item.parts), any(t for _, t in item.parts))]
        else:
            pieces = []
            run: list[str] = []
            for text, is_table in item.parts:
                if is_table:
                    # Narrative before a table is split together; the table stays whole.
                    pieces.extend((piece, False) for piece in splitter.split_text("\n".join(run)))
                    run = []
                    pieces.append((text, True))
                else:
                    run.append(text)
            pieces.extend((piece, False) for piece in splitter.split_text("\n".join(run)))

        chunks.extend(
            Chunk(
                text=text,
                section_number=item.section_number,
                section=item.section,
                clause=item.clause,
                clause_heading=item.clause_heading,
                has_table=has_table,
            )
            for text, has_table in pieces
            if text
        )
    return chunks

