# Referencia de Endpoints BDC

## Estructura actual por actores: APP, Middleware y Banco de Comercio

**Versión:** 2026-03-08  
**Fuente de verdad:** `app/api_server/routers/bdc_auth.py` y montaje en `app/main.py`

---

## 1) Vista general de integración

La APP **solo consume endpoints del Middleware** (`/bdc/...`).  
El Middleware valida identidad/autorización y luego consume el endpoint homólogo (o equivalente) en Banco de Comercio (BDC).

### Actores

- **APP**: cliente mobile/web/backend que llama al Middleware.
- **Middleware**: API FastAPI (`gateway_p`) que valida JWT de usuario, aplica reglas y reenvía a BDC.
- **Banco de Comercio (BDC)**: API externa bancaria.

---

## 2) Endpoint base (APP -> Middleware)

- **Base path BDC en Middleware:** `/bdc`
- **Host local típico:** `http://localhost:8000`

> Ejemplo completo: `POST http://localhost:8000/bdc/transfer-request?token=<JWT_APP>`

---

## 3) Mapa de endpoints vigente (APP -> Middleware -> BDC)

| Dominio | APP -> Middleware | Middleware -> BDC | Auth APP -> Middleware | Firma `X-SIGNATURE` |
|---|---|---|---|---|
| Autenticación BDC | `POST /bdc/auth` | `POST /auth` | No | No |
| Healthcheck BDC | `GET /bdc/healthcheck` | `GET /healthcheck` | No | No |
| Cuentas | `GET /bdc/accounts?token=<JWT_APP>` | `GET /accounts` | JWT en query `token` | No |
| Cuentas | `GET /bdc/accounts/info/{cbu_cvu_alias}?token=<JWT_APP>` | `GET /accounts/info/{cbu_cvu_alias}` | JWT en query `token` | No |
| Subcuentas CVU | `POST /bdc/accounts/get-cvu-accounts?token=<JWT_APP>` | `POST /accounts/get-cvu-accounts` | JWT en query `token` | Sí |
| Crear subcuenta | `POST /bdc/sub-account?token=<JWT_APP>&tipo=empresa|p2p` | `POST /sub-account` | JWT en query `token` | Sí |
| Consultar subcuenta | `GET /bdc/sub-account/{origin_id}?token=<JWT_APP>` | `GET /sub-account/{origin_id}` | JWT en query `token` | No |
| Actualizar subcuenta/alias | `PATCH /bdc/sub-account/{cvu}?token=<JWT_APP>` | `PATCH /sub-account/{cvu}` | JWT en query `token` | Sí |
| Movimientos | `POST /bdc/movements/{cbu_cvu_alias}?token=<JWT_APP>` | `POST /movements/{cbu_cvu_alias}` | JWT en query `token` | Sí |
| Datos de entidad | `POST /bdc/global/data/get-entity?token=<JWT_APP>` | `POST /global/data/get-entity` | JWT en query `token` | Sí |
| Últimos movimientos (legacy) | `POST /bdc/apiV1/ultimosMovimientos?token=<JWT_APP>` | `POST /apiV1/ultimosMovimientos` | JWT en query `token` | No |
| Crear transferencia | `POST /bdc/transfer-request?token=<JWT_APP>` | `POST /movements/transfer-request` | JWT en query `token` | Sí |
| Estado transferencia | `GET /bdc/movements/transfer-request/{origin_id}?token=<JWT_APP>` | `GET /movements/transfer-request/{origin_id}` | JWT en query `token` | No |
| Conceptos SNP | `GET /bdc/snp-concepts?token=<JWT_APP>` | `GET /get-snp-concepts` | JWT en query `token` | No |
| Alias lookup | `POST /bdc/alias?token=<JWT_APP>` | `POST /alias` | JWT en query `token` | Sí |
| Alias create | `POST /bdc/alias-create?token=<JWT_APP>` | `POST /alias-create` | JWT en query `token` | Sí |
| Alias edit | `PATCH /bdc/alias-edit?token=<JWT_APP>` | `POST /alias-edit` | JWT en query `token` | Sí |
| Alias remove | `POST /bdc/alias-remove?token=<JWT_APP>` | `POST /alias-remove` | JWT en query `token` | Sí |
| Estado auth BDC (debug) | `GET /bdc/auth/status` | Servicio interno de token BDC | JWT en `Authorization: Bearer` | No |
| Refresh auth BDC (debug) | `POST /bdc/auth/refresh` | Fuerza renovación (usa `/auth` internamente) | JWT en `Authorization: Bearer` | No |

---

## 4) Convención de autenticación actual

### Endpoints de negocio BDC (la mayoría)

- Requieren `token=<JWT_APP>` en **query param**.
- El Middleware valida ese JWT y recién luego llama a BDC con su token bancario.

### Endpoints de estado/refresh de auth

- Requieren `Authorization: Bearer <JWT_APP>` (dependency `get_current_user`).
- No usan query `token`.

---

## 5) Ejemplos rápidos (APP -> Middleware)

### 5.1 Obtener cuentas

```bash
curl -X GET "http://localhost:8000/bdc/accounts?token=<JWT_APP>"
```

### 5.2 Crear transferencia

```bash
curl -X POST "http://localhost:8000/bdc/transfer-request?token=<JWT_APP>" \
  -H "Content-Type: application/json" \
  -d '{
    "cbu_cvu_destino": "1111111111222222222233",
    "monto": 1500.00,
    "descripcion": "Pago"
  }'
```

### 5.3 Consultar estado de transferencia

```bash
curl -X GET "http://localhost:8000/bdc/movements/transfer-request/<origin_id>?token=<JWT_APP>"
```

---

## 6) Notas de implementación vigentes

- El router BDC está definido con prefijo `"/bdc"` en `app/api_server/routers/bdc_auth.py`.
- En la app principal (`app/main.py`) se incluye sin prefijo adicional: `app.include_router(bdc_router)`.
- Para múltiples operaciones, el Middleware maneja renovación de token BDC al recibir `401` del banco.

---

## 7) Estado del documento

Documento **actualizado a la estructura real del código** al 2026-03-08.
