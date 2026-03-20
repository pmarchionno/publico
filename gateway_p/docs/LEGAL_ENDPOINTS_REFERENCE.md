# API Legal Documents Endpoints Reference

# Gateway Payment - Documentos Legales (Términos y Condiciones / Políticas de Privacidad)

Documentación técnica de los endpoints para gestión de documentos legales y aceptaciones de usuarios.

## 📋 Índice

1. [Resumen General](#resumen-general)
2. [Arquitectura](#arquitectura)
3. [Endpoints](#endpoints)
4. [Flujos de Uso](#flujos-de-uso)
5. [Modelos de Datos](#modelos-de-datos)

---

## Resumen General

**Base URL**: `/legal`  
**Autenticación**: Algunos endpoints requieren JWT Bearer Token  
**Contenido**: application/json

### Tipos de Documentos Soportados

- `terms_and_conditions` - Términos y Condiciones
- `privacy_policy` - Política de Privacidad

### Características

✅ Versionado de documentos legales  
✅ Historial completo de aceptaciones por usuario  
✅ Registro de IP y User-Agent para auditoría  
✅ Consulta de estado de cumplimiento legal  
✅ Endpoints públicos para lectura y privados para aceptación

---

## Arquitectura

### Entidades Nuevas

#### 1. **LegalDocumentRecord** (Tabla: `legal_documents`)

Almacena versiones de documentos legales.

| Campo          | Tipo        | Descripción                                |
| -------------- | ----------- | ------------------------------------------ |
| id             | UUID        | ID único del documento                     |
| document_type  | String(32)  | Tipo: terms_and_conditions, privacy_policy |
| version        | String(16)  | Versión del documento (ej: 1.0, 2.1)       |
| title          | String(255) | Título del documento                       |
| content        | Text        | Contenido completo (HTML/texto)            |
| is_active      | Boolean     | Si el documento está activo                |
| effective_date | DateTime    | Fecha desde la cual es efectivo            |
| created_at     | DateTime    | Fecha de creación                          |
| updated_at     | DateTime    | Fecha de actualización                     |

#### 2. **UserLegalAcceptanceRecord** (Tabla: `user_legal_acceptances`)

Registra aceptaciones de documentos por usuarios.

| Campo       | Tipo        | Descripción                                      |
| ----------- | ----------- | ------------------------------------------------ |
| id          | UUID        | ID único de la aceptación                        |
| user_id     | UUID        | ID del usuario (FK a users)                      |
| document_id | UUID        | ID del documento aceptado (FK a legal_documents) |
| accepted_at | DateTime    | Fecha y hora de aceptación                       |
| ip_address  | String(45)  | IP del cliente (IPv4/IPv6)                       |
| user_agent  | String(512) | User agent del navegador/app                     |

---

## Endpoints

### 1. Obtener Términos y Condiciones Actuales

```
GET /legal/terms
```

**Descripción**: Obtiene la versión activa actual de los términos y condiciones.

**Autenticación**: ❌ No requiere (público)

**Response** (200 OK):

```json
{
  "id": "uuid",
  "document_type": "terms_and_conditions",
  "version": "1.0",
  "title": "Términos y Condiciones de Uso",
  "content": "<html>...</html>",
  "is_active": true,
  "effective_date": "2026-01-01T00:00:00Z",
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

**Errores**:

- `404` - No hay términos y condiciones disponibles

---

### 2. Obtener Política de Privacidad Actual

```
GET /legal/privacy
```

**Descripción**: Obtiene la versión activa actual de la política de privacidad.

**Autenticación**: ❌ No requiere (público)

**Response** (200 OK):

```json
{
  "id": "uuid",
  "document_type": "privacy_policy",
  "version": "1.0",
  "title": "Política de Privacidad y Tratamiento de Datos",
  "content": "<html>...</html>",
  "is_active": true,
  "effective_date": "2026-01-01T00:00:00Z",
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

**Errores**:

- `404` - No hay política de privacidad disponible

---

### 3. Listar Todos los Documentos Activos

```
GET /legal/documents
```

**Descripción**: Obtiene lista resumida de todos los documentos legales activos (sin el contenido completo).

**Autenticación**: ❌ No requiere (público)

**Response** (200 OK):

```json
[
  {
    "id": "uuid-1",
    "document_type": "terms_and_conditions",
    "version": "1.0",
    "title": "Términos y Condiciones de Uso",
    "is_active": true,
    "effective_date": "2026-01-01T00:00:00Z"
  },
  {
    "id": "uuid-2",
    "document_type": "privacy_policy",
    "version": "1.0",
    "title": "Política de Privacidad",
    "is_active": true,
    "effective_date": "2026-01-01T00:00:00Z"
  }
]
```

**Uso**: Útil para mostrar al usuario qué documentos debe aceptar.

---

### 4. Aceptar Documento Legal

```
POST /legal/accept
```

**Descripción**: Registra la aceptación de un documento legal por parte del usuario autenticado.

**Autenticación**: ✅ Requiere JWT Bearer Token

**Headers**:

```
Authorization: Bearer {access_token}
```

**Request**:

```json
{
  "document_id": "uuid",
  "ip_address": "192.168.1.1", // Opcional
  "user_agent": "Mozilla/5.0..." // Opcional
}
```

**Response** (201 Created):

```json
{
  "message": "Documento aceptado exitosamente",
  "acceptance": {
    "id": "uuid",
    "user_id": "uuid",
    "document_id": "uuid",
    "accepted_at": "2026-02-10T12:30:00Z",
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "document": {
      "id": "uuid",
      "document_type": "terms_and_conditions",
      "version": "1.0",
      "title": "Términos y Condiciones de Uso",
      "is_active": true,
      "effective_date": "2026-01-01T00:00:00Z"
    }
  }
}
```

**Errores**:

- `401` - No autorizado (token inválido/expirado)
- `404` - Documento no encontrado
- `400` - Documento no está activo

**Notas**:

- Si el usuario ya aceptó el documento, retorna la aceptación existente
- La IP y User-Agent se capturan automáticamente del request HTTP si no se proporcionan
- Útil para auditoría y cumplimiento legal

---

### 5. Consultar Estado Legal del Usuario

```
GET /legal/status
```

**Descripción**: Obtiene el estado de aceptaciones legales del usuario autenticado.

**Autenticación**: ✅ Requiere JWT Bearer Token

**Headers**:

```
Authorization: Bearer {access_token}
```

**Response** (200 OK):

```json
{
  "terms_accepted": true,
  "terms_version": "1.0",
  "terms_accepted_at": "2026-02-10T10:00:00Z",

  "privacy_accepted": true,
  "privacy_version": "1.0",
  "privacy_accepted_at": "2026-02-10T10:05:00Z",

  "current_terms_version": "1.0",
  "current_privacy_version": "1.0",

  "needs_update": false
}
```

**Campos de Respuesta**:

- `terms_accepted`: Si ha aceptado los términos actuales
- `terms_version`: Versión aceptada de términos
- `terms_accepted_at`: Fecha de aceptación
- `privacy_accepted`: Si ha aceptado la política actual
- `privacy_version`: Versión aceptada de política
- `privacy_accepted_at`: Fecha de aceptación
- `current_terms_version`: Versión actual disponible de términos
- `current_privacy_version`: Versión actual disponible de política
- `needs_update`: Si necesita aceptar nuevas versiones

**Errores**:

- `401` - No autorizado

**Uso**: Útil para validar si el usuario puede realizar acciones que requieren cumplimiento legal.

---

### 6. Historial de Aceptaciones del Usuario

```
GET /legal/acceptances
```

**Descripción**: Obtiene el historial completo de todas las aceptaciones del usuario autenticado.

**Autenticación**: ✅ Requiere JWT Bearer Token

**Headers**:

```
Authorization: Bearer {access_token}
```

**Response** (200 OK):

```json
[
  {
    "id": "uuid-1",
    "user_id": "uuid",
    "document_id": "uuid-doc-1",
    "accepted_at": "2026-02-10T10:05:00Z",
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "document": {
      "id": "uuid-doc-1",
      "document_type": "privacy_policy",
      "version": "1.0",
      "title": "Política de Privacidad",
      "is_active": true,
      "effective_date": "2026-01-01T00:00:00Z"
    }
  },
  {
    "id": "uuid-2",
    "user_id": "uuid",
    "document_id": "uuid-doc-2",
    "accepted_at": "2026-02-10T10:00:00Z",
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "document": {
      "id": "uuid-doc-2",
      "document_type": "terms_and_conditions",
      "version": "1.0",
      "title": "Términos y Condiciones",
      "is_active": true,
      "effective_date": "2026-01-01T00:00:00Z"
    }
  }
]
```

**Errores**:

- `401` - No autorizado

**Uso**: Auditoría, trazabilidad, historial de versiones aceptadas por el usuario.

---

## Flujos de Uso

### Flujo 1: Usuario Nuevo Registrándose

```
1. Usuario completa registro en /auth/register/complete

2. Frontend consulta documentos disponibles
   └─> GET /legal/documents
   └─> Obtiene lista de términos y privacidad

3. Frontend muestra documentos al usuario
   └─> GET /legal/terms (para ver contenido completo)
   └─> GET /legal/privacy (para ver contenido completo)

4. Usuario acepta ambos documentos
   └─> POST /legal/accept (document_id: términos)
   └─> POST /legal/accept (document_id: privacidad)

5. Frontend verifica estado
   └─> GET /legal/status
   └─> Confirma needs_update: false
```

### Flujo 2: Usuario Existente - Verificar Cumplimiento

```
1. Usuario inicia sesión
   └─> POST /auth/login

2. Backend/Frontend verifica estado legal
   └─> GET /legal/status
   └─> Revisa needs_update

3. Si needs_update = true:
   └─> GET /legal/documents
   └─> Muestra documentos pendientes
   └─> POST /legal/accept (para cada documento)

4. Permitir continuar solo si needs_update = false
```

### Flujo 3: Nueva Versión de Términos Publicada

```
1. Admin publica nueva versión v2.0 de términos
   └─> Se marca como is_active = true
   └─> Versiones antiguas se desactivan

2. Usuarios existentes con v1.0:
   └─> GET /legal/status retorna:
       - terms_accepted: false
       - terms_version: "1.0" (versión antigua)
       - current_terms_version: "2.0"
       - needs_update: true

3. Al próximo login:
   └─> Frontend detecta needs_update = true
   └─> Muestra nueva versión v2.0
   └─> Usuario debe aceptar para continuar
   └─> POST /legal/accept
```

### Flujo 4: Auditoría y Cumplimiento

```
1. Consultar historial de un usuario
   └─> GET /legal/acceptances
   └─> Muestra todas las versiones aceptadas
   └─> Incluye IP, User-Agent, timestamps

2. Validar si usuario cumple requisitos legales
   └─> GET /legal/status
   └─> Verificar needs_update: false

3. Generar reportes de auditoría
   └─> Consultar tablas user_legal_acceptances
   └─> Filtrar por fecha, documento, usuario
```

---

## Modelos de Datos

### Relaciones

```
UserRecord (users)
  └─> 1:N → UserLegalAcceptanceRecord (user_legal_acceptances)

LegalDocumentRecord (legal_documents)
  └─> 1:N → UserLegalAcceptanceRecord (user_legal_acceptances)
```

### Índices Implementados

**legal_documents**:

- `idx_legal_doc_type_active` (document_type, is_active)
- `idx_legal_doc_type_version` (document_type, version) UNIQUE

**user_legal_acceptances**:

- `idx_user_acceptance_user` (user_id)
- `idx_user_acceptance_document` (document_id)
- `idx_user_acceptance_user_doc` (user_id, document_id)

---

## Ejemplos con curl

### Obtener términos actuales

```bash
curl -X GET "http://localhost:8000/legal/terms"
```

### Aceptar documento (autenticado)

```bash
curl -X POST "http://localhost:8000/legal/accept" \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "uuid-del-documento"
  }'
```

### Consultar estado legal

```bash
curl -X GET "http://localhost:8000/legal/status" \
  -H "Authorization: Bearer eyJhbGc..."
```

### Historial de aceptaciones

```bash
curl -X GET "http://localhost:8000/legal/acceptances" \
  -H "Authorization: Bearer eyJhbGc..."
```

---

## Consideraciones de Seguridad

✅ **Trazabilidad completa**: Cada aceptación registra IP, User-Agent y timestamp  
✅ **Versionado**: Permite rastrear qué versión aceptó cada usuario  
✅ **No eliminación**: Las aceptaciones no se eliminan, solo se agregan nuevas  
✅ **Cascada controlada**: Si se elimina un usuario, sus aceptaciones también se eliminan  
✅ **Auditoría**: Historial completo disponible para cumplimiento legal

---

## Mejores Prácticas

1. **Validar cumplimiento antes de acciones críticas**:
   - Verificar `GET /legal/status` antes de permitir transferencias
   - Requerir aceptación de términos para activar cuenta

2. **Notificar cambios**:
   - Enviar email cuando se publique nueva versión
   - Mostrar banner al usuario indicando `needs_update: true`

3. **No aceptar automáticamente**:
   - Siempre requerir acción explícita del usuario
   - Mostrar el contenido completo antes de aceptar

4. **Registro completo**:
   - Siempre capturar IP y User-Agent
   - Útil para disputas legales y auditorías

---

**Última actualización**: Febrero 2026  
**Versión API**: 1.0  
**Migración requerida**: `20260210_01_add_legal_documents_tables.py`
