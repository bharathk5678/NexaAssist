# MongoDB Atlas Vector Search index

Create this index manually in Atlas (Atlas UI > Atlas Search > Create Search Index > Atlas Vector Search > JSON editor) on the collection named by `MONGODB_DB` / `MONGODB_COLLECTION`.

- **Index name:** `policy_chunks_v1` (must match `VECTOR_INDEX_NAME`)
- **numDimensions:** must match `EMBEDDING_DIMENSIONS` (1536 for `text-embedding-3-small`)

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 1536,
      "similarity": "cosine"
    },
    { "type": "filter", "path": "product_id" },
    { "type": "filter", "path": "jurisdiction" },
    { "type": "filter", "path": "effective_date" },
    { "type": "filter", "path": "effective_to_search" },
    { "type": "filter", "path": "doc_type" },
    { "type": "filter", "path": "confidentiality_level" }
  ]
}
```

`effective_date` and `effective_to_search` support the inclusive as-of query `effective_date <= d AND effective_to_search >= d`. Both are ISO date strings. Open-ended documents keep `effective_to: null` as source metadata and store `effective_to_search: "9999-12-31"` for the index. Rebuild the existing Atlas index with this JSON and re-ingest the document register before using the retrieval API; re-ingestion updates the chunk checksums and metadata. Filter fields can only be used in a query if they are in the index.

Changing the embedding model or dimension means a new index version (`policy_chunks_v2`) and a full re-embed, never a mixed index.

## Full-text index for hybrid retrieval

Create a second **Atlas Search** index on the same chunk collection. This is a text
index, separate from the Atlas Vector Search index above. Set its name to
`policy_text_v1` (matching `TEXT_INDEX_NAME`):

```json
{
  "mappings": {
    "dynamic": false,
    "fields": {
      "text": {
        "type": "string",
        "analyzer": "lucene.standard"
      }
    }
  }
}
```

Wait until both indexes are queryable, then set `RETRIEVAL_MODE=hybrid`.
`MongoDBAtlasHybridSearchRetriever` combines dense and BM25 candidates using RRF.
The vector branch uses `pre_filter`; the integration's text branch applies the
same MongoDB filter immediately after `$search`, before its candidate limit and
RRF. Text metadata filtering therefore does not require extra Atlas Search token
mappings, though this post-search filtering can cost more at scale. Both branches
enforce the same date, product, jurisdiction and confidentiality restrictions.
Index creation is always manual; there is no fallback to dense search on a missing
text index. Dense mode remains available for baseline comparisons.

References: [LangChain MongoDB hybrid retriever](https://langchain-mongodb.readthedocs.io/en/latest/_modules/langchain_mongodb/retrievers/hybrid_search.html),
[MongoDB text-search stage](https://langchain-mongodb.readthedocs.io/en/latest/_modules/langchain_mongodb/pipelines.html).

## Parent sections collection

Whole sections live in a second, plain collection named by `MONGODB_PARENT_COLLECTION` (default `policy_sections`), keyed by `parent_id` (`<doc_id>_s<NN>`) in `_id`. It is not embedded and needs no search index. MongoDB creates it on the first ingest.

## Regular index for stale-chunk removal

After each document, ingestion deletes that document's leftover chunks with a query on `doc_id`. At eight documents a collection scan is fine. At scale, add a regular (not search) index on the chunk collection:

```json
{ "doc_id": 1 }
```
