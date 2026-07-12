# Debug Session: whatsapp-no-response
- **Status**: [OPEN]
- **Issue**: El agente Socio/Agente Social Genia no responde a mensajes entrantes por WhatsApp.
- **Debug Server**: http://127.0.0.1:7777/event
- **Log File**: .dbg/trae-debug-log-whatsapp-no-response.ndjson

## Reproduction Steps
1. Abrir el chat del agente en WhatsApp.
2. Enviar un mensaje de texto como "Hola" o "reiniciar".
3. Verificar si entra al backend y si se genera respuesta.

## Hypotheses & Verification
| ID | Hypothesis | Likelihood | Effort | Evidence |
|----|------------|------------|--------|----------|
| A | El webhook QR sí recibe el POST, pero descarta el evento por diferencia de nombre/formato (`messages.upsert`, `MESSAGES_UPSERT` u otro). | High | Low | Pending |
| B | El webhook ni siquiera está siendo invocado porque la instancia QR no quedó conectada o el webhook remoto no apunta al backend actual. | High | Med | Pending |
| C | El mensaje entra al webhook, pero se descarta por estructura del payload (`remoteJid`, `message`, `fromMe`, etc.). | High | Low | Pending |
| D | El mensaje llega hasta IA, pero falla la generación/envío de respuesta por error de modelo o por `send_qr_text`. | Med | Med | Pending |
| E | La conversación/agente está en estado que inhibe respuesta (`inactive`, `handoff`, proveedor distinto, instancia/token inconsistente). | Med | Low | Pending |

## Log Evidence
- Debug Server local activo en `http://127.0.0.1:7777/event`.
- Tras la reproducción reportada por el usuario, `GET /logs` devolvió `[]` (sin eventos).
- El archivo `.dbg/trae-debug-log-whatsapp-no-response.ndjson` no recibió entradas nuevas.
- La base local consultada no muestra conversación `PAYLOAD_DEBUG` y además está vacía (`0` conversaciones, `0` mensajes).

## Verification Conclusion
- **Hipótesis B: parcialmente confirmada para entorno local.**
  La prueba del usuario no está llegando al backend local instrumentado. Eso significa una de dos:
  1. el webhook del WhatsApp QR apunta a otro backend (muy probablemente producción), o
  2. el backend local no estaba siendo usado por esa línea/instancia durante la reproducción.
- **Hipótesis A/C/D/E: todavía pendientes en el entorno real que recibe el webhook.**
