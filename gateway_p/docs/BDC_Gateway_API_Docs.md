# 📚 BDC Gateway API - Documentación Completa

## 🔐 AUTENTICACIÓN

### `POST /bdc/auth`
**Descripción:** Autenticación interna con BDC

| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Request Body** | - | Usa credenciales de configuración del servidor |
| **Response** | `BDCAuthFullResponse` | Ver abajo |

**Response `BDCAuthFullResponse`:**
```json
{
  "statusCode": 0,
  "data": {
    "accessToken": "string (JWT)",
    "expiresIn": 3600
  },
  "time": "2026-03-20T18:00:00Z"
}
```

---

### `GET /bdc/healthcheck`
**Descripción:** Verifica estado del servicio BDC

| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Request** | - | Sin parámetros |
| **Response** | `BDCHealthcheckResponse` | Ver abajo |

**Response `BDCHealthcheckResponse`:**
```json
{
  "statusCode": 0,
  "time": "2026-03-20T18:00:00Z"
}
```

---

### `GET /bdc/auth/status`
**Descripción:** Estado de autenticación actual

| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Headers** | `Authorization: Bearer <JWT>` | Token JWT requerido |
| **Response** | `dict` | Cache info y user_id |

---

### `POST /bdc/auth/refresh`
**Descripción:** Fuerza renovación de token BDC

| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Headers** | `Authorization: Bearer <JWT>` | Token JWT requerido |
| **Response** | `dict` | Status, message, cache_info |

---

## 🏦 CUENTAS

### `GET /bdc/accounts`
**Descripción:** Lista cuentas de la entidad

| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Query Params** | `token: string` | JWT requerido |
| **Response** | `BDCAccountsResponse` | Ver abajo |

**Response `BDCAccountsResponse`:**
```json
{
  "statusCode": 0,
  "data": {
    "entityType": "string",
    "entityCode": "string",
    "entityName": "string",
    "accounts": [
      {
        "accountId": "ARG-00432-001234567",
        "accountType": "CHECKING_ACCOUNT",
        "accountLabel": "alias.ejemplo.pf",
        "accountNumber": "string",
        "accountRouting": [
          {
            "addressType": "CBU_CVU",
            "address": "0000000000000000000000"
          }
        ],
        "owners": [
          {
            "personId": "20123456789",
            "personIdType": "CUI",
            "personName": "Nombre Apellido",
            "personType": "LEGAL"
          }
        ],
        "balances": [
          {
            "balanceCurrency": "032",
            "balanceConcept": "AVAILABLE",
            "balanceAmount": 10000.00,
            "balanceWithheldAmount": 0.00
          }
        ],
        "info": {
          "status": "ACTIVE",
          "networks": ["COELSA"],
          "currencies": ["032"],
          "taxes": [],
          "apiOperable": true,
          "parentAccount": false
        }
      }
    ]
  },
  "time": "2026-03-20T18:00:00Z"
}
```

---

### `GET /bdc/accounts/info/{cbu_cvu_alias}`
**Descripción:** Info de cuenta por CBU/CVU/Alias

| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Path Params** | `cbu_cvu_alias: string` | CBU, CVU o Alias |
| **Query Params** | `token: string` | JWT requerido |
| **Response** | `BDCAccountInfoResponse` | Ver abajo |

**Response `BDCAccountInfoResponse`:**
```json
{
  "statusCode": 0,
  "data": {
    "owners": [
      {
        "id": "20123456789",
        "displayName": "NOMBRE APELLIDO",
        "idType": "CUI",
        "isPhysicalPerson": true
      }
    ],
    "type": "CVU",
    "isActive": true,
    "currency": "032",
    "label": "alias.ejemplo.pf",
    "accountRouting": {
      "scheme": "CBU_CVU",
      "address": "0000000000000000000000"
    },
    "entityRouting": {
      "type": "BANK",
      "name": "BANCO DE COMERCIO",
      "code": "432"
    }
  },
  "time": "2026-03-20T18:00:00Z"
}
```

---

## 📁 SUBCUENTAS

### `POST /bdc/accounts/get-cvu-accounts`
**Descripción:** Lista subcuentas CVU

| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Query Params** | `token: string` | JWT requerido |
| **Request Body** | `BDCGetCvuAccountsRequest` | Ver abajo |
| **Response** | `BDCResponse` | Respuesta genérica |

**Request `BDCGetCvuAccountsRequest`:**
```json
{
  "cbu": "0000000000000000000000",
  "pageOffset": 1,
  "pageSize": 10,
  "sortDirection": "ASC"
}
```

---

### `POST /bdc/sub-account`
**Descripción:** Crea subcuenta CVU

| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Query Params** | `token: string` | JWT requerido |
| **Query Params** | `tipo: string` | `"p2p"` o `"empresa"` (default: empresa) |
| **Request Body** | - | Servidor genera originId y alias |
| **Response** | `dict` | Ver abajo |

**Response:**
```json
{
  "statusCode": 0,
  "data": {
    "accountId": "ARG-00432-00100325154",
    "accountType": "CHECKING_ACCOUNT",
    "accountLabel": "nombre.apellido.pf",
    "accountRouting": [
      {
        "addressType": "CBU_CVU",
        "address": "0000003200032512345678"
      }
    ],
    "owners": [
      {
        "personId": "20123456789",
        "personIdType": "CUI",
        "personName": "NOMBRE APELLIDO",
        "personType": "OWNER"
      }
    ],
    "entityRouting": {
      "entityType": "BANK",
      "entityCode": "432",
      "entityName": "BANCO DE COMERCIO"
    },
    "info": {
      "status": "ACTIVE",
      "currencies": ["032"]
    }
  },
  "time": "2026-03-20T18:00:00Z"
}
```

---

### `GET /bdc/sub-account/{origin_id}`
**Descripción:** Consulta subcuenta por originId

| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Path Params** | `origin_id: string` | ID único de la subcuenta |
| **Query Params** | `token: string` | JWT requerido |
| **Response** | `BDCSubAccountQueryResponse` | Datos de la subcuenta |

---

### `PATCH /bdc/sub-account/{cvu}`
**Descripción:** Actualiza alias/estado de subcuenta

| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Path Params** | `cvu: string` | CVU de 22 dígitos |
| **Query Params** | `token: string` | JWT requerido |
| **Request Body** | `BDCUpdateSubAccountRequest` | Ver abajo |
| **Response** | `BDCUpdateAccountResponse` | Ver abajo |

**Request `BDCUpdateSubAccountRequest`:**
```json
{
  "status": "ACTIVE",
  "accountLabel": "nuevo.alias.pf"
}
```
*Nota: Ambos campos son opcionales, enviar al menos uno.*

**Response `BDCUpdateAccountResponse`:**
```json
{
  "statusCode": 0,
  "message": "Cuenta actualizada exitosamente",
  "data": {
    "accountId": "ARG-00432-001234567",
    "status": "ACTIVE",
    "accountLabel": "nuevo.alias.pf",
    "updatedAt": "2026-03-20T18:00:00Z"
  },
  "time": "2026-03-20T18:00:00Z"
}
```

---

## 📊 MOVIMIENTOS

### `POST /bdc/movements/{cbu_cvu_alias}`
**Descripción:** Lista movimientos de cuenta

| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Path Params** | `cbu_cvu_alias: string` | CBU, CVU o Alias |
| **Query Params** | `token: string` | JWT requerido |
| **Request Body** | `BDCMovementsRequest` | Ver abajo |
| **Response** | `BDCMovementsResponse` | Ver abajo |

**Request `BDCMovementsRequest`:**
```json
{
  "startDate": "2026-01-01",
  "endDate": "2026-03-20",
  "pageSize": 50,
  "pageOffset": 1
}
```

**Response `BDCMovementsResponse`:**
```json
{
  "statusCode": 0,
  "message": "OK",
  "time": "2026-03-20T18:00:00Z",
  "data": {
    "sdtEstadoDeCuenta": {
      "productoUID": "string",
      "fechaDesde": "2026-01-01",
      "fechaHasta": "2026-03-20",
      "saldoPartida": 10000.00,
      "totalRegistros": 25,
      "movimientos": {
        "SdtsBTMovimiento": [
          {
            "movimientoUId": "123456",
            "fechaMov": "2026-03-20",
            "fechaSis": "2026-03-20",
            "horaSis": "14:30:00",
            "concepto": "TRANSFERENCIA",
            "referencia": "REF123",
            "numeroCheque": "",
            "debitoCredito": "C",
            "moneda": "032",
            "importe": 5000.00,
            "saldo": 15000.00,
            "datosAdicionales": {
              "sBTDatoAdicional": {
                "idCoelsa": "123",
                "cuitOrigen": "20111111111",
                "cbuOrigen": "0000000000000000000001",
                "cuitDestino": "20222222222",
                "cbuDestino": "0000000000000000000002",
                "titular": "NOMBRE ORIGEN"
              }
            }
          }
        ]
      }
    }
  }
}
```

