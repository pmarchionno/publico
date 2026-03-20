# Configuración de SendGrid API REST para Envío de Emails

SendGrid es la solución **recomendada para producción** por ser más moderna, segura y confiable que SMTP.

## 🚀 ¿Por qué SendGrid API en lugar de SMTP?

| Característica       | SendGrid API ✅          | SMTP ❌                     |
| -------------------- | ------------------------ | --------------------------- |
| **Seguridad**        | API Keys revocables      | App Passwords menos seguros |
| **Velocidad**        | HTTP/REST (más rápido)   | Protocolo SMTP (más lento)  |
| **Confiabilidad**    | Alta deliverability      | Puede caer en SPAM          |
| **Tracking**         | Opens, clicks, bounces   | No incluido                 |
| **Analytics**        | Dashboard completo       | Manual                      |
| **Webhooks**         | Eventos automáticos      | No disponible               |
| **Templates**        | Gestionados centralmente | Solo en código              |
| **Token Expiracion** | No expira                | App Password puede expirar  |
| **Estándar Modern**  | OAuth 2.0 compatible     | Legacy                      |

---

## 📋 Configuración Rápida

### 1. Crear Cuenta en SendGrid

1. **Registrarse**: https://signup.sendgrid.com/
2. **Plan Free**: 100 emails/día (3,000/mes) GRATIS ✅
3. **Plan Essentials**: $19.95/mes → 50,000 emails

### 2. Crear API Key

1. Ve a **Settings → API Keys**
2. Click **"Create API Key"**
3. **Name**: "PagoFlex Production"
4. **Permissions**: "Full Access" (o solo "Mail Send" para mayor seguridad)
5. **Copiar** el API Key (se muestra una sola vez)

```
SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

⚠️ **IMPORTANTE**: Guarda el API Key inmediatamente, no se volverá a mostrar.

### 3. Verificar Sender Identity

**Opción A: Single Sender (Rápido - ideal para testing)**

1. Ve a **Settings → Sender Authentication → Single Sender Verification**
2. Click **"Create New Sender"**
3. Completa formulario:
   - **From Name**: PagoFlex
   - **From Email**: noreply@pagoflex.com (o tu email real)
   - **Reply To**: support@pagoflex.com
   - **Address**, **City**, **Country**: Tu información
4. Verifica tu email (revisa spam)
5. ✅ Listo para enviar

**Opción B: Domain Authentication (Producción - más profesional)**

1. Ve a **Settings → Sender Authentication → Authenticate Your Domain**
2. Sigue el wizard para agregar registros DNS
3. SendGrid verifica automáticamente (puede tardar 24-48h)

---

## ⚙️ Configurar PagoFlex

### Crear archivo `.env`

```bash
# Email Configuration
EMAIL_ENABLED=true
EMAIL_PROVIDER=sendgrid

# SendGrid API
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SENDGRID_FROM_EMAIL=noreply@pagoflex.com
SENDGRID_FROM_NAME=PagoFlex

# Otros...
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/pagoflex
SECRET_KEY=your-super-secret-key
```

### Reiniciar Contenedores

```bash
docker compose down
docker compose up -d --build
```

---

## 🧪 Probar Envío de Emails

### 1. Registrar usuario

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "tu-email-real@gmail.com"}'
```

**Respuesta esperada (EMAIL_ENABLED=true):**

```json
{
  "message": "Se envio el correo de verificacion",
  "verification_link": null
}
```

### 2. Verificar logs

```bash
docker compose logs -f api
```

**Log esperado:**

```
✅ Email de verificación enviado (SendGrid) a: tu-email-real@gmail.com
```

### 3. Revisar tu email

- Email debe llegar en menos de 5 segundos
- Revisa **bandeja de entrada** (y spam si no aparece)
- Click en botón **"✓ Verificar mi correo"**

---

## 📊 Monitorear Emails en SendGrid

### Dashboard

1. Ve a **Activity** en SendGrid
2. Verás todos los emails enviados en tiempo real
3. Estadísticas:
   - **Delivered**: Entregados exitosamente
   - **Opens**: Cuántos abrieron el email
   - **Clicks**: Cuántos hicieron click en links
   - **Bounces**: Rechazados (email inválido)
   - **Spam Reports**: Marcados como spam

### Webhooks (Opcional - Avanzado)

Configura webhooks para recibir eventos en tu API:

- Email entregado
- Email abierto
- Link clickeado
- Rebotado (bounce)

---

## 🛠️ Desarrollo vs Producción

### Modo Desarrollo (recomendado para testing local)

```bash
# .env
EMAIL_ENABLED=false
EMAIL_PROVIDER=sendgrid
```

**Comportamiento:**

- ✅ No consume límite de SendGrid
- ✅ `verification_link` en respuesta JSON
- ✅ Copiar y pegar link manualmente

### Modo Producción

```bash
# .env
EMAIL_ENABLED=true
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=SG.real-key-here
SENDGRID_FROM_EMAIL=noreply@tudominio.com
```

**Comportamiento:**

