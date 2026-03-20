# --- Solicitud de cierre de cuenta ---
from typing import List
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from uuid import UUID
from datetime import datetime
from typing import Literal, Optional
import re


class UserRegisterEmailRequest(BaseModel):
    """Step 1: email only"""
    email: EmailStr = Field(..., description="Correo electronico")
    code: str = Field(..., description="Código de verificación")


class UserRegisterEmailResponse(BaseModel):
    """Step 1 response"""
    message: str
    code: Optional[str] = None  # Solo en desarrollo


class EmailVerificationResponse(BaseModel):
    """Email verification response"""
    message: str


class EmailStatusRequest(BaseModel):
    """Request to check email status"""
    email: EmailStr = Field(..., description="Correo electronico a consultar")


class EmailStatusResponse(BaseModel):
    """Response with email verification status"""
    exists: bool = Field(..., description="Si el email esta registrado")
    is_verified: bool = Field(..., description="Si el email fue verificado")
    can_complete_registration: bool = Field(..., description="Si puede completar el registro")
    registration_token: Optional[str] = Field(None, description="Token temporal para completar el registro (24 horas)")


class UserCompleteProfileRequest(BaseModel):
    """Step 2: profile completion"""
    email: EmailStr = Field(..., description="Correo electronico verificado")
    # registration_token: str = Field(..., description="Token obtenido desde /check-email")
    password: str = Field(
        ..., 
        min_length=8, 
        max_length=72, 
        description="Password (min 8 chars, debe contener: mayúscula, número y símbolo especial)"
    )
    dni: str = Field(..., min_length=6, max_length=32)
    first_name: str = Field(..., min_length=2, max_length=128)
    last_name: str = Field(..., min_length=2, max_length=128)
    gender: Literal["masculino", "femenino"]
    cuit_cuil: str = Field(..., min_length=8, max_length=32)
    phone: str = Field(..., min_length=6, max_length=32)
    nationality: str = Field(..., min_length=2, max_length=64)
    occupation: str = Field(..., min_length=2, max_length=64)
    marital_status: str = Field(..., min_length=2, max_length=32)
    location: str = Field(..., min_length=2, max_length=255)
    is_kyc_verified: bool = Field(..., description="Si el usuario pasó la verificación KYC (con datos personales)") 

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        # Validar longitud en bytes (bcrypt limitation)
        if len(value.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede superar 72 bytes")
        
        # Validar al menos una mayúscula
        if not re.search(r'[A-Z]', value):
            raise ValueError("La contraseña debe contener al menos una letra mayúscula")
        
        # Validar al menos un número
        if not re.search(r'[0-9]', value):
            raise ValueError("La contraseña debe contener al menos un número")
        
        # Validar al menos un símbolo especial
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', value):
            raise ValueError("La contraseña debe contener al menos un símbolo especial (!@#$%^&*()_+-=[]{}...)")
        
        return value


class UserLoginRequest(BaseModel):
    """Schema para login de usuario"""
    email: EmailStr = Field(..., description="Correo electrónico")
    password: str = Field(..., description="Contraseña")


class UserResponse(BaseModel):
    """Schema para respuesta de usuario"""
    id: UUID
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
    is_active: bool
    is_email_verified: bool
    is_kyc_verified: bool = False
    created_at: datetime
    updated_at: datetime
    password: Optional[str] = None  # Solo para validación interna, no se expone en respuestas
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Schema para respuesta de autenticación"""
    access_token: str = Field(..., description="Token de acceso JWT")
    token_type: str = Field(default="bearer", description="Tipo de token")
    user: Optional[UserResponse] = None


class RefreshTokenResponse(BaseModel):
    """Schema para respuesta de renovación de token"""
    access_token: str = Field(..., description="Nuevo token de acceso JWT")
    token_type: str = Field(default="bearer", description="Tipo de token")
    user: UserResponse


class ChangePasswordRequest(BaseModel):
    """Schema para cambio de contraseña"""
    email: EmailStr = Field(..., description="Correo electrónico")
    current_password: str = Field(..., min_length=8, description="Contraseña actual")
    new_password: str = Field(..., min_length=8, description="Nueva contraseña")
    confirm_password: str = Field(..., min_length=8, description="Confirmación de la nueva contraseña")
    
    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Las contraseñas no coinciden')
        return v


class ChangePasswordResponse(BaseModel):
    """Schema para respuesta de cambio de contraseña"""
    message: str = Field(..., description="Mensaje de confirmación")


class ChangePasswordWithTokenRequest(BaseModel):
    """Schema para cambio de contraseña con token JWT"""
    current_password: str = Field(..., min_length=8, description="Contraseña actual")
    new_password: str = Field(..., min_length=8, description="Nueva contraseña")
    confirm_password: str = Field(..., min_length=8, description="Confirmación de la nueva contraseña")

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Las contraseñas no coinciden')
        return v


class ErrorResponse(BaseModel):
    """Schema para respuestas de error"""
    detail: str = Field(..., description="Descripción del error")

class BankAccountWithBalanceResponse(BaseModel):
    """Schema para una cuenta bancaria con su saldo calculado"""
    id: str = Field(..., description="ID de la cuenta")
    cvu_cbu: str = Field(..., description="CVU o CBU de 22 dígitos")
    alias: Optional[str] = Field(None, description="Alias de la cuenta")
    account_type: str = Field(..., description="Tipo de cuenta: CBU o CVU")
    balance: float = Field(..., description="Saldo actual calculado")
    currency: str = Field(..., description="Moneda de la cuenta")
    status: str = Field(..., description="Estado: active, suspended, closed")
    is_primary: bool = Field(..., description="Si es la cuenta principal")
    created_at: Optional[str] = Field(None, description="Fecha de creación en ISO format")

    model_config = ConfigDict(from_attributes=True)


class UserAccountsResponse(BaseModel):
    """Schema para respuesta de listado de cuentas del usuario"""
    accounts: list[BankAccountWithBalanceResponse] = Field(..., description="Lista de cuentas con sus saldos")
    total_accounts: int = Field(..., description="Total de cuentas")

    model_config = ConfigDict(from_attributes=True)

class AccountClosureFormResponse(BaseModel):
    email: EmailStr = Field(..., description="Correo electrónico del usuario")
    name: str = Field(..., description="Nombre del usuario")
    app_options: List[str] = Field(default_factory=lambda: ["Sivep", "Pagoflex"], description="Opciones de aplicación")
    motivo: str = Field("", description="Motivo del cierre (campo a completar por el usuario)")
