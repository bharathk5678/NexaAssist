from __future__ import annotations

from fastapi import FastAPI

from app.api.agent import router
from app.api.agent_runs import router as runs_router
from app.core.lifespan import lifespan


def create_agent_app() -> FastAPI:
    # Reuse Phase 1's logging, Datadog and tokenizer startup, without its routes.
    app = FastAPI(title="NexaAssist Agent Service", lifespan=lifespan)
    app.include_router(router)
    app.include_router(runs_router)
    return app


app = create_agent_app()
