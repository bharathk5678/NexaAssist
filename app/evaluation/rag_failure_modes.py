"""Run a controlled offline lesson: python -m app.evaluation.rag_failure_modes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import structlog
from langchain_core.documents import Document
from pydantic import BaseModel, ConfigDict, Field

from app.chains.ingestion import chunk_checksum
from app.core.config import Settings
from app.core.logging import configure_logging
from app.models.retrieval import RetrieveResponse


class EvidenceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_id: str = Field(min_length=1)
    clause: str | None = None


class ChunkSnapshot(BaseModel):
    """A source/index manifest entry; dimensions describe the stored vector."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(min_length=1)
    checksum: str | None = Field(default=None, min_length=1)
    embedding_model: str | None = Field(default=None, min_length=1)
    embedding_dimensions: int | None = Field(default=None, ge=0)


def diagnose_retrieval(
    response: RetrieveResponse, expected: Sequence[EvidenceRef]
) -> dict[str, object]:
    """Check expected citation coverage, including nonempty but incorrect results."""
    if not expected:
        raise ValueError("Expected evidence must contain at least one citation")
    missing = [
        reference.model_dump()
        for reference in expected
        if not any(
            hit.citation.doc_id == reference.doc_id
            and (reference.clause is None or hit.citation.clause == reference.clause)
            for hit in response.results
        )
    ]
    return {
        "status": "miss" if missing else "pass",
        "returned_count": len(response.results),
        "empty": not response.results,
        "missing_evidence": missing,
    }


def _chunk_body(document: Document) -> str:
    header, separator, body = document.page_content.partition("\n")
    return body if separator and header.startswith("[") else document.page_content


def diagnose_expanded_context(
    response: RetrieveResponse,
    expected: Sequence[EvidenceRef],
    source_chunks: Sequence[Document],
) -> dict[str, object]:
    """Check verbatim source-clause bodies in returned context, separately from citations.

    This measures text availability, not semantic correctness or answer attribution.
    """
    if not expected:
        raise ValueError("Expected evidence must contain at least one citation")
    missing: list[dict[str, object]] = []
    covered: list[dict[str, object]] = []
    unindexed: list[dict[str, object]] = []
    for reference in expected:
        candidates = [
            chunk
            for chunk in source_chunks
            if chunk.metadata["doc_id"] == reference.doc_id
            and (reference.clause is None or chunk.metadata.get("clause") == reference.clause)
        ]
        matching_hits = [hit for hit in response.results if hit.citation.doc_id == reference.doc_id]
        present = bool(candidates) and (
            bool(matching_hits)
            if reference.clause is None
            else all(
                bool(_chunk_body(chunk).strip())
                and any(_chunk_body(chunk) in hit.parent_text for hit in matching_hits)
                for chunk in candidates
            )
        )
        (covered if present else missing).append(reference.model_dump())
        if not candidates:
            unindexed.append(reference.model_dump())
    return {
        "status": "miss" if missing else "pass",
        "covered_evidence": covered,
        "missing_evidence": missing,
        "unindexed_evidence": unindexed,
        "basis": "verbatim indexed clause bodies in returned parent_text",
    }


def diagnose_parent_links(
    chunks: Sequence[Document], parents: Mapping[str, Document]
) -> dict[str, object]:
    """Check existence, policy scope and body containment across the two stores."""
    missing, mismatched, absent = [], [], []
    referenced = set()
    for chunk in chunks:
        parent_id = chunk.metadata["parent_id"]
        referenced.add(parent_id)
        parent = parents.get(parent_id)
        chunk_id = chunk.id or chunk.metadata["chunk_id"]
        if parent is None:
            missing.append(chunk_id)
            continue
        if any(
            chunk.metadata.get(field) != parent.metadata.get(field)
            for field in (
                "doc_id",
                "policy_version",
                "product_id",
                "jurisdiction",
                "confidentiality_level",
                "effective_date",
                "effective_to",
                "parent_id",
            )
        ):
            mismatched.append(chunk_id)
        if not _chunk_body(chunk).strip() or _chunk_body(chunk) not in parent.page_content:
            absent.append(chunk_id)
    unreferenced = sorted(set(parents) - referenced)
    return {
        "status": "not_evaluated"
        if not chunks
        else "mismatch"
        if missing or mismatched or absent or unreferenced
        else "pass",
        "missing_parent_chunk_ids": sorted(missing),
        "scope_mismatch_chunk_ids": sorted(mismatched),
        "child_body_absent_chunk_ids": sorted(absent),
        "unreferenced_parent_ids": unreferenced,
    }


