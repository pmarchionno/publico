# ✅ CHECKLIST DE VERIFICACIÓN - Sistema de Autenticación

## Pre-requisitos ✓

- [ ] Python 3.9+
- [ ] PostgreSQL 12+ (o la BD que uses)
- [ ] Docker + Docker Compose (opcional, para ejecutar en contenedor)
- [ ] Alembic configurado
- [ ] requirements.txt actualizado

---

## Verificación de Archivos Nuevos ✓

### Ports Layer

- [ ] `app/ports/user_repository.py` existe
- [ ] Contiene clase abstracta `UserRepository`
- [ ] Métodos: create, get_by_email, get_by_id, exists_by_email, update, delete

### Adapters Layer

- [ ] `app/adapters/db/sql_user_repository.py` existe
- [ ] Implementa `UserRepository`
- [ ] Contiene método `_to_domain()` para conversión

### Domain Layer

- [ ] `app/domain/models.py` actualizado
- [ ] Contiene clase `User` con campos: id, email, full_name, is_active, created_at, updated_at
- [ ] Usa Pydantic con `EmailStr`

### Database Layer

- [ ] `app/db/models.py` actualizado
- [ ] Contiene clase `UserRecord` con modelo SQLAlchemy
- [ ] Tiene índices en email e is_active
- [ ] Importa Boolean de sqlalchemy

### Services Layer

- [ ] `app/services/user_service.py` existe
- [ ] Contiene `UserService` con métodos: register_user, authenticate_user, get_user, deactivate_user, create_user_token
- [ ] Usa verificación de contraseña con bcrypt

### Auth Layer

- [ ] `app/auth/schemas.py` existe
- [ ] Contiene: UserRegisterRequest, UserLoginRequest, UserResponse, TokenResponse, ErrorResponse
- [ ] Usa validación Pydantic

### API Layer

- [ ] `app/api_server/routers/auth.py` existe
- [ ] Contiene: @router.post("/register"), @router.post("/login")
- [ ] Retorna status correcto: 201 para register, 200 para login
- [ ] Manea errores: 400, 401, 422

### Migrations

- [ ] `migrations/versions/20260209_01_add_user_tables.py` existe
- [ ] Contiene función upgrade() con CREATE TABLE
- [ ] Contiene función downgrade() con DROP TABLE

### Tests

- [ ] `tests/test_auth.py` existe
- [ ] Contiene tests para: register, login, duplicate email, invalid credentials, weak password

### Documentation

- [ ] `docs/7_AUTENTICACION_USUARIOS.md` existe
- [ ] `docs/GUIA_PRACTICA_AUTENTICACION.md` existe
- [ ] `IMPLEMENTACION_AUTENTICACION.md` existe

---

## Verificación de Archivos Modificados ✓

### app/api_server/main.py

- [ ] Importa: `from app.api_server.routers import auth`
- [ ] Incluye router: `app.include_router(auth.router, tags=["auth"])`

### app/adapters/api/dependencies.py

- [ ] Importa: `from fastapi import Depends`
- [ ] Importa: `from app.db.session import get_db_session`
- [ ] Importa: `from app.adapters.db.sql_user_repository import SQLUserRepository`
- [ ] Importa: `from app.services.user_service import UserService`
- [ ] Contiene: `async def get_session()`
- [ ] Contiene: `async def get_user_repository()`
- [ ] Contiene: `async def get_user_service()`

### app/api_server/routers/**init**.py

- [ ] Existe el archivo
- [ ] Importa: auth, payments, kyc, webhook
- [ ] Tiene **all**

---

## Pruebas de Integración ✓

### Base de Datos

- [ ] Conexión a PostgreSQL funciona
- [ ] Base de datos existe
- [ ] Alembic puede conectar

### Migración

- [ ] Ejecutar: `alembic upgrade head`
- [ ] Verificar: `alembic current` retorna `20260209_01` (o última)
- [ ] Tabla `users` existe en BD: `SELECT * FROM users;` (puede estar vacía)

### Servidor

- [ ] Iniciar servidor: `uvicorn app.api_server.main:app --reload`
- [ ] No hay errores de import
- [ ] Swagger disponible: `http://localhost:8000/docs`
- [ ] Health check funciona: `GET /health` → 200

### Endpoints - Registro

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "full_name": "Test User",
    "password": "TestPassword123"
  }'
```

- [ ] Status 201 Created
- [ ] Response contiene: id, email, full_name, is_active, created_at, updated_at
- [ ] Response NO contiene: hashed_password
- [ ] Usuario guardado en BD

### Endpoints - Registro Duplicado

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "full_name": "Another Test",
    "password": "TestPassword123"
  }'
```

