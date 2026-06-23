# Guía de Preparación y Postulación: Build with Gemini XPRIZE Hackathon

Esta guía paso a paso te permite preparar **cualquier proyecto** para participar en el hackathon **Build with Gemini XPRIZE** ($2,000,000 en premios). Sigue estos pasos metodológicos para asegurar que el proyecto cumpla con los exigentes criterios de evaluación de los jueces (Viabilidad de Negocio, Operaciones AI-Native y uso de Google Cloud).

---

## 📋 Lista de Verificación de Requisitos Obligatorios

*   [ ] **Cuenta en Google Cloud / Vertex AI:** El proyecto debe usar activamente Vertex AI o la API de Gemini.
*   [ ] **Repositorio GitHub:** Configurado y accesible para evaluación. Debe compartirse con:
    *   `testing@devpost.com`
    *   `judging@hacker.fund`
*   [ ] **Video Demo de 3 Minutos:** Demostración del producto vivo y funcional (alojado en YouTube/Vimeo en modo público o unlisted).
*   [ ] **Narrativa de Negocio (500-1000 palabras):** Documento `NARRATIVE.md` explicando operaciones.
*   [ ] **Tracción y Finanzas:** Documento `FINANCIALS.md` demostrando ingresos/validación comercial y costos operativos.
*   [ ] **Evidencia del Producto:** Logs de ejecución del agente, récords de uso de API y panel de control.
*   [ ] **Evidencia de Clientes:** Contactos reales o testimonios de pilotos activos.

---

## 🛠️ Paso 1: Adaptación de la Arquitectura (AI-Native)

Para que tu proyecto destaque como **AI-Native**, debe estructurarse de la siguiente manera:
1.  **Modelo Principal:** Configura `gemini-2.0-flash` o `gemini-1.5-pro` a través de Vertex AI.
2.  **Uso de Herramientas (MCP / Tool Calling):** La IA no debe ser solo un chat de texto. Debe ejecutar acciones (escribir en bases de datos, consultar APIs, agendar citas) de manera autónoma.
3.  **Observabilidad:** Implementa una tabla de Logs de Acciones (`Action_Logs`) que guarde un registro de cada acción automatizada ejecutada por la IA.
4.  **Health Check con Metadatos:** En tu backend (FastAPI/Express/etc.), añade información del hackathon en el endpoint de estado raíz:
    ```json
    {
      "status": "healthy",
      "hackathon": "Build with Gemini XPRIZE",
      "google_cloud": true
    }
    ```

---

## 📈 Paso 2: Estrategia Comercial para Proyectos sin Ingresos Iniciales

Si el proyecto no tiene facturación monetaria aún, **no te descalifica**. Aplica la estrategia de **Tracción Alternativa**:
1.  **Modelo de Intercambio (Barter):** Ofrece los servicios de tu agente de IA gratis a un negocio local (ej. coworking, cafetería, consultorio) a cambio de un beneficio no monetario (espacio de oficina, publicidad, insumos). Calcula el valor equivalente en el mercado y regístralo como **Non-monetary Revenue** en tu P&L.
2.  **Pruebas Piloto Activas:** Lanza versiones beta con contratistas o conocidos. Documenta la cantidad de leads calificados por la IA y la satisfacción del usuario piloto como métrica de tracción comercial inicial.

---

## 📝 Paso 3: Documentación Estándar en tu Repositorio

Todo proyecto postulado debe tener estos 3 archivos en la raíz del repositorio:

### A. `README.md` (En inglés)
*   **Tagline impactante:** Qué hace el proyecto en una sola frase.
*   **Sección XPRIZE:** Badge y categoría elegida.
*   **Diagrama de Arquitectura:** Usa Mermaid para mostrar el flujo de datos (Vertex AI -> Frontend -> Base de Datos).
*   **Instrucciones de Instalación:** Paso a paso claro de setup local.

### B. `NARRATIVE.md` (En inglés)
Responde con detalle a estas tres preguntas para los jueces:
1.  *How does the founding team use AI in their day-to-day operations?*
2.  *What roles are handled by humans vs. AI agents?*
3.  *What jobs or economic opportunities are created/enabled for people outside the founding team?*

### C. `FINANCIALS.md` (En inglés)
*   **Pérdidas y Ganancias (P&L):** Ingresos simulados/equivalentes del intercambio comercial, costos de infraestructura (APIs, hosting).
*   **Costo de Adquisición de Clientes (CAC):** Gastos de marketing (pauta en Meta/Google) y conversión.

---

## 🎥 Paso 4: Preparación del Video Demo (3 Minutos)

El video es la carta de presentación más importante. No uses diapositivas; muestra el producto funcionando:
1.  **Gancho (0:00 - 0:30):** Presenta el problema del cliente y cómo tu app lo resuelve inmediatamente.
2.  **Demo en Vivo (0:30 - 2:00):** Muestra al agente interactuando (ej. chateando por WhatsApp o agendando citas) y cómo tu backend registra las acciones de la IA en tiempo real.
3.  **Tracción y Negocio (2:00 - 2:45):** Explica tu modelo de barter o pilotos activos y cómo planeas escalar.
4.  **Cierre (2:45 - 3:00):** Visión de futuro e infraestructura basada en Google Cloud.

*Recomendación de herramientas gratuitas de producción:* **OBS Studio** para grabar pantalla, **ElevenLabs** para voz en off realista, y **CapCut** para subtítulos y edición ágil.

---

## 🌍 Paso 5: Landing Page y Panel de Evidencia Bilingüe

Crea una ruta pública en tu frontend (ej. `/` o `/public`) accesible sin registro para los jueces:
1.  **Badge del Hackathon:** "Build with Gemini XPRIZE".
2.  **Selector de Idioma:** Botón visible **ES / EN** que cambie todo el contenido de la interfaz de forma dinámica.
3.  **Métricas en Vivo:** Gráficas o tarjetas que muestren el total de interacciones que la IA ha gestionado de forma agregada, probando que el sistema está vivo en producción.
