from uuid import uuid4

from typing import Optional
from app.core.payments.types import PaymentData, PaymentState, ConnectorResponse
from app.core.connectors.interface import ConnectorIntegration
from app.ports.transfer_repository import TransferRepository
# from app.core.kyc.service import KYCService # TODO: Import when implemented

class PaymentOperation:
    def __init__(self, transfer_repository: Optional[TransferRepository] = None, kyc_service=None): 
        # In a real DI scenario, we'd inject repositories and services here
        self.kyc_service = kyc_service
        self.transfer_repository = transfer_repository

    async def validate_request(self, data: PaymentData) -> bool:
        # Basic validation
        if data.amount <= 0:
            raise ValueError("Amount must be positive")
        return True

    async def requires_kyc(self, data: PaymentData) -> bool:
        # Example logic: payments over 1000 require KYC
        return data.amount > 1000

    async def domain_logic(self, data: PaymentData) -> PaymentData:
        # Check KYC requirements
        if await self.requires_kyc(data):
            # TODO: Integrate real KYC check
            # kyc_status = await self.kyc_service.check_status(data.customer_id)
            # if kyc_status != "VERIFIED":
            #     data.status = PaymentState.REQUIRES_KYC
            #     return data
            pass
        
        return data

    async def call_connector(self, connector: ConnectorIntegration, data: PaymentData) -> ConnectorResponse:
        request = await connector.build_request(data)
        raw_response = await connector.execute_request(request)
        response = await connector.handle_response(raw_response)
        return response

    async def update_tracker(self, data: PaymentData, new_state: PaymentState) -> PaymentData:
        data.status = new_state
        if self.transfer_repository:
            await self.transfer_repository.save(data)
        return data

    async def process(self, data: PaymentData, connector: ConnectorIntegration) -> PaymentData:
        await self.validate_request(data)
        
        data = await self.domain_logic(data)
        if data.status == PaymentState.REQUIRES_KYC:
            return await self.update_tracker(data, PaymentState.REQUIRES_KYC)

        if not data.origin_id:
            data.origin_id = uuid4().hex

        response = await self.call_connector(connector, data)

        data.metadata["connector_response"] = response.raw_response
        if response.provider_reference_id:
            data.metadata["provider_reference_id"] = response.provider_reference_id
        if response.error_message:
            data.metadata["error_message"] = response.error_message
        
        final_state = response.status
        return await self.update_tracker(data, final_state)
