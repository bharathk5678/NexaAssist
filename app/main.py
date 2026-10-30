from __future__ import annotations

from fastapi import FastAPI

from app.api.answer import router as answer_router
from app.api.feedback import router as feedback_router
from app.api.operations import router as operations_router
from app.api.retrieval import router as retrieval_router
from app.core.lifespan import lifespan


def create_app() -> FastAPI:
    app = FastAPI(title="NexaAssist", lifespan=lifespan)
    app.include_router(operations_router)
    app.include_router(retrieval_router)
    app.include_router(answer_router)
    app.include_router(feedback_router)
    return app


app = create_app()
