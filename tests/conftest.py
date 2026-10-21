from __future__ import annotations

import pytest

from app.core.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        mongodb_uri="mongodb://unused",
        mongodb_db="unused",
        mongodb_collection="chunks",
        openai_api_key="unused",
        institution="NexaBank",
        jurisdiction="IN",
        confidentiality_level="internal",
    )
