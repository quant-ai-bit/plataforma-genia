import json
import subprocess
import sys

# Load JSON
with open(r"C:\Users\User\.gcp\genia-vertex.json", "r", encoding="utf-8") as f:
    data = json.load(f)

json_str = json.dumps(data)

scope = "alejos-projects-14de84b4"

envs = {
    "GCP_SERVICE_ACCOUNT_JSON": json_str,
    "GOOGLE_CLOUD_PROJECT": "gen-lang-client-0111526550",
    "GOOGLE_CLOUD_LOCATION": "us-central1",
    "VERTEX_GEMINI_MODEL": "gemini-2.5-flash",
    "MODEL_FALLBACK_ORDER": "vertex"
}

for key, val in envs.items():
    print(f"Setting {key} in Vercel Production...")
    # Remove existing
    subprocess.run(f'npx vercel env rm {key} production --yes --scope {scope}', shell=True, capture_output=True)
    # Add new
    proc = subprocess.run(f'npx vercel env add {key} production --yes --scope {scope}', input=val.encode("utf-8"), shell=True, capture_output=True)
    print(f"Result for {key}: returncode={proc.returncode}, stdout={proc.stdout.decode('utf-8', errors='ignore')[:100]}")

print("Vercel env update complete!")