- [ ] Status 400 Bad Request
- [ ] Mensaje: "El email ... ya está registrado"

### Endpoints - Login Exitoso

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123"
  }'
```

- [ ] Status 200 OK
- [ ] Response contiene: access_token, token_type, user
- [ ] user contiene: id, email, full_name, is_active
- [ ] access_token es string válido

### Endpoints - Login Fallido

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "WrongPassword"
  }'
```

- [ ] Status 401 Unauthorized
- [ ] Mensaje: "Credenciales inválidas"

### Endpoints - Email Inválido

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "not-an-email",
    "full_name": "Test",
    "password": "TestPassword123"
  }'
```

- [ ] Status 422 Unprocessable Entity
- [ ] Mensaje contiene "invalid email"

### Endpoints - Contraseña Débil

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "short@test.com",
    "full_name": "Test",
    "password": "short"
  }'
```

- [ ] Status 400 Bad Request
- [ ] Mensaje: "La contraseña debe tener mínimo 8 caracteres"

---

## Validaciones de Seguridad ✓

### Contraseñas

- [ ] GET /health NO retorna contraseñas
- [ ] POST /auth/register NO retorna contraseña hasheada
- [ ] POST /auth/login NO retorna contraseña
- [ ] Contraseñas en BD están hasheadas (no texto plano)

### JWT

- [ ] Token tiene estructura válida: Header.Payload.Signature
- [ ] Token contiene: sub (user_id), exp (expiration)
- [ ] Token expira después de ACCESS_TOKEN_EXPIRE_MINUTES

### Base de Datos

- [ ] Email tiene UNIQUE constraint
- [ ] Email tiene índice para búsqueda rápida
- [ ] ID es UUID (no sequential integer)

---

## Verificación de Código ✓

### Imports

- [ ] No hay importaciones circular
- [ ] Todos los imports existen
- [ ] `from app.auth.schemas import EmailStr` disponible

### Type Hints

- [ ] Funciones tienen type hints
- [ ] AsyncSession está anotado correctamente
- [ ] Optional usado donde corresponde

### Async/Await

- [ ] Todas las funciones de BD son async
- [ ] `async def` usado en repositorio
- [ ] `await` usado en llamadas async

---

## Testing ✓

### Setup

- [ ] pytest instalado: `pip list | grep pytest`
- [ ] pytest-asyncio instalado: `pip list | grep pytest-asyncio`

### Ejecutar Tests

```bash
pytest tests/test_auth.py -v
```

- [ ] test_register_user PASSED
- [ ] test_register_duplicate_email PASSED
- [ ] test_login_success PASSED
- [ ] test_login_invalid_credentials PASSED
- [ ] test_register_weak_password PASSED
- [ ] test_register_invalid_email PASSED

---

## Documentación ✓

- [ ] README actualizado con nueva funcionalidad
- [ ] Documentación técnica clara
- [ ] Ejemplos de cURL proporcionados
- [ ] Ejemplos de Python proporcionados

---

## Deployment ✓

### Docker

- [ ] Dockerfile actualizado (si necesario)
- [ ] docker-compose.yml contiene variables de BD
- [ ] `docker compose up -d --build` construye correctamente

### Producción

- [ ] SECRET_KEY en .env (no hardcodeado)
- [ ] DATABASE_URL usando credenciales seguras
- [ ] HTTPS habilitado en producción
- [ ] CORS configurado si necesario

---

## Rollback (En caso necesario) ✓

Si algo sale mal:

```bash
# Deshacer migración
alembic downgrade -1

# O volver a versión específica
alembic downgrade 20260102_01

# Verificar estado actual
alembic current
```

---

## Próximos Pasos ✓

- [ ] Integrar autenticación con rutas de pagos
- [ ] Agregar protección JWT en endpoints
- [ ] Implementar refresh tokens
- [ ] Agregar email verification
- [ ] Implementar roles y permisos
- [ ] Agregar rate limiting en login
- [ ] Implementar social login

---

## Verificación Final ✓

```bash
# 1. Migración OK
alembic current

# 2. Servidor sin errores
python -m pytest -v

# 3. Endpoints funcionales
curl http://localhost:8000/docs

# 4. BD con datos
psql -c "SELECT COUNT(*) FROM users;"
```

**Status Final**:

- [ ] TODO FUNCIONA ✅
- [ ] LISTO PARA PRODUCCIÓN ✅

---

**Completado**: [Fecha de verificación]  
**Verificador**: [Tu nombre]  
**Notas**: [Cualquier nota adicional]
