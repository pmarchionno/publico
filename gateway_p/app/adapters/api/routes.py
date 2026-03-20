from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.domain.models import Payment
from app.services.payment_service import PaymentService
from app.adapters.api.dependencies import (
    get_payment_operation,
    get_payment_service,
    get_transfer_connector,
)
from app.core.payments.operation import PaymentOperation
from app.core.payments.types import PaymentData, TransferRequest, TransferInitResponse
from app.core.connectors.interface import ConnectorIntegration

router = APIRouter()

class CreatePaymentRequest(BaseModel):
    amount: float
    currency: str


# @router.post("/payments", response_model=Payment)
# async def create_payment(
#     request: CreatePaymentRequest,
#     service: PaymentService = Depends(get_payment_service), 
# ):
#     return await service.create_payment(request.amount, request.currency)

# @router.post("/payments/{payment_id}/process", response_model=Payment)
# async def process_payment(
#     payment_id: UUID,
#     service: PaymentService = Depends(get_payment_service),
# ):
#     payment = await service.process_payment(payment_id)
#     if not payment:
#         raise HTTPException(status_code=404, detail="Payment not found")
#     return payment


# @router.post("/transfers", response_model=TransferInitResponse)
# async def register_transfer(
#     request: TransferRequest,
#     operation: PaymentOperation = Depends(get_payment_operation),
#     connector: ConnectorIntegration = Depends(get_transfer_connector),
# ):
#     payment_data = PaymentData(
#         source=request.source,
#         destination=request.destination,
#         transfer_body=request.body,
#         description=request.body.description,
#         metadata={"client_request": request.model_dump(by_alias=True)},
#     )

#     try:
#         processed = await operation.process(payment_data, connector)
#     except httpx.HTTPError as exc:
#         raise HTTPException(status_code=502, detail=f"Bank request failed: {exc}") from exc

#     response = TransferInitResponse(
#         paymentId=processed.payment_id,
#         originId=processed.origin_id,
#         status=processed.status.value,
#         echoed_request=request,
#         bankResponse=processed.metadata.get("connector_response"),
#     )
#     return response


# @router.get("/transfers/{origin_id}", response_model=PaymentData)
# async def get_transfer_by_origin(
#     origin_id: str,
#     operation: PaymentOperation = Depends(get_payment_operation),
# ):
#     repository = operation.transfer_repository
#     if repository is None:
#         raise HTTPException(status_code=500, detail="Transfer repository not configured")

#     stored = await repository.get_by_origin_id(origin_id)
#     if not stored:
#         raise HTTPException(status_code=404, detail="Transfer not found")

#     return stored

# @router.get("/payments/{payment_id}", response_model=Payment)
# async def get_payment(
#     payment_id: UUID,
#     service: PaymentService = Depends(get_payment_service),
# ):
#     payment = await service.get_payment(payment_id)
#     if not payment:
#         raise HTTPException(status_code=404, detail="Payment not found")
#     return payment
