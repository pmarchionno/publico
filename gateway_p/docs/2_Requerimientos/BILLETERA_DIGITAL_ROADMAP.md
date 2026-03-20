# Billetera Digital - Requerimientos y Hoja de Ruta

## Documento de Análisis y Planificación
**Fecha:** 7 de febrero de 2026  
**Proyecto:** Pagoflex Middleware - Billetera Digital  
**Audiencia:** Jefe de Desarrollo y Equipo Técnico

---

## Índice

1. [Requerimientos Funcionales](#1-requerimientos-funcionales)
   - 1.1 [Gestión de Usuarios](#11-gestión-de-usuarios)
   - 1.2 [KYC (Know Your Customer)](#12-kyc-know-your-customer)
   - 1.3 [Gestión de Cuentas/Wallets](#13-gestión-de-cuentaswallets)
   - 1.4 [Operaciones de Transferencia](#14-operaciones-de-transferencia)
   - 1.5 [Historial y Consultas](#15-historial-y-consultas)
   - 1.6 [Notificaciones](#16-notificaciones)
   - 1.7 [Administración (Backoffice)](#17-administración-backoffice)

2. [Requerimientos No Funcionales](#2-requerimientos-no-funcionales)
   - 2.1 [Seguridad](#21-seguridad)
   - 2.2 [Performance](#22-performance)
   - 2.3 [Compliance y Regulación](#23-compliance-y-regulación)
   - 2.4 [Monitoreo y Observabilidad](#24-monitoreo-y-observabilidad)

3. [Estado Actual del Proyecto](#3-estado-actual-del-proyecto)
   - 3.1 [Infraestructura](#31-infraestructura--implementado)
   - 3.2 [Funcionalidades Existentes](#32-funcionalidades-existentes)

4. [Hoja de Ruta Propuesta](#4-hoja-de-ruta-propuesta)
   - [Fase 1: Fundamentos](#fase-1-fundamentos-4-6-semanas)
   - [Fase 2: Operaciones Core](#fase-2-operaciones-core-4-6-semanas)
   - [Fase 3: Experiencia y Seguridad](#fase-3-experiencia-y-seguridad-3-4-semanas)
   - [Fase 4: Backoffice y Polish](#fase-4-backoffice-y-polish-3-4-semanas)

5. [Arquitectura Propuesta](#5-arquitectura-propuesta)
   - 5.1 [Estructura de Base de Datos](#51-estructura-de-base-de-datos)
   - 5.2 [Servicios y Capas](#52-servicios-y-capas)
   - 5.3 [Patrones de Diseño](#53-patrones-de-diseño)

6. [Stack Tecnológico](#6-stack-tecnológico)

7. [Estimación de Esfuerzo](#7-estimación-de-esfuerzo)

8. [Riesgos y Mitigaciones](#8-riesgos-y-mitigaciones)

9. [Métricas de Éxito](#9-métricas-de-éxito)

10. [Próximos Pasos Inmediatos](#10-próximos-pasos-inmediatos)

11. [Consideraciones Finales](#11-consideraciones-finales)

[Apéndices](#apéndices)

---

## 1. REQUERIMIENTOS FUNCIONALES

### 1.1 Gestión de Usuarios

#### Registro de Usuario
- **REQ-USER-001**: Sistema de registro con email y contraseña
- **REQ-USER-002**: Validación de email mediante código de verificación
- **REQ-USER-003**: Validación de fortaleza de contraseña (mínimo 8 caracteres, mayúsculas, números, símbolos)
- **REQ-USER-004**: Captura de datos personales básicos: nombre completo, fecha de nacimiento, documento de identidad
- **REQ-USER-005**: Aceptación de términos y condiciones
- **REQ-USER-006**: Política de privacidad y tratamiento de datos

#### Autenticación y Seguridad
- **REQ-AUTH-001**: Login con email y contraseña
- **REQ-AUTH-002**: Tokens JWT con expiración (access token + refresh token)
- **REQ-AUTH-003**: Logout y revocación de tokens
- **REQ-AUTH-004**: Recuperación de contraseña mediante email
- **REQ-AUTH-005**: Cambio de contraseña (usuario logueado)
- **REQ-AUTH-006**: Autenticación de dos factores (2FA) - OTP por email/SMS (opcional fase 2)
- **REQ-AUTH-007**: Bloqueo de cuenta después de N intentos fallidos
- **REQ-AUTH-008**: Sesiones concurrentes limitadas

#### Perfil de Usuario
- **REQ-PROFILE-001**: Consultar datos del perfil
- **REQ-PROFILE-002**: Actualizar datos personales
- **REQ-PROFILE-003**: Cambiar email (con verificación)
- **REQ-PROFILE-004**: Historial de actividad/auditoría

### 1.2 KYC (Know Your Customer)

- **REQ-KYC-001**: Integración con proveedor de verificación de identidad ✅ **(IMPLEMENTADO - Didit)**
- **REQ-KYC-002**: Captura de documento de identidad (DNI/Pasaporte)
- **REQ-KYC-003**: Selfie con liveness detection
- **REQ-KYC-004**: Estados de verificación: PENDING, IN_REVIEW, APPROVED, REJECTED
- **REQ-KYC-005**: Webhook para actualización de estado KYC ✅ **(PARCIALMENTE - webhook.py)**
- **REQ-KYC-006**: Re-verificación periódica (compliance)
- **REQ-KYC-007**: Límites de transacción según nivel de verificación

### 1.3 Gestión de Cuentas/Wallets

#### Cuenta Virtual
- **REQ-WALLET-001**: Creación automática de cuenta al registrarse
- **REQ-WALLET-002**: Identificador único de cuenta (UUID o número de cuenta)
- **REQ-WALLET-003**: Soporte multi-moneda (ARS, USD, etc.)
- **REQ-WALLET-004**: Consulta de saldo disponible
- **REQ-WALLET-005**: Consulta de saldo retenido/pendiente
- **REQ-WALLET-006**: Estado de cuenta: ACTIVE, SUSPENDED, CLOSED

#### Cuentas Bancarias Vinculadas
- **REQ-BANK-001**: Vincular cuenta bancaria (CBU/CVU)
- **REQ-BANK-002**: Validación de titularidad de cuenta
- **REQ-BANK-003**: Múltiples cuentas bancarias por usuario
- **REQ-BANK-004**: Eliminar/desvincular cuenta bancaria

### 1.4 Operaciones de Transferencia

#### Carga de Fondos (Depósito)
- **REQ-DEPOSIT-001**: Transferencia desde cuenta bancaria a billetera
- **REQ-DEPOSIT-002**: Generación de CBU/CVU virtual para recibir transferencias
- **REQ-DEPOSIT-003**: Webhook de notificación de depósito recibido
- **REQ-DEPOSIT-004**: Acreditación automática de fondos
- **REQ-DEPOSIT-005**: Límites diarios/mensuales de carga

#### Transferencias entre Usuarios (P2P)
- **REQ-P2P-001**: Transferir dinero a otro usuario de la plataforma
- **REQ-P2P-002**: Búsqueda de destinatario por email, alias, número de cuenta
- **REQ-P2P-003**: Confirmación antes de ejecutar transferencia
- **REQ-P2P-004**: Comisión por transferencia (configurable)
- **REQ-P2P-005**: Notificación push/email a ambas partes
- **REQ-P2P-006**: Descripción/concepto de la transferencia
- **REQ-P2P-007**: Límites por transacción según nivel KYC

#### Retiro de Fondos (Withdrawal)
- **REQ-WITHDRAW-001**: Transferencia desde billetera a cuenta bancaria ✅ **(PARCIALMENTE - transfers endpoint)**
- **REQ-WITHDRAW-002**: Integración con banco para procesamiento ✅ **(IMPLEMENTADO - Banco Comercio)**
- **REQ-WITHDRAW-003**: Estados: PENDING, PROCESSING, COMPLETED, FAILED
- **REQ-WITHDRAW-004**: Webhook de confirmación de retiro
- **REQ-WITHDRAW-005**: Tiempo estimado de acreditación
- **REQ-WITHDRAW-006**: Comisión por retiro
- **REQ-WITHDRAW-007**: Límites diarios/mensuales de retiro

#### Pagos a Comercios (Opcional Fase 2)
- **REQ-PAY-001**: QR code para pagos
- **REQ-PAY-002**: Link de pago
- **REQ-PAY-003**: Integración con e-commerce

### 1.5 Historial y Consultas

- **REQ-HISTORY-001**: Listado de transacciones (paginado)
- **REQ-HISTORY-002**: Filtros: tipo, fecha, estado, monto
- **REQ-HISTORY-003**: Detalle de transacción individual
- **REQ-HISTORY-004**: Exportación de movimientos (PDF/CSV)
- **REQ-HISTORY-005**: Búsqueda de transacciones
- **REQ-HISTORY-006**: Estados de transacción claros y descriptivos

### 1.6 Notificaciones

- **REQ-NOTIF-001**: Email de confirmación de operaciones
- **REQ-NOTIF-002**: Push notifications (móvil)
- **REQ-NOTIF-003**: Notificaciones in-app
- **REQ-NOTIF-004**: Alertas de seguridad (login, cambio de contraseña)
- **REQ-NOTIF-005**: Centro de notificaciones en la app

### 1.7 Administración (Backoffice)

- **REQ-ADMIN-001**: Panel de administración
- **REQ-ADMIN-002**: Gestión de usuarios (buscar, suspender, activar)
- **REQ-ADMIN-003**: Revisión manual de KYC
- **REQ-ADMIN-004**: Monitoreo de transacciones sospechosas
- **REQ-ADMIN-005**: Reportes financieros
- **REQ-ADMIN-006**: Configuración de límites y comisiones
- **REQ-ADMIN-007**: Logs de auditoría

---

## 2. REQUERIMIENTOS NO FUNCIONALES

### 2.1 Seguridad
- Encriptación de contraseñas (bcrypt/argon2)
- HTTPS obligatorio
- Protección contra SQL injection, XSS, CSRF
- Rate limiting en endpoints críticos
- Logs de auditoría de todas las operaciones
- Cumplimiento PCI-DSS (si se manejan tarjetas)
- Segregación de base de datos (usuarios vs transacciones)

### 2.2 Performance
- Respuesta de API < 500ms (percentil 95)
- Disponibilidad 99.9%
- Escalabilidad horizontal
- Cache para consultas frecuentes (Redis)
- Procesamiento asíncrono de operaciones pesadas

### 2.3 Compliance y Regulación
- Cumplimiento BCRA (Banco Central República Argentina)
- Prevención de lavado de dinero (AML)
- Reportes regulatorios automáticos
- Retención de datos según normativa (mínimo 5 años)

### 2.4 Monitoreo y Observabilidad
- Logs centralizados (ELK/CloudWatch)
- Métricas de negocio (Prometheus/Grafana)
- Alertas automáticas
- Tracing distribuido
- Health checks

---

## 3. ESTADO ACTUAL DEL PROYECTO

### 3.1 Infraestructura ✅ IMPLEMENTADO
- **Base de datos PostgreSQL** en Cloud SQL
- **Deployment en GCP** (Cloud Run)
- **Docker containerizado**
- **Migraciones con Alembic**
- **Terraform para infrastructure as code**

### 3.2 Funcionalidades Existentes

#### Implementado ✅
1. **Sistema de Pagos Básico**
   - Modelo `PaymentRecord`
   - Estados: PENDING, COMPLETED, FAILED, REFUNDED
   - Endpoints: POST /payments, GET /payments/{id}

2. **Transferencias Bancarias**
   - Modelo `TransferRecord` y `TransferEventRecord`
   - Integración con Banco de Comercio
   - Endpoint: POST /api/v1/transfers
   - Estados: CREATED, AUTHORIZED, CAPTURED, FAILED, CANCELLED

3. **KYC con Didit**
   - Endpoint: POST /kyc/session
   - Webhook: POST /webhook (parcial)
   - Estados: PENDING, APPROVED, REJECTED

4. **Arquitectura Hexagonal**
   - Puertos y adaptadores
   - Repositorios (SQL + In-Memory)
   - Separación de concerns

#### Pendiente de Desarrollo ⚠️
1. **Sistema de Usuarios**
   - No existe modelo User
   - No hay registro/login
   - No hay autenticación JWT
   
2. **Gestión de Cuentas/Wallets**
   - No existe modelo Account/Wallet
   - No hay gestión de saldos
   - No hay cuentas bancarias vinculadas

3. **Transferencias P2P**
   - Solo existen transferencias bancarias
   - No hay transferencias entre usuarios

4. **Historial y Consultas**
   - Endpoints de listado muy básicos
   - Sin filtros ni paginación

5. **Notificaciones**
   - No implementado

6. **Backoffice**
   - No existe

---

## 4. HOJA DE RUTA PROPUESTA

### FASE 1: FUNDAMENTOS (4-6 semanas)

#### Sprint 1: Sistema de Usuarios y Autenticación (2 semanas)
**Objetivo:** Permitir registro, login y gestión básica de usuarios

**Tareas:**
1. Crear modelo `User` en base de datos
   ```python
   - id (UUID)
   - email (unique)
   - password_hash
   - first_name, last_name
   - document_type, document_number
   - phone_number
   - email_verified (boolean)
   - kyc_status (enum)
   - status (ACTIVE, SUSPENDED, CLOSED)
   - created_at, updated_at
   ```

2. Implementar endpoints de autenticación
   - `POST /auth/register` - Registro de usuario
   - `POST /auth/login` - Login (retorna JWT)
   - `POST /auth/refresh` - Renovar access token
   - `POST /auth/logout` - Cerrar sesión
   - `POST /auth/forgot-password` - Recuperar contraseña
   - `POST /auth/reset-password` - Cambiar contraseña

3. Implementar middleware de autenticación JWT
   - Installar `python-jose` o `PyJWT`
   - Crear decorador `@require_auth`
   - Validar tokens en cada request

4. Endpoints de perfil
   - `GET /users/me` - Datos del usuario actual
   - `PUT /users/me` - Actualizar datos
   - `POST /users/me/change-password` - Cambiar contraseña

5. Integrar sistema de verificación de email
   - Envío de código de verificación
   - `POST /auth/verify-email` - Verificar código

**Entregables:**
- Usuario puede registrarse
- Usuario puede hacer login y recibir JWT
- Usuario puede consultar/modificar su perfil
- Tests unitarios de autenticación

---

#### Sprint 2: Modelo de Cuentas y Saldos (2 semanas)
**Objetivo:** Implementar wallets con gestión de saldo

**Tareas:**
1. Crear modelo `Account` (Wallet)
   ```python
   - id (UUID)
   - user_id (FK a users)
   - account_number (unique, generado)
   - currency (ARS, USD, etc.)
   - balance (Decimal) - saldo disponible
   - balance_pending (Decimal) - saldo retenido
   - status (ACTIVE, SUSPENDED, CLOSED)
   - created_at, updated_at
   ```

2. Crear modelo `Transaction`
   ```python
   - id (UUID)
   - account_id (FK a accounts)
   - type (DEPOSIT, WITHDRAWAL, P2P_SEND, P2P_RECEIVE)
   - amount (Decimal)
   - currency
   - status (PENDING, COMPLETED, FAILED)
   - description
   - reference_id (UUID de payment/transfer)
   - metadata (JSONB)
   - created_at, completed_at
   ```

3. Implementar servicios de cuenta
   - `AccountService.create_account(user_id)`
   - `AccountService.get_balance(account_id)`
   - `AccountService.update_balance(account_id, amount, type)`
   - Control de concurrencia con locks

4. Endpoints de cuenta
   - `GET /accounts/me` - Mi(s) cuenta(s)
   - `GET /accounts/{id}/balance` - Consultar saldo
   - `GET /accounts/{id}/transactions` - Historial (paginado)

5. Migración de datos existentes
   - Crear cuentas para usuarios/payments existentes
   - Script de migración

**Entregables:**
- Cada usuario tiene una cuenta con saldo
- Se puede consultar saldo y transacciones
- Tests de operaciones concurrentes

---

### FASE 2: OPERACIONES CORE (4-6 semanas)

#### Sprint 3: Carga de Fondos (2 semanas)
**Objetivo:** Permitir depósitos desde cuentas bancarias

**Tareas:**
1. Crear modelo `BankAccount`
   ```python
   - id (UUID)
   - user_id (FK)
   - bank_name
   - account_type (CBU, CVU, ALIAS)
   - account_number (encrypted)
   - owner_name
   - verified (boolean)
   - is_default (boolean)
   - created_at
   ```

2. Generar CVU virtual por cuenta
   - Integración con banco o proveedor de CVU
   - Endpoint: `POST /accounts/{id}/generate-cvu`

3. Implementar endpoints de carga
   - `POST /bank-accounts` - Vincular cuenta bancaria
   - `GET /bank-accounts` - Listar cuentas vinculadas
   - `DELETE /bank-accounts/{id}` - Desvincular
   - `POST /deposits/init` - Iniciar depósito
   - `GET /deposits/{id}` - Estado de depósito

4. Webhook de confirmación de depósito
   - `POST /webhooks/deposits` - Recibir notificación del banco
   - Acreditar fondos automáticamente

5. Actualizar saldo y crear transacción
   - `AccountService.credit(account_id, amount)`

**Entregables:**
- Usuario puede vincular cuenta bancaria
- Usuario puede iniciar depósito
- Fondos se acreditan automáticamente
- Notificación por email

---

#### Sprint 4: Transferencias P2P (2 semanas)
**Objetivo:** Transferir dinero entre usuarios de la plataforma

**Tareas:**
1. Implementar servicio de transferencia P2P
   ```python
   class P2PTransferService:
       async def transfer(
           from_account_id: UUID,
           to_account_id: UUID,
           amount: Decimal,
           description: str
       ) -> Transaction
   ```

2. Validaciones
   - Saldo suficiente
   - Cuentas activas
   - Límites no excedidos
   - Usuario verificado (KYC)

3. Transacción atómica
   - Debitar cuenta origen
   - Acreditar cuenta destino
   - Crear 2 transacciones (SEND + RECEIVE)
   - Rollback en caso de error

4. Endpoints
   - `POST /transfers/p2p` - Ejecutar transferencia
   - `GET /transfers/p2p/{id}` - Consultar estado
   - `GET /users/search?q={email/alias}` - Buscar destinatario

5. Notificaciones
   - Email a ambas partes
   - Push notification

**Entregables:**
- Transferencias instantáneas entre usuarios
- Validaciones de seguridad
- Tests de concurrencia y rollback

---

#### Sprint 5: Retiro de Fondos (2 semanas)
**Objetivo:** Mejorar sistema de retiros existente

**Tareas:**
1. Refactorizar endpoint `/transfers` existente
   - Separar en `/withdrawals` para claridad
   - Mantener compatibilidad hacia atrás

2. Integrar con modelo `Account`
   - Debitar saldo antes de enviar a banco
   - Retener monto (pending) hasta confirmación
   - Liberar si falla

3. Implementar límites de retiro
   - Por transacción
   - Diarios/semanales/mensuales
   - Según nivel KYC

4. Webhooks de estado
   - Actualizar estado de withdrawal
   - Notificar usuario

5. Endpoints mejorados
   - `POST /withdrawals` - Iniciar retiro
   - `GET /withdrawals/{id}` - Estado
   - `GET /withdrawals` - Historial

**Entregables:**
- Retiros integrados con sistema de cuentas
- Límites configurables
- Estados claros y trazables

---

### FASE 3: EXPERIENCIA Y SEGURIDAD (3-4 semanas)

#### Sprint 6: KYC Completo (2 semanas)
**Objetivo:** Completar integración KYC y niveles de verificación

**Tareas:**
1. Completar webhook de Didit
   - Parsear todos los estados
   - Actualizar `user.kyc_status`
   - Trigger de límites según nivel

2. Implementar niveles KYC
   ```python
   class KYCLevel(Enum):
       LEVEL_0 = "UNVERIFIED"  # Sin verificar
       LEVEL_1 = "BASIC"       # Email verificado
       LEVEL_2 = "VERIFIED"    # DNI + Selfie
       LEVEL_3 = "ENHANCED"    # + Comprobante domicilio
   ```

3. Tabla de límites por nivel
   | Nivel | P2P/día | Retiro/día | Carga/mes |
   |-------|---------|------------|-----------|
   | 0     | $1,000  | $500       | $5,000    |
   | 1     | $10,000 | $5,000     | $50,000   |
   | 2     | $100,000| $50,000    | $500,000  |
   | 3     | Ilimitado| Ilimitado | Ilimitado |

4. Endpoints
   - `GET /kyc/status` - Estado de verificación
   - `POST /kyc/re-verify` - Re-verificar
   - `GET /kyc/limits` - Consultar límites

5. Validación en operaciones
   - Verificar límites antes de transferir
   - Mensaje claro si excede

**Entregables:**
- Sistema de niveles KYC funcional
- Límites aplicados automáticamente
- Usuario puede ver su nivel y límites

---

#### Sprint 7: Seguridad y Auditoría (1-2 semanas)
**Objetivo:** Reforzar seguridad y compliance

**Tareas:**
1. Implementar rate limiting
   - Librería: `slowapi`
   - Limitar intentos de login
   - Limitar API calls por usuario

2. Logs de auditoría
   - Crear tabla `audit_log`
   - Registrar todas las operaciones críticas
   - Endpoint admin: `GET /admin/audit-logs`

3. Detección de fraude básica
   - Múltiples retiros en corto tiempo
   - Cambios de cuenta bancaria + retiro inmediato
   - Alertas al equipo de compliance

4. Encriptación de datos sensibles
   - Números de cuenta bancaria
   - Documentos de identidad
   - Uso de `cryptography` library

5. 2FA (Opcional)
   - OTP por email
   - Requerido para retiros grandes

**Entregables:**
- Rate limiting activo
- Logs de auditoría completos
- Datos sensibles encriptados

---

### FASE 4: BACKOFFICE Y POLISH (3-4 semanas)

#### Sprint 8: Panel de Administración (2 semanas)
**Objetivo:** Herramientas para operaciones y compliance

**Tareas:**
1. Endpoints de administración
   - `GET /admin/users` - Listar usuarios (paginado)
   - `GET /admin/users/{id}` - Detalle de usuario
   - `PUT /admin/users/{id}/suspend` - Suspender cuenta
   - `PUT /admin/users/{id}/activate` - Activar cuenta
   - `GET /admin/transactions` - Transacciones (con filtros)
   - `GET /admin/kyc/pending` - KYC pendientes de revisión
   - `PUT /admin/kyc/{id}/approve` - Aprobar manualmente
   - `PUT /admin/kyc/{id}/reject` - Rechazar

2. Roles y permisos
   - Modelo `AdminUser`
   - Roles: SUPER_ADMIN, COMPLIANCE, SUPPORT
   - Middleware `@require_admin`

3. Dashboard básico
   - Total usuarios
   - Total transacciones (hoy/mes)
   - Volumen transaccional
   - KYCs pendientes

4. Reportes
   - Exportar usuarios a CSV
   - Exportar transacciones a CSV
   - Reporte mensual para BCRA

**Entregables:**
- Panel admin funcional (puede ser CLI o API)
- Operadores pueden gestionar usuarios
- Exportación de reportes

---

#### Sprint 9: Notificaciones y UX (1-2 semanas)
**Objetivo:** Mejorar comunicación con usuarios

**Tareas:**
1. Sistema de notificaciones
   - Tabla `notifications`
   - Tipos: EMAIL, PUSH, IN_APP
   - Queue con Celery + Redis

2. Templates de email
   - Registro exitoso
   - Depósito recibido
   - Transferencia enviada/recibida
   - Retiro procesado
   - Alertas de seguridad

3. Endpoints de notificaciones
   - `GET /notifications` - Listar (inbox)
   - `PUT /notifications/{id}/read` - Marcar como leída
   - `GET /notifications/unread-count` - Contador

4. Configuración de preferencias
   - `GET /users/me/preferences`
   - `PUT /users/me/preferences`
   - Usuario puede deshabilitar tipos de notificación

**Entregables:**
- Emails automáticos en operaciones clave
- Centro de notificaciones in-app
- Configuración personalizable

---

## 5. ARQUITECTURA PROPUESTA

### 5.1 Estructura de Base de Datos

```
users
├── accounts (1:N)
│   └── transactions (1:N)
├── bank_accounts (1:N)
├── kyc_verifications (1:1)
└── audit_logs (1:N)

payments (existente)
└── transfers (existente)

notifications
admin_users
```

### 5.2 Servicios y Capas

```
Presentation Layer (FastAPI)
├── /auth/* - AuthController
├── /users/* - UserController
├── /accounts/* - AccountController
├── /transfers/* - TransferController
├── /withdrawals/* - WithdrawalController
├── /deposits/* - DepositController
└── /admin/* - AdminController

Application Layer (Use Cases)
├── UserService
├── AccountService
├── P2PTransferService
├── WithdrawalService
├── DepositService
├── KYCService
└── NotificationService

Domain Layer (Business Logic)
├── User (Entity)
├── Account (Entity)
├── Transaction (Entity)
├── TransferLimits (Value Object)
└── KYCLevel (Value Object)

Infrastructure Layer
├── PostgreSQL (Repositories)
├── Redis (Cache + Queue)
├── SMTP (Emails)
├── Banco Comercio API (External)
└── Didit API (External)
```

### 5.3 Patrones de Diseño

- **Repository Pattern** ✅ (ya implementado)
- **Unit of Work** - Para transacciones atómicas
- **CQRS** - Separar lecturas de escrituras (opcional)
- **Event Sourcing** - Para audit trail (opcional)
- **Saga Pattern** - Para transferencias distribuidas

---

## 6. STACK TECNOLÓGICO

### Backend (Existente)
- **Python 3.11** ✅
- **FastAPI** ✅
- **SQLAlchemy** ✅
- **Alembic** ✅
- **PostgreSQL** ✅

### A Agregar
- **python-jose** o **PyJWT** - JWT tokens
- **passlib[bcrypt]** - Hashing de contraseñas
- **python-multipart** - Upload de archivos
- **celery** - Procesamiento asíncrono
- **redis** - Cache y message broker
- **sendgrid** o **AWS SES** - Envío de emails
- **slowapi** - Rate limiting
- **cryptography** - Encriptación

### DevOps (Existente)
- **Docker** ✅
- **GCP Cloud Run** ✅
- **Terraform** ✅

### A Mejorar
- **Monitoring**: Sentry para errores
- **Logging**: Structured logging con `structlog`
- **CI/CD**: GitHub Actions para tests automáticos

---

## 7. ESTIMACIÓN DE ESFUERZO

| Fase | Duración | Recursos | Riesgo |
|------|----------|----------|--------|
| Fase 1: Fundamentos | 4-6 semanas | 2 dev full-time | Medio |
| Fase 2: Operaciones | 4-6 semanas | 2 dev full-time | Alto |
| Fase 3: Seguridad | 3-4 semanas | 1 dev + 1 security | Medio |
| Fase 4: Backoffice | 3-4 semanas | 1 dev + 1 QA | Bajo |
| **TOTAL** | **14-20 semanas** | **~4 meses** | |

### Recursos Recomendados
- 1 Tech Lead
- 2 Backend Developers Senior
- 1 DevOps Engineer
- 1 QA Engineer
- 1 Product Owner (medio tiempo)

---

## 8. RIESGOS Y MITIGACIONES

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Integración bancaria compleja | Alta | Alto | Testing exhaustivo en sandbox, mockups |
| Problemas de concurrencia en saldos | Media | Crítico | Locks optimistas, tests de carga |
| Cambios regulatorios BCRA | Media | Alto | Arquitectura flexible, compliance early |
| Escalabilidad (volumen transaccional) | Media | Alto | Load testing, cache Redis, índices DB |
| Seguridad (fraude, hacking) | Alta | Crítico | Auditorías externas, 2FA, rate limiting |

---

## 9. MÉTRICAS DE ÉXITO

### KPIs Técnicos
- Uptime > 99.9%
- Response time p95 < 500ms
- Zero critical security vulnerabilities
- Test coverage > 80%

### KPIs de Negocio
- Usuarios registrados
- % Usuarios verificados (KYC)
- Volumen transaccional (ARS/mes)
- Tasa de éxito de transferencias > 99%
- NPS (Net Promoter Score) > 50

---

## 10. PRÓXIMOS PASOS INMEDIATOS

### Semana 1-2: Preparación
1. ✅ Revisión de este documento con stakeholders
2. Priorización de features (pueden eliminarse funcionalidades opcionales)
3. Setup de entorno de desarrollo
4. Configuración de herramientas (Jira, GitHub, Sentry)
5. Kickoff con equipo técnico

### Semana 3: Sprint 1 Planning
1. Refinamiento de historias de usuario
2. Diseño de base de datos (modelo User)
3. Diseño de API (OpenAPI spec)
4. Setup de CI/CD pipeline
5. Inicio de desarrollo

---

## 11. CONSIDERACIONES FINALES

### Lo que YA tenemos (reutilizable)
- ✅ Infraestructura GCP sólida
- ✅ Integración bancaria funcionando (Banco Comercio)
- ✅ Sistema de KYC integrado (Didit)
- ✅ Modelo de datos base para pagos/transferencias
- ✅ Arquitectura hexagonal bien estructurada

### Lo que falta (core de la billetera)
- ⚠️ Sistema de usuarios y autenticación
- ⚠️ Modelo de cuentas y saldos
- ⚠️ Transferencias P2P
- ⚠️ Gestión de depósitos
- ⚠️ Backoffice

### Decisiones Arquitectónicas Clave a Tomar
1. **Monolito vs Microservicios**: Recomiendo empezar con monolito modular, migrar a microservicios solo si escala lo requiere
2. **Base de datos única vs separada**: Por compliance, considerar separar DB de usuarios/cuentas vs transacciones
3. **Procesamiento síncrono vs asíncrono**: Transferencias P2P síncronas, retiros/depósitos asíncronos (Celery)
4. **Cache strategy**: Redis para saldos (con TTL corto) y sesiones JWT

---

## APÉNDICES

### A. Diagrama Entidad-Relación

```
┌─────────────┐       ┌─────────────┐       ┌─────────────────┐
│   users     │1─────N│  accounts   │1─────N│  transactions   │
├─────────────┤       ├─────────────┤       ├─────────────────┤
│ id          │       │ id          │       │ id              │
│ email       │       │ user_id     │       │ account_id      │
│ password    │       │ balance     │       │ type            │
│ first_name  │       │ currency    │       │ amount          │
│ kyc_status  │       │ status      │       │ status          │
│ ...         │       │ ...         │       │ ...             │
└─────────────┘       └─────────────┘       └─────────────────┘
       │
       │1
       │
       │N
┌─────────────────┐
│  bank_accounts  │
├─────────────────┤
│ id              │
│ user_id         │
│ account_number  │
│ verified        │
│ ...             │
└─────────────────┘
```

### B. Ejemplo de Request/Response

```json
// POST /auth/register
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "firstName": "Juan",
  "lastName": "Pérez",
  "documentType": "DNI",
  "documentNumber": "12345678"
}

// Response
{
  "userId": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "accountNumber": "0000003100123456789012",
  "message": "Usuario registrado. Por favor verifica tu email."
}
```

### C. Referencias y Recursos
- [BCRA - Normativa PSP](http://www.bcra.gob.ar/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)

---

**Documento preparado por:** Equipo de Arquitectura  
**Última actualización:** 7 de febrero de 2026  
**Versión:** 1.0
