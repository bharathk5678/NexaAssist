"""Read-only storage observations for the Session 5 teaching examples."""

from __future__ import annotations

from typing import Any

from pymongo import timeout

from app.core.config import Settings
from app.database.mongo import _database


def read_rag_snapshot(settings: Settings) -> dict[str, Any]:
    """Read index definitions and chunk payloads, replacing vectors with their lengths.

    The lesson caller runs this synchronous database work in a worker thread.
    """
    collection = _database(settings)[settings.mongodb_collection]
    with timeout(30):
        parents = list(
            _database(settings)[settings.mongodb_parent_collection].find({}, {"embedding": 0})
        )
        indexes = [
            {
                key: row.get(key)
                for key in ("name", "type", "status", "queryable", "latestDefinition")
            }
            for row in collection.list_search_indexes()
        ]
        chunks = list(
            collection.aggregate(
                [
                    {
                        "$set": {
                            "_actual_dimensions": {
                                "$cond": [
                                    {"$isArray": "$embedding"},
                                    {"$size": "$embedding"},
                                    -1,
                                ]
                            }
                        }
                    },
                    {"$project": {"embedding": 0}},
                ]
            )
        )
    return {"indexes": indexes, "chunks": chunks, "parents": parents}
