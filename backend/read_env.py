import json

vals = {}
with open(r"C:\Users\User\AppData\Local\Temp\genia_env.txt", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip().strip('"').strip("'")

creds = {
    "url": vals.get("EVOLUTION_API_URL"),
    "token": vals.get("EVOLUTION_API_TOKEN"),
}
print("URL:", creds["url"])
print("TOKEN present:", bool(creds["token"]))
json.dump(creds, open(r"C:\Users\User\AppData\Local\Temp\evo_creds.json", "w"))