- ✅ Emails enviados automáticamente
- ✅ `verification_link` es `null` (seguridad)
- ✅ Usuario recibe email profesional

---

## 🔐 Seguridad: API Key vs App Password

### SendGrid API Key ✅

```bash
SENDGRID_API_KEY=SG.xxxxx
```

- **Revocable**: Puedes desactivarlo en cualquier momento
- **Alcance limitado**: Solo permisos para enviar emails
- **Rotación**: Puedes cambiar keys sin cambiar password
- **Auditoría**: Cada key tiene logs independientes

### Gmail App Password ❌ (legacy)

```bash
SMTP_PASSWORD=abcd efgh ijkl mnop
```

- **No revocable fácilmente**: Requiere generar nueva
- **Acceso completo**: Acceso a toda tu cuenta Gmail
- **Puede expirar**: Google puede desactivarlas
- **Menos profesional**: No diseñado para apps

---

## 🐛 Troubleshooting

### Error: "The provided authorization grant is invalid, expired, or revoked"

**Causa**: API Key inválido o revocado

**Solución:**

1. Verifica que el API Key esté correcto (sin espacios)
2. Ve a SendGrid y verifica que el key exista y esté activo
3. Genera un nuevo API Key si es necesario

---

### Error: "The from address does not match a verified Sender Identity"

**Causa**: Email remitente no verificado en SendGrid

**Solución:**

1. Ve a **Settings → Sender Authentication**
2. Verifica que `SENDGRID_FROM_EMAIL` coincida con un sender verificado
3. Si usas otro email, agrégalo como nuevo sender

---

### Los emails no llegan

**Pasos a seguir:**

1. **Verificar logs**:

```bash
docker compose logs api | grep "Email"
```

2. **Buscar error 202**:

```
✅ Email de verificación enviado (SendGrid) a: ...
```

3. **Revisar SendGrid Activity**:
   - Ve al dashboard de SendGrid
   - Busca el email en "Activity"
   - Verifica estado: "Delivered" o "Bounced"

4. **Revisar SPAM**:
   - Muchos emails de verificación van a spam inicialmente
   - Marca como "No es spam" para entrenar el filtro

5. **Verificar dominio** (producción):
   - Emails desde dominios no verificados tienen menor deliverability
   - Configura Domain Authentication en SendGrid

---

### Rate Limit Exceeded

**Causa**: Superaste el límite de tu plan (100/día en Free)

**Solución:**

- Esperar 24 horas para que se resetee
- Upgrade a plan pago ($19.95/mes = 50,000 emails)
- Para desarrollo, usar `EMAIL_ENABLED=false`

---

## 💰 Planes y Precios SendGrid

| Plan           | Precio     | Emails/mes      | Ideal para         |
| -------------- | ---------- | --------------- | ------------------ |
| **Free**       | $0         | 3,000 (100/día) | Desarrollo/Testing |
| **Essentials** | $19.95/mes | 50,000          | Producción pequeña |
| **Pro**        | $89.95/mes | 100,000         | Producción media   |
| **Premier**    | Custom     | Ilimitado       | Empresa            |

**Comparativa con competencia:**

- **Mailgun**: $35/mes → 50,000 emails
- **Amazon SES**: $0.10 por 1,000 emails (más barato pero más complejo)
- **Postmark**: $15/mes → 10,000 emails

---

## 🔄 Migrar de SMTP a SendGrid

Si ya tienes SMTP configurado:

### 1. Cambiar variables en `.env`

```diff
- EMAIL_PROVIDER=smtp
+ EMAIL_PROVIDER=sendgrid

- SMTP_ENABLED=true
+ EMAIL_ENABLED=true

+ SENDGRID_API_KEY=SG.xxxxx
+ SENDGRID_FROM_EMAIL=noreply@pagoflex.com
```

### 2. Reiniciar

```bash
docker compose restart api
```

### 3. Probar

Todo sigue funcionando igual, solo cambia el proveedor interno.

---

## 📚 Referencias

- [SendGrid Signup](https://signup.sendgrid.com/)
- [SendGrid API Docs](https://docs.sendgrid.com/api-reference/mail-send/mail-send)
- [Sender Authentication](https://docs.sendgrid.com/ui/account-and-settings/how-to-set-up-domain-authentication)
- [API Key Best Practices](https://docs.sendgrid.com/ui/account-and-settings/api-keys#api-key-permissions)
- [Activity Dashboard](https://docs.sendgrid.com/ui/analytics-and-reporting/email-activity-feed)

---

## 📝 Resumen

✅ **Para desarrollo**: `EMAIL_ENABLED=false` → copiar link de respuesta JSON

✅ **Para producción**:

1. Crear cuenta SendGrid (Free = 100 emails/día)
2. Generar API Key
3. Verificar Sender Identity
4. Configurar `.env` con `EMAIL_ENABLED=true` y `EMAIL_PROVIDER=sendgrid`
5. Reiniciar contenedores
6. ¡Listo! 🎉

**SendGrid API es más moderno, seguro y confiable que SMTP.** No necesitas App Passwords ni OAuth complejo.
