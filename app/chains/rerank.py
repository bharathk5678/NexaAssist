from __future__ import annotations

from math import exp, isfinite
from typing import Any

import httpx
from langchain_core.documents import Document
from langchain_core.runnables import Runnable, RunnableLambda
from pydantic import TypeAdapter

from app.chains.context import token_encoder
from app.chains.prompts.rerank import rerank_prompt
from app.core.config import Settings


def relevance_probability(logprobs: dict[str, float]) -> float:
    """Normalize Qwen's exact lowercase yes/no tokens, without merging variants."""
    if not all(token in logprobs and isfinite(logprobs[token]) for token in ("yes", "no")):
        raise ValueError("Reranker endpoint must return finite yes AND no token logprobs")
    largest = max(logprobs["yes"], logprobs["no"])
    yes, no = exp(logprobs["yes"] - largest), exp(logprobs["no"] - largest)
    return yes / (yes + no)


def completion_probabilities(payload: dict[str, Any]) -> dict[str, float]:
    """Accept native Ollama, legacy OpenAI, and content-array logprob shapes."""
    try:
        if "logprobs" in payload:
            values = {
                item["token"]: item["logprob"] for item in payload["logprobs"][0]["top_logprobs"]
            }
            return TypeAdapter(dict[str, float]).validate_python(values)
        probabilities = payload["choices"][0]["logprobs"]
        if probabilities.get("content"):
            values = {
                item["token"]: item["logprob"]
                for item in probabilities["content"][0]["top_logprobs"]
            }
        else:
            values = probabilities["top_logprobs"][0]
        return TypeAdapter(dict[str, float]).validate_python(values)
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise ValueError("Reranker endpoint did not return alternative token logprobs") from exc


def build_rerank_chain(
    settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None
) -> Runnable[dict[str, Any], list[tuple[Document, float]]]:
    """Qwen3 pair scoring through native Ollama or OpenAI-compatible completions.

    The installed Ollama model determines its execution engine. This adapter
    does not convert GGUF weights to MLX or verify an MLX backend.
    """

    async def rerank(value: dict[str, Any]) -> list[tuple[Document, float]]:
        rows: list[tuple[Document, float]] = value["rows"]
        if not rows:
            return []
        scored = []
        async with httpx.AsyncClient(
            base_url=settings.rerank_base_url,
            headers={"Authorization": f"Bearer {settings.rerank_api_key.get_secret_value()}"},
            timeout=60,
            transport=transport,
            trust_env=False,
        ) as client:
            for document, _ in rows:
                prompt = rerank_prompt(value["query"], document.page_content, value["as_of"])
                if (
                    len(
                        token_encoder(settings.token_encoding).encode(prompt, disallowed_special=())
                    )
                    > settings.rerank_max_tokens
                ):
                    raise ValueError("Rerank candidate exceeds the configured token budget")
                if settings.rerank_api == "ollama":
                    path = "api/generate"
                    payload = {
                        "model": settings.rerank_model,
                        "prompt": prompt,
                        "raw": True,
                        "stream": False,
                        "logprobs": True,
                        "top_logprobs": 20,
                        "options": {"num_predict": 1, "temperature": 0},
                    }
                else:
                    path = "completions"
                    payload = {
                        "model": settings.rerank_model,
                        "prompt": prompt,
                        "max_tokens": 1,
                        "temperature": 0,
                        "logprobs": 20,
                    }
                response = await client.post(path, json=payload)
                response.raise_for_status()
                scored.append(
                    (document, relevance_probability(completion_probabilities(response.json())))
                )
        return sorted(scored, key=lambda row: row[1], reverse=True)

    return RunnableLambda(rerank).with_config(run_name="local_qwen3_rerank")
