"""Verification script and library for Information Retrieval (IR) metrics in NexaAssist.

Implements and rigorously verifies:
1. Precision@k
2. Recall@k
3. Mean Reciprocal Rank (MRR / RR@k)
4. Normalized Discounted Cumulative Gain (nDCG@k)

Can be executed in two modes:
  - Verification mode (--verify): Mathematical sanity and unit test assertions.
  - Evaluation mode (--live or default): Evaluates NexaAssist's retrieval against
    the golden evaluation dataset (`evaluation/datasets/retrieval.jsonl`).
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import sys
from typing import Any, Sequence

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Core Metric Calculations
# ---------------------------------------------------------------------------

def precision_at_k(retrieved: Sequence[Any], relevant: set[Any], k: int) -> float:
    """Compute Precision@k.

    Precision@k = (Number of relevant items in top-k) / k
    """
    if k <= 0:
        raise ValueError(f"k must be a positive integer, got {k}")
    if not retrieved:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for item in top_k if item in relevant)
    return hits / k


def recall_at_k(retrieved: Sequence[Any], relevant: set[Any], k: int) -> float:
    """Compute Recall@k.

    Recall@k = (Number of relevant items in top-k) / (Total relevant items)
    """
    if k <= 0:
        raise ValueError(f"k must be a positive integer, got {k}")
    if not relevant:
        return 1.0 if not retrieved else 0.0
    top_k = retrieved[:k]
    hits = sum(1 for item in top_k if item in relevant)
    return hits / len(relevant)


def reciprocal_rank(retrieved: Sequence[Any], relevant: set[Any], k: int | None = None) -> float:
    """Compute Reciprocal Rank (RR).

    RR = 1 / rank of first relevant item (1-indexed).
    Returns 0.0 if no relevant items appear within top-k.
    """
    items = retrieved if k is None else retrieved[:k]
    for rank, item in enumerate(items, start=1):
        if item in relevant:
            return 1.0 / rank
    return 0.0


def dcg_at_k(relevances: Sequence[float], k: int) -> float:
    """Compute Discounted Cumulative Gain at k.

    DCG@k = sum_{i=1}^k (2^{rel_i} - 1) / log2(i + 1)
    """
    if k <= 0:
        raise ValueError(f"k must be a positive integer, got {k}")
    dcg = 0.0
    for i, rel in enumerate(relevances[:k], start=1):
        if rel > 0:
            dcg += (math.pow(2, rel) - 1.0) / math.log2(i + 1)
    return dcg


def ndcg_at_k(
    retrieved: Sequence[Any],
    relevant: set[Any] | dict[Any, float],
    k: int,
) -> float:
    """Compute Normalized Discounted Cumulative Gain at k (nDCG@k).

    nDCG@k = DCG@k / IDCG@k

    Supports both:
    - Binary relevance (relevant is a set of relevant IDs)
    - Graded relevance (relevant is a dict mapping item_id -> relevance grade, e.g. 1.0, 2.0, 3.0)
    """
    if k <= 0:
        raise ValueError(f"k must be a positive integer, got {k}")

    # Build relevance score vector for retrieved items
    if isinstance(relevant, dict):
        rel_map = relevant
    else:
        rel_map = {item: 1.0 for item in relevant}

    retrieved_relevances = [rel_map.get(item, 0.0) for item in retrieved[:k]]
    actual_dcg = dcg_at_k(retrieved_relevances, k)

    # Ideal ranking: sort all available positive relevance scores descending
    all_relevances = sorted(rel_map.values(), reverse=True)
    ideal_dcg = dcg_at_k(all_relevances, k)

    if ideal_dcg == 0.0:
        return 1.0 if actual_dcg == 0.0 and not relevant else 0.0

    return actual_dcg / ideal_dcg


@dataclass
class QueryMetrics:
    query: str
    num_relevant: int
    num_retrieved: int
    precision: dict[int, float] = field(default_factory=dict)
    recall: dict[int, float] = field(default_factory=dict)
    rr: float = 0.0
    ndcg: dict[int, float] = field(default_factory=dict)


def evaluate_query(
    query: str,
    retrieved: Sequence[Any],
    relevant: set[Any],
    k_list: Sequence[int] = (1, 3, 5),
) -> QueryMetrics:
    qm = QueryMetrics(
        query=query,
        num_relevant=len(relevant),
        num_retrieved=len(retrieved),
        rr=reciprocal_rank(retrieved, relevant),
    )
    for k in k_list:
        qm.precision[k] = precision_at_k(retrieved, relevant, k)
        qm.recall[k] = recall_at_k(retrieved, relevant, k)
        qm.ndcg[k] = ndcg_at_k(retrieved, relevant, k)
    return qm


# ---------------------------------------------------------------------------
# Mathematical Verification / Unit Tests
# ---------------------------------------------------------------------------

def run_verification_tests() -> bool:
    """Run rigorous mathematical sanity checks against known textbook results."""
    print("=" * 80)
    print("RUNNING MATHEMATICAL VERIFICATION OF RETRIEVAL METRICS")
    print("=" * 80)

    # Test 1: Textbook case with known manual derivations
    # Relevant: {A, B}
    # Retrieved: [C, A, D, B, E]
    relevant = {"A", "B"}
    retrieved = ["C", "A", "D", "B", "E"]

    # Precision@k:
    # top 1: [C] -> 0/1 = 0.0
    # top 2: [C, A] -> 1/2 = 0.5
    # top 3: [C, A, D] -> 1/3 = 0.3333333333333333
    # top 5: [C, A, D, B, E] -> 2/5 = 0.4
    assert precision_at_k(retrieved, relevant, 1) == 0.0, "Test 1 P@1 failed"
    assert precision_at_k(retrieved, relevant, 2) == 0.5, "Test 1 P@2 failed"
    assert math.isclose(precision_at_k(retrieved, relevant, 3), 1 / 3), "Test 1 P@3 failed"
    assert precision_at_k(retrieved, relevant, 5) == 0.4, "Test 1 P@5 failed"
    print("✓ Precision@k verified (P@1=0.0, P@2=0.5, P@3=0.333, P@5=0.4)")

    # Recall@k:
    # total relevant = 2
    # top 1: [C] -> 0/2 = 0.0
    # top 2: [C, A] -> 1/2 = 0.5
    # top 3: [C, A, D] -> 1/2 = 0.5
    # top 5: [C, A, D, B, E] -> 2/2 = 1.0
    assert recall_at_k(retrieved, relevant, 1) == 0.0, "Test 1 R@1 failed"
    assert recall_at_k(retrieved, relevant, 2) == 0.5, "Test 1 R@2 failed"
    assert recall_at_k(retrieved, relevant, 3) == 0.5, "Test 1 R@3 failed"
    assert recall_at_k(retrieved, relevant, 5) == 1.0, "Test 1 R@5 failed"
    print("✓ Recall@k verified (R@1=0.0, R@2=0.5, R@3=0.5, R@5=1.0)")

    # Reciprocal Rank (RR):
    # First relevant item is 'A' at rank 2 -> RR = 1/2 = 0.5
    assert reciprocal_rank(retrieved, relevant) == 0.5, "Test 1 RR failed"
    # If restricted to k=1, 'A' not in top 1 -> RR@1 = 0.0
    assert reciprocal_rank(retrieved, relevant, k=1) == 0.0, "Test 1 RR@1 failed"
    print("✓ Reciprocal Rank verified (RR=0.5, RR@1=0.0)")

    # nDCG@k:
    # For binary relevance:
    # rel vector for [C, A, D, B, E] = [0, 1, 0, 1, 0]
    # At k=3: DCG@3 = (2^1 - 1)/log2(2+1) = 1 / log2(3) ≈ 0.63092975
    # Ideal top 3: [1, 1, 0]
    # IDCG@3 = 1/log2(2) + 1/log2(3) = 1.0 + 0.63092975 ≈ 1.63092975
    # nDCG@3 = 0.63092975 / 1.63092975 ≈ 0.3868528
    expected_dcg_3 = 1.0 / math.log2(3)
    expected_idcg_3 = 1.0 / math.log2(2) + 1.0 / math.log2(3)
    expected_ndcg_3 = expected_dcg_3 / expected_idcg_3
    computed_ndcg_3 = ndcg_at_k(retrieved, relevant, 3)
    assert math.isclose(computed_ndcg_3, expected_ndcg_3, rel_tol=1e-5), f"Test 1 nDCG@3 mismatch: {computed_ndcg_3} vs {expected_ndcg_3}"

    # At k=5:
    # DCG@5 = 1/log2(3) + 1/log2(5) ≈ 0.63092975 + 0.43067656 ≈ 1.0616063
    # IDCG@5 = 1/log2(2) + 1/log2(3) ≈ 1.63092975 (since only 2 relevant items exist total)
    # nDCG@5 = 1.0616063 / 1.63092975 ≈ 0.65092
    expected_dcg_5 = 1.0 / math.log2(3) + 1.0 / math.log2(5)
    expected_ndcg_5 = expected_dcg_5 / expected_idcg_3
    computed_ndcg_5 = ndcg_at_k(retrieved, relevant, 5)
    assert math.isclose(computed_ndcg_5, expected_ndcg_5, rel_tol=1e-5), f"Test 1 nDCG@5 mismatch: {computed_ndcg_5} vs {expected_ndcg_5}"
    print(f"✓ nDCG@k verified (nDCG@3={computed_ndcg_3:.4f}, nDCG@5={computed_ndcg_5:.4f})")

    # Test 2: Perfect Ranking
    # Relevant: {A, B}, Retrieved: [A, B, C]
    perf_rel = {"A", "B"}
    perf_ret = ["A", "B", "C"]
    assert precision_at_k(perf_ret, perf_rel, 2) == 1.0
    assert recall_at_k(perf_ret, perf_rel, 2) == 1.0
    assert reciprocal_rank(perf_ret, perf_rel) == 1.0
    assert ndcg_at_k(perf_ret, perf_rel, 2) == 1.0
    print("✓ Perfect Ranking: P@2=1.0, R@2=1.0, RR=1.0, nDCG@2=1.0")

    # Test 3: Zero Relevance / Complete Miss
    miss_ret = ["X", "Y", "Z"]
    assert precision_at_k(miss_ret, perf_rel, 3) == 0.0
    assert recall_at_k(miss_ret, perf_rel, 3) == 0.0
    assert reciprocal_rank(miss_ret, perf_rel) == 0.0
    assert ndcg_at_k(miss_ret, perf_rel, 3) == 0.0
    print("✓ Complete Miss: P@3=0.0, R@3=0.0, RR=0.0, nDCG@3=0.0")

    # Test 4: Graded Relevance
    # Items: {"doc1": 3, "doc2": 2, "doc3": 1}
    # Retrieved ranking: ["doc2", "doc1", "doc3"]
    graded_rel = {"doc1": 3.0, "doc2": 2.0, "doc3": 1.0}
    graded_ret = ["doc2", "doc1", "doc3"]
    # actual DCG@3:
    # rank 1: doc2 (rel 2) -> (2^2 - 1)/log2(2) = 3 / 1 = 3.0
    # rank 2: doc1 (rel 3) -> (2^3 - 1)/log2(3) = 7 / 1.5849625 ≈ 4.4165
    # rank 3: doc3 (rel 1) -> (2^1 - 1)/log2(4) = 1 / 2 = 0.5
    # actual = 3.0 + 4.4165 + 0.5 = 7.9165
    # ideal DCG@3 (doc1, doc2, doc3):
    # rank 1: doc1 (rel 3) -> 7 / 1 = 7.0
    # rank 2: doc2 (rel 2) -> 3 / 1.5849625 ≈ 1.8928
    # rank 3: doc3 (rel 1) -> 1 / 2 = 0.5
    # ideal = 7.0 + 1.8928 + 0.5 = 9.3928
    # nDCG@3 = 7.9165 / 9.3928 ≈ 0.8428
    graded_ndcg = ndcg_at_k(graded_ret, graded_rel, 3)
    assert 0.84 <= graded_ndcg <= 0.85, f"Graded nDCG error: {graded_ndcg}"
    print(f"✓ Graded Relevance: nDCG@3={graded_ndcg:.4f} (Ideal: 1.0, Actual: {graded_ndcg:.4f})")

    # Test 5: MRR over multiple queries
    # Query 1: first relevant at rank 1 -> RR = 1.0
    # Query 2: first relevant at rank 2 -> RR = 0.5
    # Query 3: no relevant items -> RR = 0.0
    # Expected MRR = (1.0 + 0.5 + 0.0) / 3 = 0.5
    rr_scores = [
        reciprocal_rank(["A", "B"], {"A"}),       # 1.0
        reciprocal_rank(["X", "A"], {"A"}),       # 0.5
        reciprocal_rank(["X", "Y"], {"A"}),       # 0.0
    ]
    mrr = sum(rr_scores) / len(rr_scores)
    assert mrr == 0.5, f"MRR mismatch: {mrr}"
    print(f"✓ Mean Reciprocal Rank (MRR) verified across 3 queries: MRR={mrr:.4f}")

    print("=" * 80)
    print("ALL MATHEMATICAL VERIFICATION TESTS PASSED SUCCESSFULLY! ✓")
    print("=" * 80)
    return True


# ---------------------------------------------------------------------------
# NexaAssist Golden Dataset Evaluator
# ---------------------------------------------------------------------------

def canonical_key(doc_id: str, clause: str | None) -> str:
    """Standardize evidence identifier, e.g. 'POL-HL-V3::4.1' or 'POL-HL-V3'."""
    doc = doc_id.strip()
    c = clause.strip() if clause else ""
    return f"{doc}::{c}" if c else doc


async def evaluate_nexaassist_retrieval(dataset_path: Path, top_k: int = 5) -> None:
    """Evaluate NexaAssist vector retrieval against the golden dataset."""
    from app.core.config import get_settings
    from app.models.retrieval import RetrieveRequest
    from app.services.retrieval import retrieve_policy

    if not dataset_path.exists():
        print(f"Error: Dataset file not found at {dataset_path}", file=sys.stderr)
        sys.exit(1)

    print("\n" + "=" * 80)
    print("EVALUATING NEXAASSIST LIVE RETRIEVAL AGAINST GOLDEN DATASET")
    print(f"Dataset: {dataset_path.name} | top_k: {top_k}")
    print("=" * 80)

    settings = get_settings()
    results: list[QueryMetrics] = []

    with dataset_path.open() as f:
        lines = [line.strip() for line in f if line.strip()]

    for idx, line in enumerate(lines, start=1):
        case = json.loads(line)
        inp = case["input"]
        query = inp["query"]
        as_of = inp["as_of"]

        # Extract expected ground truth items
        relevant_keys: set[str] = set()
        for ctx in case.get("context", []):
            d_id = ctx.get("doc_id", "")
            cl = ctx.get("clause")
            relevant_keys.add(canonical_key(d_id, cl))
            # Also allow document-level match if clause is optional
            relevant_keys.add(d_id)

        # Call NexaAssist retrieval service
        req = RetrieveRequest(query=query, as_of=as_of, top_k=top_k)
        response = await retrieve_policy(req, settings)

        # Extract retrieved items
        retrieved_keys: list[str] = []
        for hit in response.results:
            cit = hit.citation
            retrieved_keys.append(canonical_key(cit.doc_id, cit.clause))

        qm = evaluate_query(query, retrieved_keys, relevant_keys, k_list=[1, 3, 5])
        results.append(qm)

        # Display per-query breakdown
        print(f"\n[Q{idx}] \"{query}\"")
        print(f"  Expected   : {sorted(list(relevant_keys))}")
        print(f"  Retrieved  : {retrieved_keys[:top_k]}")
        print(
            f"  P@1: {qm.precision[1]:.2f} | P@3: {qm.precision[3]:.2f} | P@5: {qm.precision[5]:.2f} | "
            f"R@5: {qm.recall[5]:.2f} | RR: {qm.rr:.2f} | nDCG@5: {qm.ndcg[5]:.2f}"
        )

    # Calculate overall aggregate metrics
    n = len(results)
    mean_p1 = sum(r.precision[1] for r in results) / n
    mean_p3 = sum(r.precision[3] for r in results) / n
    mean_p5 = sum(r.precision[5] for r in results) / n

    mean_r1 = sum(r.recall[1] for r in results) / n
    mean_r3 = sum(r.recall[3] for r in results) / n
    mean_r5 = sum(r.recall[5] for r in results) / n

    mrr = sum(r.rr for r in results) / n

    mean_ndcg1 = sum(r.ndcg[1] for r in results) / n
    mean_ndcg3 = sum(r.ndcg[3] for r in results) / n
    mean_ndcg5 = sum(r.ndcg[5] for r in results) / n

    print("\n" + "=" * 80)
    print("NEXAASSIST RETRIEVAL METRICS SUMMARY")
    print("=" * 80)
    print(f"{'Metric':<20} | {'Value':<10} | {'Interpretation'}")
    print("-" * 80)
    print(f"{'Precision@1':<20} | {mean_p1:<10.4f} | Fraction of top-1 results that are relevant")
    print(f"{'Precision@3':<20} | {mean_p3:<10.4f} | Fraction of top-3 results that are relevant")
    print(f"{'Precision@5':<20} | {mean_p5:<10.4f} | Fraction of top-5 results that are relevant")
    print("-" * 80)
    print(f"{'Recall@1':<20} | {mean_r1:<10.4f} | Share of relevant evidence captured in top-1")
    print(f"{'Recall@3':<20} | {mean_r3:<10.4f} | Share of relevant evidence captured in top-3")
    print(f"{'Recall@5':<20} | {mean_r5:<10.4f} | Share of relevant evidence captured in top-5")
    print("-" * 80)
    print(f"{'MRR':<20} | {mrr:<10.4f} | Mean Reciprocal Rank (speed to first hit)")
    print("-" * 80)
    print(f"{'nDCG@1':<20} | {mean_ndcg1:<10.4f} | Normalized Discounted Cumulative Gain @ 1")
    print(f"{'nDCG@3':<20} | {mean_ndcg3:<10.4f} | Normalized Discounted Cumulative Gain @ 3")
    print(f"{'nDCG@5':<20} | {mean_ndcg5:<10.4f} | Normalized Discounted Cumulative Gain @ 5")
    print("=" * 80 + "\n")


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify and compute Precision@k, Recall@k, MRR, and nDCG for NexaAssist."
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run pure mathematical verification checks and unit assertions.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=PROJECT_ROOT / "evaluation" / "datasets" / "retrieval.jsonl",
        help="Path to the golden evaluation dataset JSONL file.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Top k results to retrieve and evaluate (default: 5).",
    )
    args = parser.parse_args()

    # Always run the verification suite first
    run_verification_tests()

    # If --verify was explicitly requested and not live evaluation, exit cleanly
    if args.verify:
        return

    # If dataset exists, run live evaluation
    if args.dataset.exists():
        try:
            asyncio.run(evaluate_nexaassist_retrieval(args.dataset, top_k=args.top_k))
        except Exception as err:
            print(f"\nNote: Live retrieval evaluation encountered: {err}")
            print("To run in math-only verification mode, use: python verify_retrieval_metrics.py --verify")


if __name__ == "__main__":
    main()
