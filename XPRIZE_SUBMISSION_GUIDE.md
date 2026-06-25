# Guía de Preparación y Postulación: Build with Gemini XPRIZE Hackathon

Esta guía paso a paso te permite preparar **cualquier proyecto** para participar en el hackathon **Build with Gemini XPRIZE** ($2,000,000 en premios). Sigue estos pasos metodológicos para asegurar que el proyecto cumpla con los exigentes criterios de evaluación de los jueces (Viabilidad de Negocio, Operaciones AI-Native y uso de Google Cloud).

---

## 🗓️ Fechas Clave y Plazos
*   **Período de Entrega:** 19 de Mayo, 2026 (10:00 am PT) – **17 de Agosto, 2026 (1:00 pm PT)**.
*   **Período de Evaluación:** 18 de Agosto, 2026 (10:00 am PT) – 15 de Septiembre, 2026 (5:00 pm PT).
*   **Anuncio de Ganadores:** Alrededor del 25 de Septiembre, 2026.

---

## 📋 Lista de Verificación de Requisitos Obligatorios

*   [ ] **Uso de Google Cloud:** El proyecto debe usar activamente al menos un producto de Google Cloud (ej. Vertex AI, Cloud Run, Cloud SQL).
*   [ ] **Llamada Obligatoria a Gemini API:** La aplicación desplegada debe realizar al menos una llamada a LLM utilizando la API de Gemini (directamente o vía Vertex AI). Se pueden usar otros proveedores en paralelo.
*   [ ] **Selección de Categoría:** El proyecto debe inscribirse en una de las siguientes 5 categorías oficiales:
    *   *Education & Human Potential* (Transformar aprendizaje y crecimiento).
    *   *Entrepreneurship & Job Creation* (Herramientas para fundadores y economías).
    *   *Small Business Services* (Potenciar negocios locales y tradicionales).
    *   *Money & Financial Access* (Acceso a capital, banca y libertad financiera).
    *   *Professional Services* (Conectar personas con asesoría experta).
*   [ ] **Repositorio de Código Público o Privado:** URL del repositorio con el código fuente completo. Si es privado, debe compartirse con:
    *   `testing@devpost.com`
    *   `judging@hacker.fund`
*   [ ] **Video Demostrativo de 3 Minutos:**
    *   Duración menor a 3 minutos (los jueces no verán más allá de ese tiempo).
    *   Subido a YouTube, Vimeo o Youku de manera pública o unlisted.
    *   Debe mostrar el producto funcionando en el dispositivo destino.
    *   Sin marcas de terceros ni música con copyright sin autorización.
*   [ ] **Idioma de Postulación:** Todo el material entregado (video, descripción de texto, instrucciones de prueba, Markdown del repositorio) debe estar en **inglés** o incluir una traducción completa al inglés.
*   [ ] **Evidencia de Viabilidad Comercial y Financiera:** Declaración detallada de ingresos, costos y métricas de usuario (detallados en `FINANCIALS.md`).
*   [ ] **ID Corporativo:** Requerido únicamente si la postulación se realiza como Organización.

---

## 🛠️ Paso 1: Adaptación de la Arquitectura (AI-Native)

Para que tu proyecto destaque como **AI-Native**, debe estructurarse de la siguiente manera:
1.  **Modelo Principal:** Configura `gemini-2.0-flash` o `gemini-1.5-pro` a través de Vertex AI como el motor de lenguaje principal.
2.  **Uso de Herramientas (MCP / Tool Calling):** La IA no debe ser solo un chat de texto. Debe ejecutar acciones (escribir en bases de datos, consultar APIs, agendar citas) de manera autónoma utilizando Model Context Protocol.
3.  **Observabilidad:** Implementa una tabla de Logs de Acciones (`Action_Logs`) que guarde un registro de cada acción automatizada ejecutada por la IA.
4.  **Health Check con Metadatos:** En tu backend, añade información del hackathon en el endpoint de estado raíz (`/api/` o `/`):
    ```json
    {
      "status": "online",
      "service": "PLATAFORMA GENIA Backend",
      "version": "1.0.0",
      "hackathon": "Build with Gemini XPRIZE",
      "google_cloud": true
    }
    ```

