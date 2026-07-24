import httpx
import json

BASE = "https://plataforma-genia.vercel.app"

# ── 1. Crear agente Clara ──
payload = {
    "name": "Clara",
    "description": "Asesora virtual inmobiliaria de Legaria Capital. Califica leads, recomienda propiedades y agenda llamadas.",
    "system_prompt": (
        'Eres "Clara", la asesora virtual de Legaria Capital, una inmobiliaria colombiana '
        "con sede en Pereira que ayuda a personas a invertir en bienes raíces de forma consciente, educativa y segura.\n\n"
        "## PERSONALIDAD\n"
        '- Tono: cálido, humano, transparente, educativo. NUNCA uses presión de venta.\n'
        "- Valores: Empatía, Honestidad, Profesionalismo, Claridad, Compromiso.\n"
        '- Idioma: 100% español colombiano, trato de "tú".\n'
        'Frase inicial sugerida: "Hola, soy Clara de Legaria Capital. ¿Cuál es tu nombre para empezar?"\n\n'
        "## EMBUDO DE CALIFICACIÓN (una pregunta a la vez)\n"
        "Debes seguir este orden estrictamente, UNA pregunta por mensaje:\n\n"
        "1. Preguntar el nombre del cliente.\n"
        "2. Preguntar si busca propiedad para VIVIR o para INVERSIÓN.\n"
        "3. Preguntar qué tipo de propiedad busca: Casa, Apartamento, Casa Campestre, Proyecto sobre planos o Lote campestre.\n"
        "4. Preguntar el presupuesto aproximado en COP.\n"
        "5. Según tipo + presupuesto + propósito, revisar la base de conocimiento y recomendar el proyecto que mejor se ajuste del portafolio real de Legaria Capital. Explica por qué ese proyecto es ideal para su caso.\n"
        "6. Si el presupuesto no alcanza para ningún proyecto vigente, ser honesto y ofrecer una asesoría financiera personalizada.\n"
        "7. Si mostró interés en algún proyecto, preguntar si desea agendar una llamada telefónica con un asesor especializado.\n"
        "8. Si acepta, usar la herramienta de calendario para consultar disponibilidad y agendar.\n\n"
        "## PORTAFOLIO REAL DE LEGARIA CAPITAL\n"
        "Tienes acceso a la base de conocimiento con todos los proyectos. NUNCA inventes propiedades ni precios que no estén documentados.\n\n"
        "## REGLAS OBLIGATORIAS\n"
        "- NUNCA hagas más de una pregunta por mensaje.\n"
        "- NUNCA inventes propiedades ni precios.\n"
        "- Si el cliente se desvía del tema, retoma el flujo amablemente.\n"
        "- Si mencionan presupuestos fuera del rango de los proyectos, ofrece asesoría financiera personalizada.\n"
        "- Al final de la calificación, guarda toda la información en los campos personalizados.\n"
        "- La llamada debe agendarse para un horario hábil (lunes a viernes 8am-6pm, sábados 8am-1pm)."
    ),
    "provider": "vertex",
    "model": "gemini-2.5-flash",
    "temperature": 0.6,
    "max_tokens": 2048,
    "custom_fields": [
        {"key": "nombre", "label": "Nombre del Cliente", "type": "text", "required": True},
        {"key": "telefono", "label": "Teléfono", "type": "text", "required": True},
        {"key": "tipo_propiedad", "label": "Tipo de Propiedad", "type": "select", "required": True, "options": ["Casa", "Apartamento", "Casa Campestre", "Proyecto sobre planos", "Lote campestre"]},
        {"key": "proposito", "label": "Propósito", "type": "select", "required": True, "options": ["Vivir", "Inversión"]},
        {"key": "presupuesto", "label": "Presupuesto (COP)", "type": "text", "required": True},
        {"key": "proyecto_recomendado", "label": "Proyecto Recomendado", "type": "text", "required": False}
    ],
    "channels": ["web", "whatsapp"],
    "notification_phone": "+573209673284",
    "whatsapp_provider": "qr_code",
    "stt_provider": "groq_whisper",
    "timezone": "America/Bogota"
}

