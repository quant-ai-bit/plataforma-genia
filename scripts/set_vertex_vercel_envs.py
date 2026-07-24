import json
import subprocess

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
    cmd_rm = f'npx vercel env rm "{key}" production --yes --scope "{scope}"'
    subprocess.run(cmd_rm, shell=True, cwd=cwd, capture_output=True, text=True)
    
    # Add new env using --value
    # Escaping double quotes for shell execution if needed, or pass value via temp file/script
    # For safety with json quotes, write to a temp file and read or use python subprocess list with npx.cmd
    npx_cmd = r"C:\Program Files\nodejs\npx.cmd" if subprocess.os.path.exists(r"C:\Program Files\nodejs\npx.cmd") else "npx"
    res = subprocess.run(
        [npx_cmd, "vercel", "env", "add", key, "production", "--value", value, "--yes", "--scope", scope],
        cwd=cwd,
        capture_output=True,
        text=True
    )
    print(f"Result for {key}: exit_code={res.returncode}")
    if res.stdout:
        print(f"STDOUT: {res.stdout.strip()}")
    if res.stderr:
        print(f"STDERR: {res.stderr.strip()}")

print("Done updating Vercel environment variables!")
