# API KYC Endpoints Reference

# Gateway Payment - Verificación de Identidad (KYC)

Documentación técnica de los endpoints para verificación de identidad de usuarios mediante integración con Didit.

## 📋 Índice

1. [Resumen General](#resumen-general)
2. [Integración con Didit](#integración-con-didit)
3. [Endpoints](#endpoints)
4. [Flujos de Verificación](#flujos-de-verificación)
5. [Códigos de Error](#códigos-de-error)

---

## Resumen General

**Base URL**: `/kyc`  
**Proveedor**: Didit (plataforma de verificación de identidad)  
**Autenticación**: API Key configurada en backend  
**Contenido**: application/json, multipart/form-data

### Métodos de Verificación

- ✅ **Sesión de Verificación**: Flujo completo guiado (iframe o redirect)
- ✅ **Verificación Directa**: Upload de documentos sin interfaz Didit

---

## Integración con Didit

### Variables de Configuración (settings.py)

```python
DIDIT_BASE_URL = "https://api.didit.me/v1"  # Base URL de Didit API
DIDIT_API_KEY = "your-api-key"              # API Key de Didit
DIDIT_WORKFLOW_ID = "workflow-id"           # ID del flujo de verificación
DIDIT_CALLBACK_URL = "https://..."          # URL de callback post-verificación
```

### Características de Didit

- 🔐 Verificación de documentos de identidad
- 📸 Detección de vida (liveness)
- 🎯 Validación de edad mínima
- 📋 Extracción de datos personales
- 🌐 Soporte multi-país
- 🔄 Webhooks para notificación de resultados

---

## Endpoints

### 1. Estado del Módulo KYC

```
GET /kyc/
```

**Descripción**: Verifica que el módulo KYC está operativo.

**Autenticación**: ❌ No requiere

**Response** (200 OK):

```json
{
  "message": "KYC module"
}
```

**Uso**: Health check del módulo.

---

### 2. Crear Sesión de Verificación

```
POST /kyc/session
```

**Descripción**: Crea una sesión de verificación con Didit para iniciar el proceso de KYC guiado.

**Autenticación**: ⚠️ Planeado (actualmente sin autenticación)

**Content-Type**: `multipart/form-data`

**Parámetros (Form Data)**:

```
isIframe: boolean (opcional, default: false)
  - true: Modo iframe embebido
  - false: Modo redirect con callback

vendor_data: string (requerido)
  - Dato para asociar con la verificación (e.g., email del usuario)
  - Útil para vincular la verificación con el usuario en tu sistema
```

**Request (ejemplo con curl)**:

```bash
curl -X POST "http://localhost:8000/kyc/session" \
  -F "isIframe=false" \
  -F "vendor_data=user@example.com"
```

**Response** (201 Created):

```json
{
  "session_id": "sess_abc123...",
  "verification_url": "https://app.didit.me/verify/sess_abc123...",
  "expires_at": "2026-02-10T15:30:00Z",
  "workflow_id": "wf_xyz789"
}
```

**Errores**:

- `400` - vendor_data faltante
- `500` - Error al comunicarse con Didit API

**Notas**:

- **Modo iframe** (`isIframe=true`):
  - No incluye callback URL
  - La verificación se completa en el iframe
  - Requiere polling o eventos del frontend
- **Modo redirect** (`isIframe=false`):
  - Incluye callback URL configurada
  - Usuario es redirigido tras completar verificación
  - Didit notifica resultado via webhook al callback

**Flujo**:

1. Backend crea sesión con Didit
2. Frontend recibe `verification_url`
3. Usuario completa verificación en Didit
4. Didit notifica resultado al callback (si modo redirect)

---

### 3. Resetear Verificación

```
POST /kyc/reset
```

**Descripción**: Resetea el estado de verificación de un usuario.

**Autenticación**: ⚠️ Planeado (actualmente sin autenticación)

**Response** (200 OK):

```json
{
  "message": "Verification status reset"
}
```

**Errores**:

- `500` - Error al resetear verificación

**Notas**:

- ⚠️ **TODO**: Implementar conexión con base de datos
- Actualmente retorna mensaje de éxito sin persistencia
- En producción debería actualizar estado en tabla `user_kyc_status`

---

### 4. Verificación de Documento de Identidad (Standalone)

```
POST /kyc/id-verification
```

**Descripción**: Verifica un documento de identidad mediante upload directo de imágenes, sin pasar por el flujo de sesión de Didit.

**Autenticación**: ⚠️ Planeado (actualmente sin autenticación)

**Content-Type**: `multipart/form-data`

**Parámetros (Form Data)**:

| Parámetro                   | Tipo    | Requerido              | Descripción                            |
| --------------------------- | ------- | ---------------------- | -------------------------------------- |
| `front_image`               | File    | ✅ Sí                  | Imagen frontal del documento (max 5MB) |
| `back_image`                | File    | ❌ Opcional            | Imagen trasera del documento (max 5MB) |
| `perform_document_liveness` | Boolean | ❌ No (default: false) | Detectar si es copia de pantalla       |
| `minimum_age`               | Integer | ❌ Opcional            | Edad mínima requerida (1-120)          |
| `vendor_data`               | String  | ✅ Sí                  | Dato para asociar con verificación     |

**Formatos de Imagen Aceptados**:

- JPEG (`image/jpeg`)
- PNG (`image/png`)
- WebP (`image/webp`)
- TIFF (`image/tiff`)
- PDF (`application/pdf`)

**Tamaño Máximo**: 5 MB por archivo

**Request (ejemplo con curl)**:

```bash
curl -X POST "http://localhost:8000/kyc/id-verification" \
  -F "front_image=@dni_frente.jpg" \
  -F "back_image=@dni_dorso.jpg" \
  -F "perform_document_liveness=true" \
  -F "minimum_age=18" \
  -F "vendor_data=user@example.com"
```

**Response** (200 OK):

```json
{
  "verification_id": "ver_abc123",
  "status": "approved",
  "extracted_data": {
    "full_name": "Juan Pérez",
    "document_number": "12345678",
    "date_of_birth": "1990-05-15",
    "age": 35,
    "nationality": "AR",
    "document_type": "DNI",
    "expiry_date": "2030-12-31"
  },
  "checks": {
    "document_authentic": true,
    "document_liveness": true,
    "age_verification": true,
    "data_consistency": true
  },
  "vendor_data": "user@example.com"
}
```

**Response** (200 OK - Rechazado):

```json
{
  "verification_id": "ver_abc123",
  "status": "declined",
  "reason": "Edad insuficiente",
  "extracted_data": {
    "age": 16
  },
  "checks": {
    "age_verification": false
  },
  "vendor_data": "user@example.com"
}
```

**Errores**:

- `400` - Formato de archivo inválido
- `400` - Archivo excede 5MB
- `400` - vendor_data faltante
- `500` - Error al procesar verificación

**Validaciones**:

- ✅ Tipo de archivo permitido
- ✅ Tamaño máximo 5MB
- ✅ vendor_data requerido
- ✅ minimum_age entre 1-120 (si se especifica)

**Características**:

- 🔍 Extracción automática de datos del documento
- 🎭 Detección de liveness (documento no es foto de pantalla)
- 🎂 Verificación de edad mínima
- 🔐 Validación de autenticidad del documento
- 🌍 Soporte multi-país

---

## Flujos de Verificación

### Flujo 1: Verificación con Sesión (Recomendado)

```
1. Frontend solicita crear sesión
   └─> POST /kyc/session
       - vendor_data: email del usuario
       - isIframe: false (o true para iframe)

2. Backend crea sesión en Didit
   └─> Retorna verification_url

3. Frontend redirige usuario a verification_url
   └─> Usuario completa flujo en Didit:
       • Selecciona país y tipo de documento
       • Toma foto de documento (frente y dorso)
       • Captura selfie con liveness
       • Didit valida en tiempo real

4. Usuario completa verificación
   └─> Didit envía resultado al callback (webhook)
   └─> Backend procesa resultado y actualiza BD

5. Frontend consulta estado del usuario
   └─> GET /auth/me (incluir campo kyc_status)
   └─> Muestra estado: "verified", "pending", "failed"
```

**Ventajas**:

- ✅ UX completa con UI profesional de Didit
- ✅ Liveness check automático (selfie)
- ✅ Guía paso a paso para el usuario
- ✅ Menor carga en tu backend
- ✅ Notificación automática via webhook

---

### Flujo 2: Verificación Directa (Standalone)

```
1. Usuario captura/selecciona fotos en tu app
   └─> Frontend valida tamaño y formato

2. Frontend envía documentos
   └─> POST /kyc/id-verification
       - front_image: foto frente
       - back_image: foto dorso
       - perform_document_liveness: true
       - minimum_age: 18
       - vendor_data: email

3. Backend procesa con Didit
   └─> Valida documento
   └─> Extrae datos
   └─> Verifica edad

4. Backend retorna resultado inmediatamente
   └─> Frontend procesa resultado
   └─> Actualiza estado del usuario en BD

5. Si aprobado:
   └─> Permitir continuar con proceso
   └─> Actualizar perfil con datos extraídos
```

**Ventajas**:

- ✅ Integración más simple
- ✅ Control total del flujo
- ✅ Resultados inmediatos (no callback)
- ✅ Menos pasos para el usuario

**Desventajas**:

- ❌ No incluye selfie/liveness automático
- ❌ Debes implementar UI de captura
- ❌ Mayor responsabilidad en validaciones frontend

---

### Flujo 3: Verificación en Iframe

```
1. Frontend solicita sesión con iframe
   └─> POST /kyc/session
       - isIframe: true
       - vendor_data: email

2. Frontend muestra iframe con verification_url
   └─> Usuario completa verificación embebida

3. Frontend detecta finalización
   └─> Via postMessage de Didit
   └─> O polling a tu API

4. Frontend consulta resultado
   └─> GET /kyc/status/{user_id}
   └─> Procesa resultado y continúa
```

**Ventajas**:

- ✅ Usuario no sale de tu aplicación
- ✅ UX más integrada
- ✅ Control del contexto

**Desventajas**:

- ❌ Requiere manejo de eventos iframe
- ❌ Puede tener problemas en mobile
- ❌ No hay callback automático

---

## Códigos de Error

### 400 - Bad Request

**Endpoint**: `/kyc/session`

```json
{
  "detail": "vendor_data is required"
}
```

**Solución**: Proporcionar vendor_data en el form data.

---

**Endpoint**: `/kyc/id-verification`

```json
{
  "detail": "Invalid front_image format. Allowed: JPEG, PNG, WebP, TIFF, PDF"
}
```

**Solución**: Usar formato de archivo permitido.

---

```json
{
  "detail": "front_image exceeds 5MB limit"
}
```

**Solución**: Reducir tamaño del archivo a máximo 5MB.

---

### 500 - Internal Server Error

**Endpoint**: `/kyc/session`

```json
{
  "detail": "An error occurred"
}
```

**Causas**:

- Error de conexión con Didit API
- API Key inválida
- Workflow ID incorrecto
- Didit API caída

**Solución**:

- Verificar configuración en settings.py
- Revisar logs del servidor
- Consultar status de Didit API

---

**Endpoint**: `/kyc/id-verification`

```json
{
  "detail": "Failed to process ID verification: ..."
}
```

**Causas**:

- Error al comunicarse con Didit
- Imagen corrupta o ilegible
- Formato de archivo problemático

**Solución**:

- Revisar calidad de imagen
- Intentar con otra foto
- Revisar logs para detalles

---

## Estructura de Respuesta de Didit

### Estados de Verificación

| Estado      | Descripción             |
| ----------- | ----------------------- |
| `pending`   | Verificación en proceso |
| `approved`  | Verificación exitosa    |
| `declined`  | Verificación rechazada  |
| `expired`   | Sesión expirada         |
| `cancelled` | Usuario canceló         |

### Datos Extraídos del Documento

```json
{
  "full_name": "Juan Carlos Pérez García",
  "document_number": "DNI 12345678",
  "date_of_birth": "1990-05-15",
  "age": 35,
  "nationality": "AR",
  "document_type": "DNI",
  "expiry_date": "2030-12-31",
  "address": "Calle Falsa 123, Buenos Aires",
  "gender": "M"
}
```

### Checks de Validación

```json
{
  "document_authentic": true, // Documento es auténtico
  "document_liveness": true, // No es foto de pantalla
  "age_verification": true, // Cumple edad mínima
  "data_consistency": true, // Datos consistentes
  "face_match": true, // Selfie coincide con documento
  "document_readable": true // Documento legible
}
```

---

## Configuración del Webhook (Callback)

Para recibir notificaciones automáticas de Didit, configura un endpoint:

```python
@router.post("/kyc/webhook")
async def didit_webhook(request: Request):
    """
    Recibe notificaciones de Didit sobre verificaciones completadas
    """
    # Validar firma del webhook
    signature = request.headers.get("X-Didit-Signature")

    # Leer payload
    payload = await request.json()

    # Procesar resultado
    verification_id = payload.get("verification_id")
    status = payload.get("status")
    vendor_data = payload.get("vendor_data")
    extracted_data = payload.get("extracted_data")

    # Actualizar estado del usuario en BD
    # user = await update_user_kyc_status(vendor_data, status, extracted_data)

    return {"received": True}
```

**URL de Webhook en Didit**:

```
https://tu-dominio.com/kyc/webhook
```

---

## Consideraciones de Seguridad

### ⚠️ Pendientes de Implementación

1. **Autenticación de Usuarios**:
   - Todos los endpoints KYC deben requerir JWT token
   - Solo el usuario autenticado puede iniciar su verificación
   - Implementar: `current_user = Depends(get_current_user)`

2. **Validación de Webhook**:
   - Verificar firma de Didit en webhook
   - Prevenir webhook spoofing
   - Usar HTTPS en producción

3. **Persistencia de Datos**:
   - Crear tabla `user_kyc_verifications`
   - Almacenar resultados de verificación
   - Vincular verification_id con user_id

4. **Rate Limiting**:
   - Limitar intentos de verificación por usuario
   - Prevenir abuso de la API

### ✅ Implementadas

- ✅ Validación de tipos de archivo
- ✅ Validación de tamaño de archivo (5MB)
- ✅ Validación de vendor_data requerido
- ✅ API Key segura en backend

---

## Mejores Prácticas

### Para Integración Segura

1. **Usar Sesión de Verificación** (flujo recomendado):
   - Mejor UX con interfaz de Didit
   - Incluye liveness automático
   - Menor carga en tu backend

2. **Almacenar Resultados**:
   - Guardar `verification_id` de Didit
   - Persistir datos extraídos relevantes
   - Mantener historial de intentos

3. **Validar Edad**:
   - Siempre especificar `minimum_age` según requerimientos legales
   - En Argentina: típicamente 18 años para servicios financieros

4. **Manejo de Errores**:
   - Permitir al usuario reintentar con mejores fotos
   - Proporcionar feedback claro sobre qué falló
   - Ofrecer soporte humano para casos complejos

5. **Cumplimiento Legal**:
   - Implementar políticas de retención de datos
   - Informar al usuario qué datos se capturan
   - Obtener consentimiento explícito

---

## Ejemplos de Implementación

### Frontend React - Iniciar Verificación

```javascript
async function startKYCVerification(userEmail) {
  const formData = new FormData();
  formData.append("isIframe", "false");
  formData.append("vendor_data", userEmail);

  const response = await fetch("/kyc/session", {
    method: "POST",
    body: formData,
  });

  const data = await response.json();

  // Redirigir al usuario
  window.location.href = data.verification_url;
}
```

### Frontend React - Upload Documento

```javascript
async function uploadIDDocument(frontFile, backFile, userEmail) {
  const formData = new FormData();
  formData.append("front_image", frontFile);
  formData.append("back_image", backFile);
  formData.append("perform_document_liveness", "true");
  formData.append("minimum_age", "18");
  formData.append("vendor_data", userEmail);

  const response = await fetch("/kyc/id-verification", {
    method: "POST",
    body: formData,
  });

  const result = await response.json();

  if (result.status === "approved") {
    console.log("Verificación aprobada:", result.extracted_data);
    // Continuar con el proceso
  } else {
    console.log("Verificación rechazada:", result.reason);
    // Mostrar error al usuario
  }
}
```

---

## Roadmap

### Próximas Implementaciones

- [ ] Autenticación JWT en todos los endpoints
- [ ] Tabla de base de datos para almacenar verificaciones
- [ ] Endpoint GET `/kyc/status` para consultar estado
- [ ] Webhook endpoint con validación de firma
- [ ] Rate limiting por usuario
- [ ] Logs de auditoría de verificaciones
- [ ] Integración con tabla de usuarios
- [ ] Notificaciones por email de resultados
- [ ] Panel admin para revisar verificaciones

---

**Última actualización**: Febrero 2026  
**Versión API**: 1.0  
**Proveedor**: Didit (https://didit.me)
