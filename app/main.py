from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.answer import router as answer_router
from app.api.feedback import router as feedback_router
from app.api.operations import router as operations_router
from app.api.retrieval import router as retrieval_router
from app.chains.context import token_encoder
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.telemetry import init_telemetry


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    init_telemetry(settings.dd_trace_enabled)
    configure_logging(settings.log_level)
    await asyncio.to_thread(token_encoder, settings.token_encoding)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="NexaAssist", lifespan=lifespan)
    app.include_router(operations_router)
    app.include_router(retrieval_router)
    app.include_router(answer_router)
    app.include_router(feedback_router)
    return app


app = create_app()
