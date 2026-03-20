# Diagrama de Secuencia - Registro de Usuarios en Dos Pasos

Este documento describe el flujo completo del registro de usuarios implementado con verificación de email en dos pasos.

## Flujo General

```mermaid
sequenceDiagram
    actor Usuario
    participant App as Frontend App
    participant API as API /auth
    participant Service as UserService
    participant Repo as UserRepository
    participant DB as PostgreSQL
    participant Email as Email Provider<br/>(simulado)

    Note over Usuario,DB: PASO 1: Registro de Email

    Usuario->>App: Ingresa email
    App->>API: POST /auth/register<br/>{email}
    API->>Service: start_email_registration(email)
    Service->>Repo: get_by_email(email)
    Repo->>DB: SELECT * FROM users<br/>WHERE email = ?
    DB-->>Repo: user (si existe)

    alt Email ya verificado
        Service-->>API: ValueError("Email ya verificado")
        API-->>App: 400 Bad Request
    else Email nuevo o no verificado
        Service->>Repo: create(user, None)
        Repo->>DB: INSERT INTO users<br/>(email, is_email_verified=false,<br/>hashed_password=NULL)
        DB-->>Repo: ✓ Usuario creado
        Service->>Service: create_email_verification_token(email)
        Service-->>API: verification_link
        API-->>App: 200 OK<br/>{verification_link}
        App->>Email: Enviar email con link<br/>(simulado: se retorna en response)
        Email-->>Usuario: Email con link de verificación
    end

    Note over Usuario,DB: VERIFICACIÓN DE EMAIL

    Usuario->>Usuario: Click en link de verificación
    Usuario->>App: GET /auth/verify-email?token=xyz
    App->>API: GET /auth/verify-email?token=xyz
    API->>Service: verify_email(token)
    Service->>Service: verify_email_verification_token(token)

    alt Token inválido o expirado
        Service-->>API: ValueError("Token invalido")
        API-->>App: 400 Bad Request
    else Token válido
        Service->>Repo: set_email_verified(email, true)
        Repo->>DB: UPDATE users<br/>SET is_email_verified = true<br/>WHERE email = ?
        DB-->>Repo: ✓ Actualizado
        Repo-->>Service: User actualizado
        Service-->>API: User
        API-->>App: 200 OK<br/>{message: "Email verificado"}
        App-->>Usuario: "Email verificado exitosamente"
    end

    Note over Usuario,DB: OPCIONAL: Consultar Estado

    App->>API: POST /auth/check-email<br/>{email}
    API->>Service: check_email_status(email)
    Service->>Repo: get_by_email(email)
    Repo->>DB: SELECT * FROM users<br/>WHERE email = ?
    DB-->>Repo: user + hashed_password
    Service-->>API: {exists, is_verified,<br/>can_complete_registration}
    API-->>App: 200 OK<br/>{exists: true,<br/>is_verified: true,<br/>can_complete: true}

    Note over Usuario,DB: PASO 2: Completar Registro

    Usuario->>App: Completa formulario<br/>(password, dni, nombre, etc)
    App->>API: POST /auth/register/complete<br/>{email, password, dni, first_name,<br/>last_name, gender, cuit_cuil, ...}
    API->>Service: complete_registration(...)
    Service->>Repo: get_by_email(email)
    Repo->>DB: SELECT * FROM users<br/>WHERE email = ?
    DB-->>Repo: user + NULL password

    alt Email no verificado
        Service-->>API: ValueError("Email no verificado")
        API-->>App: 400 Bad Request
    else Email verificado
        Service->>Service: get_password_hash(password)
        Service->>Repo: complete_registration(email, user, hashed_password)
        Repo->>DB: UPDATE users SET<br/>first_name=?, last_name=?, dni=?,<br/>hashed_password=?, ...<br/>WHERE email = ?
        DB-->>Repo: ✓ Perfil completo
        Repo-->>Service: User completo
        Service-->>API: User
        API-->>App: 200 OK<br/>{user completo}
        App-->>Usuario: "Registro completado"
    end

    Note over Usuario,DB: LOGIN

    Usuario->>App: Ingresa email y password
    App->>API: POST /auth/login<br/>{email, password}
    API->>Service: authenticate_user(email, password)
    Service->>Repo: get_by_email(email)
    Repo->>DB: SELECT * FROM users<br/>WHERE email = ?
    DB-->>Repo: user + hashed_password

    alt Password o verificación inválida
        Service->>Service: verify_password(password, hashed)
        Service-->>API: None (credenciales inválidas)
        API-->>App: 401 Unauthorized
    else Credenciales válidas + email verificado
        Service->>Service: verify_password(password, hashed)
        Service->>Service: create_access_token(user_id)
        Service-->>API: User
        API->>Service: create_user_token(user.id)
        Service-->>API: access_token (JWT)
        API-->>App: 200 OK<br/>{access_token, user}
        App-->>Usuario: "Sesión iniciada"
    end
```

