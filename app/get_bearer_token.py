import json
import secrets

from dotenv import dotenv_values, set_key

existing = dotenv_values(".env").get("AGENT_PRINCIPALS")
if existing and json.loads(existing):
    raise SystemExit("Named credentials already exist; leaving them unchanged.")

principals = [
    {
        "principal_id": role,
        "token": secrets.token_urlsafe(32),
        "customer_ids": ["NXC-0010"],
        "can_approve": role == "reviewer",
    }
    for role in ("owner", "reviewer")
]
set_key(".env", "AGENT_PRINCIPALS", json.dumps(principals))

for principal in principals:
    print(f"{principal['principal_id']}: {principal['token']}")
