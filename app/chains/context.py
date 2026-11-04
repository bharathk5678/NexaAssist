"""Pack and render complete retrieved passages within a serialized token budget."""

from __future__ import annotations

import json
from functools import lru_cache

import tiktoken

from app.models.retrieval import RetrieveHit


@lru_cache
def token_encoder(name: str) -> tiktoken.Encoding:
    """Return the cached tokenizer for the configured encoding.

    Args:
        name: Configured tokenizer or metric identifier.
    """
    return tiktoken.get_encoding(name)


def render_context(sources: dict[int, RetrieveHit]) -> str:
    """Render numbered evidence with its matched citation metadata as JSON.

    Args:
        sources: Numbered policy passages and citation metadata retained for generation.
    """
    return json.dumps(
        [
            {
                "evidence_id": number,
                "matched_child": hit.citation.model_dump(mode="json"),
                "retrieved_context": hit.parent_text,
            }
            for number, hit in sources.items()
        ],
        ensure_ascii=False,
    )


def assemble_context(
    hits: list[RetrieveHit], max_tokens: int, encoding: str
) -> dict[int, RetrieveHit]:
    """Pack complete parents, falling back to complete children; never cut a table.

    The budget covers the serialized evidence payload, excluding prompt and output.
    Reorder selected evidence so the two best-ranked passages sit at the edges.

    Args:
        hits: Ranked policy passages supplied by retrieval.
        max_tokens: Maximum serialized evidence tokens retained in the context.
        encoding: Tokenizer encoding used for bounded context or model-work estimates.
    """
    encoder = token_encoder(encoding)
    sources: dict[int, RetrieveHit] = {}
    seen: set[tuple[str, str, str]] = set()
    for hit in hits:
        number = len(sources) + 1
        for text in dict.fromkeys((hit.parent_text, hit.text)):
            key = (hit.citation.doc_id, hit.citation.policy_version, text)
            if key in seen:
                break
            candidate = hit.model_copy(update={"parent_text": text})
            if (
                len(
                    encoder.encode(
                        render_context({**sources, number: candidate}), disallowed_special=()
                    )
                )
                <= max_tokens
            ):
                sources[number] = candidate
                seen.add(key)
                break
    items = list(sources.items())
    return dict(items[::2] + items[1::2][::-1])
