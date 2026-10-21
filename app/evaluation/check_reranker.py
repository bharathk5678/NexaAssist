from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
import structlog
from langchain_core.documents import Document

from app.chains.rerank import build_rerank_chain
from app.core.config import get_settings
from app.core.logging import configure_logging


async def check() -> dict[str, object]:
    settings = get_settings()
    if urlparse(settings.rerank_base_url).hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("This smoke test only permits a local reranker endpoint")
    report: dict[str, object] = {
        "captured_at": datetime.now(UTC).isoformat(),
        "model": settings.rerank_model,
        "endpoint": settings.rerank_base_url,
        "api": settings.rerank_api,
        "status": "failed",
        "input_kind": "fixed fictional passages; no Atlas or OpenAI cloud calls",
    }
    rows = [
        (Document(page_content="A car loan requires a vehicle invoice."), 0.9),
        (Document(page_content="A home loan processing fee is 0.35 percent of the amount."), 0.5),
    ]
    try:
        ranked = await build_rerank_chain(settings).ainvoke(
            {
                "query": "What is the home loan processing fee?",
                "as_of": "2026-10-01",
                "rows": rows,
            }
        )
        report["scores"] = [{"text": doc.page_content, "score": score} for doc, score in ranked]
        if ranked[0][0].page_content == rows[1][0].page_content and ranked[0][1] > ranked[1][1]:
            report["status"] = "passed"
    except (httpx.HTTPError, ValueError) as exc:
        report["error_type"] = type(exc).__name__
        if isinstance(exc, ValueError):
            report["reason"] = str(exc)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Check local Qwen reranker API compatibility")
    parser.add_argument(
        "--output", type=Path, default=Path("app/evaluation/results/reranker_check.json")
    )
    args = parser.parse_args()
    configure_logging("INFO")
    report = asyncio.run(check())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2))
    structlog.get_logger().info("local_reranker_check", **report)
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
