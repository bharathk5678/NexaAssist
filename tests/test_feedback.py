from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import mongomock
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.database import feedback as database
from app.database import mongo
from app.main import create_app
from app.models.answer import AnswerResponse
from app.models.feedback import FeedbackRequest
from app.models.retrieval import RetrieveRequest, RetrieveTimings
from app.services import feedback as service


@pytest.mark.parametrize("helpful", [True, False])
@pytest.mark.parametrize("delivery", ["enabled", "disabled", "legacy", "failure"])
def test_feedback_persists_review_and_prevents_overwriting(
    monkeypatch: pytest.MonkeyPatch, settings: Settings, helpful: bool, delivery: str
) -> None:
    publish = Mock(side_effect=RuntimeError("offline") if delivery == "failure" else None)
    monkeypatch.setattr(
        service, "LLMObs", SimpleNamespace(enabled=delivery != "disabled", submit_feedback=publish)
    )
    storage: Any = mongomock.MongoClient().db
    monkeypatch.setattr(database, "_database", lambda _: storage)
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    request = FeedbackRequest(
        request=RetrieveRequest(query="fee", as_of=date(2026, 10, 1)),
        response=AnswerResponse(
            as_of=date(2026, 10, 1),
            status="insufficient_evidence",
            answer="No evidence",
            citations=[],
            generation_ms=0,
            datadog_span_id=None if delivery == "legacy" else "10965486069833089691",
            retrieval_timings=RetrieveTimings(search_ms=0, parent_ms=0, total_ms=0),
        ),
        helpful=helpful,
        correction="The current circular is missing.",
    )
    response = client.post("/feedback", json=request.model_dump(mode="json"))
    assert response.status_code == 201
    identifier = response.json()["feedback_id"]
    if delivery in {"enabled", "failure"}:
        publish.assert_called_once_with(
            label="thumbs",
            metric_type="boolean",
            value=helpful,
            submitter={"id": str(request.submitter_id), "type": "end_user"},
            span_id=request.response.datadog_span_id,
            agent_service=settings.dd_service,
            assessment="pass" if helpful else "fail",
            reasoning=request.correction,
            tags={"feedback_id": identifier},
        )
    else:
        publish.assert_not_called()
    review = {
        "status": "accepted",
        "reviewer": "Instructor",
        "review_note": "Add a regression case.",
    }
    assert client.post(f"/feedback/{identifier}/review", json=review).status_code == 200
    assert client.post(f"/feedback/{identifier}/review", json=review).status_code == 409
    assert client.get("/feedback").json()[0]["status"] == "accepted"
    other_settings = settings.model_copy(update={"institution": "OtherBank"})
    assert database.list_feedback(other_settings, 20) == []
    assert client.post(f"/feedback/{uuid4()}/review", json=review).status_code == 409


def test_retire_document_removes_both_stores_only_in_current_scope(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    storage: Any = mongomock.MongoClient().db
    monkeypatch.setattr(mongo, "_database", lambda _: storage)
    for name in (settings.mongodb_collection, settings.mongodb_parent_collection):
        storage[name].insert_many(
            [
                {
                    "doc_id": "OLD",
                    "institution": institution,
                    "jurisdiction": "IN",
                    "confidentiality_level": "internal",
                }
                for institution in ("NexaBank", "OtherBank")
            ]
        )
    assert mongo.retire_document(settings, "OLD") == {"chunks_removed": 1, "parents_removed": 1}
    assert storage.chunks.find_one()["institution"] == "OtherBank"
