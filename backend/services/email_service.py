"""
Servicio de Notificaciones por Correo Electrónico para PLATAFORMA GENIA.

Utiliza el servidor SMTP de Spacemail (mail.spacemail.com) para enviar alertas
al equipo administrativo cuando un nuevo usuario se registra y requiere autorización.
"""

import os
import smtplib
import ssl
import logging
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

# Configuración SMTP de Spacemail
SMTP_HOST = os.getenv("SMTP_HOST", "mail.spacemail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "no-responder@genia.com.co")
SMTP_PASS = os.getenv("SMTP_PASS", "cakDYV@V4UK9*?n")
SMTP_SENDER_NAME = "GENIA Notificaciones"

# Configuración del frontend / dominio oficial
FRONTEND_URL = (os.getenv("FRONTEND_URL") or "https://genia.com.co").strip().rstrip("/")

# Destinatarios administrativos
ADMIN_NOTIFY_EMAILS = [
    "conecta@genia.com.co",
    "alejandr.ia.8725@gmail.com",
]


def _send_smtp_email(to_email: str, subject: str, html_body: str):
    """Envía un correo de forma síncrona mediante SMTP SSL."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{SMTP_SENDER_NAME} <{SMTP_USER}>"
        msg["To"] = to_email

        part = MIMEText(html_body, "html", "utf-8")
        msg.attach(part)

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=10.0) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [to_email], msg.as_string())

        logger.info("[EMAIL] Alerta enviada con éxito a %s: %s", to_email, subject)
    except Exception as e:
        logger.error("[EMAIL] Error al enviar correo a %s: %s", to_email, str(e), exc_info=True)


def notify_admin_new_user_registered(user_email: str, user_id: str):
    """
    Envía una notificación por correo a los administradores informando que
    un nuevo usuario se registró y está a la espera de autorización y asignación de agente.
    Se ejecuta en segundo plano (hilo independiente) para no bloquear la petición HTTP.
    """
    subject = f"🔔 Nuevo usuario registrado en GENIA: {user_email}"
    
    html_content = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 560px; margin: 0 auto; background-color: #0d1321; border-radius: 16px; padding: 32px 24px; border: 1px solid #1e293b; color: #f8fafc;">
      
      <div style="text-align: center; margin-bottom: 24px;">
        <h1 style="color: #ffffff; font-size: 22px; font-weight: 800; margin: 0; letter-spacing: 0.5px;">PLATAFORMA GENIA</h1>
        <p style="color: #94a3b8; font-size: 12px; margin-top: 4px;">Alerta Administrativa de Acceso</p>
      </div>

      <div style="background-color: #161f38; border-radius: 12px; padding: 24px; border: 1px solid #2d3a5f;">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
          <span style="background-color: #3b82f6; color: white; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;">NUEVA SOLICITUD</span>
        </div>

        <p style="color: #e2e8f0; font-size: 14px; line-height: 1.5; margin-top: 0;">
          Un nuevo usuario se ha registrado en la plataforma y se encuentra <strong>pendiente de verificación</strong>:
        </p>

        <div style="background-color: #070b13; border: 1px solid #334155; border-radius: 8px; padding: 16px; margin: 16px 0;">
          <p style="margin: 0 0 6px 0; font-size: 13px; color: #94a3b8;">
            <strong style="color: #e2e8f0;">Correo:</strong> {user_email}
          </p>
          <p style="margin: 0; font-size: 12px; color: #64748b;">
            <strong style="color: #94a3b8;">ID de Usuario:</strong> {user_id}
          </p>
        </div>

        <p style="color: #cbd5e1; font-size: 13px; line-height: 1.5;">
          El usuario actualmente no tiene acceso a ningún agente hasta que autorices su cuenta y le asignes el agente correspondiente.
        </p>

        <div style="text-align: center; margin-top: 24px;">
          <a href="{FRONTEND_URL}/users" style="display: inline-block; background-color: #2563eb; color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 10px; font-size: 13px; font-weight: bold; letter-spacing: 0.3px;">
            Gestionar y Asignar Agente →
          </a>
        </div>
      </div>

      <div style="text-align: center; margin-top: 24px;">
        <p style="color: #475569; font-size: 11px; margin: 0;">
          Notificación automática enviada por el Sistema de Acreditación GENIA.
        </p>
      </div>

    </div>
    """

    for admin_email in ADMIN_NOTIFY_EMAILS:
        t = threading.Thread(
            target=_send_smtp_email,
            args=(admin_email, subject, html_content),
            daemon=True
        )
        t.start()


def notify_user_account_approved(user_email: str, agent_name: str):
    """
    Envía una notificación por correo al usuario informándole que su cuenta ha sido autorizada
    y que su agente de Inteligencia Artificial asignado está listo para ser utilizado.
    Se ejecuta en segundo plano (hilo independiente).
    """
    subject = f"🚀 ¡Tu cuenta en GENIA está activa! Agente conectado: {agent_name}"

    html_content = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 560px; margin: 0 auto; background-color: #0d1321; border-radius: 16px; padding: 36px 28px; border: 1px solid #1e293b; color: #f8fafc;">
      
      <div style="text-align: center; margin-bottom: 24px;">
        <h1 style="color: #ffffff; font-size: 24px; font-weight: 800; margin: 0; letter-spacing: 0.5px;">PLATAFORMA GENIA</h1>
        <p style="color: #94a3b8; font-size: 13px; margin-top: 4px;">Acceso Autorizado</p>
      </div>

      <div style="background-color: #161f38; border-radius: 12px; padding: 26px; border: 1px solid #2d3a5f; text-align: center;">
        
        <div style="display: inline-block; background-color: #10b981; color: white; padding: 6px 14px; border-radius: 20px; font-size: 11px; font-weight: bold; letter-spacing: 0.5px; margin-bottom: 16px;">
          ✓ CUENTA VERIFICADA Y CONECTADA
        </div>

        <h2 style="color: #ffffff; font-size: 18px; font-weight: 700; margin: 0 0 10px 0;">
          ¡Bienvenido a tu entorno de IA!
        </h2>

        <p style="color: #cbd5e1; font-size: 14px; line-height: 1.6; margin: 0 0 20px 0;">
          Un administrador ha autorizado tu cuenta y ha conectado tu agente de Inteligencia Artificial personalizado:
        </p>

        <div style="background-color: #070b13; border: 1px solid #3b82f6; border-radius: 12px; padding: 18px; margin: 18px 0; text-align: left;">
          <div style="font-size: 11px; color: #60a5fa; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">
            Agente Asignado
          </div>
          <div style="font-size: 16px; font-weight: 800; color: #ffffff;">
            🤖 {agent_name}
          </div>
          <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
            Estado: <span style="color: #34d399; font-weight: 600;">Listo para interactuar</span>
          </div>
        </div>

        <p style="color: #94a3b8; font-size: 13px; line-height: 1.5; margin: 0 0 24px 0;">
          Ya puedes acceder a tu consola, probar las respuestas en el simulador Sandbox, consultar la base de conocimiento y monitorear tus conversaciones.
        </p>

        <div>
          <a href="{FRONTEND_URL}/login" style="display: inline-block; background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%); color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 10px; font-size: 14px; font-weight: 700; letter-spacing: 0.3px; box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4);">
            Ingresar a la Plataforma →
          </a>
        </div>

      </div>

      <div style="text-align: center; margin-top: 24px;">
        <p style="color: #475569; font-size: 11px; margin: 0;">
          Este correo fue generado automáticamente por la Plataforma GENIA.
        </p>
        <p style="color: #334155; font-size: 10px; margin-top: 6px;">
          &copy; GENIA &mdash; genia.com.co
        </p>
      </div>

    </div>
    """

    t = threading.Thread(
        target=_send_smtp_email,
        args=(user_email, subject, html_content),
        daemon=True
    )
    t.start()
