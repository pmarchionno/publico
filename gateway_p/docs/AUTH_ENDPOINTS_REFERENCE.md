# API Authentication Endpoints Reference

# Gateway Payment - Autenticación de Usuarios

Documentación técnica de los endpoints de autenticación del sistema Gateway Pagoflex.

## 📋 Índice

1. [Resumen General](#resumen-general)
2. [Endpoints](#endpoints)
3. [Flujo de Autenticación](#flujo-de-autenticación)
4. [Errores Comunes](#errores-comunes)

---

## Resumen General

**Base URL**: `/auth`  
**Autenticación**: JWT Bearer Token  
**Contenido**: application/json

---

## Endpoints

### 1. Registrar Email (Step 1)

```
POST /auth/register
```

**Descripción**: Inicia el proceso de registro recibiendo el email y enviando un link de verificación.

**Request**:

```json
{
  "email": "usuario@example.com"
}
```

**Response** (200 OK):

```json
{
  "message": "Se envio el correo de verificacion",
  "verification_link": "https://..." // null si EMAIL_ENABLED=true
}
```

**Errores**:

- `400` - Email ya verificado o datos inválidos

**Notas**:

- En desarrollo (EMAIL deshabilitado), retorna el link de verificación en la respuesta
- En producción (EMAIL habilitado), envía el link por email y retorna null

---

### 2. Verificar Email

```
GET /auth/verify-email?token={token}
```

**Descripción**: Marca el email como verificado usando el token recibido por email.

**Parámetros**:

- `token` (query, obligatorio): Token de verificación enviado por email

**Response** (200 OK):

```json
{
  "message": "Email verificado"
}
```

**Errores**:

- `400` - Token inválido o expirado

---

### 3. Consultar Estado de Email

```
POST /auth/check-email
```

**Descripción**: Verifica el estado de un email y obtiene un token temporal para completar el registro.

**Request**:

```json
{
  "email": "usuario@example.com"
}
```

**Response** (200 OK):

```json
{
  "exists": true,
  "is_verified": true,
  "can_complete_registration": true,
  "registration_token": "eyJhbGc..." // válido por 24 horas
}
```

**Campos de Respuesta**:

- `exists`: Si el email está registrado en el sistema
- `is_verified`: Si el email fue verificado correctamente
- `can_complete_registration`: Si puede proceder a completar el registro
- `registration_token`: Token temporal para usar en `/register/complete` (expira en 24 horas)

**Notas**:

- **OBLIGATORIO**: Este endpoint debe ejecutarse ANTES de `/register/complete` para obtener un token válido
- El token es válido únicamente para el email consultado

---

### 4. Completar Registro (Step 2)

```
POST /auth/register/complete
```

**Descripción**: Completa el perfil de usuario después de verificar el email. Retorna automáticamente un token JWT válido.

**Request**:

```json
{
  "email": "usuario@example.com",
  "registration_token": "eyJhbGc...",
  "password": "SecurePass123!",
  "dni": "12345678",
  "first_name": "Juan",
  "last_name": "Pérez",
  "gender": "M",
  "cuit_cuil": "20123456789",
  "phone": "+543812345678",
  "nationality": "ARG",
  "occupation": "Engineer",
  "marital_status": "Single",
  "location": "Buenos Aires"
}
```

**Requisitos de Contraseña**:

- ✅ Mínimo 8 caracteres, máximo 72
- ✅ Al menos una letra mayúscula (A-Z)
- ✅ Al menos un número (0-9)
- ✅ Al menos un símbolo especial (!@#$%^&\*()\_+-=[]{}...)

**Ejemplos de contraseñas válidas**:

- `SecurePass123!`
- `MyP@ssw0rd`
- `C0mpl3x#Pass`

**Response** (200 OK):

```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "usuario@example.com",
    "first_name": "Juan",
    "last_name": "Pérez",
    "dni": "12345678"
    // ... resto de datos del usuario
  }
}
```

**Errores**:

- `400` - Email no verificado o datos inválidos
- `401` - Token de registro inválido, expirado o email no coincide

**Notas**:

- El `registration_token` se invalida después de establecer la contraseña
- Se genera automáticamente un token JWT de sesión válido por 30 minutos
- El token de registro es válido por 24 horas

---

### 5. Login

```
POST /auth/login
```

**Descripción**: Inicia sesión y retorna un token JWT válido.

**Request**:

```json
{
  "email": "usuario@example.com",
  "password": "SecurePassword123"
}
```

**Response** (200 OK):

```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "usuario@example.com",
    "first_name": "Juan",
    "last_name": "Pérez"
    // ... resto de datos del usuario
  }
}
```

**Errores**:

- `401` - Credenciales inválidas

---

### 6. Obtener Datos Usuario Actual

```
GET /auth/me
```

**Descripción**: Obtiene todos los datos del usuario autenticado.

**Headers**:

```
Authorization: Bearer {access_token}
```

**Response** (200 OK):

```json
{
  "id": "uuid",
  "email": "usuario@example.com",
  "first_name": "Juan",
  "last_name": "Pérez",
  "dni": "12345678",
  "gender": "M",
  "cuit_cuil": "20123456789",
  "phone": "+543812345678",
  "nationality": "ARG",
  "occupation": "Engineer",
  "marital_status": "Single",
  "location": "Buenos Aires"
}
```

**Errores**:

- `401` - No autorizado (token inválido o expirado)

---

### 7. Renovar Token

```
POST /auth/refresh
```

**Descripción**: Renovar el token de acceso usando un token válido.

**Headers**:

```
Authorization: Bearer {access_token}
```

**Response** (200 OK):

```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

**Errores**:

- `401` - Token inválido o expirado

**Notas**:

- El nuevo token es válido por 30 minutos
- Se puede usar cualquier token válido para obtener uno nuevo

---

## Flujo de Autenticación

### Flujo de Registro Completo

```
1. POST /auth/register
   └─> Envía email de verificación
   └─> Retorna link de verificación (solo en desarrollo)

2. GET /auth/verify-email?token={token}
   └─> Usuario hace clic en link o lo proporciona
   └─> Email marcado como verificado

3. POST /auth/check-email
   └─> Consulta estado del email
   └─> Obtiene registration_token (válido 24 horas)

4. POST /auth/register/complete
   └─> Proporciona datos personales y registration_token
   └─> Crea usuario y retorna access_token
   └─> Registration token se invalida
```

### Flujo de Login

```
1. POST /auth/login
   └─> Email + Password
   └─> Retorna access_token + datos usuario

2. Usar token en requests posteriores
   └─> Header: Authorization: Bearer {access_token}
```

### Renovación de Token

```
1. Token válido está próximo a expirar (30 minutos)
   └─> POST /auth/refresh
   └─> Retorna nuevo access_token válido por otros 30 minutos
```

---

## Errores Comunes

### 400 - Email ya verificado o datos inválidos

**Endpoint**: `/auth/register`

**Causas**:

- El email ya está registrado y verificado
- Formato de email inválido
- Email vacío o nulo

**Solución**:

- Usar un email diferente
- Usar `/auth/check-email` para verificar estado del email

---

### 401 - Token de registro inválido o expirado

**Endpoint**: `/auth/register/complete`

**Causas**:

- El registration_token expiró (máximo 24 horas)
- El email proporcionado no coincide con el del token
- El token fue modificado

**Solución**:

- Ejecutar nuevamente `/auth/check-email` para obtener un nuevo registration_token
- Asegurar que el email coincida con el registrado

---

### 400 - Contraseña no cumple requisitos de seguridad

**Endpoint**: `/auth/register/complete`

**Causas**:

- La contraseña no contiene al menos una mayúscula
- La contraseña no contiene al menos un número
- La contraseña no contiene al menos un símbolo especial
- La contraseña es menor a 8 caracteres o mayor a 72

**Solución**:

- Usar una contraseña que cumpla con todos los requisitos: mínimo 8 caracteres, al menos una mayúscula, un número y un símbolo especial
- Ejemplos válidos: `SecurePass123!`, `MyP@ssw0rd`, `C0mpl3x#Pass`

---

### 401 - Credenciales inválidas

**Endpoint**: `/auth/login`

**Causas**:

- Email no existe
- Password incorrecto
- Email no verificado

**Solución**:

- Verificar que el email está correctamente registrado
- Permitir al usuario completar el proceso de verificación si fue interrumpido
- Limpiar credenciales en caché del cliente

---

### 401 - No autorizado (token inválido o expirado)

**Endpoints**: `/auth/me`, `/auth/refresh`

**Causas**:

- Token expirado (después de 30 minutos)
- Token malformado o modificado
- Header Authorization incorrecto

**Solución**:

- Usar `/auth/refresh` para obtener un nuevo token
- Si refresh falla, requerir nuevo login
- Verificar formato del header: `Authorization: Bearer {token}`

---

## Autenticación en Requests

Todos los endpoints que requieren autenticación esperan el siguiente header:

```
Authorization: Bearer {access_token}
```

**Ejemplo con curl**:

```bash
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Ejemplo con curl POST**:

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@example.com",
    "password": "SecurePassword123"
  }'
```

---

## Información de Tokens

### Access Token (JWT)

- **Duración**: 30 minutos
- **Uso**: Autenticación en todos los endpoints protegidos
- **Formato**: JWT Bearer Token
- **Renovación**: POST `/auth/refresh`

### Registration Token

- **Duración**: 24 horas
- **Uso**: Exclusivamente para POST `/auth/register/complete`
- **Validez**: Solo para el email que lo generó
- **Generador**: POST `/auth/check-email`

---

**Última actualización**: Febrero 2026  
**Versión API**: 1.0
