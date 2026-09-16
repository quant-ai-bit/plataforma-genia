# Dispatch Log

## 2026-09-15T19:49:36-05:00

You are the Project Orchestrator for Plataforma GENIA.

Your working directory is:
C:\Users\User\Desktop\ANTIGRAVITY\PLATAFORMA GENIA\.agents\teamwork_preview_orchestrator_1

The project workspace is:
C:\Users\User\Desktop\ANTIGRAVITY\PLATAFORMA GENIA

The original user request is documented in:
C:\Users\User\Desktop\ANTIGRAVITY\PLATAFORMA GENIA\ORIGINAL_REQUEST.md

Mission:
Execute full implementation and verification of the user request:
1. R1: Rediseño Visual y Estética Homogénea con genia.com.co
   - Aplicar el sistema de diseño de genia.com.co: Dark Mode (#070a12, #0b0f19), acentos degradados (#4f46e5, #6366f1, #38bdf8), glassmorphism, tipografía moderna.
   - Sidebar reactivo con estricta separación de roles:
     * Cliente (user): Solo ve Resumen, Conversaciones (Inbox), CRM (Kanban/Tabla), Agenda, Catálogo, Flujos, Integraciones, Mi Negocio. NUNCA ve prompts, configuraciones LLM, temperatura ni tokens.
     * Super Admin (admin): Acceso exclusivo y protegido a /admin con gestión de subcuentas, asignación de tiers, configs técnicas de agentes y auditoría.
2. R2: CRM Pipeline con Columnas y Etapas Totalmente Editables
   - Crear, renombrar, reordenar y eliminar etapas del pipeline en vista Kanban y vista tabular (Excel-like).
   - Persistencia en base de datos (PipelineColumn) vinculada al agente/subcuenta.
   - Drag and drop interactivo y edición en línea de nombres de columnas.
   - Alternancia fluida Kanban / Tabla con exportación CSV.
3. R3: Hub de Conexiones e Integraciones Nativas
   - Interfaz visual basada en tarjetas interactivas con estados de conexión en tiempo real:
     * WhatsApp (Meta Cloud API / WAHA QR)
     * Telegram (Bot API nativo con token propio del cliente)
     * Google Calendar / Outlook (OAuth 2.0)
     * Email (envío nativo vía OAuth o SMTP)
     * WASI (API Key + sincronización de catálogo)
     * Catálogo Propio (carga Excel/CSV y editor manual)
4. R4: Motor Nativo de Workflows y Automatizaciones
   - Reemplazar Make mediante ejecutor nativo interno de GENIA en FastAPI basado en eventos (triggers), condiciones lógicas y acciones programadas (delays/mensajes/recordatorios).

Acceptance Criteria:
- UI & Navegación idéntica a genia.com.co, rol user sin exposición a prompts/LLM/admin, /admin protegido.
- Pipeline editable (nombres, etapas, orden), toggle Kanban/Tabla + CSV.
- Telegram Bot nativo y conectores operando autónomamente en backend sin Make.
