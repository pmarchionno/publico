# Configuración Brevo (antes Sendinblue) - La Más Simple ⭐

**Brevo es la opción MÁS FÁCIL** para enviar emails de verificación. No requiere configuración DNS y ofrece 300 emails/día gratis.

---

## 🚀 Setup en 3 Minutos

### 1. Crear Cuenta (1 minuto)

**Registrarse**: https://app.brevo.com/account/register

- Email válido
- Contraseña
- Confirmar email
- ✅ Cuenta creada (sin tarjeta de crédito)

---

### 2. Generar API Key (1 minuto)

1. **Login** en https://app.brevo.com/
2. Ve a **Settings** (arriba derecha) → **SMTP & API** → **API Keys**
3. Click **"Generate a new API key"**
4. **Name**: "PagoFlex Production"
5. **Copiar** el key:
   ```
   xkeysib-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

⚠️ **Importante**: Guarda el API Key, no se volverá a mostrar.

---

### 3. Configurar PagoFlex (1 minuto)

Crea archivo `.env` en la raíz del proyecto:

```bash
# Email Configuration
EMAIL_ENABLED=true
EMAIL_PROVIDER=brevo

# Brevo API
BREVO_API_KEY=xkeysib-tu-key-completa-aqui
BREVO_FROM_EMAIL=tu-email-personal@gmail.com  # Tu email real
BREVO_FROM_NAME=PagoFlex

# Otras configuraciones...
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/pagoflex
SECRET_KEY=your-super-secret-key
```

**Reiniciar contenedores:**

```bash
docker compose restart api
```

✅ **¡Listo! Ya puedes enviar emails**

---

## 🧪 Probar Envío

### Registrar un usuario

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "tu-email-real@gmail.com"}'
```

**Respuesta esperada:**

```json
{
  "message": "Se envio el correo de verificacion",
  "verification_link": null
}
```

### Verificar logs

```bash
docker compose logs -f api | grep "Email"
```

**Log esperado:**

```
✅ Email de verificación enviado (Brevo) a: tu-email-real@gmail.com
```

### Revisar tu email

- Email llega en **menos de 5 segundos**
- Revisa bandeja de entrada (y spam si no aparece)
- Click en **"✓ Verificar mi correo"**

---

## 📊 Ventajas de Brevo

| Característica          | Brevo ✅   | SendGrid    | Gmail SMTP      |
| ----------------------- | ---------- | ----------- | --------------- |
| **Setup**               | 3 minutos  | 5 minutos   | 3 minutos       |
| **DNS Requerido**       | ❌ NO      | ⚠️ Opcional | ❌ NO           |
| **Verificación Sender** | ❌ NO      | ✅ Sí       | ⚠️ App Password |
| **Emails Gratis/Día**   | **300** 🎉 | 100         | ~500            |
| **API Key Seguro**      | ✅ Sí      | ✅ Sí       | ⚠️ App Password |
| **Analytics**           | ✅ Sí      | ✅ Sí       | ❌ No           |
| **Webhooks**            | ✅ Sí      | ✅ Sí       | ❌ No           |
| **Producción**          | ✅ Sí      | ✅ Sí       | ❌ No           |

**Brevo gana**: Más emails gratis + NO requiere DNS + Setup instantáneo

---

## 🎯 Email Sender Configuration

### Opción 1: Usar tu Gmail Personal (Recomendado para desarrollo)

```bash
BREVO_FROM_EMAIL=tu-email@gmail.com
```

✅ **No necesitas verificar nada**  
✅ Funciona inmediatamente  
⚠️ Los emails se envían "desde" tu cuenta

---

### Opción 2: Dominio Propio (Opcional - Producción)

Si tienes un dominio (ej: `pagoflex.com`):

1. Ve a **Settings → Senders & IP**
2. Click **"Add a new sender"**
3. Email: `noreply@tudominio.com`
4. Verificar email

```bash
BREVO_FROM_EMAIL=noreply@tudominio.com
```

✅ Más profesional  
⚠️ Requiere acceso al email para verificación

---

## 📊 Monitorear Emails

### Dashboard

1. **Login** en https://app.brevo.com/
2. Ve a **Statistics** → **Email**
3. Verás en tiempo real:
   - **Delivered**: Entregados
   - **Opens**: Abiertos
   - **Clicks**: Clicks en links
   - **Bounces**: Rechazados
   - **Spam Reports**: Marcados como spam

### Logs Detallados

Ve a **Logs → Email Logs** para ver cada email enviado con detalles completos.

---

