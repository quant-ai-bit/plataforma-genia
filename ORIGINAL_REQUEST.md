# Original User Request

## 2026-09-16T00:48:42Z

Plataforma GENIA: Rediseño completo de la interfaz de usuario bajo la identidad visual de genia.com.co, separación estricta de roles (cliente final sin exposición de prompts/LLM vs. super admin en /admin), CRM Pipeline con etapas/columnas personalizables y Hub de Integraciones nativas (WhatsApp, Telegram, Calendar, WASI, Email).

Working directory: C:\Users\User\Desktop\ANTIGRAVITY\PLATAFORMA GENIA
Integrity mode: development

## Requirements

### R1. Rediseño Visual y Estética Homogénea con genia.com.co
- Aplicar el sistema de diseño visual de la landing page `genia.com.co`: tema oscuro profundo (Dark Mode, fondos `#070a12` / `#0b0f19`), acentos en gradiente azul y púrpura (`#4f46e5`, `#6366f1`, `#38bdf8`), tipografía moderna y efectos glassmorphism.
- Sidebar reactivo y limpio que separe estrictamente la experiencia:
  - **Cliente (`user`):** Solo ve Resumen, Conversaciones (Inbox), CRM (Kanban/Tabla), Agenda, Catálogo, Flujos, Integraciones y Mi Negocio. NUNCA ve prompts, configuraciones LLM, temperatura ni tokens.
  - **Super Admin (`admin`):** Acceso a `/admin` con panel de control de todas las subcuentas, asignación de capas (Tiers), configuración técnica de agentes y auditoría.

### R2. CRM Pipeline con Columnas y Etapas Totalmente Editables
- Permitir al usuario crear, renombrar, reordenar y eliminar etapas del pipeline en vista Kanban y vista tabular (Excel-like).
- Persistencia en base de datos (`PipelineColumn`) vinculada al agente/subcuenta.
- Drag and drop interactivo y edición en línea de nombres de columnas.

### R3. Hub de Conexiones e Integraciones Nativas (Sin intermediarios externos)
- Interfaz visual basada en tarjetas interactivas con estados de conexión en tiempo real:
  - **WhatsApp** (Meta Cloud API / WAHA QR)
  - **Telegram** (Bot API con token propio del cliente de forma nativa)
  - **Google Calendar / Outlook** (OAuth 2.0)
  - **Email** (Envío nativo del agente vía OAuth o SMTP)
  - **WASI** (API Key + sincronización de catálogo)
  - **Catálogo Propio** (Carga de Excel/CSV y editor manual)

### R4. Motor Nativo de Workflows y Automatizaciones
- Reemplazar la necesidad de herramientas externas como Make mediante un ejecutor nativo interno de GENIA en FastAPI basado en eventos (triggers), condiciones lógicas y acciones programadas (delays/mensajes/recordatorios).

## Acceptance Criteria

### UI & Navegación
- [ ] La interfaz de usuario utiliza exactamente la paleta de colores, componentes y tipografía coherentes con `genia.com.co`.
- [ ] Un usuario con rol `user` no tiene acceso ni visualización alguna de los prompts del sistema, modelos LLM, RAG interno o rutas administrativas.
- [ ] La ruta `/admin` está debidamente protegida y exclusiva para usuarios administradores de GENIA.

### CRM y Pipeline
- [ ] El usuario puede editar el nombre de cualquier columna del pipeline con un clic/modal.
- [ ] El usuario puede agregar nuevas etapas y reorganizarlas según su flujo de negocio.
- [ ] Alternancia fluida entre vista Kanban y vista de Tabla estilo Excel con exportación CSV.

### Integraciones y Conectores
- [ ] Inclusión de tarjeta y conector para **Telegram Bot** (configuración de Bot Token) de forma nativa.
- [ ] Integraciones operando de forma autónoma en backend sin depender de plataformas de terceros como Make.
