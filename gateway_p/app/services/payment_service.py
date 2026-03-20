from uuid import UUID
from typing import Optional
from app.domain.models import Payment, PaymentStatus
from app.ports.repository import PaymentRepository
from app.ports.gateway import PaymentGateway

class PaymentService:
    def __init__(self, repository: PaymentRepository, gateway: PaymentGateway):
        self.repository = repository
        self.gateway = gateway

    async def create_payment(self, amount: float, currency: str) -> Payment:
        payment = Payment(amount=amount, currency=currency)
        return await self.repository.create(payment)

    async def process_payment(self, payment_id: UUID) -> Optional[Payment]:
        payment = await self.repository.get_by_id(payment_id)
        if not payment:
            return None

        if payment.status != PaymentStatus.PENDING:
            return payment  # Already processed

        success = await self.gateway.process_payment(payment)
        
        if success:
            payment.status = PaymentStatus.COMPLETED
        else:
            payment.status = PaymentStatus.FAILED

        return await self.repository.update(payment)

    async def get_payment(self, payment_id: UUID) -> Optional[Payment]:
        return await self.repository.get_by_id(payment_id)