## 🐛 Troubleshooting

### Error: "Unauthorized"

**Causa**: API Key inválido

**Solución:**

```bash
# Verificar API Key en .env
echo $BREVO_API_KEY
# Debe empezar con xkeysib-
```

1. Ve a Brevo → Settings → API Keys
2. Verifica que el key esté activo
3. Genera uno nuevo si es necesario

---

### Error: "sender email not verified"

**Causa**: Email remitente no autorizado

**Solución:**

```bash
# Usa tu email personal verificado
BREVO_FROM_EMAIL=tu-email-personal@gmail.com
```

O verifica el email en Settings → Senders & IP

---

### Los emails no llegan

1. **Ver logs**:

```bash
docker compose logs api | grep "Brevo"
```

2. **Buscar status 201**:

```
✅ Email de verificación enviado (Brevo) a: ...
```

3. **Ver Brevo Logs**:
   - Dashboard → Logs → Email Logs
   - Busca el email
   - Verifica status: "Delivered" o "Bounced"

4. **Revisar SPAM**:
   - Muchos emails van a spam inicialmente
   - Marca como "No es spam"

---

## 💰 Planes y Precios Brevo

| Plan         | Precio  | Emails/Mes      | Ideal para                      |
| ------------ | ------- | --------------- | ------------------------------- |
| **Free**     | $0      | 9,000 (300/día) | Desarrollo + Producción pequeña |
| **Starter**  | $25/mes | 20,000          | Producción media                |
| **Business** | $65/mes | 100,000         | Producción grande               |

**Comparativa:**

- **SendGrid Free**: 100/día (3,000/mes)
- **Brevo Free**: 300/día (9,000/mes) ← **3x más** ✅

---

## ✨ Features de Brevo

✅ **300 emails/día gratis** (vs 100 de SendGrid)  
✅ **Sin DNS requerido** (funciona de inmediato)  
✅ **Sin verificación compleja** (usa tu Gmail)  
✅ **API REST moderna** (HTTP, no SMTP)  
✅ **Dashboard completo** (analytics + logs)  
✅ **Webhooks incluidos** (eventos automáticos)  
✅ **Templates visuales** (editor drag & drop)  
✅ **SMTP también disponible** (por si lo necesitas)

---

## 🔄 Migrar entre Proveedores

El código soporta Brevo, SendGrid y SMTP. Cambiar es solo editar `.env`:

### De SendGrid a Brevo:

```bash
- EMAIL_PROVIDER=sendgrid
+ EMAIL_PROVIDER=brevo

+ BREVO_API_KEY=xkeysib-xxxxx
+ BREVO_FROM_EMAIL=tu-email@gmail.com
```

### De SMTP a Brevo:

```bash
- EMAIL_PROVIDER=smtp
+ EMAIL_PROVIDER=brevo

+ BREVO_API_KEY=xkeysib-xxxxx
+ BREVO_FROM_EMAIL=tu-email@gmail.com
```

```bash
docker compose restart api
```

✅ **Cero cambios en el código**

---

## 📚 Referencias

- [Brevo Signup](https://app.brevo.com/account/register)
- [Brevo API Docs](https://developers.brevo.com/docs)
- [API Keys Management](https://app.brevo.com/settings/keys/api)
- [Email Statistics](https://app.brevo.com/statistics/email)
- [Sender Management](https://app.brevo.com/settings/sender)

---

## 📝 Resumen

✅ **Para desarrollo Y producción pequeña**: Brevo Free (300/día)

**3 pasos:**

1. Crear cuenta: https://app.brevo.com/account/register
2. Generar API Key: Settings → API Keys
3. Configurar `.env`:
   ```bash
   EMAIL_ENABLED=true
   EMAIL_PROVIDER=brevo
   BREVO_API_KEY=xkeysib-tu-key
   BREVO_FROM_EMAIL=tu-email@gmail.com
   ```
4. Reiniciar: `docker compose restart api`

**¡Listo en 3 minutos! 🎉**

---

## 🆚 ¿Brevo o SendGrid?

### Usa Brevo si:

- ✅ Quieres setup instantáneo (3 min)
- ✅ No tienes dominio propio
- ✅ Necesitas más emails gratis (300/día vs 100)
- ✅ Prefieres simplicidad

### Usa SendGrid si:

- ✅ Ya tienes cuenta SendGrid activa
- ✅ Necesitas más de 300 emails/día (plan pago)
- ✅ Tu empresa ya usa SendGrid

**Para PagoFlex Gateway**: **Brevo es más simple** ⭐
