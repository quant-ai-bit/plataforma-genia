import httpx

r = httpx.get("https://plataforma-genia.vercel.app/api/agents", timeout=15)
agents = r.json()
print(f"Total agentes: {len(agents)}")
for a in agents:
    cfields = a.get("custom_fields", [])
    print(f'  [{a["id"][:8]}] {a["name"]} | provider={a["provider"]} | model={a["model"]} | custom_fields={len(cfields)}')
