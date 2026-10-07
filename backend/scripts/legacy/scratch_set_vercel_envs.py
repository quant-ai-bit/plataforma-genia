import json
import subprocess
import os

with open(r"C:\Users\User\.gcp\genia-vertex.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)

json_str = json.dumps(json_data)

scope = "alejos-projects-14de84b4"
project = "plataforma-genia"
cwd = r"c:\Users\User\Desktop\ANTIGRAVITY\PLATAFORMA GENIA"

envs = {
    "GCP_SERVICE_ACCOUNT_JSON": json_str,
    "GOOGLE_CLOUD_PROJECT": "gen-lang-client-0111526550",
    "GOOGLE_CLOUD_LOCATION": "us-central1",
    "VERTEX_GEMINI_MODEL": "gemini-2.5-flash",
    "MODEL_FALLBACK_ORDER": "vertex"
}

for key, val in envs.items():
    print(f"=== Setting {key} ===")
    # 1. Remove existing
    rm_cmd = f"npx vercel env rm {key} production --yes --scope {scope}"
    rm_res = subprocess.run(rm_cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    print(f"RM Output: {rm_res.stdout.strip()} {rm_res.stderr.strip()}")

    # 2. Add new
    add_cmd = f"npx vercel env add {key} production --yes --scope {scope}"
    add_res = subprocess.run(add_cmd, input=val, shell=True, capture_output=True, text=True, cwd=cwd)
    print(f"ADD Output: {add_res.stdout.strip()} {add_res.stderr.strip()}")

print("All Vertex AI variables set successfully!")
