# Configuración de SMTP para Envío de Emails

Este documento explica cómo configurar el envío de emails de verificación usando SMTP.

## 📋 Configuración Rápida

### 1. Variables de Entorno

Copia `.env.example` a `.env` y configura:

```bash
# Habilitar SMTP
SMTP_ENABLED=true

# Configuración del servidor SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=tu-email@gmail.com
SMTP_PASSWORD=tu-app-password-aqui
SMTP_FROM_EMAIL=noreply@pagoflex.com
SMTP_FROM_NAME=PagoFlex
```

### 2. Reinstalar Dependencias

```bash
pip install -r requirements.txt
# o en el contenedor
docker compose down
docker compose up -d --build
```

## 🔐 Configuración por Proveedor

### Gmail

1. **Activar verificación en 2 pasos** en tu cuenta de Google
2. **Generar App Password**:
   - Ve a: https://myaccount.google.com/apppasswords
   - Nombre: "PagoFlex SMTP"
   - Copia el password de 16 caracteres generado

3. **Configurar .env**:

```bash
SMTP_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=tu-email@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop  # App password (sin espacios)
SMTP_FROM_EMAIL=tu-email@gmail.com
SMTP_FROM_NAME=PagoFlex
```

⚠️ **Importante**: Usa el **App Password**, NO tu contraseña de Gmail.

---

### Outlook / Hotmail

```bash
SMTP_ENABLED=true
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USERNAME=tu-email@outlook.com
SMTP_PASSWORD=tu-password
SMTP_FROM_EMAIL=tu-email@outlook.com
SMTP_FROM_NAME=PagoFlex
```

---

### SendGrid (Recomendado para producción)

1. **Crear cuenta**: https://sendgrid.com/
2. **Generar API Key**: Settings → API Keys
3. **Configurar**:

```bash
SMTP_ENABLED=true
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey  # Literal "apikey"
SMTP_PASSWORD=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxx  # Tu API Key
SMTP_FROM_EMAIL=noreply@tudominio.com
SMTP_FROM_NAME=PagoFlex
```

⚠️ Debes verificar tu dominio en SendGrid para producción.

---

### Mailgun

1. **Crear cuenta**: https://www.mailgun.com/
2. **Obtener credenciales**: Settings → SMTP
3. **Configurar**:

```bash
SMTP_ENABLED=true
SMTP_HOST=smtp.mailgun.org
SMTP_PORT=587
SMTP_USERNAME=postmaster@mg.tudominio.com
SMTP_PASSWORD=tu-smtp-password
SMTP_FROM_EMAIL=noreply@tudominio.com
SMTP_FROM_NAME=PagoFlex
```

---

### Amazon SES

```bash
SMTP_ENABLED=true
SMTP_HOST=email-smtp.us-east-1.amazonaws.com  # Tu región
SMTP_PORT=587
SMTP_USERNAME=tu-aws-smtp-username
SMTP_PASSWORD=tu-aws-smtp-password
SMTP_FROM_EMAIL=noreply@tudominio.com
SMTP_FROM_NAME=PagoFlex
```

⚠️ Necesitas verificar tu dominio/email en AWS SES.

---

## 🧪 Modo Desarrollo (Sin SMTP)

Si `SMTP_ENABLED=false` (por defecto):

- ✅ No se envían emails reales
- ✅ El `verification_link` se retorna en la respuesta JSON
- ✅ Copiar link y pegar en navegador para probar

```json
{
  "message": "Correo de verificacion generado (SMTP deshabilitado)",
  "verification_link": "http://localhost:8000/auth/verify-email?token=eyJ..."
}
```

## 🚀 Modo Producción (Con SMTP)

Si `SMTP_ENABLED=true`:

- ✅ Se envía email HTML al usuario
- ✅ NO se retorna el `verification_link` en la respuesta (seguridad)
- ✅ Usuario recibe email con botón de verificación

```json
{
  "message": "Se envio el correo de verificacion",
  "verification_link": null
}
```

## 📧 Emails que se Envían

### 1. Email de Verificación

Se envía cuando el usuario se registra con su email (`POST /auth/register`):

- **Asunto**: "Verifica tu correo - PagoFlex"
- **Contenido**: Link de verificación con token JWT
- **Expiración**: 24 horas

### 2. Email de Bienvenida

Se envía cuando el usuario completa su registro (`POST /auth/register/complete`):

- **Asunto**: "¡Bienvenido a PagoFlex!"
- **Contenido**: Mensaje de bienvenida con primeros pasos

## 🐛 Troubleshooting

### Error: "Connection refused"

- Verifica que `SMTP_HOST` y `SMTP_PORT` sean correctos
- Revisa firewall/security groups

### Error: "Authentication failed"

- Verifica `SMTP_USERNAME` y `SMTP_PASSWORD`
- Para Gmail, asegúrate de usar **App Password**

### Error: "Sender address rejected"

- Verifica que `SMTP_FROM_EMAIL` sea válido
- Para producción, usa dominio verificado

### No llegan los emails

- Revisa carpeta de SPAM
- Verifica logs del contenedor: `docker compose logs -f api`
- Busca líneas con "✅ Email" o "❌ Error enviando email"

## 🔍 Logs

Los emails se registran en los logs de la aplicación:

```bash
# Ver logs en vivo
docker compose logs -f api

# Buscar mensajes de email
docker compose logs api | grep "Email"
```

Logs esperados:

- `📧 SMTP deshabilitado. Link de verificación: http://...` (desarrollo)
- `✅ Email de verificación enviado a: usuario@example.com` (producción)
- `❌ Error enviando email a usuario@example.com: ...` (error)

## 🎯 Recomendaciones

**Para Desarrollo:**

- `SMTP_ENABLED=false` → Copiar link de la respuesta JSON
- Rápido y sin configuración

**Para Testing/Staging:**

- Gmail con App Password
- SendGrid Free Tier (12,000 emails/mes)

**Para Producción:**

- SendGrid ($15/mes, 40,000 emails)
- Mailgun ($35/mes, 50,000 emails)
- Amazon SES (más barato: $0.10 por 1,000 emails)
- Usar dominio verificado

## 📝 Ejemplo Completo

```bash
# .env
SMTP_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=micorreo@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop
SMTP_FROM_EMAIL=micorreo@gmail.com
SMTP_FROM_NAME=PagoFlex Gateway
```

```bash
# Reiniciar
docker compose restart api

# Probar registro
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "prueba@example.com"}'

# Revisar logs
docker compose logs -f api
```

Deberías ver: `✅ Email de verificación enviado a: prueba@example.com`

## 🔗 Referencias

- [Gmail App Passwords](https://support.google.com/accounts/answer/185833)
- [SendGrid Docs](https://docs.sendgrid.com/)
- [Mailgun SMTP](https://documentation.mailgun.com/docs/mailgun/user-manual/get-started/sending-email/#via-smtp)
- [AWS SES SMTP](https://docs.aws.amazon.com/ses/latest/dg/send-email-smtp.html)
