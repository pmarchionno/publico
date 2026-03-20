# Catálogo de Endpoints

Este documento resume los endpoints HTTP disponibles en la plataforma actual. Se agrupan según el servicio FastAPI que los expone dentro del proyecto.

## 1. Servicio `app.main` (Pagoflex Middleware)

> Estado actual: Desde el 26/12/2025 el `docker-compose` del entorno (`services.api.command`) levanta esta aplicación, por lo que los endpoints siguientes están disponibles en `http://localhost:8000`.

| Método | Ruta | Descripción | Entrada principal | Respuesta (HTTP 200) |
|--------|------|-------------|-------------------|----------------------|
| GET | /health | Verificación de estado del servicio. | — | `{ "status": "ok" }` |
| POST | /api/v1/payments | Crea un pago en memoria y devuelve su representación. | JSON: `{ "amount": float, "currency": str }` | Objeto `Payment` con campos `id`, `amount`, `currency`, `status`, `created_at`, `updated_at`.
| POST | /api/v1/payments/{payment_id}/process | Procesa el pago indicado utilizando el mock gateway. | Ruta: `payment_id` (UUID) | Mismo objeto `Payment` con estado actualizado (`COMPLETED` si monto < 1000, `FAILED` en caso contrario).
| GET | /api/v1/payments/{payment_id} | Recupera un pago específico almacenado en memoria. | Ruta: `payment_id` (UUID) | Objeto `Payment` correspondiente o error 404 si no existe.
| POST | /api/v1/transfers | Inicia una transferencia bancaria a través del conector Banco Comercio. | JSON con `source`, `destination`, `body` (detalle debajo) | `{ "paymentId", "originId", "status", "echoed_request", "bankResponse" }`.
| GET | /api/v1/transfers/{originId} | Recupera el estado de una transferencia registrada. | Ruta: `originId` (string) | Objeto `PaymentData` almacenado o error 404 si no existe.

### Notas operativas
- Desde enero 2026 el gateway persiste pagos, transferencias y eventos en PostgreSQL (`payments`, `transfers`, `transfer_events`). El contenedor `api` corre `alembic upgrade head` automáticamente; verificar la base `pagoflex` si se ejecuta por fuera de Docker.
- El repositorio puede degradarse a memoria configurando `PERSISTENCE_BACKEND=memory` (por defecto `database`).
- El procesamiento simula una pasarela mediante `MockPaymentGateway`; no hay interacción con proveedores externos reales.
- El conector Banco Comercio requiere `BDC_BASE_URL`, `BDC_CLIENT_ID`, `BDC_CLIENT_SECRET`, `BDC_SECRET_KEY` y `TRANSFER_CONNECTOR_MODE` (ver `config/settings.py`).
- La variable `TRANSFER_CONNECTOR_MODE` define si el gateway usa el conector simulado (`mock`, valor por defecto) o el conector real de Banco Comercio (`banco_comercio`, `live`, `prod`). Con el modo simulado se puede forzar un rechazo enviando `concept: "REJECT"` o `concept: "FAIL"` en el body.
- Ejemplo real (26/12/2025): `POST /api/v1/payments` con `{ "amount": 100.0, "currency": "USD" }` devolvió el pago `5decdb50-25d3-4850-ba84-c5de1e41c278` con estado `PENDING`; `GET /api/v1/payments/5decdb50-25d3-4850-ba84-c5de1e41c278` confirmó el mismo estado.

#### Contrato `POST /api/v1/transfers`

```json
{
	"source": {
		"addressType": "CBU_CVU",
		"address": "0000000000000000000000",
		"owner": {
			"personIdType": "CUI",
			"personId": "20304050607",
			"personName": "John Doe"
		}
	},
	"destination": {
		"addressType": "CBU_CVU",
		"address": "9999999999999999999999",
		"owner": {
			"personIdType": "CUI",
			"personId": "20987654321",
			"personName": "Jane Roe"
		}
	},
	"body": {
		"amount": "123.45",
		"currency": "ARS",
		"description": "Test transfer",
		"concept": "VAR"
	}
}
```

Respuesta (200):

```json
{
	"paymentId": "e7fc8e79-7ca3-48c0-9c5b-0f26ff3bd2d2",
	"originId": "6f0b9ea9541349f5b0399d0118c7d36d",
	"status": "AUTHORIZED",
	"echoed_request": { /* payload original normalizado */ },
	"bankResponse": { "statusCode": 0, "message": "Transferencia creada con exito", ... }
}
```

Errores esperados: `400` por validaciones de esquema (p.ej. monto negativo), `502` si falla la comunicación con el banco.

## 2. Servicio `app.api_server.main` (API Server Modular)

| Método | Ruta | Descripción | Respuesta (HTTP 200) |
|--------|------|-------------|----------------------|
| GET | /health | Verificación de estado del API modular. | `{ "status": "ok", "service": "api_server" }` |
| GET | /payments/ | Placeholder informativo del módulo de pagos. | `{ "message": "Payments module" }` |
| GET | /kyc/ | Placeholder informativo del módulo KYC. | `{ "message": "KYC module" }` |

### Notas operativas
- Ambos endpoints (`/payments/` y `/kyc/`) son placeholders y no ofrecen lógica de negocio aún.
- Para exponer este servicio se debe iniciar el módulo `app.api_server.main` (no forma parte del `docker compose` por defecto).

## 3. Futuras extensiones
- Cuando se incorporen repositorios persistentes o conectores reales, actualizar este documento con los nuevos endpoints y sus contratos.
- Añadir ejemplos curl/postman y códigos de estados adicionales (400, 404, 500) en futuras iteraciones.
