from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from functools import lru_cache
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_mongodb.docstores import MongoDBDocStore
from pymongo import MongoClient, ReplaceOne
from pymongo.collection import Collection
from pymongo.database import Database

from app.core.config import Settings


@lru_cache
def _client(uri: str) -> MongoClient[Any]:
    return MongoClient(uri)


def _database(settings: Settings) -> Database[Any]:
    return _client(settings.mongodb_uri.get_secret_value())[settings.mongodb_db]


def get_vector_store(settings: Settings, embedding: Embeddings) -> MongoDBAtlasVectorSearch:
    """Chunk store shared by the write path and the read path.

    The Atlas Vector Search index is created manually; see indexes.md.
    """
    return MongoDBAtlasVectorSearch(
        collection=_database(settings)[settings.mongodb_collection],
        embedding=embedding,
        index_name=settings.vector_index_name,
        text_key="text",
        embedding_key="embedding",
        relevance_score_fn="cosine",
        auto_create_index=False,
    )


class UpsertingParentStore(MongoDBDocStore):
    """Keep existing section keys readable while replacing their contents."""

    def insert_many(
        self, texts: Iterable[str], metadatas: Iterable[dict[str, Any]], ids: list[str]
    ) -> None:
        operations = [
            ReplaceOne(
                {"_id": key},
                {**metadata, "_id": key, self._text_key: text},
                upsert=True,
            )
            for key, text, metadata in zip(ids, texts, metadatas, strict=True)
        ]
        if operations:
            self.collection.bulk_write(operations)

    def yield_keys(self, *, prefix: str | None = None) -> Iterator[str]:
        # The integration treats prefixes as regex; BaseStore callers expect literals.
        return super().yield_keys(prefix=re.escape(prefix) if prefix is not None else None)


def get_parent_store(settings: Settings) -> MongoDBDocStore:
    """Whole sections keyed by parent_id, in their own collection. Not embedded."""
    return UpsertingParentStore(_database(settings)[settings.mongodb_parent_collection])


def delete_stale_chunks(collection: Collection[Any], doc_id: str, keep_ids: list[str]) -> int:
    """Retire chunks of `doc_id` that the latest ingest no longer produced."""
    result = collection.delete_many({"doc_id": doc_id, "_id": {"$nin": keep_ids}})
    return result.deleted_count


def retire_document(settings: Settings, doc_id: str) -> dict[str, int]:
    """Explicitly retire one withdrawn document from both stores, scoped to this corpus."""
    scope = {
        "doc_id": doc_id,
        "institution": settings.institution,
        "jurisdiction": settings.jurisdiction,
        "confidentiality_level": settings.confidentiality_level,
    }
    database = _database(settings)
    return {
        "chunks_removed": database[settings.mongodb_collection].delete_many(scope).deleted_count,
        "parents_removed": database[settings.mongodb_parent_collection]
        .delete_many(scope)
        .deleted_count,
    }
