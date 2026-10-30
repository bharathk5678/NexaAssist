"""Regression tests for llamacpp rerank."""

from __future__ import annotations

import asyncio
import json
from math import log

import httpx
import pytest
from langchain_core.documents import Document

from app.chains.rerank import build_rerank_chain, completion_probabilities, relevance_probability
from app.core.config import Settings


@pytest.mark.parametrize("field", ["probs", "completion_probabilities"])
def test_constrained_sampling_retains_original_yes_no_logit_ratio(field: str) -> None:
    # Other allowed prefixes change the common denominator, not the yes/no ratio.
    """Verify constrained sampling retains original yes no logit ratio.

    Args:
        field: Field fixture or parametrized input for this scenario.
    """
    values = completion_probabilities(
        {
            field: [
                {
                    "top_probs": [
                        {"token": "yes", "prob": 0.6},
                        {"token": "no", "prob": 0.2},
                        {"token": "y", "prob": 0.1},
                        {"token": "n", "prob": 0.1},
                    ]
                }
            ]
        }
    )
    assert relevance_probability(values) == pytest.approx(
        relevance_probability({"yes": log(0.06), "no": log(0.02)})
    )
    assert relevance_probability(values) == pytest.approx(0.75)


@pytest.mark.parametrize("value", [0, -0.1, 1.1, float("nan"), float("inf"), True, "0.5"])
def test_invalid_target_probabilities_are_rejected(value) -> None:
    """Verify invalid target probabilities are rejected.

    Args:
        value: Candidate value supplied by validation or the calling integration.
    """
    with pytest.raises(ValueError):
        completion_probabilities({"probs": [{"top_probs": [{"token": "yes", "prob": value}]}]})


@pytest.mark.parametrize(
    "tokens", [[], [{"token": "Yes", "prob": 0.9}, {"token": "no", "prob": 0.1}]]
)
def test_missing_exact_target_still_fails(tokens) -> None:
    """Verify missing exact target still fails.

    Args:
        tokens: Tokens fixture or parametrized input for this scenario.
    """
    with pytest.raises(ValueError, match="yes AND no"):
        relevance_probability(completion_probabilities({"probs": [{"top_probs": tokens}]}))


def test_native_api_uses_unbiased_constrained_likelihoods(settings: Settings) -> None:
    """Verify native api uses unbiased constrained likelihoods.

    Args:
        settings: Validated application configuration for this operation.
    """
    bodies = []

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/completion"
        body = json.loads(request.content)
        bodies.append(body)
        relevant = "Home loan fee" in body["prompt"]
        return httpx.Response(
            200,
            json={
                "probs": [
                    {
                        "top_probs": [
                            {"token": "yes", "prob": 0.8 if relevant else 0.1},
                            {"token": "no", "prob": 0.1 if relevant else 0.8},
                        ]
                    }
                ]
            },
        )

    settings = settings.model_copy(
        update={"rerank_api": "llamacpp", "rerank_base_url": "http://local/"}
    )
    rows = [
        (Document(page_content="Vehicle registration"), 0.9),
        (Document(page_content="Home loan fee"), 0.5),
    ]
    result = asyncio.run(
        build_rerank_chain(settings, transport=httpx.MockTransport(respond)).ainvoke(
            {"query": "home fee?", "as_of": "2026-10-01", "rows": rows}
        )
    )
    assert result[0][0].page_content == "Home loan fee" and result[0][1] > result[1][1]
    assert len(bodies) == 2
    for body in bodies:
        assert body["grammar"] == 'root ::= "yes" | "no"'
        assert body["logit_bias"] == [["yes", 100.0], ["no", 100.0]]
        assert body["temperature"] == body["top_p"] == body["repeat_penalty"] == 1
        assert (
            body["top_k"]
            == body["min_p"]
            == body["presence_penalty"]
            == body["frequency_penalty"]
            == 0
        )
        assert body["post_sampling_probs"] is True and body["n_predict"] == 1
