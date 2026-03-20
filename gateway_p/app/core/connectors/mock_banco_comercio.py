from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import uuid4

from app.core.connectors.banco_comercio import BancoComercioConnector
from app.core.payments.types import ConnectorResponse, PaymentData, PaymentState


@dataclass
class MockBancoComercioBehaviour:
    failure_concepts: tuple[str, ...] = ("REJECT", "FAIL")
    failure_amount_threshold: Optional[Decimal] = None
    success_status_code: int = 0
    failure_status_code: int = 4099


class MockBancoComercioConnector(BancoComercioConnector):
    """Simulates Banco de Comercio connector for local and automated tests."""

    def __init__(
        self,
        behaviour: Optional[MockBancoComercioBehaviour] = None,
    ) -> None:
        self.behaviour = behaviour or MockBancoComercioBehaviour()

    async def build_request(self, data: PaymentData) -> Dict[str, Any]:
        request = await super().build_request(data)
        if not request.get("originId"):
            request["originId"] = data.origin_id or uuid4().hex
        return request

    async def execute_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        body = request.get("body", {})
        concept = str(body.get("concept", ""))
        amount = Decimal(str(body.get("amount", "0")))

        should_fail = concept.upper() in self.behaviour.failure_concepts
        if self.behaviour.failure_amount_threshold is not None:
            should_fail = should_fail or amount > self.behaviour.failure_amount_threshold

        status_code = self.behaviour.failure_status_code if should_fail else self.behaviour.success_status_code
        message = "Simulated transfer rejected" if should_fail else "Simulated transfer accepted"

        simulated_response = {
            "statusCode": status_code,
            "message": message,
            "dest_ori_trx_id": request.get("originId"),
            "data": {
                "request": request,
                "originId": request.get("originId"),
                "concept": concept,
            },
        }

        if should_fail:
            simulated_response["errors"] = [
                {
                    "code": "MOCK-FAILURE",
                    "detail": "Connector configured to reject this transfer",
                }
            ]

        return simulated_response

    async def handle_response(self, response: Dict[str, Any]) -> ConnectorResponse:
        status_code = response.get("statusCode")
        status = PaymentState.AUTHORIZED if status_code == self.behaviour.success_status_code else PaymentState.FAILED

        error_message = None
        if status != PaymentState.AUTHORIZED:
            error_message = response.get("message") or "Simulated connector failure"

        provider_reference = response.get("dest_ori_trx_id") or response.get("data", {}).get("originId")
        return ConnectorResponse(
            status=status,
            provider_reference_id=provider_reference,
            error_message=error_message,
            raw_response=response,
        )
