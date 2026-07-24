import json
import subprocess
import os

# Read genia-vertex.json
json_path = r"C:\Users\User\.gcp\genia-vertex.json"
with open(json_path, "r", encoding="utf-8") as f:
    json_data = json.load(f)

minified_json = json.dumps(json_data)

envs_to_update = {
    "GCP_SERVICE_ACCOUNT_JSON": minified_json,
    "GOOGLE_CLOUD_PROJECT": "gen-lang-client-0111526550",
    "GOOGLE_CLOUD_LOCATION": "us-central1",
    "VERTEX_GEMINI_MODEL": "gemini-2.5-flash",
    "MODEL_FALLBACK_ORDER": "vertex"
}

scope = "alejos-projects-14de84b4"
cwd = r"c:\Users\User\Desktop\ANTIGRAVITY\PLATAFORMA GENIA"

for key, value in envs_to_update.items():
    print(f"Setting {key} in Vercel Production...")
    # Remove existing env
    subprocess.run(
        f'npx vercel env rm {key} production --yes --scope {scope}',
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    # Add new env
    proc = subprocess.Popen(
        f'npx vercel env add {key} production --scope {scope}',
        shell=True,
        cwd=cwd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = proc.communicate(input=value)
    print(f"Result for {key}: {stdout.strip()} {stderr.strip()}")

print("Done updating Vercel environment variables!")
