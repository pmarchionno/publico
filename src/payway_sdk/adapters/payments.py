"""
Servicio de pagos.

Este servicio maneja el procesamiento de pagos con tarjeta.

Endpoints:
    POST /payments - Crear un pago
    GET /payments/{payment_id} - Obtener un pago
    GET /payments - Listar pagos
    PUT /payments/{payment_id} - Actualizar un pago (capturar pre-autorización)
    DELETE /payments/{payment_id} - Anular un pago
"""

from decimal import Decimal
from typing import Any

from payway_sdk.adapters.base import BaseService
from payway_sdk.domain.models import (
    Customer,
    PaymentRequest,
    PaymentResponse,
    PaymentStatus,
)


class PaymentService(BaseService):
    """Servicio para procesamiento de pagos."""

    async def create(
        self,
        payment: PaymentRequest | dict[str, Any],
    ) -> PaymentResponse:
        """
        Procesa un nuevo pago.
        
        Args:
            payment: Datos del pago (PaymentRequest o dict)
        
        Returns:
            PaymentResponse con el resultado del pago
        
        Raises:
            PaywayValidationError: Si los datos son inválidos
            PaywayPaymentDeclinedError: Si el pago es rechazado
            PaywayError: Para otros errores
        
        Example:
            >>> payment = await client.payments.create(PaymentRequest(
            ...     site_transaction_id="ORDER-001",
            ...     token="abc123",
            ...     payment_method_id=1,
            ...     amount=Decimal("1500.00"),
            ...     installments=1,
            ... ))
            >>> if payment.is_approved:
            ...     print(f"Pago aprobado: {payment.authorization_code}")
        """
        if isinstance(payment, PaymentRequest):
            payload = payment.model_dump(mode="json", by_alias=True, exclude_none=True)
        else:
            validated = PaymentRequest.model_validate(payment)
            payload = validated.model_dump(mode="json", by_alias=True, exclude_none=True)

        # Convertir amount a centavos si es necesario
        if "amount" in payload and isinstance(payload["amount"], (int, float, Decimal)):
            # Payway espera el monto en centavos
            payload["amount"] = int(Decimal(str(payload["amount"])) * 100)

        self._logger.info(
            "Procesando pago",
            site_transaction_id=payload.get("site_transaction_id"),
            amount=payload.get("amount"),
            installments=payload.get("installments"),
        )

        response = await self._http.post("/payments", json=payload)
        
        result = PaymentResponse.model_validate(response)

        self._logger.info(
            "Pago procesado",
            payment_id=result.id,
            status=result.status,
            authorization_code=result.authorization_code,
        )

        return result

    async def get(self, payment_id: int | str) -> PaymentResponse:
        """
        Obtiene un pago por su ID.
        
        Args:
            payment_id: ID del pago en Payway
        
        Returns:
            PaymentResponse con la información del pago
        
        Raises:
            PaywayNotFoundError: Si el pago no existe
        """
        self._logger.debug("Obteniendo pago", payment_id=payment_id)
        
        response = await self._http.get(f"/payments/{payment_id}")
        
        return PaymentResponse.model_validate(response)

    async def get_by_site_transaction_id(
        self,
        site_transaction_id: str,
    ) -> PaymentResponse | None:
        """
        Busca un pago por el ID de transacción del sitio.
        
        Args:
            site_transaction_id: ID único de tu sistema
        
        Returns:
            PaymentResponse si se encuentra, None si no existe
        """
        self._logger.debug(
            "Buscando pago por site_transaction_id",
            site_transaction_id=site_transaction_id,
        )
        
        try:
            payments = await self.list(
                params={"siteTransactionId": site_transaction_id}
            )
            if payments:
                return payments[0]
            return None
        except Exception:
            return None

    async def list(
        self,
        params: dict[str, Any] | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[PaymentResponse]:
        """
        Lista pagos con filtros opcionales.
        
        Args:
            params: Filtros adicionales (dateFrom, dateTo, status, etc.)
            offset: Offset para paginación
            limit: Límite de resultados (max 50)
        
        Returns:
            Lista de PaymentResponse
        """
        query_params = params or {}
        query_params["offset"] = offset
        query_params["pageSize"] = min(limit, 50)

        self._logger.debug("Listando pagos", **query_params)
        
        response = await self._http.get("/payments", params=query_params)
        
        # La respuesta puede ser una lista o un objeto con "results"
        if isinstance(response, list):
            items = response
        else:
            items = response.get("results", response.get("payments", []))

        return [PaymentResponse.model_validate(item) for item in items]

    async def capture(
        self,
        payment_id: int | str,
        amount: Decimal | None = None,
    ) -> PaymentResponse:
        """
        Captura una pre-autorización.
        
        Args:
            payment_id: ID del pago pre-autorizado
            amount: Monto a capturar (opcional, si es menor al original)
        
        Returns:
            PaymentResponse actualizado
        """
        self._logger.info("Capturando pago", payment_id=payment_id, amount=amount)
        
        payload: dict[str, Any] = {}
        if amount is not None:
            payload["amount"] = int(amount * 100)

        response = await self._http.put(f"/payments/{payment_id}", json=payload)
        
        return PaymentResponse.model_validate(response)

    async def cancel(self, payment_id: int | str) -> PaymentResponse:
        """
        Anula un pago (antes del cierre de lote).
        
        Args:
            payment_id: ID del pago a anular
        
        Returns:
            PaymentResponse actualizado con status ANNULLED
        """
        self._logger.info("Anulando pago", payment_id=payment_id)
        
        response = await self._http.delete(f"/payments/{payment_id}")
        
        return PaymentResponse.model_validate(response)

    # Métodos síncronos

    def create_sync(
        self,
        payment: PaymentRequest | dict[str, Any],
    ) -> PaymentResponse:
        """Versión síncrona de create()."""
        if isinstance(payment, PaymentRequest):
            payload = payment.model_dump(mode="json", by_alias=True, exclude_none=True)
        else:
            validated = PaymentRequest.model_validate(payment)
            payload = validated.model_dump(mode="json", by_alias=True, exclude_none=True)

        if "amount" in payload and isinstance(payload["amount"], (int, float, Decimal)):
            payload["amount"] = int(Decimal(str(payload["amount"])) * 100)

        self._logger.info(
            "Procesando pago (sync)",
            site_transaction_id=payload.get("site_transaction_id"),
            amount=payload.get("amount"),
        )

        response = self._http.post_sync("/payments", json=payload)
        return PaymentResponse.model_validate(response)

    def get_sync(self, payment_id: int | str) -> PaymentResponse:
        """Versión síncrona de get()."""
        response = self._http.get_sync(f"/payments/{payment_id}")
        return PaymentResponse.model_validate(response)
