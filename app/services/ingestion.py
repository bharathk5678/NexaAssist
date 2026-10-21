from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import structlog

from app.chains.embeddings import get_embeddings
from app.chains.ingestion import build_ingestion_chain
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.telemetry import init_telemetry
from app.database.mongo import (
    delete_stale_chunks,
    get_parent_store,
    get_vector_store,
    retire_document,
)
from app.models.ingestion import IngestRequest, IngestResponse

logger = structlog.get_logger()

DOC_TYPES = {"POL": "policy", "CIR": "circular"}


def requests_from_register(register_path: Path, settings: Settings) -> list[IngestRequest]:
    """One IngestRequest per authoritative document in document_register.json."""
    return [
        IngestRequest(
            source_path=str(register_path.parent / entry["file"]),
            doc_id=entry["doc_id"],
            title=entry["title"],
            institution=settings.institution,
            product_id=entry["product_id"],
            policy_version=entry["version"],
            effective_date=entry["effective_from"],
            effective_to=entry["effective_to"],
            supersedes=entry["supersedes"],
            jurisdiction=settings.jurisdiction,
            doc_type=DOC_TYPES[entry["doc_id"].split("-")[0]],
            confidentiality_level=settings.confidentiality_level,
        )
        for entry in json.loads(register_path.read_text())
        if entry["authoritative"]
    ]


async def ingest(requests: list[IngestRequest]) -> list[IngestResponse]:
    """Embed only new or changed chunks, then retire chunks the source no longer has."""
    settings = get_settings()
    vector_store = get_vector_store(settings, get_embeddings(settings))
    chain = build_ingestion_chain(vector_store, get_parent_store(settings), settings)
    responses = []
    for request in requests:
        response = await chain.ainvoke({"request": request})
        removed = await asyncio.to_thread(
            delete_stale_chunks, vector_store.collection, request.doc_id, response.chunk_ids
        )
        logger.info(
            "document_ingested",
            doc_id=response.doc_id,
            chunk_count=response.chunk_count,
            embedded_count=response.embedded_count,
            unchanged_count=response.unchanged_count,
            stale_chunks_removed=removed,
            embedding_model=response.embedding_model,
            policy_version=request.policy_version,
            effective_date=request.effective_date.isoformat(),
        )
        responses.append(response)
    return responses


def main() -> None:
    """Ingest a register, or explicitly retire one document withdrawn from it."""
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("register", type=Path)
    parser.add_argument("--retire-doc", help="Delete a withdrawn document from both MongoDB stores")
    args = parser.parse_args()
    settings = get_settings()
    init_telemetry(settings.dd_trace_enabled)
    configure_logging(settings.log_level)
    if args.retire_doc:
        entries = json.loads(args.register.read_text())
        if any(entry["doc_id"] == args.retire_doc and entry["authoritative"] for entry in entries):
            parser.error("Cannot retire a document still marked authoritative in the register")
        counts = retire_document(settings, args.retire_doc)
        logger.info("document_retired", doc_id=args.retire_doc, **counts)
    else:
        asyncio.run(ingest(requests_from_register(args.register, settings)))


if __name__ == "__main__":
    main()
