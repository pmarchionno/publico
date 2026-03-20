from abc import ABC, abstractmethod
from app.domain.models import Payment

class PaymentGateway(ABC):
    @abstractmethod
    async def process_payment(self, payment: Payment) -> bool:
        pass
