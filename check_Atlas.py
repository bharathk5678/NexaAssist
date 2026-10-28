from app.core.config import get_settings
from app.database.mongo import _database

s = get_settings()
db = _database(s)
c = db[s.mongodb_collection]
print("chunks:", c.count_documents({}), "| parents:", db[s.mongodb_parent_collection].count_documents({}))
print("V3 chunks:", c.count_documents({"doc_id": "POL-HL-V3"}))
print("search indexes:", [(i.get("name"), i.get("type"), i.get("queryable")) for i in c.list_search_indexes()])
d = c.find_one({"doc_id": "POL-HL-V3"}, {"embedding": 0})
keys = ["product_id", "jurisdiction", "institution", "confidentiality_level", "effective_date", "effective_to_search"]
print({k: (d or {}).get(k) for k in keys})
