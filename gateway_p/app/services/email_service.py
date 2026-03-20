"""Servicio de envío de emails con Brevo, SendGrid o SMTP"""
import logging
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from aiosmtplib import SMTP
import httpx
from config.settings import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Servicio para envío de emails usando Brevo, SendGrid o SMTP"""

    def __init__(self):
        self.email_enabled = settings.EMAIL_ENABLED
        self.email_provider = settings.EMAIL_PROVIDER.lower()
        
        # Brevo configuration (recomendado - más simple)
        self.brevo_api_key = settings.BREVO_API_KEY
        self.brevo_from_email = settings.BREVO_FROM_EMAIL
        self.brevo_from_name = settings.BREVO_FROM_NAME
        
        # SendGrid configuration
        self.sendgrid_api_key = settings.SENDGRID_API_KEY
        self.sendgrid_from_email = settings.SENDGRID_FROM_EMAIL
        self.sendgrid_from_name = settings.SENDGRID_FROM_NAME
        
        # SMTP configuration (legacy)
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_from_email = settings.SMTP_FROM_EMAIL
        self.smtp_from_name = settings.SMTP_FROM_NAME

    async def send_verification_email(self, to_email: str, code: str, minutes: str, first_name: Optional[str] = None) -> bool:
        """
        Envía email de verificación con el código de confirmación

        Args:
            to_email: Email del destinatario
            code: Código de verificación
            minutes: Tiempo de expiración del código en minutos
            first_name: Nombre del usuario (opcional)

        Returns:
            True si se envió correctamente, False en caso contrario
        """
        logger.info("[BREVO/EMAIL] send_verification_email llamado - to=%s EMAIL_ENABLED=%s", to_email, self.email_enabled)

        if not self.email_enabled:
            logger.info("[BREVO/EMAIL] Email deshabilitado - código generado pero no enviado para %s", to_email)
            return False

        logger.info("[BREVO/EMAIL] Provider=%s - iniciando envío a %s", self.email_provider, to_email)

        if self.email_provider == "brevo":
            return await self._send_verification_brevo(to_email, code, minutes, first_name)
        elif self.email_provider == "sendgrid":
            return await self._send_verification_sendgrid(to_email, code, minutes, first_name)
        else:
            return await self._send_verification_smtp(to_email, code, minutes, first_name)
    
    async def send_welcome_email(self, to_email: str, first_name: str) -> bool:
        """
        Envía email de bienvenida después de completar el registro
        
        Args:
            to_email: Email del destinatario
            first_name: Nombre del usuario
            
        Returns:
            True si se envió correctamente, False en caso contrario
        """
        if not self.email_enabled:
            logger.info(f"📧 Email deshabilitado. Bienvenida para: {to_email}")
            return False
        
        if self.email_provider == "brevo":
            return await self._send_welcome_brevo(to_email, first_name)
        elif self.email_provider == "sendgrid":
            return await self._send_welcome_sendgrid(to_email, first_name)
        else:
            return await self._send_welcome_smtp(to_email, first_name)

    # ==================== Brevo API Methods ====================
    
    async def _send_verification_brevo(self, to_email: str, code: str, minutes: str, first_name: Optional[str] = None) -> bool:
        """Envía email de verificación usando Brevo API REST"""
        try:
            logger.info("[BREVO] Iniciando envío a %s - subject=Verifica tu correo - PagoFlex", to_email)

            html_content = self._get_verification_html(code, minutes, first_name)
            text_content = self._get_verification_text(code, minutes, first_name)

            payload = {
                "sender": {
                    "name": self.brevo_from_name,
                    "email": self.brevo_from_email
                },
                "to": [
                    {"email": to_email}
                ],
                "subject": "Verifica tu correo - PagoFlex",
                "htmlContent": html_content,
                "textContent": text_content
            }

            logger.info("[BREVO] POST api.brevo.com/v3/smtp/email - to=%s from=%s", to_email, self.brevo_from_email)
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.brevo.com/v3/smtp/email",
                    headers={
                        "api-key": self.brevo_api_key,
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=10.0
                )

                if response.status_code == 201:
                    try:
                        resp_json = response.json() if response.text else {}
                    except Exception:
                        resp_json = {}
                    message_id = resp_json.get("messageId", resp_json.get("message_id", "N/A"))
                    logger.info(
                        "[BREVO] ✅ Servidor procesó correctamente - email aceptado por Brevo | to=%s status=201 messageId=%s",
                        to_email, message_id
                    )
                    return True
                else:
                    logger.error(
                        "[BREVO] ❌ Brevo rechazó el envío | to=%s status=%s body=%s",
                        to_email, response.status_code, response.text[:500]
                    )
                    return False

        except Exception as e:
            logger.error(
                "[BREVO] ❌ Excepción al enviar a %s: %s",
                to_email, str(e), exc_info=True
            )
            return False
    
    async def _send_welcome_brevo(self, to_email: str, first_name: str) -> bool:
        """Envía email de bienvenida usando Brevo API REST"""
        try:
            html_content = self._get_welcome_html(first_name)
            text_content = self._get_welcome_text(first_name)
            
            payload = {
                "sender": {
                    "name": self.brevo_from_name,
                    "email": self.brevo_from_email
                },
                "to": [
                    {"email": to_email}
                ],
                "subject": "¡Bienvenido a PagoFlex!",
                "htmlContent": html_content,
                "textContent": text_content
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.brevo.com/v3/smtp/email",
                    headers={
                        "api-key": self.brevo_api_key,
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=10.0
                )
                
                if response.status_code == 201:
                    logger.info(f"✅ Email de bienvenida enviado (Brevo) a: {to_email}")
                    return True
                else:
                    logger.error(f"❌ Error Brevo ({response.status_code}): {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error enviando email de bienvenida con Brevo a {to_email}: {str(e)}")
            return False

    # ==================== SendGrid API Methods ====================
    
    async def _send_verification_sendgrid(self, to_email: str, code: str, minutes: str, first_name: Optional[str] = None) -> bool:
        """Envía email de verificación usando SendGrid API REST"""
        try:
            html_content = self._get_verification_html(code, minutes, first_name)
            text_content = self._get_verification_text(code, minutes, first_name)
            
            payload = {
                "personalizations": [
                    {
                        "to": [{"email": to_email}],
                        "subject": "Verifica tu correo - PagoFlex"
                    }
                ],
                "from": {
                    "email": self.sendgrid_from_email,
                    "name": self.sendgrid_from_name
                },
                "content": [
                    {"type": "text/plain", "value": text_content},
                    {"type": "text/html", "value": html_content}
                ]
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={
                        "Authorization": f"Bearer {self.sendgrid_api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=10.0
                )
                
                if response.status_code == 202:
                    logger.info(f"✅ Email de verificación enviado (SendGrid) a: {to_email}")
                    return True
                else:
                    logger.error(f"❌ Error SendGrid ({response.status_code}): {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error enviando email con SendGrid a {to_email}: {str(e)}")
            return False
    
    async def _send_welcome_sendgrid(self, to_email: str, first_name: str) -> bool:
        """Envía email de bienvenida usando SendGrid API REST"""
        try:
            html_content = self._get_welcome_html(first_name)
            text_content = self._get_welcome_text(first_name)
            
            payload = {
                "personalizations": [
                    {
                        "to": [{"email": to_email}],
                        "subject": "¡Bienvenido a PagoFlex!"
                    }
                ],
                "from": {
                    "email": self.sendgrid_from_email,
                    "name": self.sendgrid_from_name
                },
                "content": [
                    {"type": "text/plain", "value": text_content},
                    {"type": "text/html", "value": html_content}
                ]
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={
                        "Authorization": f"Bearer {self.sendgrid_api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=10.0
                )
                
                if response.status_code == 202:
                    logger.info(f"✅ Email de bienvenida enviado (SendGrid) a: {to_email}")
                    return True
                else:
                    logger.error(f"❌ Error SendGrid ({response.status_code}): {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error enviando email de bienvenida con SendGrid a {to_email}: {str(e)}")
            return False

    # ==================== SMTP Methods (Legacy) ====================
    
    async def _send_verification_smtp(self, to_email: str, code: str, minutes: str, first_name: Optional[str] = None) -> bool:
        """Envía email de verificación usando SMTP (legacy)"""
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = "Verifica tu correo - PagoFlex"
            message["From"] = f"{self.smtp_from_name} <{self.smtp_from_email}>"
            message["To"] = to_email
            
            html_content = self._get_verification_html(code, minutes, first_name)
            text_content = self._get_verification_text(code, minutes, first_name)
            
            part_text = MIMEText(text_content, "plain")
            part_html = MIMEText(html_content, "html")
            message.attach(part_text)
            message.attach(part_html)

            smtp = SMTP(hostname=self.smtp_host, port=self.smtp_port)
            async with smtp:
                await smtp.starttls()
                await smtp.login(self.smtp_username, self.smtp_password)
                await smtp.send_message(message)

            logger.info(f"✅ Email de verificación enviado (SMTP) a: {to_email}")
            return True

        except Exception as e:
            logger.error(f"❌ Error enviando email con SMTP a {to_email}: {str(e)}")
            return False
    
    async def _send_welcome_smtp(self, to_email: str, first_name: str) -> bool:
        """Envía email de bienvenida usando SMTP (legacy)"""
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = "¡Bienvenido a PagoFlex!"
            message["From"] = f"{self.smtp_from_name} <{self.smtp_from_email}>"
            message["To"] = to_email

            html_content = self._get_welcome_html(first_name)
            text_content = self._get_welcome_text(first_name)

            part_text = MIMEText(text_content, "plain")
            part_html = MIMEText(html_content, "html")
            message.attach(part_text)
            message.attach(part_html)

            smtp = SMTP(hostname=self.smtp_host, port=self.smtp_port)
            async with smtp:
                await smtp.starttls()
                await smtp.login(self.smtp_username, self.smtp_password)
                await smtp.send_message(message)

            logger.info(f"✅ Email de bienvenida enviado (SMTP) a: {to_email}")
            return True

        except Exception as e:
            logger.error(f"❌ Error enviando email de bienvenida con SMTP a {to_email}: {str(e)}")
            return False

    # ==================== HTML Templates ====================
    
    def _get_verification_html(self, code: str, minutes: str, first_name: Optional[str] = None) -> str:
        """Template HTML para email de verificación con código (estilo BBVA)"""
        user_name = first_name.upper() if first_name else "USUARIO"
        return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Código de Verificación - PagoFlex</title>
</head>
<body style="margin: 0; padding: 0; background: #f3f4f6; font-family: Arial, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background: #f3f4f6; padding: 40px 0;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.08);">
                    <!-- Logo -->
                    <tr>
                        <td style="padding: 24px; text-align: left;">
                            <h1 style="margin: 0; color: #4F46E5; font-size: 28px; font-weight: bold;">PagoFlex</h1>
                        </td>
                    </tr>
                    
                    <!-- Shield Icon -->
                    <tr>
                        <td style="padding: 20px; text-align: center;">
                            <div style="display: inline-block; width: 80px; height: 80px; background: linear-gradient(135deg, #60A5FA 0%, #3B82F6 100%); border-radius: 50%; position: relative;">
                                <svg width="80" height="80" viewBox="0 0 80 80" style="position: absolute; top: 0; left: 0;">
                                    <path d="M40 10 L60 20 L60 40 Q60 60 40 70 Q20 60 20 40 L20 20 Z" fill="#3B82F6" stroke="#2563EB" stroke-width="2"/>
                                    <path d="M35 45 L38 48 L48 35" stroke="white" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
                                </svg>
                            </div>
                        </td>
                    </tr>
                    
                    <!-- Message -->
                    <tr>
                        <td style="padding: 0 32px 20px; text-align: center;">
                            <p style="margin: 0; font-size: 16px; color: #1f2937; line-height: 1.5;">
                                <strong>{user_name}</strong>, el <strong>código de seguridad</strong> para verificar tu cuenta es:
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Code Box -->
                    <tr>
                        <td style="padding: 0 32px 20px;">
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td style="padding: 0 16px;">
                                        <div style="background: #1e3a8a; border-radius: 10px; padding: 24px; text-align: center;">
                                            <p style="margin: 0; color: #ffffff; font-size: 40px; font-weight: bold; letter-spacing: 8px; font-family: 'Courier New', monospace;">
                                                {code}
                                            </p>
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Validity Notice -->
                    <tr>
                        <td style="padding: 0 32px 30px; text-align: center;">
                            <p style="margin: 0; font-size: 14px; color: #6b7280; font-style: italic;">
                                El código es válido por <strong>{minutes} minutos</strong>.
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Security Tips -->
                    <tr>
                        <td style="padding: 0 32px 32px;">
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td style="padding: 0 16px;">
                                        <div style="background: #dbeafe; border-radius: 10px; padding: 24px;">
                                            <h2 style="margin: 0 0 16px; color: #1e3a8a; font-size: 20px;">🔒 Protegé tu cuenta</h2>
                                            <ul style="margin: 0; padding-left: 20px; color: #1e40af; line-height: 1.8;">
                                                <li style="margin-bottom: 8px;">Nunca te vamos a pedir tu usuario, clave o código por mensaje, llamada, email o redes sociales.</li>
                                                <li style="margin-bottom: 8px;">Usá tus claves solo para operar en nuestros canales digitales. No las compartas con nadie.</li>
                                                <li style="margin-bottom: 8px;">No te vamos a llamar de forma urgente para que hagas operaciones de ningún tipo.</li>
                                                <li>Desconfiá de enlaces donde te soliciten datos personales o confidenciales.</li>
                                            </ul>
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 24px; text-align: center; border-top: 1px solid #e5e7eb;">
                            <p style="margin: 0 0 8px; color: #6b7280; font-size: 12px;">© 2026 PagoFlex - Gateway de Pagos</p>
                            <p style="margin: 0; color: #9ca3af; font-size: 11px;">Este es un correo automático, por favor no responder.</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

    def _get_verification_text(self, code: str, minutes: str, first_name: Optional[str] = None) -> str:
        """Template de texto plano para email de verificación"""
        user_name = first_name.upper() if first_name else "USUARIO"
        return f"""
