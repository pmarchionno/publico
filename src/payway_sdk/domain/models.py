"""
Modelos de dominio para Payway SDK.

Todos los modelos usan Pydantic v2 con:
- extra="allow" para tolerancia a campos adicionales
- Campos opcionales para backward compatibility
- Validación estricta donde corresponde
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BasePaywayModel(BaseModel):
    """Modelo base con configuración común para todos los modelos."""

    model_config = ConfigDict(
        extra="allow",  # Permite campos adicionales no definidos
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
        use_enum_values=True,
    )


# =============================================================================
# ENUMS
# =============================================================================


class PaymentStatus(str, Enum):
    """Estados posibles de un pago."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ANNULLED = "annulled"
    REFUNDED = "refunded"
    PARTIAL_REFUND = "partial_refund"
    REVIEW = "review"
    PRE_APPROVED = "pre_approved"


class CardBrand(str, Enum):
    """Marcas de tarjeta soportadas."""

    VISA = "visa"
    MASTERCARD = "mastercard"
    AMEX = "amex"
    CABAL = "cabal"
    NARANJA = "naranja"
    NATIVA = "nativa"
    TARJETA_SHOPPING = "tarshop"
    CENCOSUD = "cencosud"
    DINERS = "diners"
    ARGENCARD = "argencard"
    UNKNOWN = "unknown"


class TransactionType(str, Enum):
    """Tipos de transacción."""

    SALE = "sale"
    AUTHORIZATION = "authorization"
    CAPTURE = "capture"
    VOID = "void"
    REFUND = "refund"


class Currency(str, Enum):
    """Monedas soportadas."""

    ARS = "ARS"
    USD = "USD"


# =============================================================================
# MODELOS DE TARJETA / TOKEN
# =============================================================================


class CardHolder(BasePaywayModel):
    """Datos del titular de la tarjeta."""

    name: str = Field(..., min_length=1, max_length=100, description="Nombre del titular")
    identification_type: str | None = Field(
        default="DNI",
        alias="identification_type",
        description="Tipo de documento (DNI, CUIL, CUIT, etc.)",
    )
    identification_number: str | None = Field(
        default=None,
        alias="identification_number",
        description="Número de documento",
    )
    email: str | None = Field(default=None, description="Email del titular")
    phone: str | None = Field(default=None, description="Teléfono del titular")


class CardData(BasePaywayModel):
    """Datos de la tarjeta para tokenización."""

    card_number: str = Field(
        ...,
        min_length=13,
        max_length=19,
        description="Número de tarjeta (sin espacios ni guiones)",
    )
    card_expiration_month: str = Field(
        ...,
        min_length=2,
        max_length=2,
        description="Mes de vencimiento (MM)",
    )
    card_expiration_year: str = Field(
        ...,
        min_length=2,
        max_length=4,
        description="Año de vencimiento (YY o YYYY)",
    )
    security_code: str = Field(
        ...,
        min_length=3,
        max_length=4,
        alias="cvv",
        description="Código de seguridad (CVV/CVC)",
    )
    card_holder: CardHolder = Field(..., alias="card_holder", description="Datos del titular")

    @field_validator("card_number")
    @classmethod
    def validate_card_number(cls, v: str) -> str:
        """Valida y limpia el número de tarjeta."""
        cleaned = "".join(c for c in v if c.isdigit())
        if len(cleaned) < 13 or len(cleaned) > 19:
            raise ValueError("Número de tarjeta inválido")
        return cleaned

    @field_validator("card_expiration_month")
    @classmethod
    def validate_month(cls, v: str) -> str:
        """Valida el mes de vencimiento."""
        month = int(v)
        if month < 1 or month > 12:
            raise ValueError("Mes de vencimiento inválido")
        return v.zfill(2)

    @field_validator("card_expiration_year")
    @classmethod
    def validate_year(cls, v: str) -> str:
        """Normaliza el año a formato YY."""
        if len(v) == 4:
            return v[2:]
        return v.zfill(2)


