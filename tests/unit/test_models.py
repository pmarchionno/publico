"""Tests para los modelos de dominio."""

import pytest
from decimal import Decimal

from payway_sdk.domain.models import (
    CardData,
    CardHolder,
    CardTokenResponse,
    PaymentRequest,
    PaymentResponse,
    PaymentStatus,
    Customer,
    Address,
    RefundRequest,
    RefundResponse,
)


class TestCardHolder:
    """Tests para CardHolder."""

    def test_create_basic(self):
        """Crea un CardHolder básico."""
        holder = CardHolder(name="Juan Perez")
        assert holder.name == "Juan Perez"
        assert holder.identification_type == "DNI"

    def test_create_full(self):
        """Crea un CardHolder con todos los campos."""
        holder = CardHolder(
            name="Juan Perez",
            identification_type="CUIL",
            identification_number="20-12345678-9",
            email="juan@email.com",
            phone="+5491112345678",
        )
        assert holder.name == "Juan Perez"
        assert holder.identification_type == "CUIL"
        assert holder.email == "juan@email.com"


class TestCardData:
    """Tests para CardData."""

    def test_create_valid(self, sample_card_data):
        """Crea CardData con datos válidos."""
        card = CardData.model_validate(sample_card_data)
        assert card.card_number == "4111111111111111"
        assert card.card_expiration_month == "12"
        assert card.card_expiration_year == "25"

    def test_card_number_cleaned(self):
        """Limpia espacios y guiones del número de tarjeta."""
        card = CardData(
            card_number="4111-1111-1111-1111",
            card_expiration_month="12",
            card_expiration_year="2025",
            security_code="123",
            card_holder=CardHolder(name="Test"),
        )
        assert card.card_number == "4111111111111111"

    def test_year_normalized(self):
        """Normaliza año de 4 a 2 dígitos."""
        card = CardData(
            card_number="4111111111111111",
            card_expiration_month="12",
            card_expiration_year="2025",
            security_code="123",
            card_holder=CardHolder(name="Test"),
        )
        assert card.card_expiration_year == "25"

    def test_invalid_card_number(self):
        """Rechaza números de tarjeta inválidos."""
        with pytest.raises(ValueError):
            CardData(
                card_number="1234",  # Muy corto
                card_expiration_month="12",
                card_expiration_year="25",
                security_code="123",
                card_holder=CardHolder(name="Test"),
            )

    def test_invalid_month(self):
        """Rechaza meses inválidos."""
        with pytest.raises(ValueError):
            CardData(
                card_number="4111111111111111",
                card_expiration_month="13",  # Inválido
                card_expiration_year="25",
                security_code="123",
                card_holder=CardHolder(name="Test"),
            )


class TestCardTokenResponse:
    """Tests para CardTokenResponse."""

    def test_parse_response(self, sample_token_response):
        """Parsea una respuesta de token."""
        token = CardTokenResponse.model_validate(sample_token_response)
        assert token.id == "token_abc123"
        assert token.bin == "411111"
        assert token.last_four_digits == "1111"

    def test_allows_extra_fields(self, sample_token_response):
        """Permite campos adicionales no definidos."""
        sample_token_response["new_unknown_field"] = "value"
        token = CardTokenResponse.model_validate(sample_token_response)
        assert token.id == "token_abc123"


class TestPaymentRequest:
    """Tests para PaymentRequest."""

    def test_create_basic(self, sample_payment_request):
        """Crea un PaymentRequest básico."""
        payment = PaymentRequest.model_validate(sample_payment_request)
        assert payment.site_transaction_id == "ORDER-001"
        assert payment.token == "token_abc123"
        assert payment.payment_method_id == 1
        assert payment.installments == 1

    def test_with_customer(self, sample_payment_request):
        """Crea PaymentRequest con datos de cliente."""
        sample_payment_request["customer"] = {
            "email": "customer@email.com",
            "first_name": "Juan",
            "last_name": "Perez",
        }
        payment = PaymentRequest.model_validate(sample_payment_request)
        assert payment.customer is not None
        assert payment.customer.email == "customer@email.com"


class TestPaymentResponse:
    """Tests para PaymentResponse."""

    def test_parse_approved(self, sample_payment_response):
        """Parsea un pago aprobado."""
        payment = PaymentResponse.model_validate(sample_payment_response)
        assert payment.id == 12345
        assert payment.status == PaymentStatus.APPROVED
        assert payment.is_approved is True
        assert payment.is_rejected is False

    def test_parse_rejected(self, sample_payment_response):
        """Parsea un pago rechazado."""
        sample_payment_response["status"] = "rejected"
        payment = PaymentResponse.model_validate(sample_payment_response)
        assert payment.status == PaymentStatus.REJECTED
        assert payment.is_approved is False
        assert payment.is_rejected is True

    def test_allows_extra_fields(self, sample_payment_response):
        """Permite campos adicionales no definidos."""
        sample_payment_response["future_field"] = {"nested": "data"}
        payment = PaymentResponse.model_validate(sample_payment_response)
        assert payment.id == 12345


class TestRefund:
    """Tests para modelos de devolución."""

    def test_refund_request_partial(self):
        """Crea un request de devolución parcial."""
        refund = RefundRequest(
            amount=Decimal("500.00"),
            reason="Producto defectuoso",
        )
        assert refund.amount == Decimal("500.00")
        assert refund.reason == "Producto defectuoso"

    def test_refund_request_full(self):
        """Crea un request de devolución total (sin amount)."""
        refund = RefundRequest()
        assert refund.amount is None

    def test_refund_response(self, sample_refund_response):
        """Parsea una respuesta de devolución."""
        refund = RefundResponse.model_validate(sample_refund_response)
        assert refund.id == 9876
        assert refund.payment_id == 12345
        assert refund.status == "approved"


class TestAddress:
    """Tests para Address."""

    def test_create_full(self):
        """Crea una dirección completa."""
        address = Address(
            street="Av. Corrientes 1234",
            city="Buenos Aires",
            state="CABA",
            postal_code="C1043AAZ",
            country="AR",
            floor="5",
            apartment="A",
        )
        assert address.street == "Av. Corrientes 1234"
        assert address.country == "AR"


class TestCustomer:
    """Tests para Customer."""

    def test_create_basic(self):
        """Crea un cliente básico."""
        customer = Customer(email="test@email.com")
        assert customer.email == "test@email.com"

    def test_create_full(self):
        """Crea un cliente con todos los datos."""
        customer = Customer(
            id="CUST-001",
            email="test@email.com",
            first_name="Juan",
            last_name="Perez",
            phone="+5491112345678",
            identification_type="DNI",
            identification_number="12345678",
            ip_address="192.168.1.1",
            billing_address=Address(
                street="Calle Falsa 123",
                city="Springfield",
            ),
        )
        assert customer.id == "CUST-001"
        assert customer.billing_address is not None
        assert customer.billing_address.city == "Springfield"
