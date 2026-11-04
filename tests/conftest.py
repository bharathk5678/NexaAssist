from __future__ import annotations

from typing import Any

import pytest

from app.core.config import Settings


@pytest.fixture
def workflow_settings(settings: Settings) -> Settings:
    from uuid import uuid4

    return settings.model_copy(update={"mongodb_db": "nexa_agent_test_" + uuid4().hex})


@pytest.fixture
def run_store(workflow_settings: Settings, monkeypatch: pytest.MonkeyPatch):
    import os

    import mongomock
    from mongomock.collection import BulkOperationBuilder
    from pymongo import MongoClient

    from app.database import agent_runs

    uri = os.environ.get("NEXA_TEST_MONGODB_URI")
    client: Any = (
        MongoClient(uri, timeoutMS=5000, tz_aware=True)
        if uri
        else mongomock.MongoClient(tz_aware=True)
    )
    if uri is None:
        original = BulkOperationBuilder.add_update

        def compatible_update(self, selector, document, *args, **kwargs):
            # mongomock 4.3 predates PyMongo's optional sort argument.
            assert kwargs.pop("sort", None) is None
            return original(self, selector, document, *args, **kwargs)

        monkeypatch.setattr(BulkOperationBuilder, "add_update", compatible_update)
    monkeypatch.setattr(agent_runs, "_agent_client", lambda _: client)
    yield agent_runs.MongoRunStore(workflow_settings)
    client.drop_database(workflow_settings.mongodb_db)
    client.close()


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
