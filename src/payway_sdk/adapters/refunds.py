"""
Servicio de devoluciones (refunds).

Este servicio maneja las devoluciones totales y parciales de pagos.

Endpoints:
    POST /payments/{payment_id}/refunds - Crear devolución
    GET /payments/{payment_id}/refunds - Listar devoluciones de un pago
    DELETE /payments/{payment_id}/refunds/{refund_id} - Anular devolución
"""

from decimal import Decimal
from typing import Any

from payway_sdk.adapters.base import BaseService
from payway_sdk.domain.models import RefundRequest, RefundResponse


class RefundService(BaseService):
    """Servicio para devoluciones."""

    async def create(
        self,
        payment_id: int | str,
        amount: Decimal | None = None,
        reason: str | None = None,
    ) -> RefundResponse:
        """
        Crea una devolución para un pago.
        
        Si no se especifica amount, se realiza una devolución total.
        Si se especifica, se realiza una devolución parcial.
        
        Args:
            payment_id: ID del pago original
            amount: Monto a devolver (None para devolución total)
            reason: Razón de la devolución (opcional)
        
        Returns:
            RefundResponse con los datos de la devolución
        
        Raises:
            PaywayNotFoundError: Si el pago no existe
            PaywayValidationError: Si el pago no es elegible para devolución
        
        Example:
            >>> # Devolución total
            >>> refund = await client.refunds.create(payment_id=123)
            >>> 
            >>> # Devolución parcial
            >>> refund = await client.refunds.create(
            ...     payment_id=123,
            ...     amount=Decimal("500.00"),
            ...     reason="Producto defectuoso"
            ... )
        """
        payload: dict[str, Any] = {}
        
        if amount is not None:
            # Convertir a centavos
            payload["amount"] = int(amount * 100)
        
        if reason:
            payload["reason"] = reason

        self._logger.info(
            "Creando devolución",
            payment_id=payment_id,
            amount=amount,
            reason=reason,
        )

        response = await self._http.post(
            f"/payments/{payment_id}/refunds",
            json=payload if payload else None,
        )

        result = RefundResponse.model_validate(response)

        self._logger.info(
            "Devolución creada",
            refund_id=result.id,
            payment_id=payment_id,
            status=result.status,
        )

        return result

    async def create_from_request(
        self,
        payment_id: int | str,
        refund_request: RefundRequest | dict[str, Any],
    ) -> RefundResponse:
        """
        Crea una devolución desde un RefundRequest.
        
        Args:
            payment_id: ID del pago original
            refund_request: Datos de la devolución
        
        Returns:
            RefundResponse con los datos de la devolución
        """
        if isinstance(refund_request, RefundRequest):
            data = refund_request
        else:
            data = RefundRequest.model_validate(refund_request)

        return await self.create(
            payment_id=payment_id,
            amount=data.amount,
            reason=data.reason,
        )

    async def list(self, payment_id: int | str) -> list[RefundResponse]:
        """
        Lista todas las devoluciones de un pago.
        
        Args:
            payment_id: ID del pago
        
        Returns:
            Lista de RefundResponse
        """
        self._logger.debug("Listando devoluciones", payment_id=payment_id)
        
        response = await self._http.get(f"/payments/{payment_id}/refunds")
        
        # Manejar diferentes formatos de respuesta
        if isinstance(response, list):
            items = response
        else:
            items = response.get("refunds", response.get("results", []))

        return [RefundResponse.model_validate(item) for item in items]

    async def cancel(
        self,
        payment_id: int | str,
        refund_id: int | str,
    ) -> RefundResponse:
        """
        Anula una devolución pendiente.
        
        Args:
            payment_id: ID del pago original
            refund_id: ID de la devolución a anular
        
        Returns:
            RefundResponse actualizado
        
        Raises:
            PaywayNotFoundError: Si la devolución no existe
            PaywayValidationError: Si la devolución no puede anularse
        """
        self._logger.info(
            "Anulando devolución",
            payment_id=payment_id,
            refund_id=refund_id,
        )

        response = await self._http.delete(
            f"/payments/{payment_id}/refunds/{refund_id}"
        )

        return RefundResponse.model_validate(response)

    async def get_total_refunded(self, payment_id: int | str) -> Decimal:
        """
        Calcula el total devuelto de un pago.
        
        Args:
            payment_id: ID del pago
        
        Returns:
            Monto total devuelto (en pesos, no centavos)
        """
        refunds = await self.list(payment_id)
        
        total = sum(
            refund.amount or Decimal("0")
            for refund in refunds
            if refund.status not in ("cancelled", "rejected")
        )
        
        # Convertir de centavos a pesos
        return total / 100

    # Métodos síncronos

    def create_sync(
        self,
        payment_id: int | str,
        amount: Decimal | None = None,
        reason: str | None = None,
    ) -> RefundResponse:
        """Versión síncrona de create()."""
        payload: dict[str, Any] = {}
        
        if amount is not None:
            payload["amount"] = int(amount * 100)
        
        if reason:
            payload["reason"] = reason

        self._logger.info(
            "Creando devolución (sync)",
            payment_id=payment_id,
            amount=amount,
        )

        response = self._http.post_sync(
            f"/payments/{payment_id}/refunds",
            json=payload if payload else None,
        )

        return RefundResponse.model_validate(response)

    def list_sync(self, payment_id: int | str) -> list[RefundResponse]:
        """Versión síncrona de list()."""
        response = self._http.get_sync(f"/payments/{payment_id}/refunds")
        
        if isinstance(response, list):
            items = response
        else:
            items = response.get("refunds", response.get("results", []))

        return [RefundResponse.model_validate(item) for item in items]