Código de Verificación - PagoFlex

{user_name}, el código de seguridad para verificar tu cuenta es:

{code}

El código es válido por {minutes} minutos.

Protegé tu cuenta:
- Nunca te vamos a pedir tu usuario, clave o código por mensaje, llamada, email o redes sociales.
- Usá tus claves solo para operar en nuestros canales digitales. No las compartas con nadie.
- No te vamos a llamar de forma urgente para que hagas operaciones de ningún tipo.
- Desconfiá de enlaces donde te soliciten datos personales o confidenciales.

Si no solicitaste este código, puedes ignorar este correo.

© 2026 PagoFlex - Gateway de Pagos
"""

    def _get_welcome_html(self, first_name: str) -> str:
        """Template HTML para email de bienvenida"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #10B981; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }}
        .footer {{ text-align: center; padding: 20px; color: #6b7280; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 ¡Registro Completado!</h1>
        </div>
        <div class="content">
            <h2>¡Hola {first_name}!</h2>
            <p>Tu cuenta en PagoFlex ha sido creada exitosamente.</p>
            <p>Ya puedes comenzar a usar todos nuestros servicios de pagos y transferencias.</p>
            <p style="margin-top: 30px;">
                <strong>¿Qué puedes hacer ahora?</strong>
            </p>
            <ul>
                <li>Realizar pagos seguros</li>
                <li>Transferir dinero</li>
                <li>Consultar tu historial de transacciones</li>
            </ul>
            <p style="color: #6b7280; margin-top: 30px;">
                Si tienes alguna pregunta, no dudes en contactarnos.
            </p>
        </div>
        <div class="footer">
            <p>© 2026 PagoFlex - Gateway de Pagos</p>
        </div>
    </div>
</body>
</html>
"""

    def _get_welcome_text(self, first_name: str) -> str:
        """Template de texto plano para email de bienvenida"""
        return f"""
¡Bienvenido a PagoFlex!

¡Hola {first_name}!

Tu cuenta en PagoFlex ha sido creada exitosamente.

Ya puedes comenzar a usar todos nuestros servicios.

© 2026 PagoFlex - Gateway de Pagos
"""
