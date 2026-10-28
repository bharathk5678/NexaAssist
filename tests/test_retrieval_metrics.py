from __future__ import annotations

import math
import pytest

from verify_retrieval_metrics import (
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
    dcg_at_k,
    ndcg_at_k,
    evaluate_query,
)


def test_precision_at_k():
    relevant = {"A", "B"}
    retrieved = ["A", "C", "B", "D"]

    assert precision_at_k(retrieved, relevant, 1) == 1.0  # ["A"] -> 1/1
    assert precision_at_k(retrieved, relevant, 2) == 0.5  # ["A", "C"] -> 1/2
    assert precision_at_k(retrieved, relevant, 3) == 2 / 3  # ["A", "C", "B"] -> 2/3
    assert precision_at_k(retrieved, relevant, 4) == 0.5  # ["A", "C", "B", "D"] -> 2/4

    # k out of range / empty
    assert precision_at_k([], relevant, 1) == 0.0
    with pytest.raises(ValueError):
        precision_at_k(retrieved, relevant, 0)


def test_recall_at_k():
    relevant = {"A", "B", "E"}
    retrieved = ["A", "C", "B", "D"]

    assert recall_at_k(retrieved, relevant, 1) == 1 / 3  # ["A"] -> 1/3
    assert recall_at_k(retrieved, relevant, 2) == 1 / 3  # ["A", "C"] -> 1/3
    assert recall_at_k(retrieved, relevant, 3) == 2 / 3  # ["A", "C", "B"] -> 2/3
    assert recall_at_k(retrieved, relevant, 4) == 2 / 3  # ["A", "C", "B", "D"] -> 2/3

    # Empty relevant set
    assert recall_at_k([], set(), 1) == 1.0
    assert recall_at_k(["A"], set(), 1) == 0.0


def test_reciprocal_rank():
    relevant = {"target"}

    assert reciprocal_rank(["target", "x", "y"], relevant) == 1.0
    assert reciprocal_rank(["x", "target", "y"], relevant) == 0.5
    assert reciprocal_rank(["x", "y", "target"], relevant) == 1 / 3
    assert reciprocal_rank(["x", "y", "z"], relevant) == 0.0

    # With k restriction
    assert reciprocal_rank(["x", "target"], relevant, k=1) == 0.0
    assert reciprocal_rank(["x", "target"], relevant, k=2) == 0.5


def test_dcg_and_ndcg_at_k():
    # Binary relevance
    relevant = {"docA", "docB"}
    retrieved = ["docC", "docA", "docD", "docB"]

    # k=1: ["docC"] -> rel 0 -> DCG=0, nDCG=0
    assert ndcg_at_k(retrieved, relevant, 1) == 0.0

    # k=2: ["docC", "docA"] -> rels [0, 1]
    # DCG = (2^1 - 1) / log2(3) = 1 / log2(3) ≈ 0.6309
    # Ideal top 2: rels [1, 1] -> IDCG = 1/log2(2) + 1/log2(3) = 1 + 0.6309 = 1.6309
    expected_ndcg_2 = (1 / math.log2(3)) / (1 + 1 / math.log2(3))
    assert math.isclose(ndcg_at_k(retrieved, relevant, 2), expected_ndcg_2, rel_tol=1e-5)

    # Perfect ranking
    assert ndcg_at_k(["docA", "docB"], relevant, 2) == 1.0

    # Complete miss
    assert ndcg_at_k(["x", "y"], relevant, 2) == 0.0


def test_evaluate_query():
    qm = evaluate_query("test query", ["A", "B", "C"], {"A", "B"}, k_list=[1, 2, 3])
    assert qm.query == "test query"
    assert qm.rr == 1.0
    assert qm.precision[1] == 1.0
    assert qm.precision[2] == 1.0
    assert qm.recall[2] == 1.0
    assert qm.ndcg[2] == 1.0
