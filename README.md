# Payway SDK para Python

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

SDK Python profesional para integrar con **Payway Gateway API** (pasarela de pagos de Argentina, ex-Decidir).

## 🚀 Características

- ✅ **Python 3.12+** con type hints completos
- ✅ **Async/await** nativo con soporte síncrono
- ✅ **Arquitectura hexagonal/limpia**
- ✅ **Cliente HTTP robusto** con httpx, retries y backoff exponencial
- ✅ **Modelos Pydantic v2** flexibles (toleran campos adicionales)
- ✅ **Manejo de errores** con jerarquía de excepciones
- ✅ **Logging estructurado** con structlog
- ✅ **Configuración por entorno** (.env, variables de entorno)
- ✅ **Tests completos** con pytest y mocks

## 📦 Instalación

```bash
# Desde PyPI (cuando se publique)
pip install payway-sdk

# Desde el repositorio
pip install git+https://github.com/pmarchionno/publico.git

# Desarrollo local
git clone https://github.com/pmarchionno/publico.git
cd payway-middleware
pip install -e ".[dev]"
```

## 🔧 Configuración

### Variables de entorno

```bash
# .env
PAYWAY_PUBLIC_KEY=pk_test_xxxxxxxx    # Para tokenización
PAYWAY_PRIVATE_KEY=sk_test_xxxxxxxx   # Para operaciones
PAYWAY_ENVIRONMENT=sandbox            # sandbox o production
```

### Código

```python
from payway_sdk import PaywayClient

# Opción 1: Desde variables de entorno
client = PaywayClient()

# Opción 2: Credenciales explícitas
client = PaywayClient(
    public_key="pk_test_xxx",
    private_key="sk_test_xxx",
    environment="sandbox",
)

# Opción 3: Helpers de fábrica
client = PaywayClient.sandbox("pk_test_xxx", "sk_test_xxx")
client = PaywayClient.production("pk_live_xxx", "sk_live_xxx")
```

## 📖 Uso Básico

### Tokenizar una tarjeta

```python
from payway_sdk import PaywayClient, CardData, CardHolder

async with PaywayClient() as client:
    token = await client.tokens.create(CardData(
        card_number="4111111111111111",
        card_expiration_month="12",
        card_expiration_year="25",
        security_code="123",
        card_holder=CardHolder(name="Juan Perez"),
    ))
    
    print(f"Token: {token.id}")
    print(f"BIN: {token.bin}")
    print(f"Últimos 4: {token.last_four_digits}")
```

### Procesar un pago

```python
from decimal import Decimal
from payway_sdk import PaymentRequest, Customer

payment = await client.payments.create(PaymentRequest(
    site_transaction_id="ORDER-001",
    token=token.id,
    payment_method_id=1,  # 1=Visa, 15=Mastercard, etc.
    amount=Decimal("1500.00"),
    installments=3,
    customer=Customer(
        email="cliente@email.com",
        first_name="Juan",
        last_name="Perez",
    ),
))

if payment.is_approved:
    print(f"✓ Pago aprobado: {payment.authorization_code}")
else:
    print(f"✗ Pago rechazado: {payment.status}")
```

### Consultar un pago

```python
payment = await client.payments.get(12345)
print(f"Estado: {payment.status}")
```

### Realizar una devolución

```python
# Devolución total
refund = await client.refunds.create(payment_id=12345)

# Devolución parcial
refund = await client.refunds.create(
    payment_id=12345,
    amount=Decimal("500.00"),
    reason="Producto defectuoso",
)
```

### Listar devoluciones

```python
refunds = await client.refunds.list(payment_id=12345)
for refund in refunds:
    print(f"Devolución #{refund.id}: ${refund.amount/100:.2f}")
```

## 🔄 Uso Síncrono

Para código no-async, usa los métodos `*_sync`:

```python
from payway_sdk import PaywayClient

client = PaywayClient()

# Tokenizar
token = client.tokens.create_sync(card_data)

# Pagar
payment = client.payments.create_sync(payment_data)

# Devolución
refund = client.refunds.create_sync(payment_id=123)
```