---

## 📈 Paso 2: Estrategia Comercial y Evidencia Requerida

El hackathon exige pruebas concretas de tracción. Si el proyecto está en etapa temprana o pre-revenue, aplica la **Estrategia de Tracción Alternativa**:
1.  **Modelo de Intercambio (Barter):** Ofrece el servicio de IA gratis a un negocio local a cambio de un beneficio no monetario (espacio de oficina, publicidad, insumos). Calcula el valor equivalente en el mercado y regístralo como **Non-monetary Revenue** en tu P&L.
2.  **Pruebas Piloto Activas:** Documenta la cantidad de usuarios, leads calificados y la satisfacción del usuario piloto como métrica de validación inicial.

---

## 📝 Paso 3: Estructura de Documentación del Repositorio

Todo proyecto postulado debe tener estos 3 archivos en inglés en la raíz del repositorio:

### A. `README.md`
*   **Tagline:** Explicación clara de qué hace el proyecto en una sola frase.
*   **Sección XPRIZE:** Categoría elegida y justificación corta.
*   **Diagrama de Arquitectura:** Diagrama Mermaid con el flujo de datos (Vertex AI Gemini -> Backend -> Frontend).
*   **Setup local:** Guía paso a paso de instalación.

### B. `NARRATIVE.md`
Responde con detalle a las tres preguntas operativas de los jueces:
1.  *How does the founding team use AI in their day-to-day operations?* (Ej: pair-programming, generación de copys, automatización de soporte).
2.  *What roles are handled by humans vs. AI agents?* (HITL - Human in the loop).
3.  *What jobs or economic opportunities are created/enabled for people outside the founding team?* (Beneficios y crecimiento para tus clientes o contratistas).

### C. `FINANCIALS.md`
Debe incluir de manera mandatoria los siguientes campos en formato estructurado:
1.  **Total Revenue:** Ingresos totales de clientes terceros independientes (arms-length) en USD durante el hackathon.
2.  **Revenue by Month:** Desglose mensual para Mayo, Junio, Julio y Agosto 2026.
3.  **Total Costs:** Costos de infraestructura, APIs y contratistas (excluyendo marketing) explicados en **una sola frase**.
4.  **Marketing & Customer Acquisition Spend:** Gasto total en pauta o adquisición (debe declararse incluso si es $0).
5.  **Related-Party Revenue:** Ingresos de familiares, socios o clientes preexistentes (se reporta por separado).
6.  **User Evidence:** Número de usuarios reales, perfil o tipo de usuarios y testimonios consentidos.
7.  **Evidence of Product Running:** Logs de ejecución de agentes, registros de uso de APIs y capturas de dashboards que prueben la ejecución continua en producción.

---

## 🎥 Paso 4: Preparación del Video Demo (3 Minutos)

El video es evaluado de manera estricta por los jueces:
1.  **Gancho (0:00 - 0:30):** Presenta el problema del cliente y cómo tu app lo resuelve inmediatamente.
2.  **Demo en Vivo (0:30 - 2:00):** Muestra al agente interactuando (ej. chateando por WhatsApp o ejecutando herramientas) y el backend registrando las acciones de la IA en tiempo real.
3.  **Tracción y Negocio (2:00 - 2:45):** Explica tu modelo de barter/pilotos y desglosa las métricas financieras básicas.
4.  **Cierre (2:45 - 3:00):** Visión de futuro e infraestructura basada en Google Cloud.

---

## 🌍 Paso 5: Landing Page y Panel de Evidencia Bilingüe

Crea una ruta pública en tu frontend (ej. `/evidence` y `/public`) accesible sin registro para los jueces:
1.  **Badge del Hackathon:** "Build with Gemini XPRIZE".
2.  **Selector de Idioma:** Botón visible **ES / EN** para traducir el contenido.
3.  **Métricas en Vivo:** Gráficas o tarjetas que muestren el total de interacciones que la IA ha gestionado de forma agregada, probando que el sistema está activo.
