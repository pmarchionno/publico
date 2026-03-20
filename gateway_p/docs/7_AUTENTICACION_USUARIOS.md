# Sistema de Autenticación - Documentación Técnica

## 📋 Resumen

Implementación de un sistema de autenticación con **registro** y **login** usando arquitectura Clean Architecture + FastAPI + SQLAlchemy.

## 🏗️ Estructura de Capas

### 1. **Domain Layer** (`app/domain/models.py`)

- **User**: Entidad pura sin dependencias
  - `id`: UUID único
  - `email`: EmailStr validado
  - `full_name`: Nombre completo
  - `is_active`: Bandera de estado activo
  - `created_at`, `updated_at`: Timestamps

### 2. **Persistence Layer**

#### Puerto (Interfaz) - `app/ports/user_repository.py`

```python
class UserRepository(ABC):
    async def create(user: User, hashed_password: str) -> User
    async def get_by_email(email: str) -> Optional[tuple[User, str]]
    async def exists_by_email(email: str) -> bool
    async def get_by_id(user_id: UUID) -> Optional[User]
    async def update(user: User) -> User
    async def delete(user_id: UUID) -> bool
```

#### Adaptador (Implementación) - `app/adapters/db/sql_user_repository.py`

- Implementa `UserRepository` con SQLAlchemy
- Conversión automática entre `UserRecord` ↔ `User`
- Queries async con índices para performance

#### Modelo de BD - `app/db/models.py`

```sql
users:
  - id (UUID, PK)
  - email (VARCHAR 255, UNIQUE, INDEX)
  - full_name (VARCHAR 255)
  - hashed_password (VARCHAR 255)
  - is_active (BOOLEAN, default: true)
  - created_at (TIMESTAMP)
  - updated_at (TIMESTAMP)
```

### 3. **Service Layer** - `app/services/user_service.py`

Lógica de negocio:

- **Validaciones**: Email único, longitud de contraseña mínimo 8 caracteres
- **Hashing**: bcrypt con passlib
- **Autenticación**: verify de contraseña + verificación de usuario activo
- **JWT**: Generación de tokens con `create_access_token()`

```python
class UserService:
    async def register_user(email, full_name, password) -> User
    async def authenticate_user(email, password) -> Optional[User]
    async def get_user(user_id) -> Optional[User]
    async def deactivate_user(user_id) -> bool
    def create_user_token(user_id) -> str  # JWT
```

### 4. **API Layer** - `app/api_server/routers/auth.py`

#### Endpoint: `POST /auth/register`

**Request:**

```json
{
  "email": "user@example.com",
  "full_name": "John Doe",
  "password": "securepassword123"
}
```

**Response:** `201 Created`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "created_at": "2026-02-09T10:00:00Z",
  "updated_at": "2026-02-09T10:00:00Z"
}
```

**Errores:**

- `400`: Email ya registrado / Contraseña débil
- `422`: Validación de datos fallida (email inválido, etc.)

#### Endpoint: `POST /auth/login`

**Request:**

```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:** `200 OK`

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "full_name": "John Doe",
    "is_active": true,
    "created_at": "2026-02-09T10:00:00Z",
    "updated_at": "2026-02-09T10:00:00Z"
  }
}
```

**Errores:**

- `401`: Credenciales inválidas
- `422`: Validación fallida

### 5. **Schema (DTOs)** - `app/auth/schemas.py`

- `UserRegisterRequest`: Validación de entrada para registro
- `UserLoginRequest`: Validación de entrada para login
- `UserResponse`: Respuesta con info de usuario
- `TokenResponse`: Respuesta con token JWT
- `ErrorResponse`: Respuesta estándar de error

### 6. **Security** - `app/auth/security.py`

Funciones disponibles:

```python
def verify_password(plain_password: str, hashed_password: str) -> bool
def get_password_hash(password: str) -> str
def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str
```

### 7. **Dependency Injection** - `app/adapters/api/dependencies.py`

```python
async def get_session() -> AsyncSession  # Sesión de BD
async def get_user_repository() -> UserRepository  # Repo inyectado
async def get_user_service() -> UserService  # Servicio inyectado
```

## 🔄 Flujo de Datos

### Registro

```
POST /auth/register
    ↓
UserRegisterRequest (validación Pydantic)
    ↓
FastAPI → Depends(get_user_service) → UserService.register_user()
    ↓
UserService valida email único + hash de contraseña
    ↓
UserRepository.create(user, hashed_password)
    ↓
SQLUserRepository → UserRecord → BD
    ↓
UserRecord convertido a User (domain model)
    ↓
Response 201 + UserResponse
```

### Login

```
POST /auth/login
    ↓
