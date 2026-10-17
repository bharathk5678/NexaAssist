from __future__ import annotations

import json
import re
from time import perf_counter

import structlog
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable, RunnableLambda

from app.chains.prompts.answer import ANSWER_PROMPT
from app.models.answer import AnswerCitation, AnswerDraft, AnswerResponse
from app.models.retrieval import RetrieveHit, RetrieveRequest, RetrieveResponse

logger = structlog.get_logger()
INSUFFICIENT_EVIDENCE = "I cannot answer this question reliably from the retrieved policy evidence."


def build_answer_chain(
    retriever: Runnable[RetrieveRequest, RetrieveResponse], llm: BaseChatModel
) -> Runnable[RetrieveRequest, AnswerResponse]:
    """Retrieve evidence, generate a draft, and validate its citation references."""
    generation = ANSWER_PROMPT | llm.with_structured_output(
        AnswerDraft, method="json_schema", strict=True
    )

    async def answer(request: RetrieveRequest) -> AnswerResponse:
        retrieved = await retriever.ainvoke(request)
        sources: dict[int, RetrieveHit] = {}
        seen: set[tuple[str, str, str]] = set()
        for hit in retrieved.results:
            key = (hit.citation.doc_id, hit.citation.policy_version, hit.parent_text)
            if key not in seen:
                seen.add(key)
                sources[len(sources) + 1] = hit

        response = AnswerResponse(
            as_of=request.as_of,
            status="insufficient_evidence",
            answer=INSUFFICIENT_EVIDENCE,
            citations=[],
            retrieval_timings=retrieved.timings,
            generation_ms=0,
        )
        if not sources:
            return response

        context = [
            {
                "evidence_id": number,
                "matched_child": hit.citation.model_dump(mode="json"),
                "retrieved_context": hit.parent_text,
            }
            for number, hit in sources.items()
        ]
        started = perf_counter()
        raw = await generation.ainvoke(
            {
                "query": request.query,
                "as_of": request.as_of.isoformat(),
                "context": json.dumps(context, ensure_ascii=False),
            }
        )
        response.generation_ms = round((perf_counter() - started) * 1000, 2)
        draft = AnswerDraft.model_validate(raw)
        if draft.status == "insufficient_evidence":
            return response

        markers = {int(number) for number in re.findall(r"\[(\d+)\]", draft.answer)}
        evidence_ids = {item.evidence_id for item in draft.evidence}
        if (
            not evidence_ids
            or markers != evidence_ids
            or any(
                item.evidence_id not in sources
                or not item.quote.strip()
                or item.quote not in sources[item.evidence_id].parent_text
                for item in draft.evidence
            )
        ):
            logger.warning("answer_citation_validation_failed")
            return response

        response.status = "answered"
        response.answer = draft.answer
        response.citations = [
            AnswerCitation(**item.model_dump(), matched_child=sources[item.evidence_id].citation)
            for item in draft.evidence
        ]
        return response

    return RunnableLambda(answer).with_config(run_name="answer_policy")