## ⚠️ Manejo de Errores

```python
from payway_sdk import (
    PaywayError,              # Base
    PaywayAuthenticationError,  # 401, 403
    PaywayValidationError,      # 400, 422
    PaywayNotFoundError,        # 404
    PaywayTimeoutError,         # Timeout
    PaywayConnectionError,      # Network error
    PaywayRateLimitError,       # 429
    PaywayServerError,          # 5xx
)

try:
    payment = await client.payments.create(data)
except PaywayValidationError as e:
    print(f"Error de validación: {e.message}")
    for error in e.validation_errors:
        print(f"  - {error['field']}: {error['message']}")
except PaywayTimeoutError as e:
    # IMPORTANTE: La transacción puede haberse procesado
    print(f"Timeout después de {e.timeout_seconds}s")
    print("Verificar estado del pago antes de reintentar")
except PaywayError as e:
    print(f"Error: {e}")
    print(f"Request ID: {e.request_id}")
```

## 🔢 Códigos de Método de Pago

| ID | Marca |
|----|-------|
| 1 | Visa |
| 15 | Mastercard |
| 65 | American Express |
| 23 | Tarjeta Naranja |
| 24 | Tarjeta Shopping |
| 31 | Cabal |
| 37 | Argencard |
| 43 | Diners |
| 63 | Cencosud |
| 104 | Maestro |

## 📁 Estructura del Proyecto

```
payway-middleware/
├── src/payway_sdk/
│   ├── __init__.py          # Exports públicos
│   ├── adapters/            # Cliente y servicios
│   │   ├── client.py        # PaywayClient
│   │   ├── tokens.py        # TokenService
│   │   ├── payments.py      # PaymentService
│   │   └── refunds.py       # RefundService
│   ├── domain/              # Modelos y excepciones
│   │   ├── models.py        # Modelos Pydantic
│   │   └── exceptions.py    # Jerarquía de errores
│   └── infrastructure/      # HTTP, config, logging
│       ├── config.py        # PaywayConfig
│       ├── http_client.py   # HTTPClient
│       └── logging.py       # Logging estructurado
├── tests/
│   ├── unit/                # Tests unitarios
│   └── integration/         # Tests con mocks
├── examples/                # Ejemplos de uso
├── pyproject.toml
└── README.md
```

## 🧪 Testing

```bash
# Instalar dependencias de desarrollo
pip install -e ".[dev]"

# Ejecutar todos los tests
pytest

# Con cobertura
pytest --cov=src/payway_sdk --cov-report=html

# Solo tests unitarios
pytest tests/unit/

# Solo tests de integración
pytest tests/integration/
```

## 📋 Resumen de Endpoints

| Servicio | Método | Endpoint | Descripción |
|----------|--------|----------|-------------|
| **Tokens** | POST | `/tokens` | Tokenizar tarjeta |
| | GET | `/tokens/{id}` | Obtener token |
| | DELETE | `/tokens/{id}` | Eliminar token |
| **Payments** | POST | `/payments` | Crear pago |
| | GET | `/payments/{id}` | Obtener pago |
| | GET | `/payments` | Listar pagos |
| | PUT | `/payments/{id}` | Capturar pre-auth |
| | DELETE | `/payments/{id}` | Anular pago |
| **Refunds** | POST | `/payments/{id}/refunds` | Crear devolución |
| | GET | `/payments/{id}/refunds` | Listar devoluciones |
| | DELETE | `/payments/{id}/refunds/{rid}` | Anular devolución |

## 🔗 Documentación de Payway

- [Portal de Desarrolladores](https://developers.decidir.com)
- [Documentación API](https://documentacion-ventasonline.payway.com.ar)

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE)

## 👨‍💻 Autor

Desarrollado por Pablo Marchionno

---

**⚠️ Nota:** Este SDK es para uso en **sandbox/testing** por defecto. Para producción, asegúrate de:
1. Usar credenciales de producción
2. Configurar `environment="production"`
3. Implementar manejo adecuado de errores
4. No loggear datos sensibles
