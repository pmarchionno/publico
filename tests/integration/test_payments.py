"""Tests de integración para el servicio de pagos."""

import pytest
import respx
from decimal import Decimal
from httpx import Response

from payway_sdk import PaywayClient, PaymentRequest, PaywayValidationError


@pytest.mark.asyncio
class TestPaymentService:
    """Tests de integración para PaymentService."""

    async def test_create_payment(self, client, mock_api, sample_payment_request, sample_payment_response):
        """Crea un pago exitosamente."""
        mock_api.post("/payments").mock(
            return_value=Response(200, json=sample_payment_response)
        )

        payment = await client.payments.create(sample_payment_request)

        assert payment.id == 12345
        assert payment.site_transaction_id == "ORDER-001"
        assert payment.is_approved is True
        assert payment.authorization_code == "AUTH123"

    async def test_create_payment_with_model(self, client, mock_api, sample_payment_response):
        """Crea un pago usando el modelo PaymentRequest."""
        mock_api.post("/payments").mock(
            return_value=Response(200, json=sample_payment_response)
        )

        request = PaymentRequest(
            site_transaction_id="ORDER-001",
            token="token_abc123",
            payment_method_id=1,
            amount=Decimal("1500.00"),
            installments=1,
        )

        payment = await client.payments.create(request)
        assert payment.id == 12345

    async def test_get_payment(self, client, mock_api, sample_payment_response):
        """Obtiene un pago por ID."""
        mock_api.get("/payments/12345").mock(
            return_value=Response(200, json=sample_payment_response)
        )

        payment = await client.payments.get(12345)
        assert payment.id == 12345
        assert payment.status.value == "approved"

    async def test_list_payments(self, client, mock_api, sample_payment_response):
        """Lista pagos."""
        mock_api.get("/payments").mock(
            return_value=Response(200, json={"results": [sample_payment_response]})
        )

        payments = await client.payments.list()
        assert len(payments) == 1
        assert payments[0].id == 12345

    async def test_cancel_payment(self, client, mock_api, sample_payment_response):
        """Anula un pago."""
        sample_payment_response["status"] = "annulled"
        mock_api.delete("/payments/12345").mock(
            return_value=Response(200, json=sample_payment_response)
        )

        payment = await client.payments.cancel(12345)
        assert payment.status.value == "annulled"

    async def test_payment_rejected(self, client, mock_api, sample_payment_response):
        """Maneja un pago rechazado."""
        sample_payment_response["status"] = "rejected"
        sample_payment_response["status_details"] = {
            "error": {
                "type": "insufficient_funds",
                "message": "Fondos insuficientes",
            }
        }
        mock_api.post("/payments").mock(
            return_value=Response(200, json=sample_payment_response)
        )

        payment = await client.payments.create({
            "site_transaction_id": "ORDER-002",
            "token": "token_abc123",
            "payment_method_id": 1,
            "amount": "100000.00",
            "installments": 1,
        })

        assert payment.is_rejected is True
        assert payment.is_approved is False

    async def test_payment_validation_error(self, client, mock_api):
        """Maneja error de validación en pagos."""
        mock_api.post("/payments").mock(
            return_value=Response(400, json={
                "message": "Token inválido",
                "code": "invalid_token",
            })
        )

        with pytest.raises(PaywayValidationError) as exc_info:
            await client.payments.create({
                "site_transaction_id": "ORDER-003",
                "token": "invalid_token",
                "payment_method_id": 1,
                "amount": "100.00",
                "installments": 1,
            })

        assert exc_info.value.status_code == 400
