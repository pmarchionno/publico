from abc import ABC, abstractmethod
from uuid import UUID
from typing import Optional
from app.domain.models import Payment

class PaymentRepository(ABC):
    @abstractmethod
    async def create(self, payment: Payment) -> Payment:
        pass

    @abstractmethod
    async def get_by_id(self, payment_id: UUID) -> Optional[Payment]:
        pass

    @abstractmethod
    async def update(self, payment: Payment) -> Payment:
        pass
