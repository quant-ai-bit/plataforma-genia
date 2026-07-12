"""Script to update agent model in Supabase using env vars from Vercel."""

import os
import http.client
import json
import sys

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL", "https://ppzsnsovdmxwofmuppfv.supabase.co"
)
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

if not SERVICE_KEY:
    print("ERROR: SUPABASE_SERVICE_KEY not found in environment")
    sys.exit(1)

AGENT_ID = "547c07f714394e399c504d4bb3da37ac"

conn = http.client.HTTPSConnection(SUPABASE_URL.replace("https://", ""))

# 1. Update agent provider and model
payload = json.dumps({"provider": "groq", "model": "llama-3.3-70b-versatile"})
conn.request(
    "PATCH",
    f"/rest/v1/agents?id=eq.{AGENT_ID}",
    payload,
    {
        "Content-Type": "application/json",
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Prefer": "return=minimal",
    },
)
resp = conn.getresponse()
print(f"Agent update: {resp.status} {resp.reason}")
resp.read()

# 2. Reset exhausted model statuses
conn.request(
    "DELETE",
    "/rest/v1/free_model_statuses",
    headers={"apikey": SERVICE_KEY, "Authorization": f"Bearer {SERVICE_KEY}"},
)
resp = conn.getresponse()
print(f"Free model statuses reset: {resp.status} {resp.reason}")
resp.read()

conn.close()
print("Done!")
