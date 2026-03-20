from enum import Enum
from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from uuid import UUID, uuid4

class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class AccountStatus(str, Enum):
    """Estados posibles de una cuenta bancaria"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class AccountType(str, Enum):
    """Tipos de cuentas bancarias"""
    CBU = "CBU"
    CVU = "CVU"


class Payment(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    amount: float
    currency: str
    status: PaymentStatus = PaymentStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class User(BaseModel):
    """Entidad de usuario en el dominio"""
    id: UUID = Field(default_factory=uuid4)
    email: EmailStr
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    dni: Optional[str] = None
    gender: Optional[str] = None
    cuit_cuil: Optional[str] = None
    phone: Optional[str] = None
    nationality: Optional[str] = None
    occupation: Optional[str] = None
    marital_status: Optional[str] = None
    location: Optional[str] = None
    is_active: bool = True
    is_email_verified: bool = False
    is_kyc_verified: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class BankAccount(BaseModel):
    """Entidad de cuenta bancaria en el dominio"""
    id: UUID = Field(default_factory=uuid4)
    origin_id: Optional[int] = Field(None, description="ID numérico autoincremental para BDC")
    user_id: UUID
    cvu_cbu: str = Field(..., min_length=22, max_length=22, description="CVU o CBU de 22 dígitos")
    account_type: AccountType = Field(..., description="Tipo de cuenta: CBU o CVU")
    alias: Optional[str] = Field(None, description="Alias de la cuenta")
    status: AccountStatus = Field(default=AccountStatus.ACTIVE, description="Estado de la cuenta")
    is_primary: bool = Field(default=False, description="Indica si es la cuenta principal")
    bdc_account_id: Optional[str] = Field(None, description="ID de cuenta en BDC")
    currency: str = Field(default="ARS", description="Moneda de la cuenta")
    balance: Optional[Decimal] = Field(None, description="Saldo actual")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)
