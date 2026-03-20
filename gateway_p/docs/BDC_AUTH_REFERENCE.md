# API BDC Integration - Autenticación

# Gateway Payment - Integración con Banco de Comercio

Documentación técnica de la integración con API de Banco de Comercio (BDC).

## 📋 Índice

1. [Resumen General](#resumen-general)
2. [Autenticación](#autenticación)
3. [Endpoints Internos](#endpoints-internos)
4. [Esquemas](#esquemas)
5. [Manejo de Tokens](#manejo-de-tokens)
6. [Flujos](#flujos)

---

## Resumen General

**Proveedor**: Banco de Comercio (BDC)  
**Base URL**: `https://api-homo.bdcconecta.com` (sandbox) / `https://api.bdcconecta.com` (producción)  
**Autenticación**: JWT Bearer Token (obtenido de BDC)  
**Contenido**: application/json

### Características

- 🔐 Autenticación con clientId/clientSecret
- ♻️ Caching automático de tokens con renovación
- 🔄 Reintentos automáticos en caso de token expirado
- 📊 Endpoints para monitoreo de autenticación
- 🛡️ Manejo de errores robusto

---

## Autenticación

### Flujo de Autenticación (Backend)

El sistema de autenticación está diseñado para ser transparente:

```
1. Primera solicitud de transferencia
   └─> Backend necesita token
   └─> Servicio BDCAuthService verifica cache

2. Si no hay token o está expirado
   └─> Servicio solicita nuevo token a BDC
   └─> POST /auth (a BDC API)
   └─> Recibe accessToken y expiresIn

3. Token se cachea en memoria
   └─> Próximas solicitudes usan el token cacheado

4. Cuando expire
   └─> Automático: se obtiene uno nuevo
   └─> Manual: POST /bdc/auth/refresh (nuestro endpoint)
```

### Request de Autenticación a BDC

```
POST https://api-homo.bdcconecta.com/auth
Content-Type: application/json

{
  "clientId": "1111",
  "clientSecret": "2222"
}
```

**Headers de BDC**:

```
access-control-allow-origin: *
cache-control: no-cache, private
connection: keep-alive
content-encoding: gzip
content-length: 192
content-type: application/json
date: Tue, 10 Feb 2026 18:06:38 GMT
x-ratelimit-limit: 60
x-ratelimit-remaining: 59
```

### Response de Autenticación BDC

```json
{
  "statusCode": 0,
  "message": "Token generado correctamente.",
  "data": {
    "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "expiresIn": 3600
  },
  "time": "Tue, 10 Feb 2026 18:06:38 +0000"
}
```

---

## Endpoints Internos

### 1. Obtener Estado de Autenticación BDC

```
GET /bdc/auth/status
```

**Descripción**: Verifica el estado actual de autenticación con BDC (información de cache).

**Autenticación**: ✅ Requiere JWT Bearer Token

**Response** (200 OK):

```json
{
  "status": "ok",
  "bdc_auth": {
    "cached": true,
    "created_at": "2026-02-10T18:06:38+00:00",
    "expires_at": "2026-02-10T19:06:38+00:00",
    "expires_in_seconds": 3599,
    "is_expired": false,
    "is_expiring_soon": false
  },
  "user_id": "uuid-del-usuario"
}
```

**Información retornada**:

- `cached`: Si hay token en cache
- `created_at`: Cuándo se obtuvo el token
- `expires_at`: Cuándo expira
- `expires_in_seconds`: Segundos restantes
- `is_expired`: Si ya pasó la fecha de expiración
- `is_expiring_soon`: Si está próximo a expirar (buffer 60s)

**Uso**: Debugging, monitoreo, verificar si es necesario renovar.

---

### 2. Renovar Token BDC

```
POST /bdc/auth/refresh
```

**Descripción**: Fuerza la renovación del token de autenticación con BDC.

**Autenticación**: ✅ Requiere JWT Bearer Token

**Response** (200 OK):

```json
{
  "status": "refreshed",
  "message": "Token de BDC renovado exitosamente",
  "cache_info": {
    "cached": true,
    "created_at": "2026-02-10T18:10:00+00:00",
    "expires_at": "2026-02-10T19:10:00+00:00",
    "expires_in_seconds": 3600,
    "is_expired": false,
    "is_expiring_soon": false
  }
}
```

**Cuándo usar**:

- Después de recibir errores de autenticación
- Antes de operaciones críticas
- Forzar token fresco (aunque normalmente es automático)

**Errores**:

- `500` - Error al conectar con BDC

---

### 3. Verificar Conectividad con BDC

```
GET /bdc/health
```

**Descripción**: Verifica que BDC está operativo intentando obtener un token.

**Autenticación**: ❌ No requiere (público)

**Response** (200 OK):

```json
{
  "status": "ok",
  "message": "Conectividad con BDC OK",
  "has_cached_token": true
}
```

**Response** (503 Service Unavailable):

```json
{
  "detail": "No se puede conectar con BDC: Connection error..."
}
```

**Uso**: Health checks, monitoreo de disponibilidad de BDC.

---

### 4. Verificar Salud de BDC (Health Check)

```
GET /bdc/healthcheck
```

**Descripción**: Consulta el endpoint de healthcheck de BDC para verificar su estado y disponibilidad operativa.

**Autenticación**: ❌ No requiere (público)

**Response** (200 OK):

```json
{
  "statusCode": 0,
  "time": "2026-02-10T14:30:25.123Z"
}
```

**Response** (503 Service Unavailable):

```json
{
  "detail": "No se puede conectar con BDC: Connection error..."
}
```

**Cuándo usar**:

- Verificar que BDC está operativo
- Monitoreo continuo de disponibilidad
- Debugging de conectividad
- Alertas de uptime

---

### 5. Verificar Salud de BDC con Detalles (Autenticado)

```
GET /bdc/healthcheck-detailed
```

**Descripción**: Consulta el healthcheck de BDC incluyendo información detallada del token cacheado.

**Autenticación**: ✅ Requiere JWT válido

**Headers**:

```
Authorization: Bearer {access_token}
```

**Response** (200 OK):

```json
{
  "bdc_healthcheck": {
    "statusCode": 0,
    "time": "2026-02-10T14:30:25.123Z"
  },
  "cache_info": {
    "has_token": true,
    "expires_in_seconds": 1842,
    "is_expiring_soon": false
  },
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response** (401 Unauthorized):

```json
{
  "detail": "No hay token de autenticación o es inválido"
}
```

**Response** (503 Service Unavailable):

```json
{
  "detail": "No se puede conectar con BDC: Connection error..."
}
```

**Cuándo usar**:

- Admin/staff verifica estado detallado
- Debugging de token caching
- Monitoreo interno de salud
- Verificar tiempo restante de token
- Identificar necesidad de refresh

---

## Esquemas

### BDCAuthRequest

```python
{
  "clientId": str,       # ID del cliente BDC
  "clientSecret": str    # Secret del cliente BDC
}
```

### BDCAuthResponse

```python
{
  "accessToken": str,    # JWT token
  "expiresIn": int       # Segundos hasta expiración
}
```

### BDCResponse (Genérico)

```python
{
  "statusCode": int,           # 0 = éxito, otro = error
  "message": str,              # Mensaje descriptivo
  "data": dict,                # Datos de respuesta (variable)
  "time": str                  # Timestamp del servidor
}
```

### BDCTokenCache (Interno)

```python
{
  "access_token": str,         # Token JWT
  "expires_at": datetime,      # Cuándo expira
  "created_at": datetime,      # Cuándo se obtuvo

  # Métodos
  is_expired() -> bool         # ¿Ya expiró?
  is_expiring_soon(buffer=60) -> bool  # ¿Por expirar?
}
```

### BDCHealthcheckResponse

```python
{
  "statusCode": int,    # 0 = operativo, otro = error
  "time": str           # Timestamp del servidor BDC (ISO 8601)
}
```

### TokenCacheInfo (Cache Status)

```python
{
  "has_token": bool,              # ¿Hay token en cache?
  "expires_in_seconds": int|null, # Segundos restantes (null si no hay token)
  "is_expiring_soon": bool        # ¿Próximo a expirar en 60 segundos?
}
```

### HealthcheckDetailedResponse

```python
{
  "bdc_healthcheck": BDCHealthcheckResponse,  # Respuesta de BDC
  "cache_info": TokenCacheInfo,               # Estado del cache local
  "user_id": str                              # ID del usuario autenticado
}
```

---

## Manejo de Tokens

### Caching Automático

El servicio `BDCAuthService` maneja automáticamente:

1. **Cache en memoria**: Token se almacena en cache
2. **Validación de expiración**: Verifica si el token sigue siendo válido
3. **Buffer de renovación**: Renueva 60 segundos antes de expirar
4. **Invalidación manual**: `invalidate_cache()` en caso de error 401

### Flujo de Obtención de Token

```python
async def get_token() -> str:
    # 1. Verificar cache
    if cache_válido_y_no_próximo_a_expirar():
        return cache.access_token  # Retornar token cacheado

    # 2. Token no existe o está por expirar
    token = await _refresh_token()  # Solicitar a BDC
    return token
```

### Reintentos Automáticos

Si el conector recibe un **401** (Unauthorized):

```python
if response.status_code == 401:
    auth_service.invalidate_cache()  # Invalidar token
    token = await auth_service.get_token()  # Obtener uno nuevo
    # Reintentar request original
```

---

## Flujos

### Flujo 1: Primera Transferencia (Sin Token)

```
1. Usuario solicita transferencia
   └─> POST /payments/transfer

2. Backend (conector BDC) necesita token
   └─> Llama BDCAuthService.get_token()
   └─> No hay token en cache

3. Servicio obtiene nuevo token
   └─> POST /auth (a BDC)
   └─> Recibe accessToken con expiresIn=3600
   └─> Cachea token

4. Conector usa token
   └─> POST /movements/transfer-request (a BDC)
   └─> Con Authorization: Bearer {token}
   └─> Con X-SIGNATURE calculado

5. BDC procesa transferencia
   └─> Retorna statusCode: 0 (éxito)
```

### Flujo 2: Segunda Transferencia (Token Cacheado)

```
1. Usuario solicita otra transferencia
   └─> POST /payments/transfer

2. Conector necesita token
   └─> Llama BDCAuthService.get_token()

3. Servicio verifica cache
   └─> Token existe y es válido
   └─> NO próximo a expirar
   └─> Retorna token cacheado inmediatamente
   └─> Sin request a BDC AUTH

4. Conector usa token
   └─> POST /movements/transfer-request (a BDC)
   └─> Transferencia procesada
```

### Flujo 3: Token Expirado

```
1. Múltiples transferencias a lo largo del día

2. Después de 1 hora (3600 segundos)
   └─> Token caduca

3. Nueva transferencia solicita token
   └─> Servicio verifica cache
   └─> Token expirado o próximo a expirar

4. Automático
   └─> Obtiene nuevo token de BDC
   └─> Actualiza cache
   └─> Continúa normal

5. Usuario no se percata del refresh
   └─> Es transparente
```

### Flujo 4: Error 401 (Token Rechazado)

```
1. Transferencia con token cacheado
   └─> Conector envía request
   └─> BDC rechaza: 401 Unauthorized

2. Conector detecta 401
   └─> Invalida cache
   └─> Obtiene nuevo token
   └─> Reintenta request original

3. Con nuevo token
   └─> Transferencia se procesa
```

### Flujo 5: Monitoreo Manual

```
1. Admin verifica estado
   └─> GET /bdc/auth/status
   └─> Obtiene info de cache

2. Si necesario, renovar
   └─> POST /bdc/auth/refresh
   └─> Fuerza obtención de nuevo token

3. Próximo request usa token fresco
   └─> Transferencias sin issues
```

---

## Consideraciones de Seguridad

### ✅ Implementado

- ✅ Credentials seguros en `settings.py` (no en código)
- ✅ Tokens en cache en memoria (no persistidos)
- ✅ Buffer de renovación (60s antes de expirar)
- ✅ Reintentos automáticos en 401
- ✅ Logs de auditoría
- ✅ Invalidación manual de cache

### 📋 Pendiente (Producción)

- [ ] Encriptación de tokens en cache
- [ ] Almacenamiento seguro de credentials (secrets manager)
- [ ] Monitoring y alertas de fallos de autenticación
- [ ] Rate limiting para renovaciones
- [ ] Rotación de credentials cada X días

---

## Mejores Prácticas

1. **No manejar tokens manualmente**
   - El servicio se encarga automáticamente
   - Solo usar `get_token()` internamente

2. **Monitorear fallos**
   - Revisar logs de `app.core.bdc.auth`
   - Verificar `/bdc/health` regularmente

3. **En caso de error 401**
   - No reintentar manualmente (conector lo hace)
   - Revisar credenciales en settings.py

4. **Para debugging**
   - Usar GET `/bdc/auth/status` para ver cache
   - POST `/bdc/auth/refresh` para forzar token fresco

---

**Última actualización**: Febrero 2026  
**Versión API**: 1.0  
**Proveedor**: Banco de Comercio (BDC)
