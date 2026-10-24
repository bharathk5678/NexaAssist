from __future__ import annotations

import re
from time import perf_counter

import structlog
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable, RunnableLambda

from app.chains.context import assemble_context, render_context
from app.chains.prompts.answer import ANSWER_PROMPT, ANSWER_PROMPT_ID, ANSWER_PROMPT_VERSION
from app.core.config import Settings
from app.core.observability import prompt_annotation_context
from app.models.answer import AnswerCitation, AnswerDraft, AnswerResponse
from app.models.retrieval import RetrieveRequest, RetrieveResponse

logger = structlog.get_logger()
INSUFFICIENT_EVIDENCE = (
    "I cannot answer this question reliably from the retrieved policy evidence. "
    "Check the selected product and policy date, and specify the policy term you want to check."
)


def build_answer_chain(
    retriever: Runnable[RetrieveRequest, RetrieveResponse],
    llm: BaseChatModel,
    settings: Settings,
) -> Runnable[RetrieveRequest, AnswerResponse]:
    """Retrieve evidence, generate a draft, and validate its citation references."""
    generation = ANSWER_PROMPT | llm.with_structured_output(
        AnswerDraft, method="json_schema", strict=True
    )

    async def answer(request: RetrieveRequest) -> AnswerResponse:
        retrieved = await retriever.ainvoke(request)
        sources = assemble_context(
            retrieved.evidence, settings.context_max_tokens, settings.token_encoding
        )

        response = AnswerResponse(
            as_of=request.as_of,
            status="insufficient_evidence",
            answer=INSUFFICIENT_EVIDENCE,
            citations=[],
            retrieval_timings=retrieved.timings,
            generation_ms=0,
        )
        if any(
            not any(source.parent_text == amendment.parent_text for source in sources.values())
            for amendment in retrieved.amendments
        ):
            return response

        started = perf_counter()
        for attempt in range(2):
            variables = {
                "query": request.query,
                "as_of": request.as_of.isoformat(),
                "product_id": request.product_id or "All products",
                "context": render_context(sources),
                "citation_feedback": ""
                if attempt == 0
                else "The previous draft failed citation validation. Copy exact contiguous "
                "quotes and ensure every evidence ID matches its inline markers.",
            }
            with prompt_annotation_context(
                ANSWER_PROMPT,
                variables,
                prompt_id=ANSWER_PROMPT_ID,
                version=ANSWER_PROMPT_VERSION,
            ):
                raw = await generation.ainvoke(variables)
            response.generation_ms = round((perf_counter() - started) * 1000, 2)
            draft = AnswerDraft.model_validate(raw)
            if draft.status == "insufficient_evidence":
                return response
            if draft.status == "needs_clarification":
                response.status = "needs_clarification"
                response.answer = (
                    "Which product and policy date should I use, "
                    "and what specific rate or policy term do you want to check?"
                )
                return response
            if not sources:
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
                logger.warning("answer_citation_validation_failed", attempt=attempt + 1)
                continue

            response.status = "answered"
            response.answer = draft.answer
            response.citations = [
                AnswerCitation(
                    **item.model_dump(), matched_child=sources[item.evidence_id].citation
                )
                for item in draft.evidence
            ]
            return response
        return response

    return RunnableLambda(answer).with_config(run_name="answer_policy")
