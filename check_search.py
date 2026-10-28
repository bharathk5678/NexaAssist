from app.chains.embeddings import get_embeddings
from app.core.config import get_settings
from app.database.mongo import _database

s = get_settings()
c = _database(s)[s.mongodb_collection]
print("app index name:", s.vector_index_name)
for i in c.list_search_indexes():
    print("index:", i.get("name"), i.get("status"), i.get("latestDefinition") or i.get("definition"))

vec = get_embeddings(s).embed_query("What is the maximum loan amount for a NexaHome Loan?")


def run(flt):
    stage = {"index": s.vector_index_name, "path": "embedding", "queryVector": vec, "numCandidates": 50, "limit": 3}
    if flt:
        stage["filter"] = flt
    try:
        return [d["_id"] for d in c.aggregate([{"$vectorSearch": stage}, {"$project": {"_id": 1}}])]
    except Exception as exc:
        return f"ERROR: {type(exc).__name__}: {str(exc)[:200]}"


print("no filter:", run(None))
print("product only:", run({"product_id": "NEXA-HL"}))
print("date filter:", run({"$and": [{"effective_date": {"$lte": "2026-10-01"}}, {"effective_to_search": {"$gte": "2026-10-01"}}]}))