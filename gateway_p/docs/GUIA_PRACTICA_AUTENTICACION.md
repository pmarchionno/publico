# Guía Práctica - Endpoints de Autenticación

## 🚀 Inicio Rápido

### 1. Ejecutar la migración de BD

```bash
alembic upgrade head
```

### 2. Iniciar el servidor

```bash
docker compose up -d --build
# o
uvicorn app.api_server.main:app --reload --port 8000
```

### 3. Acceder a la documentación interactiva

```
http://localhost:8000/docs
```

---

## 📝 Ejemplos de Uso

### Con cURL

#### Registro

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "juan@example.com",
    "full_name": "Juan Pérez",
    "password": "MiPassword2024!"
  }'
```

**Respuesta (201 Created):**

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "email": "juan@example.com",
  "full_name": "Juan Pérez",
  "is_active": true,
  "created_at": "2026-02-09T14:30:00.000000",
  "updated_at": "2026-02-09T14:30:00.000000"
}
```

#### Login

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "juan@example.com",
    "password": "MiPassword2024!"
  }'
```

**Respuesta (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhMWIyYzNkNC1lNWY2LTc4OTAtYWJjZC1lZjEyMzQ1Njc4OTAiLCJleHAiOjE3NDQ0MDM4MDB9.xYz...",
  "token_type": "bearer",
  "user": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "email": "juan@example.com",
    "full_name": "Juan Pérez",
    "is_active": true,
    "created_at": "2026-02-09T14:30:00.000000",
    "updated_at": "2026-02-09T14:30:00.000000"
  }
}
```

---

### Con Python + requests

```python
import requests
import json

BASE_URL = "http://localhost:8000"

# 1. Registro
registro_response = requests.post(
    f"{BASE_URL}/auth/register",
    json={
        "email": "sofia@example.com",
        "full_name": "Sofia García",
        "password": "SecurePass123!"
    }
)

print("Registro:", registro_response.json())
user_id = registro_response.json()["id"]

# 2. Login
login_response = requests.post(
    f"{BASE_URL}/auth/login",
    json={
        "email": "sofia@example.com",
        "password": "SecurePass123!"
    }
)

print("Login:", login_response.json())
token = login_response.json()["access_token"]

# 3. Usar token en requests futuros
headers = {"Authorization": f"Bearer {token}"}
# requests.get(f"{BASE_URL}/profile", headers=headers)
```

---

### Con Python + httpx (async)

```python
import asyncio
import httpx

BASE_URL = "http://localhost:8000"

async def main():
    async with httpx.AsyncClient() as client:
        # 1. Registro
        reg_resp = await client.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": "maria@example.com",
                "full_name": "María López",
                "password": "MySecurePass789!"
            }
        )
        print("Registro:", reg_resp.json())

        # 2. Login
        login_resp = await client.post(
            f"{BASE_URL}/auth/login",
            json={
                "email": "maria@example.com",
                "password": "MySecurePass789!"
            }
        )
        print("Login:", login_resp.json())
        token = login_resp.json()["access_token"]

asyncio.run(main())
```

---

### Con JavaScript/Node.js

```javascript
const BASE_URL = "http://localhost:8000";

async function register() {
  const response = await fetch(`${BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: "carlos@example.com",
      full_name: "Carlos Domínguez",
      password: "Carlos2024Secure!",
    }),
  });

  const user = await response.json();
  console.log("Usuario registrado:", user);
  return user;
}

async function login() {
  const response = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: "carlos@example.com",
      password: "Carlos2024Secure!",
    }),
  });

  const data = await response.json();
  console.log("Token:", data.access_token);
  console.log("Usuario:", data.user);
  return data;
}

// Ejecutar
(async () => {
  await register();
  await login();
})();
```

---

## ⚠️ Casos de Error

### Email ya registrado

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "juan@example.com",
    "full_name": "Juan Otro",
    "password": "MiPassword2024!"
  }'
```

**Respuesta (400 Bad Request):**

```json
{
  "detail": "El email juan@example.com ya está registrado"
}
```

### Contraseña débil

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "full_name": "Test User",
    "password": "short"
  }'
```

**Respuesta (400 Bad Request):**

```json
{
  "detail": "La contraseña debe tener mínimo 8 caracteres"
}
```

### Email inválido

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "not-an-email",
    "full_name": "Test User",
    "password": "SecurePassword123"
  }'
```

