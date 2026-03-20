# Configuración de Emails - PagoFlex Gateway

Sistema de envío de emails para verificación de usuarios con soporte para **Brevo** (recomendado), **SendGrid** y **SMTP**.

---

## 🎯 ¿Qué proveedor usar?

### ✅ Brevo (Recomendado - MÁS SIMPLE)

**Para desarrollo y producción pequeña/media**

- ✅ **Setup en 3 minutos** (el más rápido)
- ✅ **Sin DNS requerido** (funciona de inmediato)
- ✅ **300 emails/día GRATIS** (3x más que SendGrid)
- ✅ API Keys seguras (revocables)
- ✅ Analytics + webhooks incluidos
- ✅ Sin verificación compleja

**👉 Ver guía completa**: [`BREVO_SETUP.md`](BREVO_SETUP.md) ← **Empieza aquí**

---

### ⚙️ SendGrid API REST

**Para producción enterprise**

- ✅ Más seguro (API Keys en lugar de passwords)
- ✅ Mayor confiabilidad (mejor deliverability)
- ✅ Analytics + webhooks
- ⚠️ Solo 100 emails/día gratis (vs 300 de Brevo)
- ⚠️ Requiere verificación de sender

**👉 Ver guía**: [`SENDGRID_SETUP.md`](SENDGRID_SETUP.md)

---

### ⚠️ SMTP (Gmail/Outlook) - Legacy

**Solo para pruebas rápidas locales**

- ⚠️ App Passwords son menos seguros
- ⚠️ Más lento que API REST
- ⚠️ Sin analytics ni tracking
- ⚠️ No recomendado para producción

**👉 Ver guía legacy**: [`CONFIGURACION_SMTP.md`](CONFIGURACION_SMTP.md)

---

## 🚀 Setup Rápido

### Opción A: Brevo (3 minutos) ⭐

1. **Crear cuenta**: https://app.brevo.com/account/register
2. **Generar API Key**: Settings → API Keys → Generate
3. **Configurar `.env`**:

```bash
EMAIL_ENABLED=true
EMAIL_PROVIDER=brevo
BREVO_API_KEY=xkeysib-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
BREVO_FROM_EMAIL=tu-email@gmail.com  # Tu email personal
BREVO_FROM_NAME=PagoFlex
```

4. **Reiniciar**: `docker compose restart api`

✅ **¡Listo! Ya puedes enviar 300 emails/día**

---

### Opción B: SendGrid (5 minutos)

1. **Crear cuenta**: https://signup.sendgrid.com/
2. **Generar API Key**: Settings → API Keys → Create
3. **Verificar sender**: Settings → Sender Authentication → Single Sender
4. **Configurar `.env`**:

```bash
EMAIL_ENABLED=true
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SENDGRID_FROM_EMAIL=tu-email-verificado@gmail.com
SENDGRID_FROM_NAME=PagoFlex
```

5. **Reiniciar**: `docker compose restart api`

---

### Opción B: SMTP / Gmail (legacy)

1. **Generar App Password**: https://myaccount.google.com/apppasswords
2. **Configurar `.env`**:

```bash
EMAIL_ENABLED=true
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=tucorreo@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop
SMTP_FROM_EMAIL=tucorreo@gmail.com
SMTP_FROM_NAME=PagoFlex
```

3. **Reiniciar**: `docker compose restart api`

---

### Opción C: Modo Desarrollo (sin envío real)

**Recomendado para testing local sin consumir recursos**

```bash
EMAIL_ENABLED=false
```

**Comportamiento:**

- El `verification_link` se retorna en la respuesta JSON
- Copiar y pegar link manualmente en el navegador
- No se consume límite de SendGrid ni SMTP

---

## 📧 Emails que se Envían

### 1. Email de Verificación

**Cuándo**: Usuario registra su email (`POST /auth/register`)

**Contenido**:

- Asunto: "Verifica tu correo - PagoFlex"
- Botón con link de verificación (token JWT válido 24h)
- Versiones HTML y texto plano

### 2. Email de Bienvenida

**Cuándo**: Usuario completa su registro (`POST /auth/register/complete`)

**Contenido**:

- Asunto: "¡Bienvenido a PagoFlex!"
- Mensaje de bienvenida personalizado con nombre
- Primeros pasos

---

## 🔧 Variables de Entorno

### Generales

```bash
EMAIL_ENABLED=false           # true para enviar emails reales
EMAIL_PROVIDER=sendgrid       # "sendgrid" o "smtp"
```

### SendGrid (recomendado)

```bash
SENDGRID_API_KEY=SG.xxxxx
SENDGRID_FROM_EMAIL=noreply@pagoflex.com
SENDGRID_FROM_NAME=PagoFlex
```

