from app.domain.models import Payment
from app.ports.gateway import PaymentGateway

class MockPaymentGateway(PaymentGateway):
    async def process_payment(self, payment: Payment) -> bool:
        # Simulate processing - always successful for amounts < 1000
        return payment.amount < 1000
