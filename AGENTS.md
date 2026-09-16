# Agent Instructions: Python FastAPI Backend, Next.js React Expert & Web Design Pro

This file defines the specialized rules and best practices for developing the **PLATAFORMA GENIA** application.

---

## 🛡️ REGLA CRÍTICA: Garantía de Cero Interrupción en Producción (Zero Downtime)

1. **Disponibilidad Continua:** Las modificaciones en el backend o frontend nunca deben interrumpir el servicio en producción (Vercel, Railway, WAHA/Docker).
2. **Manejo Defensivo en WhatsApp / WAHA / Meta API:**
   - Toda llamada externa a servicios de mensajería (WAHA, Meta Graph API, OpenAI/Gemini providers) debe estar protegida con bloques `try/except` o fallbacks defensivos.
   - Si un proveedor externo falla o no responde, el sistema debe responder de forma limpia e ininterrumpida sin tirar la ejecución ni romper la sesión del cliente.
3. **Protección de Variables de Entorno (.env):**
   - Nunca exponer tokens, secretos ni llaves de producción (`.env.production.local`, `update_production_envs.ps1`) en respuestas públicas, código cliente o registros visibles.

---

## 📒 REGLA OBLIGATORIA: Bitácora compartida (`PROGRESS.md`)

Este proyecto se desarrolla desde múltiples plataformas (Kiro, opencode, Antigravity, etc.).
Para mantener el contexto sincronizado entre todas, existe el archivo **`PROGRESS.md`** en la raíz.

1. **AL INICIAR cualquier sesión de trabajo:** lee primero `PROGRESS.md` (la entrada más reciente está arriba) para saber el estado actual y los pendientes.
2. **AL TERMINAR un cambio relevante:** añade una nueva entrada **al inicio del historial** de `PROGRESS.md`, siguiendo el formato definido en ese mismo archivo (fecha, plataforma, tipo, archivos, estado y siguiente paso).
3. **Nunca borres entradas anteriores.** El historial completo es la fuente de verdad del progreso.
4. Indica siempre **desde qué plataforma** se hizo el cambio.
5. **Fecha y Hora Real (Hora Colombiana - COT):** Las entradas deben registrar siempre la **fecha real** y la **hora colombiana (COT, UTC-5)**. No uses fechas estimadas ni asumas la fecha actual sin verificarla. Debes consultar la hora actual del sistema o el tiempo local proporcionado en tus metadatos (ej. offset `-05:00`) para registrar la fecha y hora exacta en formato `YYYY-MM-DD HH:MM (COT)`.

---

## ⚙️ Protocolo de Verificación y Build

1. **Validación de Código:** Antes de dar por completado un cambio en frontend o backend, verificar la integridad sintáctica (`npx tsc --noEmit` en TypeScript / compilación en Python).
2. **Pruebas No Destructivas:** Las migraciones de base de datos o esquemas deben realizarse con cláusulas no destructivas (`CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ADD COLUMN IF NOT EXISTS`).

---

## Skill: Python FastAPI Backend

### Core Guidelines
1. **Asynchronous HTTP Routing:**
   - Define paths (`@app.get`, `@app.post`, etc.) and handle non-blocking processes with `async def`.
   - Use `httpx.AsyncClient()` for external requests instead of the synchronous `requests` library.
2. **Pydantic (v2) Schemas:**
   - Use strict data validation models with clear typing, defaults, and examples.
3. **Quality Checklist:**
   - [ ] Ensure explicit and secure CORS configuration (no wildcard `*` in production).
   - [ ] Implement custom exception handlers for clean error JSON responses.
   - [ ] Secure endpoints with token dependency verification.

---

## Skill: Next.js React Expert

### Core Guidelines
1. **Next.js App Router & RSC:**
   - Prefer React Server Components for pages; use `"use client"` only for states/effects.
2. **Quality Checklist:**
   - [ ] Do interactive component files start with `"use client"`?
   - [ ] Are credentials called via environment variables (never exposed to client)?

---

## Skill: Web Design Pro

### Core Guidelines
1. **Sleek Aesthetics:**
   - Wow users with visual details (Curated HSL colors, dark modes, micro-interactions).
2. **Quality Checklist:**
   - [ ] Is layout responsive on mobile, tablet, and desktop?
   - [ ] Do colors have correct contrast and readability?