### SMTP (legacy)

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=tu-email@gmail.com
SMTP_PASSWORD=tu-app-password
SMTP_FROM_EMAIL=noreply@pagoflex.com
SMTP_FROM_NAME=PagoFlex
```

---

## 🧪 Probar Envío

### 1. Registrar email

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "tu-email@gmail.com"}'
```

### 2. Verificar logs

```bash
docker compose logs -f api | grep "Email"
```

**Esperado con SendGrid:**

```
✅ Email de verificación enviado (SendGrid) a: tu-email@gmail.com
```

**Esperado con SMTP:**

```
✅ Email de verificación enviado (SMTP) a: tu-email@gmail.com
```

**Esperado con email deshabilitado:**

```
📧 Email deshabilitado. Link de verificación: http://localhost:8000/auth/verify-email?token=eyJ...
```

### 3. Revisar inbox

- Emails llegan en 3-10 segundos
- Revisar spam si no aparece

---

## 📊 Comparativa Proveedores

| Característica     | SendGrid ✅    | SMTP ❌        | Desarrollo |
| ------------------ | -------------- | -------------- | ---------- |
| **Seguridad**      | API Keys       | App Passwords  | N/A        |
| **Velocidad**      | HTTP REST      | Protocolo SMTP | Instant    |
| **Deliverability** | Alta           | Media          | N/A        |
| **Analytics**      | ✅ Incluido    | ❌ No          | ❌ No      |
| **Webhooks**       | ✅ Sí          | ❌ No          | ❌ No      |
| **Gratis/mes**     | 3,000 emails   | Gmail limits   | Ilimitado  |
| **Producción**     | ✅ Recomendado | ❌ No          | ❌ No      |
| **Setup**          | 5 min          | 3 min          | 0 min      |

---

## 🐛 Troubleshooting Común

### Los emails no llegan

**SendGrid:**

1. Verificar API Key correcto
2. Verificar Sender Identity
3. Revisar Activity en dashboard SendGrid
4. Revisar carpeta SPAM

**SMTP:**

1. Verificar App Password correcto
2. Verificar firewall no bloquea puerto 587
3. Gmail: máximo 500 emails/día
4. Revisar carpeta SPAM

### Error: "Authorization failed"

**SendGrid:**

```bash
# Verificar API Key en .env
echo $SENDGRID_API_KEY
# Debe empezar con SG.
```

**SMTP:**

```bash
# Verificar App Password (16 caracteres sin espacios)
echo $SMTP_PASSWORD
```

### Error: "Sender not verified"

**SendGrid:**

1. Ve a Settings → Sender Authentication
2. Verifica que `SENDGRID_FROM_EMAIL` esté validado
3. Revisa tu email para confirmar verificación

---

## 📚 Documentación Detallada

- **SendGrid API Setup**: [`SENDGRID_SETUP.md`](SENDGRID_SETUP.md) ← **Recomendado**
- **SMTP Legacy Setup**: [`CONFIGURACION_SMTP.md`](CONFIGURACION_SMTP.md)
- **Registro 2 Pasos**: [`7_SECUENCIA_REGISTRO_USUARIOS.md`](7_SECUENCIA_REGISTRO_USUARIOS.md)

---

## 💡 Recomendaciones

### Para Desarrollo Local

```bash
EMAIL_ENABLED=false
```

- No consume recursos
- Link en respuesta JSON
- Más rápido para testing

### Para Testing/Staging

```bash
EMAIL_ENABLED=true
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=...
```

- Usar plan Free de SendGrid (100/día)
- Probar flujo completo

### Para Producción

```bash
EMAIL_ENABLED=true
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=...
```

- Plan Essentials de SendGrid ($19.95/mes = 50k emails)
- Domain Authentication configurado
- Monitoreo en dashboard

---

## 🎯 Migración SMTP → SendGrid

Si ya tienes SMTP:

```bash
# 1. Cambiar proveedor
EMAIL_PROVIDER=sendgrid

# 2. Agregar API Key
SENDGRID_API_KEY=SG.xxxxx
SENDGRID_FROM_EMAIL=noreply@pagoflex.com

# 3. (Opcional) Mantener SMTP como backup
# Las variables SMTP pueden quedar configuradas
```

```bash
docker compose restart api
```

✅ **Cero cambios en el código, solo configuración**

---

## ✨ Features Implementados

✅ Verificación de email con token JWT (24h expiración)  
✅ Email de bienvenida personalizado  
✅ Templates HTML + texto plano  
✅ Soporte SendGrid API REST  
✅ Soporte SMTP legacy  
✅ Modo desarrollo sin envío real  
✅ Logs detallados de envío  
✅ Error handling robusto

---

## 📞 Soporte

Si tienes problemas:

1. Revisa logs: `docker compose logs api | grep "Email"`
2. Verifica `.env` esté cargado correctamente
3. Consulta documentación del proveedor
4. Revisa el código en `app/services/email_service.py`
