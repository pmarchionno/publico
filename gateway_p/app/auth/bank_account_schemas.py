"""
Schemas para operaciones con cuentas bancarias
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class BankAccountCreate(BaseModel):
    """Schema para crear una cuenta bancaria"""
    cvu_cbu: str = Field(..., min_length=22, max_length=22, description="CVU o CBU de 22 dígitos")
    account_type: str = Field(..., description="Tipo de cuenta: CBU o CVU")
    alias: Optional[str] = Field(None, description="Alias de la cuenta")
    is_primary: bool = Field(default=False, description="Marcar como cuenta principal")
    bdc_account_id: Optional[str] = Field(None, description="ID de cuenta en BDC")
    currency: str = Field(default="ARS", description="Moneda: ARS, USD")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cvu_cbu": "0000003100010000000001",
                "account_type": "CVU",
                "alias": "mi.cuenta.personal",
                "is_primary": True,
                "currency": "ARS"
            }
        }
    )


class BankAccountUpdate(BaseModel):
    """Schema para actualizar una cuenta bancaria"""
    alias: Optional[str] = Field(None, description="Nuevo alias")
    status: Optional[str] = Field(None, description="Nuevo estado: active, suspended, closed")
    is_primary: Optional[bool] = Field(None, description="Cambiar cuenta principal")
    balance: Optional[Decimal] = Field(None, description="Actualizar saldo")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "alias": "nuevo.alias.cuenta",
                "status": "active"
            }
        }
    )


class BankAccountResponse(BaseModel):
    """Schema para respuesta de cuenta bancaria"""
    id: UUID
    user_id: UUID
    cvu_cbu: str
    account_type: str
    alias: Optional[str] = None
    status: str
    is_primary: bool
    bdc_account_id: Optional[str] = None
    currency: str
    balance: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class BankAccountListResponse(BaseModel):
    """Schema para lista de cuentas bancarias"""
    accounts: list[BankAccountResponse]
    total: int


class BankAccountBalanceRequest(BaseModel):
    """Schema para consultar saldo de cuenta(s)"""
    cvu_cbu: Optional[str] = Field(None, min_length=22, max_length=22, description="CVU o CBU de 22 digitos (opcional, si no se envía retorna todas las cuentas)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cvu_cbu": "0000003100010000000001"
            }
        }
    )


class BankAccountBalanceResponse(BaseModel):
    """Schema para respuesta de saldo de cuenta"""
    account_id: UUID
    cvu_cbu: str
    alias: Optional[str] = None
    balance: float
    currency: str

    model_config = ConfigDict(from_attributes=True)


class BankAccountBalanceListResponse(BaseModel):
    """Schema para lista de saldos de cuentas"""
    accounts: list[BankAccountBalanceResponse]
    total: int