## Endpoints Disponibles

### 1. POST /auth/register

**Paso 1: Registro de email**

**Request:**

```json
{
  "email": "usuario@example.com"
}
```

**Response 200 OK:**

```json
{
  "message": "Se envio el link de verificacion",
  "verification_link": "http://localhost:8000/auth/verify-email?token=eyJhbG..."
}
```

**Response 400 Bad Request:**

```json
{
  "detail": "El email usuario@example.com ya esta verificado"
}
```

---

### 2. GET /auth/verify-email?token={jwt_token}

**Verificación de email mediante token JWT**

**Response 200 OK:**

```json
{
  "message": "Email verificado"
}
```

**Response 400 Bad Request:**

```json
{
  "detail": "Token invalido o expirado"
}
```

---

### 3. POST /auth/check-email

**Consultar estado de verificación de un email**

**Request:**

```json
{
  "email": "usuario@example.com"
}
```

**Response 200 OK:**

```json
{
  "exists": true,
  "is_verified": true,
  "can_complete_registration": true
}
```

---

### 4. POST /auth/register/complete

**Paso 2: Completar perfil después de verificar email**

**Request:**

```json
{
  "email": "usuario@example.com",
  "password": "SecurePass123",
  "dni": "12345678",
  "first_name": "Juan",
  "last_name": "Pérez",
  "gender": "masculino",
  "cuit_cuil": "20123456789",
  "phone": "+5491112345678",
  "nationality": "Argentina",
  "occupation": "Developer",
  "marital_status": "Soltero",
  "location": "Buenos Aires"
}
```

**Response 200 OK:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "usuario@example.com",
  "full_name": "Juan Pérez",
  "first_name": "Juan",
  "last_name": "Pérez",
  "dni": "12345678",
  "gender": "masculino",
  "cuit_cuil": "20123456789",
  "phone": "+5491112345678",
  "nationality": "Argentina",
  "occupation": "Developer",
  "marital_status": "Soltero",
  "location": "Buenos Aires",
  "is_active": true,
  "is_email_verified": true,
  "created_at": "2026-02-10T12:00:00Z",
  "updated_at": "2026-02-10T12:05:00Z"
}
```

**Response 400 Bad Request:**

```json
{
  "detail": "Email no verificado"
}
```

---

### 5. POST /auth/login

**Iniciar sesión (requiere email verificado y perfil completo)**

**Request:**

```json
{
  "email": "usuario@example.com",
  "password": "SecurePass123"
}
```

**Response 200 OK:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "usuario@example.com",
    "full_name": "Juan Pérez",
    ...
  }
}
```

**Response 401 Unauthorized:**

```json
{
  "detail": "Credenciales invalidas"
}
```

## Estados del Usuario en BD

### Estado 1: Registro Inicial (Pendiente)

```sql
email: 'usuario@example.com'
is_email_verified: false
hashed_password: NULL
first_name: NULL
last_name: NULL
...
```

### Estado 2: Email Verificado (Puede completar registro)

```sql
email: 'usuario@example.com'
is_email_verified: true
hashed_password: NULL
first_name: NULL
...
```

### Estado 3: Registro Completo (Puede hacer login)

```sql
email: 'usuario@example.com'
is_email_verified: true
hashed_password: '$2b$12$...'
first_name: 'Juan'
last_name: 'Pérez'
dni: '12345678'
...
```

## Validaciones de Seguridad

1. ✅ **Email verificado obligatorio** para completar registro
2. ✅ **Email verificado obligatorio** para login
3. ✅ **Password hasheado** (bcrypt) antes de guardar en BD
4. ✅ **Token JWT con expiración** (24 horas para verificación, 30 min para acceso)
5. ✅ **Password mínimo 8 caracteres**
6. ✅ **No permite re-registro** de emails ya verificados
7. ✅ **Scope en tokens** para prevenir uso indebido (email_verification vs access)

## Configuración

En `config/settings.py`:

```python
SECRET_KEY = "tu-secret-key-super-segura"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Token de login
EMAIL_VERIFICATION_EXPIRE_MINUTES = 60 * 24  # 24 horas
EMAIL_VERIFICATION_BASE_URL = "http://localhost:8000/auth/verify-email"
```

## Arquitectura

- **Clean Architecture**: separación en capas (API → Service → Port → Adapter → Domain → Data)
- **Async/Await**: operaciones asincrónicas con SQLAlchemy async
- **Repository Pattern**: abstracción de acceso a datos
- **Domain Models**: entidades puras sin dependencias de framework
- **DTO Schemas**: validación con Pydantic v2
