import subprocess
import os

from dotenv import dotenv_values

env_path = ".env.production"
if not os.path.exists(env_path):
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env.production")

if not os.path.exists(env_path):
    raise FileNotFoundError(f"No se pudo encontrar el archivo .env.production en {os.path.abspath(env_path)}")

print(f"Cargando variables de entorno desde: {os.path.abspath(env_path)}")
envs = dotenv_values(env_path)

# Asegurar valores por defecto requeridos si no están en .env
if "ENVIRONMENT" not in envs or not envs["ENVIRONMENT"]:
    envs["ENVIRONMENT"] = "production"
if "NEXT_PUBLIC_API_URL" not in envs or not envs["NEXT_PUBLIC_API_URL"]:
    envs["NEXT_PUBLIC_API_URL"] = "https://plataforma-genia.vercel.app"
if "FRONTEND_URL" not in envs or not envs["FRONTEND_URL"]:
    envs["FRONTEND_URL"] = "https://plataforma-genia.vercel.app"


scope = "alejos-projects-14de84b4"

print("Starting environment variable updates on Vercel...")
for key, val in envs.items():
    print(f"\n--- Configuring {key} ---")
    
    # Try to remove the variable first (ignore error if it doesn't exist)
    rm_cmd = ["vercel", "env", "rm", key, "production", "--yes", "--scope", scope]
    print(f"Executing: vercel env rm {key} production --yes --scope {scope}")
    res_rm = subprocess.run(rm_cmd, capture_output=True, text=True, shell=True, stdin=subprocess.DEVNULL)
    if res_rm.returncode == 0:
        print(f"Old variable {key} removed successfully.")
    else:
        print(f"Variable {key} did not exist or could not be removed (ignoring).")
    
    # Add the variable
    add_cmd = ["vercel", "env", "add", key, "production", "--value", val, "--yes", "--scope", scope]
    print(f"Executing: vercel env add {key} production --value *** --yes --scope {scope}")
    res_add = subprocess.run(add_cmd, capture_output=True, text=True, shell=True, stdin=subprocess.DEVNULL)
    if res_add.returncode != 0:
        print(f"Error adding {key}: {res_add.stderr.strip() or res_add.stdout.strip()}")
    else:
        print(f"Successfully added {key}!")

print("\nFinished configuring all variables on Vercel.")
