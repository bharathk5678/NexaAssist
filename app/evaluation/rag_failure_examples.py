"""Read-only Atlas examples: python -m app.evaluation.rag_failure_examples R1.

Retrieval cases call Atlas and the configured embedding provider. Staleness and
compatibility fault injections change local snapshots only, never stored data.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

import structlog
from langchain_core.documents import Document
from langchain_core.stores import InMemoryStore
from langchain_core.vectorstores import VectorStore
from openai import OpenAIError
from pymongo.errors import PyMongoError

from app.chains.embeddings import get_embeddings
from app.chains.ingestion import build_ingestion_chain, chunk_checksum
from app.chains.retrieval import build_retrieval_chain
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.database.diagnostics import read_rag_snapshot
from app.database.mongo import get_parent_store, get_vector_store
from app.evaluation.rag_failure_modes import (
    ChunkSnapshot,
    EvidenceRef,
    diagnose_embeddings,
    diagnose_expanded_context,
    diagnose_parent_links,
    diagnose_retrieval,
    diagnose_staleness,
)
from app.models.retrieval import RetrieveRequest, RetrieveResponse
from app.services.ingestion import requests_from_register

CASE_IDS = tuple(
    f"{p}{n}" for p, count in (("R", 4), ("S", 5), ("E", 4)) for n in range(1, count + 1)
)
ROOT = Path(__file__).resolve().parents[2]
FEE_QUERY = "What is the current processing fee for a NexaHome Loan?"
FOCUSED_QUERY = (
    "What processing fee does Circular CIR-2026-07 prescribe in revised clause 6.2, "
    "and which loans sanctioned from 1 July 2026 does it cover?"
)
FEE_REFS = [EvidenceRef(doc_id="CIR-2026-07", clause=c) for c in ("3.1", "5.1")]


async def _source_manifests(settings: Settings) -> tuple[list[ChunkSnapshot], list[ChunkSnapshot]]:
    """Run the actual parse/chunk/enrich path while capturing all writes in memory."""
    children: list[Document] = []

    async def capture(documents: list[Document], **kwargs: Any) -> list[str]:
        children.extend(documents)
        return cast(list[str], kwargs["ids"])

    memory_store = Mock(spec=VectorStore)
    memory_store.aget_by_ids = AsyncMock(return_value=[])
    memory_store.aadd_documents = AsyncMock(side_effect=capture)
    parent_store = InMemoryStore()
    chain = build_ingestion_chain(cast(VectorStore, memory_store), parent_store, settings)
    for request in requests_from_register(
        ROOT / "nexa_synthetic_data/document_register.json", settings
    ):
        await chain.ainvoke({"request": request})
    child_manifest = [
        ChunkSnapshot(chunk_id=doc.metadata["chunk_id"], checksum=doc.metadata["checksum"])
        for doc in children
    ]
    parent_ids = [key async for key in parent_store.ayield_keys()]
    parents = await parent_store.amget(parent_ids)
    parent_manifest = [
        ChunkSnapshot(chunk_id=key, checksum=chunk_checksum(doc.page_content, doc.metadata))
        for key, doc in zip(parent_ids, parents, strict=True)
        if doc is not None
    ]
    return child_manifest, parent_manifest


async def example_report(selected: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    storage = await asyncio.to_thread(read_rag_snapshot, settings)
    chunks = storage["chunks"]
    if not chunks:
        raise ValueError("The configured collection contains no policy chunks")
    child_documents = [
        Document(
            id=str(row["_id"]),
            page_content=row["text"],
            metadata={
                key: value
                for key, value in row.items()
                if key not in {"_id", "text", "_actual_dimensions"}
            },
        )
        for row in chunks
    ]
    parents = {
        str(row["_id"]): Document(
            id=str(row["_id"]),
            page_content=row["page_content"],
            metadata={
                key: value for key, value in row.items() if key not in {"_id", "page_content"}
            },
        )
        for row in storage["parents"]
    }
    parent_snapshots = [
        ChunkSnapshot(chunk_id=key, checksum=chunk_checksum(doc.page_content, doc.metadata))
        for key, doc in parents.items()
    ]
    child_lookup = {(doc.metadata["doc_id"], doc.page_content): doc for doc in child_documents}
    snapshots = [
        ChunkSnapshot(
            chunk_id=str(row["_id"]),
            checksum=row.get("checksum"),
            embedding_model=row.get("embedding_model"),
            embedding_dimensions=(
                row["_actual_dimensions"] if row["_actual_dimensions"] >= 0 else None
            ),
        )
        for row in chunks
    ]
    contract = diagnose_embeddings(
        snapshots, settings.embedding_model, settings.embedding_dimensions
    )
    inventory = Counter((s.embedding_model, s.embedding_dimensions) for s in snapshots)
    report: dict[str, Any] = {
        "captured_at": datetime.now(UTC).isoformat(),
        "target": f"{settings.mongodb_db}.{settings.mongodb_collection}",
        "configured_index": settings.vector_index_name,
        "indexes": storage["indexes"],
        "chunk_count": len(chunks),
        "parent_target": f"{settings.mongodb_db}.{settings.mongodb_parent_collection}",
        "parent_count": len(parents),
        "parent_integrity": diagnose_parent_links(child_documents, parents),
        "documents": dict(sorted(Counter(row["doc_id"] for row in chunks).items())),
        "embedding_inventory": [
            {"model": m, "dimensions": d, "chunks": n} for (m, d), n in inventory.items()
        ],
        "embedding_contract": contract,
        "cases": {},
    }
    cases = report["cases"]
    chain = build_retrieval_chain(
        get_vector_store(settings, get_embeddings(settings)), get_parent_store(settings), settings
    )
    cache: dict[str, RetrieveResponse] = {}

    async def retrieve(query: str, refs: list[EvidenceRef], **changes: Any) -> dict[str, Any]:
        request = RetrieveRequest.model_validate(
            {"query": query, "as_of": "2026-10-01", "product_id": "NEXA-HL", **changes}
        )
        key = request.model_dump_json()
        if key not in cache:
            cache[key] = await asyncio.wait_for(chain.ainvoke(request), timeout=60)
        response = cache[key]
        return {
            "request": request.model_dump(mode="json"),
            "diagnosis": diagnose_retrieval(response, refs),
            "expanded_context": diagnose_expanded_context(response, refs, child_documents),
            "hits": [
                {
                    "rank": h.rank,
                    "score": h.score,
                    **h.citation.model_dump(mode="json"),
                    "parent_id": child_lookup[(h.citation.doc_id, h.text)].metadata["parent_id"],
                    "parent_characters": len(h.parent_text),
                }
                for h in response.results
            ],
            "timings": response.timings.model_dump(),
        }

    wanted = lambda key: selected is None or selected == key
    if wanted("R1"):
        cases["R1"] = {
            "mode": "live_queries",
            "title": "Wrong product filter",
            "before": await retrieve(FEE_QUERY, FEE_REFS, product_id="NEXA-PL"),
            "after": await retrieve(FEE_QUERY, FEE_REFS),
            "interpretation": "Correcting the product may leave a separate ranking miss. Inspect both reports.",
        }
    if wanted("R2"):
        query = "What was the minimum part prepayment on a NexaHome Loan on 31 March 2024?"
        refs = [EvidenceRef(doc_id="POL-HL-V1", clause="8.3")]
        cases["R2"] = {
            "mode": "live_queries",
            "title": "Effective-date boundary",
            "before": await retrieve(query, refs, as_of="2024-04-01"),
            "after": await retrieve(query, refs, as_of="2024-03-31"),
        }
    if wanted("R3"):
        cases["R3"] = {
            "mode": "live_queries",
            "title": "Circular evidence below the cutoff",
            "top1": await retrieve(FEE_QUERY, FEE_REFS, top_k=1),
            "top20": await retrieve(FEE_QUERY, FEE_REFS, top_k=20),
            "focused": await retrieve(FOCUSED_QUERY, FEE_REFS, top_k=20),
            "interpretation": "Focused wording is a debugging experiment, not a general production guarantee.",
        }
    if wanted("R4"):
        query = "What was the maximum tenure for a NexaHome Loan in June 2023, and how does it compare with today?"
        old = [EvidenceRef(doc_id="POL-HL-V1", clause="4.2")]
        new = [EvidenceRef(doc_id="POL-HL-V3", clause="4.2")]
        cases["R4"] = {
            "mode": "live_queries",
            "title": "Two dated evidence calls",
            "one_call": await retrieve(query, old + new, as_of="2023-06-01"),
            "historical": await retrieve(query, old, as_of="2023-06-01"),
            "current": await retrieve(query, new),
        }
    if selected is None or selected.startswith("S"):
        source, source_parents = await _source_manifests(settings)
        baseline = diagnose_staleness(source, snapshots)
        report["source_freshness"] = baseline
        report["parent_source_freshness"] = diagnose_staleness(source_parents, parent_snapshots)
        if wanted("S1"):
            altered = [
                snapshots[0].model_copy(update={"checksum": "sha256:CONTROLLED_OLDER_COPY"}),
                *snapshots[1:],
            ]
            cases["S1"] = {
                "mode": "local_fault_on_live_snapshot",
                "title": "Changed checksum",
                "observed": baseline,
                "injected": diagnose_staleness(source, altered),
                "note": "Only an in-memory checksum changed. No source file or stored record changed.",
            }
        if wanted("S2"):
            without_circular = [s for s in snapshots if not s.chunk_id.startswith("CIR-2026-07_")]
            cases["S2"] = {
                "mode": "local_fault_on_live_snapshot",
                "title": "Missing circular",
                "observed": baseline,
                "injected": diagnose_staleness(source, without_circular),
                "note": "All actual circular IDs are omitted from a local copy only.",
            }
        if wanted("S3"):
            extra = snapshots[0].model_copy(update={"chunk_id": "CONTROLLED_RETIRED_COPY"})
            cases["S3"] = {
                "mode": "local_fault_on_live_snapshot",
                "title": "Retired chunk remains",
                "observed": baseline,
                "injected": diagnose_staleness(source, [*snapshots, extra]),
                "note": "The extra ID exists only in memory. Historical policy versions remain intact.",
            }
        if wanted("S4"):
            cases["S4"] = {
                "mode": "live_differential_diagnosis",
                "title": "Freshness versus ranking",
                "observed_freshness": baseline,
                "index_status": storage["indexes"],
                "generic": await retrieve(FEE_QUERY, FEE_REFS),
                "focused": await retrieve(FOCUSED_QUERY, FEE_REFS, top_k=20),
                "note": "A focused hit proves this evidence is searchable. Generic misses do not alone prove index lag.",
            }
        if wanted("S5"):
            normal = await retrieve(FEE_QUERY, FEE_REFS, top_k=20)
            response = cache[RetrieveRequest.model_validate(normal["request"]).model_dump_json()]
            parent_id = "CIR-2026-07_s05"
            if parent_id not in parents:
                raise ValueError("S5 requires the circular applicability parent in the baseline")
            missing_parents = {key: doc for key, doc in parents.items() if key != parent_id}
            stale_parents = {
                **parents,
                parent_id: parents[parent_id].model_copy(
                    update={
                        "page_content": "CONTROLLED_STALE_PARENT_TEXT",
                    }
                ),
            }

            def replay(local_parents: dict[str, Document]) -> RetrieveResponse:
                hits = []
                for hit in response.results:
                    child = child_lookup[(hit.citation.doc_id, hit.text)]
                    parent = local_parents.get(child.metadata["parent_id"])
                    hits.append(
                        hit.model_copy(
                            update={
                                "parent_text": parent.page_content if parent else hit.text,
                            }
                        )
                    )
                return response.model_copy(update={"results": hits})

            cases["S5"] = {
                "mode": "local_parent_replay_on_live_results",
                "title": "Missing or stale parent loses expanded clause evidence",
                "parent_id": parent_id,
                "observed": {
                    "links": report["parent_integrity"],
                    "expanded_context": normal["expanded_context"],
                    "child_citations": normal["diagnosis"],
                },
                "missing_parent_copy": {
                    "links": diagnose_parent_links(child_documents, missing_parents),
                    "expanded_context": diagnose_expanded_context(
                        replay(missing_parents), FEE_REFS, child_documents
                    ),
                },
                "stale_parent_copy": {
                    "links": diagnose_parent_links(child_documents, stale_parents),
                    "expanded_context": diagnose_expanded_context(
                        replay(stale_parents), FEE_REFS, child_documents
                    ),
                    "parent_source_freshness": diagnose_staleness(
                        source_parents,
                        [
                            ChunkSnapshot(
                                chunk_id=key,
                                checksum=chunk_checksum(doc.page_content, doc.metadata),
                            )
                            for key, doc in stale_parents.items()
                        ],
                    ),
                },
                "note": "Replays the existing chain's parent expansion/fallback on actual retrieved child hits. No MongoDB writes or new vector ranking.",
            }
    if wanted("E1"):
        cases["E1"] = {
            "mode": "counterfactual_config_on_live_snapshot",
            "title": "Wrong query model",
            "observed": contract,
            "counterfactual": diagnose_embeddings(
                snapshots, "text-embedding-3-large", settings.embedding_dimensions
            ),
            "note": "No alternate model call or stored-vector change occurs.",
        }
    if wanted("E2"):
        row = chunks[0]
        metadata = {
            k: v
            for k, v in row.items()
            if k not in {"_id", "text", "checksum", "_actual_dimensions"}
        }
        cases["E2"] = {
            "mode": "counterfactual_config_on_live_snapshot",
            "title": "Dimension change",
            "observed": contract,
            "counterfactual": diagnose_embeddings(snapshots, settings.embedding_model, 1024),
            "stored_metadata_has_dimensions": "embedding_dimensions" in metadata,
            "stored_checksum_matches_payload": chunk_checksum(row["text"], metadata)
            == row.get("checksum"),
            "suggested_hash_1536": chunk_checksum(
                row["text"], {**metadata, "embedding_dimensions": 1536}
            ),
            "suggested_hash_1024": chunk_checksum(
                row["text"], {**metadata, "embedding_dimensions": 1024}
            ),
            "note": "The proposed hash hardening is demonstrated locally, not applied to ingestion.",
        }
    if wanted("E3"):
        mixed = [
            snapshots[0].model_copy(update={"embedding_model": "text-embedding-3-large"}),
            *snapshots[1:],
        ]
        cases["E3"] = {
            "mode": "local_metadata_fault_on_live_snapshot",
            "title": "Mixed-model metadata",
            "observed": contract,
            "injected": diagnose_embeddings(
                mixed, settings.embedding_model, settings.embedding_dimensions
            ),
            "note": "This injects a metadata inconsistency locally. It does not simulate numerical vectors from another model.",
        }
    if wanted("E4"):
        cohort = []
        for line in (ROOT / "evaluation/datasets/retrieval.jsonl").read_text().splitlines():
            golden = json.loads(line)
            refs = [
                EvidenceRef(doc_id=r["doc_id"], clause=r.get("clause")) for r in golden["context"]
            ]
            observation = await retrieve(
                golden["input"]["query"], refs, as_of=golden["input"]["as_of"], product_id=None
            )
            cohort.append(observation)
        cases["E4"] = {
            "mode": "live_quality_snapshot",
            "title": "Compatible vectors and incomplete evidence",
            "observed": contract,
            "cohort": cohort,
            "complete_cases": sum(r["diagnosis"]["status"] == "pass" for r in cohort),
            "expanded_context_complete_cases": sum(
                r["expanded_context"]["status"] == "pass" for r in cohort
            ),
            "total_cases": len(cohort),
            "historical_baseline": "not_available",
            "distribution_drift": "not_measured",
            "note": "Current evidence coverage is measured. Regression over time and embedding drift are unproven.",
        }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", nargs="?", choices=CASE_IDS)
    selected = parser.parse_args().case
    configure_logging("INFO")
    try:
        report = asyncio.run(example_report(selected))
    except (PyMongoError, OpenAIError, ValueError, TimeoutError) as exc:
        structlog.get_logger().error("atlas_lesson_failed", error_type=type(exc).__name__)
        raise SystemExit(1) from None
    structlog.get_logger().info("rag_atlas_examples", **report)


if __name__ == "__main__":
    main()
