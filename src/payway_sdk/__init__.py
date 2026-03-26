"""
Payway SDK - Cliente Python para Payway Gateway API

Este SDK proporciona una interfaz limpia y robusta para interactuar
con la API de Payway (pasarela de pagos de Argentina).

Ejemplo básico:
    >>> from payway_sdk import PaywayClient
    >>> client = PaywayClient(public_key="pk_xxx", private_key="sk_xxx")
    >>> token = await client.tokens.create(card_data)
    >>> payment = await client.payments.create(payment_data)
"""

from payway_sdk.adapters.client import PaywayClient
from payway_sdk.domain.models import (
    CardData,
    CardHolder,
    CardTokenResponse,
    Payment,
    PaymentRequest,
    PaymentResponse,
    Refund,
    RefundRequest,
    RefundResponse,
    Customer,
    Address,
    PaymentStatus,
    ErrorResponse,
)
from payway_sdk.domain.exceptions import (
    PaywayError,
    PaywayAuthenticationError,
    PaywayValidationError,
    PaywayConnectionError,
    PaywayTimeoutError,
    PaywayRateLimitError,
    PaywayServerError,
    PaywayNotFoundError,
)
from payway_sdk.infrastructure.config import PaywayConfig, Environment

__version__ = "1.0.0"
__author__ = "Pablo Marchionno"

__all__ = [
    # Cliente principal
    "PaywayClient",
    # Configuración
    "PaywayConfig",
    "Environment",
    # Modelos de dominio
    "CardData",
    "CardHolder",
    "CardTokenResponse",
    "Payment",
    "PaymentRequest",
    "PaymentResponse",
    "Refund",
    "RefundRequest",
    "RefundResponse",
    "Customer",
    "Address",
    "PaymentStatus",
    "ErrorResponse",
    # Excepciones
    "PaywayError",
    "PaywayAuthenticationError",
    "PaywayValidationError",
    "PaywayConnectionError",
    "PaywayTimeoutError",
    "PaywayRateLimitError",
    "PaywayServerError",
    "PaywayNotFoundError",
]
