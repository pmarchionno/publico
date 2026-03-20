# 🎯 REFERENCIA RÁPIDA - Sistema de Autenticación

## 📱 Endpoints Disponibles

```bash
# REGISTRO
POST /auth/register
Content-Type: application/json

{
  "email": "usuario@example.com",
  "full_name": "Nombre Completo",
  "password": "MinimoPalabra8"
}

Response: 201 Created
{
  "id": "uuid",
  "email": "usuario@example.com",
  "full_name": "Nombre Completo",
  "is_active": true,
  "created_at": "2026-02-09T...",
  "updated_at": "2026-02-09T..."
}
```

```bash
# LOGIN
POST /auth/login
Content-Type: application/json

{
  "email": "usuario@example.com",
  "password": "MinimoPalabra8"
}

Response: 200 OK
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "usuario@example.com",
    "full_name": "Nombre Completo",
    "is_active": true,
    "created_at": "2026-02-09T...",
    "updated_at": "2026-02-09T..."
  }
}
```

---

## 🔗 Archivos Clave

### Rutas

| Archivo                          | Propósito      |
| -------------------------------- | -------------- |
| `app/api_server/routers/auth.py` | Endpoints HTTP |

### Lógica

| Archivo                        | Propósito         |
| ------------------------------ | ----------------- |
| `app/services/user_service.py` | Lógica de negocio |
| `app/auth/schemas.py`          | Validación DTOs   |
| `app/auth/security.py`         | Hash + JWT        |

### Datos

| Archivo                                  | Propósito         |
| ---------------------------------------- | ----------------- |
| `app/ports/user_repository.py`           | Interface         |
| `app/adapters/db/sql_user_repository.py` | Implementación BD |
| `app/db/models.py`                       | Modelo SQLAlchemy |
| `app/domain/models.py`                   | Entidad dominio   |

### DI

| Archivo                            | Propósito |
| ---------------------------------- | --------- |
| `app/adapters/api/dependencies.py` | Inyección |

---

## 🗄️ Tabla BD

```sql
users
├── id (UUID, PK)
├── email (VARCHAR 255, UNIQUE, INDEX)
├── full_name (VARCHAR 255)
├── hashed_password (VARCHAR 255)
├── is_active (BOOLEAN, default: true, INDEX)
├── created_at (TIMESTAMP TZ)
└── updated_at (TIMESTAMP TZ)
```

**Índices**:

- `idx_user_email` - Búsqueda por email
- `idx_user_is_active` - Filtro activos

---

## ✔️ Validaciones

### Registro

- ✅ Email: RFC 5322 válido
- ✅ Email: Único en BD
- ✅ Full Name: 2-255 caracteres
- ✅ Password: Mínimo 8 caracteres

### Login

- ✅ Email: Formato válido
- ✅ Email: Existe en BD
- ✅ Password: Hash coincide
- ✅ Usuario: is_active = true

---

## 🔐 Seguridad

| Aspecto                | Implementado          |
| ---------------------- | --------------------- |
| Hash                   | bcrypt + salt         |
| Token                  | JWT HS256             |
| Expiración             | 30 min (configurable) |
| Email                  | Validado RFC 5322     |
| Password               | Min 8 caracteres      |
| Contraseña en Response | ❌ Nunca              |

---

## 🚀 Pasos de Setup

```bash
# 1. Migración BD
alembic upgrade head

# 2. Iniciar
docker compose up -d --build

# 3. Acceder docs
http://localhost:8000/docs
```

---

## 🐍 Usando en Python

```python
import httpx

client = httpx.Client()

# Registro
reg = client.post("http://localhost:8000/auth/register", json={
    "email": "user@example.com",
    "full_name": "User Name",
    "password": "Password123"
})
print(reg.json())

# Login
login = client.post("http://localhost:8000/auth/login", json={
    "email": "user@example.com",
    "password": "Password123"
})
token = login.json()["access_token"]

# Usar token en futuras llamadas
headers = {"Authorization": f"Bearer {token}"}
# response = client.get("...", headers=headers)
```

---

## ₘ🌐 Usando en JavaScript

```javascript
const base = "http://localhost:8000";

// Registro
const reg = await fetch(`${base}/auth/register`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    email: "user@example.com",
    full_name: "User Name",
    password: "Password123",
  }),
});
const user = await reg.json();

// Login
const login = await fetch(`${base}/auth/login`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    email: "user@example.com",
    password: "Password123",
  }),
});
const data = await login.json();
const token = data.access_token;

// Usar token
// fetch("...", {
//   headers: { "Authorization": `Bearer ${token}` }
// })
```