class CardTokenResponse(BasePaywayModel):
    """Respuesta de tokenización de tarjeta."""

    id: str = Field(..., alias="id", description="ID del token")
    status: str | None = Field(default=None, description="Estado del token")
    card_number_length: int | None = Field(default=None, description="Longitud del número")
    date_created: datetime | None = Field(default=None, description="Fecha de creación")
    bin: str | None = Field(default=None, description="BIN de la tarjeta (primeros 6 dígitos)")
    last_four_digits: str | None = Field(
        default=None,
        alias="last_four_digits",
        description="Últimos 4 dígitos",
    )
    expiration_month: int | None = Field(default=None, description="Mes de vencimiento")
    expiration_year: int | None = Field(default=None, description="Año de vencimiento")
    card_holder: CardHolder | None = Field(default=None, description="Datos del titular")
    security_code_length: int | None = Field(default=None, description="Longitud del CVV")
    fraud_detection: dict[str, Any] | None = Field(
        default=None,
        description="Datos de detección de fraude",
    )


# =============================================================================
# MODELOS DE DIRECCIÓN Y CLIENTE
# =============================================================================


class Address(BasePaywayModel):
    """Dirección de facturación o envío."""

    street: str | None = Field(default=None, description="Calle y número")
    city: str | None = Field(default=None, description="Ciudad")
    state: str | None = Field(default=None, description="Provincia/Estado")
    postal_code: str | None = Field(default=None, alias="zip_code", description="Código postal")
    country: str | None = Field(default="AR", description="Código de país ISO")
    floor: str | None = Field(default=None, description="Piso")
    apartment: str | None = Field(default=None, description="Departamento")


class Customer(BasePaywayModel):
    """Datos del cliente/comprador."""

    id: str | None = Field(default=None, description="ID del cliente en tu sistema")
    email: str = Field(..., description="Email del cliente")
    first_name: str | None = Field(default=None, description="Nombre")
    last_name: str | None = Field(default=None, description="Apellido")
    phone: str | None = Field(default=None, description="Teléfono")
    identification_type: str | None = Field(default="DNI", description="Tipo de documento")
    identification_number: str | None = Field(default=None, description="Número de documento")
    ip_address: str | None = Field(default=None, description="IP del cliente")
    billing_address: Address | None = Field(default=None, description="Dirección de facturación")
    shipping_address: Address | None = Field(default=None, description="Dirección de envío")


# =============================================================================
# MODELOS DE PAGO
# =============================================================================


class SubPayment(BasePaywayModel):
    """Sub-pago para pagos distribuidos."""

    site_id: str = Field(..., description="ID del sitio receptor")
    amount: Decimal = Field(..., gt=0, description="Monto del sub-pago")
    installments: int = Field(default=1, ge=1, description="Cuotas")


class PaymentRequest(BasePaywayModel):
    """Request para crear un pago."""

    site_transaction_id: str = Field(
        ...,
        min_length=1,
        max_length=40,
        description="ID único de la transacción en tu sistema",
    )
    token: str = Field(..., description="Token de la tarjeta")
    payment_method_id: int = Field(
        ...,
        description="ID del método de pago (1=Visa, 15=Mastercard, etc.)",
    )
    amount: Decimal = Field(..., gt=0, description="Monto total en centavos")
    currency: Currency = Field(default=Currency.ARS, description="Moneda")
    installments: int = Field(default=1, ge=1, le=48, description="Cantidad de cuotas")
    payment_type: str | None = Field(default="single", description="Tipo de pago")
    establishment_name: str | None = Field(default=None, description="Nombre del comercio")
    description: str | None = Field(default=None, max_length=255, description="Descripción")
    customer: Customer | None = Field(default=None, description="Datos del cliente")
    sub_payments: list[SubPayment] | None = Field(
        default=None,
        description="Sub-pagos para pagos distribuidos",
    )
    fraud_detection: dict[str, Any] | None = Field(
        default=None,
        description="Datos adicionales para Cybersource",
    )
    aggregate_data: dict[str, Any] | None = Field(
        default=None,
        description="Datos de agregador",
    )
    soft_descriptor: str | None = Field(
        default=None,
        max_length=22,
        description="Texto en el resumen de la tarjeta",
    )


