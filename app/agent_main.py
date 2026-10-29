from pathlib import Path
import sys

# Ensure repository root is on sys.path so 'app' package can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI

from app.api.agent import router
from app.main import lifespan


def create_agent_app() -> FastAPI:
    # Reuse Phase 1's logging, Datadog and tokenizer startup, without its routes.
    app = FastAPI(title="NexaAssist Agent Service", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_agent_app()
