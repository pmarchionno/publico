from abc import ABC, abstractmethod
from typing import Any, Dict
from app.core.payments.types import PaymentData, ConnectorResponse

class ConnectorIntegration(ABC):
    @abstractmethod
    async def build_request(self, data: PaymentData) -> Dict[str, Any]:
        """Convert domain data to provider specific request format"""
        pass

    @abstractmethod
    async def execute_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the HTTP request to the provider"""
        pass

    @abstractmethod
    async def handle_response(self, response: Dict[str, Any]) -> ConnectorResponse:
        """Convert provider response back to domain format"""
        pass
