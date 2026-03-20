from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field, ConfigDict, model_validator
from datetime import datetime
from uuid import UUID, uuid4

class PaymentState(str, Enum):
    CREATED = "CREATED"
    REQUIRES_PM = "REQUIRES_PM"
    REQUIRES_KYC = "REQUIRES_KYC"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class TransferPartyOwner(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    person_id_type: str = Field(..., alias="personIdType")
    person_id: str = Field(..., alias="personId", min_length=1, max_length=110)
    person_name: Optional[str] = Field(None, alias="personName")


class TransferParty(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    address_type: str = Field(..., alias="addressType")
    address: str = Field(..., min_length=6)
    owner: TransferPartyOwner


class TransferBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    amount: Decimal
    currency_id: str = Field(..., alias="currencyId")
    description: Optional[str] = None
    concept: Optional[str] = None

    @model_validator(mode="after")
    def ensure_two_decimals(cls, values):
        quantized = values.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if quantized != values.amount:
            values.amount = quantized
        return values


class TransferRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    origin_id: str = Field('0000000000', alias="originId")
    source: TransferParty
    destination: TransferParty
    body: TransferBody


class TransferInitResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    payment_id: UUID = Field(..., alias="paymentId")
    origin_id: int = Field(..., alias="originId")
    status: str
    echoed_request: TransferRequest
    bank_response: Dict[str, Any] | None = Field(default=None, alias="bankResponse")


class PaymentData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    payment_id: UUID = Field(default_factory=uuid4)
    origin_id: Optional[int] = None
    amount: Decimal = Field(default=Decimal("0"))
    currency: str = ""
    customer_id: Optional[str] = None
    description: Optional[str] = None
    status: PaymentState = PaymentState.CREATED
    connector_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source: Optional[TransferParty] = None
    destination: Optional[TransferParty] = None
    transfer_body: Optional[TransferBody] = Field(default=None, alias="body")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def sync_amount_currency(cls, values):
        if values.transfer_body:
            values.amount = values.transfer_body.amount
            # TransferBody usa currency_id (alias 'currencyId')
            values.currency = values.transfer_body.currency_id
        return values

class ConnectorResponse(BaseModel):
    status: PaymentState
    provider_reference_id: Optional[str] = None
    error_message: Optional[str] = None
    raw_response: Dict[str, Any] = Field(default_factory=dict)