r = httpx.post(f"{BASE}/api/agents", json=payload, timeout=15)
print(f"Crear agente: {r.status_code}")
if r.status_code == 201:
    agent = r.json()
    agent_id = agent["id"]
    print(f"  Nombre: {agent['name']}")
    print(f"  ID: {agent_id}")

    # ── 2. Subir documentos de conocimiento ──
    docs = [
        (
            "proyecto_maple.txt",
            "PROYECTO MAPLE\n\nUbicación: Pereira\nPrecio desde: $297.000.000 COP\nÁrea desde: 53.98 m²\nHabitaciones: 1, 2 y 3 habitaciones\nPlazo de financiación: hasta 30 meses\nTipo: Apartamento sobre planos\nIdeal para: Inversión o vivienda, entrada accesible",
        ),
        (
            "proyecto_dominica.txt",
            "PROYECTO DOMINICA\n\nUbicación: Pereira\nPrecio desde: $450.000.000 COP\nÁrea desde: 70.24 m²\nHabitaciones: 1, 2 y 3 habitaciones\nPlazo de financiación: hasta 36 meses\nTipo: Apartamento sobre planos\nIdeal para: Familias que buscan espacio y plusvalía",
        ),
        (
            "proyecto_perla_nova.txt",
            "PROYECTO PERLA NOVA\n\nUbicación: Pereira\nPrecio desde: $357.699.000 COP\nÁrea desde: 50.72 m²\nHabitaciones: 1, 2 y 3 habitaciones\nPlazo de financiación: hasta 36 meses\nTipo: Apartamento sobre planos\nIdeal para: Inversión con precio competitivo",
        ),
        (
            "proyecto_bela_vista.txt",
            "PROYECTO BELA VISTA\n\nUbicación: Pereira\nPrecio desde: $406.000.000 COP\nÁrea desde: 62 m²\nHabitaciones: 2 y 3 habitaciones\nPlazo de financiación: hasta 30 meses\nTipo: Apartamento sobre planos\nIdeal para: Vivienda familiar con buena relación costo-beneficio",
        ),
        (
            "proyecto_zenda.txt",
            "PROYECTO ZENDA\n\nUbicación: Pereira\nPrecio desde: $514.235.000 COP\nÁrea desde: 59 m²\nHabitaciones: 2 y 3 habitaciones\nPlazo de financiación: hasta 34 meses\nTipo: Apartamento sobre planos\nIdeal para: Quienes buscan diseño moderno y buena ubicación",
        ),
        (
            "proyecto_sereno.txt",
            "PROYECTO SERENO\n\nUbicación: Pereira\nPrecio desde: $893.485.959 COP\nÁrea desde: 80 m²\nHabitaciones: 2 y 3 habitaciones\nPlazo de financiación: hasta 37 meses\nTipo: Apartamento sobre planos\nIdeal para: Segmento premium, espacios amplios y acabados de lujo",
        ),
        (
            "proyecto_verdii.txt",
            "PROYECTO CASAS VERDII\n\nUbicación: Pereira\nPrecio desde: $1.390.033.260 COP\nÁrea desde: 140.65 m²\nHabitaciones: 1, 2 y 3 habitaciones\nPlazo de financiación: hasta 36 meses\nTipo: Casa Campestre\nIdeal para: Familias que buscan casa con zona verde y amplitud",
        ),
        (
            "proyecto_arhu.txt",
            "PROYECTO CASAS ARHÚ\n\nUbicación: Pereira\nPrecio desde: $900.676.000 COP\nÁrea desde: 122.95 m²\nHabitaciones: Casas de 3 habitaciones\nPlazo de financiación: hasta 36 meses\nTipo: Casa Campestre\nIdeal para: Casas amplias en entorno campestre",
        ),
        (
            "proyecto_lino.txt",
            "PROYECTO LOTES LINO\n\nUbicación: Pereira\nPrecio desde: $472.697.130 COP\nÁrea desde: 2,499 m² (lotes)\nTipo: Lotes campestres\nEntrega: Inmediata\nIdeal para: Construir tu casa soñada o invertir en tierra con valorización",
        ),
        (
            "proyecto_nexo14.txt",
            "PROYECTO NEXO 14\n\nUbicación: Pereira\nPrecio desde: $500.584.400 COP\nÁrea desde: 53.24 m²\nHabitaciones: 1, 2 y 3 habitaciones\nPlazo de financiación: hasta 30 meses\nTipo: Apartamento sobre planos\nIdeal para: Inversión con excelente relación ubicación-precio",
        ),
        (
            "proyecto_arvore.txt",
            "PROYECTO ARVORE\n\nUbicación: Pereira\nPrecio desde: $773.083.112 COP\nÁrea desde: 60.51 m²\nHabitaciones: 1, 2 y 3 habitaciones\nPlazo de financiación: hasta 24 meses\nTipo: Apartamento sobre planos\nIdeal para: Inversión con plazo corto de financiación",
        ),
        (
            "info_legaria_capital.txt",
            "LEGARIA CAPITAL - Información de la Empresa\n\nNombre: Legaria Capital\nUbicación: Pereira, Colombia\nTeléfono: +57 320 9673284 / +57 318 9993535\nEmail: gerente@legariacapital.com\nSitio web: https://legariacapital.com\nRedes: @esteban.realestate (Instagram/TikTok)\n\nServicios:\n1. Proyectos sobre planos - Acceso a precios preferenciales y alto potencial de valorización\n2. Propiedades usadas - Opciones listas para habitar o con potencial de rentabilidad\n3. Club de inversionistas - Inversión colaborativa en proyectos de alto impacto\n4. Asesoría financiera personalizada - Plan de inversión consciente según perfil y objetivos\n\nValores: Empatía, Honestidad, Profesionalismo, Claridad, Compromiso\nMisión: Transformar la experiencia de inversión en bienes raíces, llevándola de lo incierto a lo claro.",
        ),
    ]

    ok = 0
    fail = 0
    for title, content in docs:
        rd = httpx.post(
            f"{BASE}/api/agents/{agent_id}/documents/text",
            json={"title": title, "content": content},
            timeout=15,
        )
        if rd.status_code == 201:
            ok += 1
        else:
            fail += 1
            print(f"  ❌ {title}: {rd.status_code} {rd.text[:100]}")

    print(f"\n  Documentos: {ok} subidos ✅  {fail} fallidos ❌")
    print(f"\n  🎉 Clara creada exitosamente!")
    print(f"     ID: {agent_id}")
    print(f"     Ver: https://plataforma-genia.vercel.app/agents/{agent_id}")
else:
    print(f"  ❌ Error: {r.status_code} {r.text[:500]}")
