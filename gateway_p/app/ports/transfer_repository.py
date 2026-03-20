from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.core.payments.types import PaymentData


class TransferRepository(ABC):
    @abstractmethod
    async def save(self, data: PaymentData) -> PaymentData:
        """Persist or update a transfer request."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_origin_id(self, origin_id: str) -> Optional[PaymentData]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_payment_id(self, payment_id: UUID) -> Optional[PaymentData]:
        raise NotImplementedError
