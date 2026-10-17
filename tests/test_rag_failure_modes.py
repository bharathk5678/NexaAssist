from __future__ import annotations

import pytest

from app.evaluation.rag_failure_modes import (
    ChunkSnapshot,
    demo_report,
    diagnose_embeddings,
    diagnose_staleness,
)


def test_demo_distinguishes_misses_staleness_and_compatibility() -> None:
    report = demo_report()
    assert report["mode"] == "offline_demo"
    retrieval = report["retrieval"]
    assert isinstance(retrieval, dict)
    assert retrieval["healthy"]["status"] == "pass"
    assert retrieval["nonempty_miss"]["status"] == "miss"
    assert retrieval["nonempty_miss"]["empty"] is False
    assert retrieval["nonempty_miss"]["missing_evidence"] == [
        {"doc_id": "POL-HL-V3", "clause": "8.3"}
    ]
    assert retrieval["empty_miss"]["empty"] is True
    stale = report["staleness"]
    assert isinstance(stale, dict)
    assert stale["healthy"]["status"] == "pass"
    assert stale["stale"]["missing_chunks"] == ["POL-HL-V3_8.3_c01"]
    assert stale["stale"]["changed_chunks"] == ["POL-HL-V3_6.2_c01"]
    assert stale["stale"]["unexpected_chunks"] == ["WITHDRAWN_8.3_c01"]
    embeddings = report["embeddings"]
    assert isinstance(embeddings, dict)
    assert embeddings["healthy"]["status"] == "pass"
    assert embeddings["healthy"]["distribution_drift"] == "not_measured"
    assert embeddings["incompatible"]["model_mismatch"] == ["POL-HL-V3_6.2_c01"]
    assert embeddings["incompatible"]["dimension_mismatch"] == ["POL-HL-V3_6.2_c01"]


def test_unknown_snapshots_do_not_report_healthy() -> None:
    with pytest.raises(ValueError, match="Source snapshot"):
        diagnose_staleness([], [])
    with pytest.raises(ValueError, match="checksums"):
        diagnose_staleness([ChunkSnapshot(chunk_id="a")], [])
    assert diagnose_embeddings([], "model", 3)["status"] == "not_evaluated"
    chunk = ChunkSnapshot(chunk_id="a", checksum="source")
    assert diagnose_staleness([chunk], [ChunkSnapshot(chunk_id="a")])["changed_chunks"] == ["a"]
    assert diagnose_embeddings([chunk], "model", 3)["model_mismatch"] == ["a"]
    assert diagnose_embeddings([chunk], "model", 3)["dimension_mismatch"] == ["a"]


def test_reject_duplicate_chunk_ids_and_invalid_embedding_contract() -> None:
    chunk = ChunkSnapshot(chunk_id="a", checksum="source")
    with pytest.raises(ValueError, match="duplicate"):
        diagnose_staleness([chunk], [chunk, chunk])
    with pytest.raises(ValueError, match="positive dimensions"):
        diagnose_embeddings([chunk], "model", 0)
