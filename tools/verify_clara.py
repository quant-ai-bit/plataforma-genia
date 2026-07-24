import httpx

r = httpx.get("https://plataforma-genia.vercel.app/api/agents/f28b2e93be7141edbfda4aa59833d348", timeout=15)
if r.status_code == 200:
    a = r.json()
    print(f'Nombre: {a["name"]}')
    print(f'Provider: {a["provider"]}')
    print(f'Model: {a["model"]}')
    print(f'Temp: {a["temperature"]}')
    print(f'Max tokens: {a["max_tokens"]}')
    print(f'Channels: {a["channels"]}')
    print(f'Timezone: {a["timezone"]}')
    sp = a.get("system_prompt", "")
    print(f'System prompt length: {len(sp)} chars')
    print(f'Starts with: {sp[:80]}...')
    has_funnel = "EMBUDO" in sp or "embudo" in sp
    has_portfolio = "PORTAFOLIO" in sp or "Legaria" in sp
    print(f'Contains funnel instructions: {has_funnel}')
    print(f'Contains portfolio info: {has_portfolio}')
    cf = a.get("custom_fields", [])
    print(f'Custom fields: {len(cf)}')
    for f in cf:
        opts = ""
        if f.get("options"):
            opts = f" options={f['options']}"
        print(f'  - {f["key"]} ({f["type"]}) required={f["required"]}{opts}')
else:
    print(f"Error: {r.status_code}")