UserLoginRequest (validación Pydantic)
    ↓
FastAPI → Depends(get_user_service) → UserService.authenticate_user()
    ↓
UserRepository.get_by_email() → obtiene User + hashed_password
    ↓
verify_password(plain, hashed)
    ↓
Si es válido: create_access_token() → JWT
    ↓
Response 200 + TokenResponse (con token + usuario)
```

## 🗄️ Base de Datos

### Crear tabla (Alembic Migration)

```bash
alembic upgrade head
```

Con la migración en `migrations/versions/20260209_01_add_user_tables.py`

### Índices para performance

- `idx_user_email`: Búsqueda rápida por email (login/registro)
- `idx_user_is_active`: Filtrado de usuarios activos

## 🔐 Seguridad

- **Hashing**: bcrypt con salt automático
- **Validación**: Email format + constrain de BD (UNIQUE)
- **Contraseña**: Mínimo 8 caracteres, nunca se retorna en respuestas
- **JWT**: Firmado con SECRET_KEY + ALGORITHM (configurables en `config/settings.py`)
- **HTTPS**: Recomendado en producción

## 📦 Compatibilidad con Arquitectura Existente

La implementación sigue **exactamente** el patrón ya establecido en tu proyecto:

✅ **Ports Pattern**: `UserRepository` en `app/ports/`
✅ **Adapters**: `SQLUserRepository` en `app/adapters/db/`  
✅ **Services**: `UserService` en `app/services/`
✅ **Routers Modulares**: `auth.py` en `app/api_server/routers/`
✅ **Dependency Injection**: En `adapters/api/dependencies.py`
✅ **DTOs con Pydantic**: Schema con validaciones en `auth/schemas.py`
✅ **Domain Models**: User en `app/domain/models.py`
✅ **SQLAlchemy Async**: Consistente con `PaymentRecord`, `TransferRecord`

## 📝 Extensiones Futuras

### Fácilmente extensible para:

1. **JWT Verification**:

   ```python
   # En router
   from fastapi import Header
   async def get_current_user(authorization: str = Header(...)):
       token = authorization.split(" ")[1]
       payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
       return await service.get_user(UUID(payload["sub"]))
   ```

2. **Roles y Permisos**:

   ```python
   # Agregar a UserRecord: role: Mapped[str]
   # Agregar a User: role: str
   enum UserRole(str, Enum):
       ADMIN = "admin"
       USER = "user"
   ```

3. **Refresh Tokens**:

   ```python
   async def refresh_token(request: RefreshTokenRequest):
       # Validar refresh_token
       # Retornar nuevo access_token
   ```

4. **Social Login** (OAuth2):

   ```python
   async def login_with_google(code: str):
       # Integrar con Google OAuth
   ```

5. **Email Verification**:
   ```python
   # Agregar verificación de email antes de activar usuario
   ```

## 🧪 Testing

Ver `tests/test_auth.py` para ejemplos de tests:

- Test registro exitoso
- Test email duplicado (debe fallar)
- Test login exitoso
- Test credenciales inválidas
- Test contraseña débil
- Test email inválido

Para ejecutar:

```bash
pytest tests/test_auth.py -v
```

## 📚 Archivos Creados/Modificados

### Creados ✨

- `app/ports/user_repository.py` - Puerto (interfaz)
- `app/adapters/db/sql_user_repository.py` - Adaptador (implementación)
- `app/auth/schemas.py` - DTOs para autenticación
- `app/services/user_service.py` - Lógica de negocio
- `app/api_server/routers/auth.py` - Endpoints HTTP
- `migrations/versions/20260209_01_add_user_tables.py` - Migración de BD
- `tests/test_auth.py` - Tests de autenticación

### Modificados 📝

- `app/domain/models.py` - Agregado User model
- `app/db/models.py` - Agregado UserRecord + Boolean import
- `app/api_server/main.py` - Incluido auth router
- `app/adapters/api/dependencies.py` - Agregado inyección de User\*

## ✅ Próximos Pasos

1. **Ejecutar migración**:

   ```bash
   alembic upgrade head
   ```

2. **Probar endpoints**:
   - Swagger UI: http://localhost:8000/docs
   - POST /auth/register
   - POST /auth/login

3. **Proteger rutas**:

   ```python
   from fastapi import Depends, HTTPException
   from app.auth.security import verify_token

   async def get_current_user(token: str = Depends(oauth2_scheme)):
       # Verificar token
       return user

   @router.get("/profile")
   async def get_profile(current_user: User = Depends(get_current_user)):
       return current_user
   ```

4. **Integrar con endpoints existentes**:
   - Agregar `user_id` a Payment
   - Agregar user auth a rutas de pagos