class PaymentResponse(BasePaywayModel):
    """Respuesta de un pago procesado."""

    id: int | None = Field(default=None, description="ID del pago en Payway")
    site_transaction_id: str = Field(..., description="ID de la transacción en tu sistema")
    token: str | None = Field(default=None, description="Token utilizado")
    payment_method_id: int | None = Field(default=None, description="ID del método de pago")
    amount: Decimal | None = Field(default=None, description="Monto cobrado")
    currency: str | None = Field(default=None, description="Moneda")
    installments: int | None = Field(default=None, description="Cuotas")
    status: PaymentStatus | None = Field(default=None, description="Estado del pago")
    status_details: dict[str, Any] | None = Field(default=None, description="Detalles del estado")
    date: datetime | None = Field(default=None, description="Fecha del pago")
    date_created: datetime | None = Field(default=None, description="Fecha de creación")
    date_approved: datetime | None = Field(default=None, description="Fecha de aprobación")
    date_last_updated: datetime | None = Field(default=None, description="Última actualización")
    authorization_code: str | None = Field(default=None, description="Código de autorización")
    ticket: str | None = Field(default=None, description="Número de ticket")
    card_brand: str | None = Field(default=None, description="Marca de la tarjeta")
    bin: str | None = Field(default=None, description="BIN de la tarjeta")
    last_four_digits: str | None = Field(default=None, description="Últimos 4 dígitos")
    fraud_detection: dict[str, Any] | None = Field(default=None, description="Resultado antifraude")
    customer: Customer | None = Field(default=None, description="Datos del cliente")
    establishment_name: str | None = Field(default=None, description="Nombre del comercio")
    sub_payments: list[dict[str, Any]] | None = Field(default=None, description="Sub-pagos")

    @property
    def is_approved(self) -> bool:
        """Indica si el pago fue aprobado."""
        return self.status == PaymentStatus.APPROVED

    @property
    def is_rejected(self) -> bool:
        """Indica si el pago fue rechazado."""
        return self.status == PaymentStatus.REJECTED


class Payment(PaymentResponse):
    """Alias para PaymentResponse (retrocompatibilidad)."""

    pass


# =============================================================================
# MODELOS DE DEVOLUCIÓN
# =============================================================================


class RefundRequest(BasePaywayModel):
    """Request para crear una devolución."""

    amount: Decimal | None = Field(default=None, gt=0, description="Monto a devolver (parcial)")
    reason: str | None = Field(default=None, max_length=255, description="Razón de la devolución")


class RefundResponse(BasePaywayModel):
    """Respuesta de una devolución."""

    id: int | None = Field(default=None, description="ID de la devolución")
    payment_id: int | None = Field(default=None, description="ID del pago original")
    amount: Decimal | None = Field(default=None, description="Monto devuelto")
    status: str | None = Field(default=None, description="Estado de la devolución")
    date_created: datetime | None = Field(default=None, description="Fecha de creación")
    ticket: str | None = Field(default=None, description="Número de ticket")


class Refund(RefundResponse):
    """Alias para RefundResponse (retrocompatibilidad)."""

    pass


# =============================================================================
# MODELOS DE ERROR
# =============================================================================


class ValidationErrorDetail(BasePaywayModel):
    """Detalle de un error de validación."""

    code: str | None = Field(default=None, description="Código del error")
    field: str | None = Field(default=None, alias="param", description="Campo con error")
    message: str | None = Field(default=None, description="Mensaje descriptivo")


class ErrorResponse(BasePaywayModel):
    """Respuesta de error de la API."""

    error_type: str | None = Field(default=None, description="Tipo de error")
    error_code: str | None = Field(default=None, alias="code", description="Código de error")
    message: str | None = Field(default=None, description="Mensaje de error")
    validation_errors: list[ValidationErrorDetail] | None = Field(
        default=None,
        description="Errores de validación",
    )
    request_id: str | None = Field(default=None, description="ID del request")


# =============================================================================
# MODELOS DE CYBERSOURCE
# =============================================================================


class CybersourceDecision(str, Enum):
    """Decisiones posibles de Cybersource."""

    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    REVIEW = "REVIEW"
    ERROR = "ERROR"


class CybersourceResult(BasePaywayModel):
    """Resultado del análisis de Cybersource."""

    decision: CybersourceDecision | None = Field(default=None, description="Decisión")
    reason_code: str | None = Field(default=None, description="Código de razón")
    score: float | None = Field(default=None, ge=0, le=100, description="Score de riesgo (0-100)")
    factors: list[str] | None = Field(default=None, description="Factores de riesgo")
    details: dict[str, Any] | None = Field(default=None, description="Detalles adicionales")


# =============================================================================
# MODELOS DE HEALTHCHECK
# =============================================================================


class HealthStatus(str, Enum):
    """Estados de salud del servicio."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheckResponse(BasePaywayModel):
    """Respuesta del healthcheck."""

    status: HealthStatus = Field(..., description="Estado del servicio")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp")
    version: str | None = Field(default=None, description="Versión de la API")
    services: dict[str, str] | None = Field(default=None, description="Estado de sub-servicios")