---

### `POST /bdc/apiV1/ultimosMovimientos`
**Descripción:** Últimos movimientos (legacy)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Query Params** | `token: string` | JWT requerido |
| **Request Body** | `BDCUltimosMovimientosRequest` | Ver abajo |
| **Response** | `dict` | Respuesta directa de BDC |

**Request `BDCUltimosMovimientosRequest`:**
```json
{
  "cbu": "0000000000000000000000",
  "cvu": "",
  "startDate": "2026-01-01",
  "endDate": "2026-03-20",
  "pageSize": 1,
  "pageOffset": 50
}
```

---

## 💸 TRANSFERENCIAS

### `POST /bdc/transfer-request`
**Descripción:** Crea transferencia (simplificado y seguro)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Query Params** | `token: string` | JWT (opcional) |
| **Request Body** | `BDCTransferRequestSimpleInput` | Ver abajo |
| **Response** | `BDCTransferSuccessResponse` | Ver abajo |

**Request `BDCTransferRequestSimpleInput`:**
```json
{
  "originCbuCvu": "0000000000000000000001",
  "destinationCbuCvu": "0000000000000000000002",
  "amount": 1500.50,
  "description": "Pago de servicios",
  "concept": "VAR",
  "currencyId": "032"
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `originCbuCvu` | string(22) | ✅ | CBU/CVU origen |
| `destinationCbuCvu` | string(22) | ✅ | CBU/CVU destino |
| `amount` | float | ✅ | Monto (> 0) |
| `description` | string | ❌ | Descripción (default: "Transferencia") |
| `concept` | string(3) | ❌ | Concepto: VAR, ALQ, CUO, etc. (default: "VAR") |
| `currencyId` | string | ❌ | Moneda: 032=ARS, 840=USD (default: "032") |

**Response `BDCTransferSuccessResponse`:**
```json
{
  "statusCode": 0,
  "message": "Transferencia procesada exitosamente",
  "time": "2026-03-20T18:00:00Z",
  "updatedBalance": "8500.00"
}
```

---

### `GET /bdc/movements/transfer-request/{origin_id}`
**Descripción:** Consulta estado de transferencia

| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Path Params** | `origin_id: string` | ID único de la transferencia |
| **Query Params** | `token: string` | JWT (opcional) |
| **Response** | `BDCTransferDetailResponse` | Ver abajo |

**Response `BDCTransferDetailResponse`:**
```json
{
  "statusCode": 0,
  "data": {
    "request": {
      "originId": "1234567890",
      "from": {
        "addressType": "CBU_CVU",
        "address": "0000000000000000000001",
        "owner": {
          "personIdType": "CUI",
          "personId": "20111111111"
        }
      },
      "to": {
        "addressType": "CBU_CVU",
        "address": "0000000000000000000002",
        "owner": {
          "personIdType": "CUI",
          "personId": "20222222222"
        }
      },
      "body": {
        "currencyId": "032",
        "amount": 1500.50,
        "description": "Pago de servicios",
        "concept": "VAR"
      }
    },
    "response": {
      "respuesta": {
        "codigo": "00",
        "descripcion": "APROBADA"
      },
      "credito": {
        "cuit": "20222222222",
        "banco": "432",
        "cuenta": { "cbu": "0000000000000000000002" }
      },
      "importe": {
        "moneda": "032",
        "importe": 1500.50
      },
      "fechaHoraEjecucion": "2026-03-20T18:00:00Z",
      "objeto": {
        "tipo": "TRANSFER",
        "id": "TRF123456",
        "estado": {
          "codigo": "COMPLETED",
          "descripcion": "Transferencia completada"
        }
      }
    },
    "estado": "COMPLETED"
  },
  "time": "2026-03-20T18:00:00Z"
}
```

---

### `GET /bdc/snp-concepts`
**Descripción:** Lista conceptos SNP para transferencias

| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Query Params** | `token: string` | JWT requerido |
| **Response** | `BDCSnpConceptsResponse` | Ver abajo |

**Response `BDCSnpConceptsResponse`:**
```json
{
  "statusCode": 0,
  "data": {
    "concepts": [
      { "id": "VAR", "description": "Varios" },
      { "id": "ALQ", "description": "Alquiler" },
      { "id": "CUO", "description": "Cuota" },
      { "id": "EXP", "description": "Expensas" },
      { "id": "FAC", "description": "Factura" },
      { "id": "PRE", "description": "Préstamo" },
      { "id": "SEG", "description": "Seguro" },
      { "id": "HON", "description": "Honorarios" },
      { "id": "HAB", "description": "Haberes" }
    ]
  },
  "time": "2026-03-20T18:00:00Z"
}
```

---

## 🏷️ ALIAS

### `POST /bdc/alias`
**Descripción:** Consulta alias

| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Query Params** | `token: string` | JWT (opcional) |
| **Request Body** | `BDCAliasLookupRequest` | Ver abajo |
| **Response** | `BDCResponse` | Respuesta genérica |

**Request `BDCAliasLookupRequest`:**
```json
{
  "tipoConsulta": "ALIAS",
  "valorConsulta": "alias.ejemplo.pf"
}
```

---

### `POST /bdc/alias-create`
**Descripción:** Crea alias

| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Query Params** | `token: string` | JWT requerido |
| **Request Body** | `BDCAliasCreateRequest` | Ver abajo |
| **Response** | `BDCResponse` | Respuesta genérica |

**Request `BDCAliasCreateRequest`:**
```json
{
  "cuitTitular": "20123456789",
  "cbuCuenta": "0000000000000000000000",
  "valorAliasCVU": "nuevo.alias.pf"
}
```

---

### `PATCH /bdc/alias-edit`
**Descripción:** Edita alias

| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Query Params** | `token: string` | JWT requerido |
| **Request Body** | `BDCAliasEditRequest` | Ver abajo |
| **Response** | `BDCResponse` | Respuesta genérica |

**Request `BDCAliasEditRequest`:**
```json
{
  "cuitTitular": "20123456789",
  "cbuCuenta": "0000000000000000000000",
  "aliasNuevo": "nuevo.alias.pf",
  "aliasAnterior": "viejo.alias.pf"
}
```

---

### `POST /bdc/alias-remove`
**Descripción:** Elimina alias

| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Query Params** | `token: string` | JWT requerido |
| **Request Body** | `BDCAliasRemoveRequest` | Ver abajo |
| **Response** | `BDCResponse` | Respuesta genérica |

**Request `BDCAliasRemoveRequest`:**
```json
{
  "cuitTitular": "20123456789",
  "cbuCuenta": "0000000000000000000000",
  "valorAliasCVU": "alias.a.eliminar.pf"
}
```

---

## 👤 INFORMACIÓN PERSONAL

### `POST /bdc/global/data/get-entity`
**Descripción:** Info de entidad por CBU/CVU/Alias

| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Query Params** | `token: string` | JWT requerido |
| **Request Body** | `BDCGetEntityRequest` | Ver abajo |
| **Response** | `BDCResponse` | Respuesta genérica |

**Request `BDCGetEntityRequest`:**
```json
{
  "addressType": "CBU_CVU",
  "address": "0000000000000000000000"
}
```

---

## 📝 Códigos de Estado (statusCode)

| Código | Descripción |
|--------|-------------|
| `0` | ✅ Éxito |
| `1` | Error de validación |
| `2` | Error de autenticación |
| `3` | Origin ID duplicado |
| `4` | Cuenta no encontrada |
| `5+` | Otros errores de negocio |

---

## 🔐 Autenticación

Todos los endpoints (excepto `/bdc/auth` y `/bdc/healthcheck`) requieren un token JWT válido.

El token se envía como **query parameter**: `?token=<JWT>`

---

*Documentación generada por Jinzo - Hitofusion*
*Fecha: 2026-03-20*
