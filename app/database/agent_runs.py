"""Persist institution-scoped run records, atomic leases and typed graph checkpoints."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any

from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from pymongo import MongoClient, ReturnDocument, timeout
from pymongo.collection import Collection

from app.core.config import Settings
from app.models.agent import AgentRequest, AgentResponse, IntentDecision
from app.models.answer import AnswerCitation, AnswerResponse
from app.models.retrieval import (
    Citation,
    RetrieveHit,
    RetrieveRequest,
    RetrieveResponse,
    RetrieveTimings,
)
from app.models.validation import (
    ServiceRequestDetails,
    ServiceRequestProposal,
    ServiceRequestReceipt,
    SubmittedServiceRequest,
    ValidationEvidence,
    ValidationResult,
)


@lru_cache
def _agent_client(uri: str) -> MongoClient[Any]:
    return MongoClient(
        uri,
        timeoutMS=5000,
        serverSelectionTimeoutMS=5000,
        tz_aware=True,
        w="majority",
        journal=True,
        readConcernLevel="majority",
    )


class MongoRunStore:
    """Durable workflow checkpoints plus an atomic lease for each run mutation.

    Args:
        settings: Validated application configuration for this operation.
    """

    def __init__(self, settings: Settings) -> None:
        self.institution = settings.institution
        self.retention_seconds = settings.mongodb_agent_retention_seconds
        with timeout(5):
            database = _agent_client(settings.mongodb_uri.get_secret_value())[settings.mongodb_db]
            self.collection: Collection[Any] = database[settings.mongodb_agent_runs_collection]
            self.collection.create_index("purge_at", expireAfterSeconds=0)
            allowed = [
                (model.__module__, model.__name__)
                for model in (
                    AgentRequest,
                    AgentResponse,
                    IntentDecision,
                    AnswerResponse,
                    AnswerCitation,
                    RetrieveRequest,
                    RetrieveResponse,
                    RetrieveHit,
                    RetrieveTimings,
                    Citation,
                    ValidationResult,
                    ValidationEvidence,
                    ServiceRequestDetails,
                    ServiceRequestProposal,
                    ServiceRequestReceipt,
                    SubmittedServiceRequest,
                )
            ]
            self.checkpointer = MongoDBSaver(
                database.client,
                db_name=settings.mongodb_db,
                checkpoint_collection_name=settings.mongodb_agent_checkpoints_collection,
                writes_collection_name=settings.mongodb_agent_writes_collection,
                ttl=self.retention_seconds,
                serde=JsonPlusSerializer(
                    allowed_msgpack_modules=allowed, allowed_json_modules=allowed
                ),
            )

    async def _call[T](self, operation: Callable[[], T]) -> T:
        def bounded() -> T:
            """Execute the synchronous store operation within its MongoDB deadline.

            Returns:
                T value produced by this operation.
            """
            with timeout(5):
                return operation()

        return await asyncio.to_thread(bounded)

    def _scope(self, run_id: str) -> dict[str, Any]:
        return {"_id": run_id, "institution": self.institution}

    async def create(self, record: dict[str, Any]) -> None:
        """Insert an institution-scoped run with its retention deadline.

        Args:
            record: Retained evaluation case, generated answer and supporting source identities.
        """
        await self._call(
            lambda: self.collection.insert_one(
                {
                    **record,
                    "institution": self.institution,
                    "purge_at": datetime.now(UTC) + timedelta(seconds=self.retention_seconds),
                }
            )
        )

    async def get(self, run_id: str) -> dict[str, Any] | None:
        """Read a run only within the configured institution.

        Args:
            run_id: Identifier of the saved workflow to read or resume.

        Returns:
            Scoped run record, or None when no matching run exists.
        """
        return await self._call(lambda: self.collection.find_one(self._scope(run_id)))

    async def claim(self, run_id: str, lease: str, seconds: float) -> dict[str, Any] | None:
        """Atomically acquire an available or expired execution lease.

        Args:
            run_id: Identifier of the saved workflow to read or resume.
            lease: Lease supplied by the caller.
            seconds: Seconds supplied by the caller.

        Returns:
            Claimed run record, or None if the lease is unavailable.
        """
        now = datetime.now(UTC)
        return await self._call(
            lambda: self.collection.find_one_and_update(
                {
                    **self._scope(run_id),
                    "$or": [{"lease_until": {"$lte": now}}, {"lease_until": None}],
                },
                {"$set": {"lease_id": lease, "lease_until": now + timedelta(seconds=seconds)}},
                return_document=ReturnDocument.AFTER,
            )
        )

    async def update(self, run_id: str, lease: str, **changes: Any) -> bool:
        """Update a run only while the caller owns its unexpired lease.

        Args:
            run_id: Identifier of the saved workflow to read or resume.
            lease: Lease supplied by the caller.
            changes: Input mutations used to exercise validation boundaries.

        Returns:
            Whether the matching owned run was updated.
        """
        result = await self._call(
            lambda: self.collection.update_one(
                {
                    **self._scope(run_id),
                    "lease_id": lease,
                    "lease_until": {"$gt": datetime.now(UTC)},
                },
                {"$set": changes},
            )
        )
        return result.matched_count == 1

    async def release(self, run_id: str, lease: str, status: str) -> None:
        """Persist final status and release only the caller's execution lease.

        Args:
            run_id: Identifier of the saved workflow to read or resume.
            lease: Lease supplied by the caller.
            status: HTTP or workflow status used by the scenario.
        """
        await self._call(
            lambda: self.collection.update_one(
                {**self._scope(run_id), "lease_id": lease},
                {"$set": {"status": status}, "$unset": {"lease_id": "", "lease_until": ""}},
            )
        )
