"""Configuración compartida para tests."""

import pytest
import respx
from pydantic import SecretStr

from payway_sdk import PaywayClient
from payway_sdk.infrastructure.config import Environment, PaywayConfig


@pytest.fixture
def mock_config() -> PaywayConfig:
    """Configuración de prueba."""
    return PaywayConfig(
        public_key=SecretStr("pk_test_12345"),
        private_key=SecretStr("sk_test_67890"),
        environment=Environment.SANDBOX,
        timeout=10.0,
        max_retries=1,
        log_requests=False,
    )


@pytest.fixture
def client(mock_config: PaywayConfig) -> PaywayClient:
    """Cliente de Payway para testing."""
    return PaywayClient(config=mock_config)


@pytest.fixture
def mock_api():
    """Mock del API de Payway."""
    with respx.mock(base_url="https://developers.decidir.com/api/v2") as respx_mock:
        yield respx_mock


# Datos de prueba comunes

@pytest.fixture
def sample_card_data() -> dict:
    """Datos de tarjeta de prueba."""
    return {
        "card_number": "4111111111111111",
        "card_expiration_month": "12",
        "card_expiration_year": "25",
        "security_code": "123",
        "card_holder": {
            "name": "Juan Perez",
            "identification_type": "DNI",
            "identification_number": "12345678",
        }
    }


@pytest.fixture
def sample_token_response() -> dict:
    """Respuesta de token de prueba."""
    return {
        "id": "token_abc123",
        "status": "active",
        "bin": "411111",
        "last_four_digits": "1111",
        "expiration_month": 12,
        "expiration_year": 25,
        "card_holder": {
            "name": "Juan Perez",
        }
    }


@pytest.fixture
def sample_payment_request() -> dict:
    """Request de pago de prueba."""
    return {
        "site_transaction_id": "ORDER-001",
        "token": "token_abc123",
        "payment_method_id": 1,
        "amount": "1500.00",
        "currency": "ARS",
        "installments": 1,
    }


@pytest.fixture
def sample_payment_response() -> dict:
    """Respuesta de pago de prueba."""
    return {
        "id": 12345,
        "site_transaction_id": "ORDER-001",
        "token": "token_abc123",
        "payment_method_id": 1,
        "amount": 150000,  # En centavos
        "currency": "ARS",
        "installments": 1,
        "status": "approved",
        "authorization_code": "AUTH123",
        "ticket": "TICKET456",
        "card_brand": "visa",
        "bin": "411111",
        "last_four_digits": "1111",
    }


@pytest.fixture
def sample_refund_response() -> dict:
    """Respuesta de devolución de prueba."""
    return {
        "id": 9876,
        "payment_id": 12345,
        "amount": 150000,
        "status": "approved",
    }
