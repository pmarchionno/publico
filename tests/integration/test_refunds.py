"""Tests de integración para el servicio de devoluciones."""

import pytest
import respx
from decimal import Decimal
from httpx import Response

from payway_sdk import PaywayClient


@pytest.mark.asyncio
class TestRefundService:
    """Tests de integración para RefundService."""

    async def test_create_full_refund(self, client, mock_api, sample_refund_response):
        """Crea una devolución total."""
        mock_api.post("/payments/12345/refunds").mock(
            return_value=Response(200, json=sample_refund_response)
        )

        refund = await client.refunds.create(payment_id=12345)

        assert refund.id == 9876
        assert refund.payment_id == 12345
        assert refund.status == "approved"

    async def test_create_partial_refund(self, client, mock_api, sample_refund_response):
        """Crea una devolución parcial."""
        sample_refund_response["amount"] = 50000  # 500.00 en centavos
        mock_api.post("/payments/12345/refunds").mock(
            return_value=Response(200, json=sample_refund_response)
        )

        refund = await client.refunds.create(
            payment_id=12345,
            amount=Decimal("500.00"),
            reason="Producto defectuoso",
        )

        assert refund.id == 9876
        assert refund.amount == 50000

    async def test_list_refunds(self, client, mock_api, sample_refund_response):
        """Lista devoluciones de un pago."""
        mock_api.get("/payments/12345/refunds").mock(
            return_value=Response(200, json={"refunds": [sample_refund_response]})
        )

        refunds = await client.refunds.list(payment_id=12345)
        assert len(refunds) == 1
        assert refunds[0].id == 9876

    async def test_cancel_refund(self, client, mock_api, sample_refund_response):
        """Anula una devolución."""
        sample_refund_response["status"] = "cancelled"
        mock_api.delete("/payments/12345/refunds/9876").mock(
            return_value=Response(200, json=sample_refund_response)
        )

        refund = await client.refunds.cancel(payment_id=12345, refund_id=9876)
        assert refund.status == "cancelled"
