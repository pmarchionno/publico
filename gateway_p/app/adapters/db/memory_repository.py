from typing import Dict, Optional
from uuid import UUID

from app.domain.models import Payment
from app.ports.repository import PaymentRepository

class InMemoryPaymentRepository(PaymentRepository):
    def __init__(self):
        self.payments: Dict[UUID, Payment] = {}

    async def create(self, payment: Payment) -> Payment:
        self.payments[payment.id] = payment
        return payment

    async def get_by_id(self, payment_id: UUID) -> Optional[Payment]:
        return self.payments.get(payment_id)

    async def update(self, payment: Payment) -> Payment:
        self.payments[payment.id] = payment
        return payment
