from abc import ABC, abstractmethod
from typing import Dict, Optional
from app.core.kyc.types import IdentityData, VerificationResult, KYCStatus

class KYCProvider(ABC):
    @abstractmethod
    async def verify_identity(self, identity_data: IdentityData) -> VerificationResult:
        pass

    @abstractmethod
    async def check_status(self, verification_id: str) -> VerificationResult:
        pass

class KYCService:
    def __init__(self, providers: Dict[str, KYCProvider]):
        self.providers = providers

    async def initiate_verification(self, customer_id: str, provider_name: str, identity_data: IdentityData) -> VerificationResult:
        provider = self.providers.get(provider_name)
        if not provider:
            raise ValueError(f"Provider {provider_name} not found")
        
        result = await provider.verify_identity(identity_data)
        # TODO: Persist result linked to customer_id
        return result

    async def get_status(self, customer_id: str) -> KYCStatus:
        # TODO: Retrieve from DB
        return KYCStatus.NOT_STARTED
