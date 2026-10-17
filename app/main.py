from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.answer import router as answer_router
from app.api.operations import router as operations_router
from app.api.retrieval import router as retrieval_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.telemetry import init_telemetry


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    init_telemetry(settings.dd_trace_enabled)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="NexaAssist", lifespan=lifespan)
    app.include_router(operations_router)
    app.include_router(retrieval_router)
    app.include_router(answer_router)
    return app


app = create_app()