---

## 🔴 Códigos de Error

| Código | Caso             | Mensaje                            |
| ------ | ---------------- | ---------------------------------- |
| 201    | Registro OK      | User creado                        |
| 200    | Login OK         | Token + User                       |
| 400    | Email duplicado  | "ya está registrado"               |
| 400    | Password débil   | "mínimo 8 caracteres"              |
| 401    | Login fallido    | "Credenciales inválidas"           |
| 422    | Validación falla | "invalid email" o "field required" |

---

## 📊 Estructura de Respuestas

### UserResponse

```json
{
  "id": "uuid",
  "email": "string",
  "full_name": "string",
  "is_active": boolean,
  "created_at": "2026-02-09T...",
  "updated_at": "2026-02-09T..."
}
```

### TokenResponse

```json
{
  "access_token": "string",
  "token_type": "bearer",
  "user": { UserResponse }
}
```

### ErrorResponse

```json
{
  "detail": "string"
}
```

---

## 📚 Documentación

| Doc           | Link                                  |
| ------------- | ------------------------------------- |
| **Técnica**   | `docs/7_AUTENTICACION_USUARIOS.md`    |
| **Práctica**  | `docs/GUIA_PRACTICA_AUTENTICACION.md` |
| **Cambios**   | `MAPA_CAMBIOS.md`                     |
| **Checklist** | `CHECKLIST_AUTENTICACION.md`          |
| **Inicio**    | `INICIO_RAPIDO_AUTENTICACION.md`      |

---

## 🧪 Tests

```bash
# Ejecutar todos
pytest tests/test_auth.py -v

# Test específico
pytest tests/test_auth.py::test_register_user -v
```

---

## 🔗 Integración con Pagos

**Próxima tarea**: Agregar `user_id` a Payment

```python
# En app/domain/models.py
class Payment(BaseModel):
    id: UUID
    user_id: UUID  # ← NUEVO
    amount: float
    currency: str
    status: PaymentStatus

# En app/db/models.py
class PaymentRecord(Base):
    id: ...
    user_id: Mapped[UUID] = ...  # ← NUEVO
    amount: ...

# En router payment
async def create_payment(
    request: CreatePaymentRequest,
    current_user = Depends(get_current_user),  # ← Agregar
    service: PaymentService = Depends(...)
):
    return await service.create_payment(
        current_user.id,  # ← Pasar user_id
        request.amount,
        request.currency
    )
```

---

## 🎓 Flujo de Aprendizaje Recomendado

1. 📖 Lee `INICIO_RAPIDO_AUTENTICACION.md` (este doc)
2. 🧪 Prueba endpoints en `/docs`
3. 📚 Lee `docs/7_AUTENTICACION_USUARIOS.md` (arquitectura)
4. 💻 Lee `docs/GUIA_PRACTICA_AUTENTICACION.md` (ejemplos)
5. ✅ Usa `CHECKLIST_AUTENTICACION.md` para verificar
6. 🔍 Revisa código en `app/services/user_service.py`

---

## 📝 Recordatorio: Seguridad

⚠️ **En Producción**:

- [ ] SECRET_KEY en environment variable (no hardcoded)
- [ ] DATABASE_URL segura
- [ ] HTTPS habilitado
- [ ] CORS configurado
- [ ] Rate limiting en login
- [ ] Logs de intentos fallidos

---

## 💡 Tips Útiles

**Decodificar JWT**:

```bash
# En https://jwt.io, pega el token
# O en Python:
import jwt
payload = jwt.decode(token, "YOUR_SECRET_KEY", algorithms=["HS256"])
print(payload)  # {"sub": "user_id", "exp": ...}
```

**Ver tabla BD**:

```bash
psql -U usuario -d pagoflex
SELECT * FROM users;
```

**Limpiar usuarios de prueba**:

```bash
DELETE FROM users WHERE email LIKE '%test%';
```

**Resetear tabla**:

```bash
alembic downgrade -1  # Deshacer última migración
alembic upgrade head  # Reaplicar
```

---

## 🚀 Próximas Características

```
Fase 1 (Actual)  ✅
├─ Registro
├─ Login
└─ JWT

Fase 2 (Próximo)
├─ Refresh tokens
├─ Email verification
└─ 2FA

Fase 3
├─ Roles y permisos
├─ Social login
└─ Password reset
```

---

**Última actualización**: 2026-02-09  
**Estado**: ✅ FUNCIONAL  
**Versión**: 1.0