**Respuesta (422 Unprocessable Entity):**

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "email"],
      "msg": "invalid email format"
    }
  ]
}
```

### Credenciales inválidas en login

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "juan@example.com",
    "password": "PasswordIncorrecto!"
  }'
```

**Respuesta (401 Unauthorized):**

```json
{
  "detail": "Credenciales inválidas"
}
```

---

## 🧪 Casos de Prueba Completos

### Test 1: Flujo Exitoso (Register → Login)

```bash
#!/bin/bash

BASE_URL="http://localhost:8000"
EMAIL="test_$(date +%s)@example.com"
PASS="SecurePassword123"

echo "1. Registrando usuario..."
REGISTER=$(curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"full_name\":\"Test User\",\"password\":\"$PASS\"}")
echo $REGISTER | jq .

echo -e "\n2. Haciendo login..."
LOGIN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}")
echo $LOGIN | jq .

TOKEN=$(echo $LOGIN | jq -r '.access_token')
echo -e "\n✅ Token obtenido: $TOKEN"
```

---

## 📊 Flujo Visual de Autenticación

```
┌─────────────────────────────────────────────────────────────────┐
│                    REGISTRO (Register)                          │
├─────────────────────────────────────────────────────────────────┤
│ 1. Cliente envía: email, full_name, password                   │
│ 2. API valida formato (email, longitud password)               │
│ 3. UserService comprueba: ¿email único?                        │
│ 4. ✅ Si es único:                                              │
│    - Hash password con bcrypt                                  │
│    - Crear User en dominio                                     │
│    - SQLUserRepository.create(user, hashed_password)           │
│    - Guardar en BD (PostgreSQL)                                │
│    - Retornar User (sin contraseña) → 201 Created             │
│ 5. ❌ Si no es único:                                           │
│    - Retornar error 400: "ya está registrado"                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                       LOGIN (Login)                             │
├─────────────────────────────────────────────────────────────────┤
│ 1. Cliente envía: email, password                              │
│ 2. API valida formato                                          │
│ 3. UserService.authenticate_user():                            │
│    - SQLUserRepository.get_by_email(email)                     │
│    - Obtener User + hashed_password de BD                      │
│ 4. ✅ Si usuario existe:                                        │
│    - verify_password(plain_password, hashed_password)         │
│    - ✅ Si match:                                              │
│      - Generar JWT con create_access_token()                 │
│      - Retornar TokenResponse → 200 OK                       │
│    - ❌ Si no match:                                           │
│      - Retornar error 401: "Credenciales inválidas"          │
│ 5. ❌ Si no existe:                                             │
│    - Retornar error 401: "Credenciales inválidas"            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔐 Tokens JWT

### Estructura del Token

El token retornado sigue el estándar JWT con estructura:

```
Header.Payload.Signature
```

**Ejemplo decoded:**

```json
{
  "sub": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "exp": 1744403800
}
```

### Uso del Token en futuras requests

```bash
curl -X GET "http://localhost:8000/profile" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Configuración del Token

En `config/settings.py`:

```python
SECRET_KEY = "tu-clave-secreta-segura"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Expiración en 30 minutos
```

---

## ✅ Checklist de Pruebas

- [ ] Registrar usuario válido
- [ ] Intentar registrar con email duplicado
- [ ] Intentar registrar con password < 8 caracteres
- [ ] Intentar registrar con email inválido
- [ ] Login con credenciales válidas
- [ ] Login con contraseña incorrecta
- [ ] Login con email no registrado
- [ ] Verificar que respuesta no contiene contraseña
- [ ] Verificar que token es válido (decode en jwt.io)
- [ ] Probar con diferentes clientes (curl, postman, browser, etc.)

---

## 🐛 Troubleshooting

### Error: "Password hash check failed"

- Verificar que la migración se ejecutó: `alembic current`
- Verificar BD conectada correctamente

### Error: "relation 'users' does not exist"

```bash
# Ejecutar migración
alembic upgrade head
```

### Token expirado

- Hacer nuevo login
- O extender `ACCESS_TOKEN_EXPIRE_MINUTES` en settings.py

---

## 📚 Referencias

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [JWT.io - Decodificar tokens](https://jwt.io)
- [Pydantic Validation](https://docs.pydantic.dev/)
- [Python Jose](https://python-jose.readthedocs.io/)