def _by_id(chunks: Sequence[ChunkSnapshot]) -> dict[str, ChunkSnapshot]:
    indexed = {chunk.chunk_id: chunk for chunk in chunks}
    if len(indexed) != len(chunks):
        raise ValueError("Snapshot contains duplicate chunk IDs")
    return indexed


def diagnose_staleness(
    source: Sequence[ChunkSnapshot], indexed: Sequence[ChunkSnapshot]
) -> dict[str, object]:
    """Compare a freshly prepared source manifest to a complete stored manifest.

    This checks stored chunk freshness, not the Atlas Search index's readiness.
    """
    if not source or any(chunk.checksum is None for chunk in source):
        raise ValueError("Source snapshot must be nonempty and contain checksums")
    expected, stored = _by_id(source), _by_id(indexed)
    missing = sorted(expected.keys() - stored.keys())
    unexpected = sorted(stored.keys() - expected.keys())
    changed = sorted(
        key
        for key in expected.keys() & stored.keys()
        if expected[key].checksum != stored[key].checksum
    )
    return {
        "status": "stale" if missing or unexpected or changed else "pass",
        "missing_chunks": missing,
        "changed_chunks": changed,
        "unexpected_chunks": unexpected,
        "atlas_index_readiness": "not_checked",
    }


def diagnose_embeddings(
    indexed: Sequence[ChunkSnapshot], expected_model: str, expected_dimensions: int
) -> dict[str, object]:
    """Check embedding compatibility; statistical distribution drift is not measured."""
    if not expected_model.strip() or expected_dimensions < 1:
        raise ValueError("Expected model and positive dimensions are required")
    _by_id(indexed)
    models = sorted(chunk.chunk_id for chunk in indexed if chunk.embedding_model != expected_model)
    dimensions = sorted(
        chunk.chunk_id for chunk in indexed if chunk.embedding_dimensions != expected_dimensions
    )
    status = "not_evaluated" if not indexed else "mismatch" if models or dimensions else "pass"
    return {
        "status": status,
        "model_mismatch": models,
        "dimension_mismatch": dimensions,
        "distribution_drift": "not_measured",
    }


def demo_report() -> dict[str, object]:
    """Synthetic snapshots and responses; no Atlas, embeddings, or model downloads."""
    model = str(Settings.model_fields["embedding_model"].default)
    dimensions = int(Settings.model_fields["embedding_dimensions"].default)
    source = [
        ChunkSnapshot(
            chunk_id=key,
            checksum=chunk_checksum(text, {"embedding_model": model}),
            embedding_model=model,
            embedding_dimensions=dimensions,
        )
        for key, text in (
            ("POL-HL-V3_6.2_c01", "Processing fee: current source text"),
            ("POL-HL-V3_8.3_c01", "Part prepayment: current source text"),
        )
    ]
    response = RetrieveResponse.model_validate(
        {
            "as_of": "2025-10-01",
            "results": [
                {
                    "rank": 1,
                    "score": 0.9,
                    "text": "Processing fee",
                    "parent_text": "Fee section",
                    "citation": {
                        "doc_id": "POL-HL-V3",
                        "title": "NexaHome Loan Policy",
                        "policy_version": "3.0",
                        "clause": "6.2",
                        "effective_date": "2025-10-01",
                    },
                }
            ],
            "timings": {"search_ms": 1, "parent_ms": 1, "total_ms": 2},
        }
    )
    faulty_index = [
        source[0].model_copy(update={"checksum": "sha256:older-source"}),
        source[1].model_copy(update={"chunk_id": "WITHDRAWN_8.3_c01"}),
    ]
    faulty_embeddings = [
        source[0].model_copy(
            update={
                "embedding_model": "demo-mismatched-model",
                "embedding_dimensions": 8,
            }
        )
    ]
    return {
        "mode": "offline_demo",
        "retrieval": {
            "healthy": diagnose_retrieval(
                response, [EvidenceRef(doc_id="POL-HL-V3", clause="6.2")]
            ),
            "nonempty_miss": diagnose_retrieval(
                response, [EvidenceRef(doc_id="POL-HL-V3", clause="8.3")]
            ),
            "empty_miss": diagnose_retrieval(
                response.model_copy(update={"results": []}), [EvidenceRef(doc_id="POL-HL-V3")]
            ),
        },
        "staleness": {
            "healthy": diagnose_staleness(source, source),
            "stale": diagnose_staleness(source, faulty_index),
        },
        "embeddings": {
            "healthy": diagnose_embeddings(source, model, dimensions),
            "incompatible": diagnose_embeddings(faulty_embeddings, model, dimensions),
        },
    }


def main() -> None:
    configure_logging("INFO")
    structlog.get_logger().info("rag_failure_modes_demo", **demo_report())


if __name__ == "__main__":
    main()
