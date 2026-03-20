from typing import Dict, Optional
from uuid import UUID

from app.core.payments.types import PaymentData
from app.ports.transfer_repository import TransferRepository


class InMemoryTransferRepository(TransferRepository):
    def __init__(self):
        self._by_origin: Dict[str, PaymentData] = {}
        self._by_payment: Dict[UUID, PaymentData] = {}

    async def save(self, data: PaymentData) -> PaymentData:
        copy = data.model_copy(deep=True)
        self._by_origin[copy.origin_id] = copy
        self._by_payment[copy.payment_id] = copy
        return copy

    async def get_by_origin_id(self, origin_id: str) -> Optional[PaymentData]:
        stored = self._by_origin.get(origin_id)
        return stored.model_copy(deep=True) if stored else None

    async def get_by_payment_id(self, payment_id: UUID) -> Optional[PaymentData]:
        stored = self._by_payment.get(payment_id)
        return stored.model_copy(deep=True) if stored else None
