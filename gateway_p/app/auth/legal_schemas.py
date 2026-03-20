"""
Schemas para documentos legales (términos y condiciones, políticas de privacidad)
"""
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, Literal


# Tipos de documentos legales
LegalDocumentType = Literal["terms_and_conditions", "privacy_policy"]


class LegalDocumentResponse(BaseModel):
    """Schema para respuesta de un documento legal"""
    id: UUID
    document_type: str = Field(..., description="Tipo de documento")
    version: str = Field(..., description="Versión del documento")
    title: str = Field(..., description="Título del documento")
    content: str = Field(..., description="Contenido HTML o texto del documento")
    is_active: bool = Field(..., description="Si el documento está activo")
    effective_date: datetime = Field(..., description="Fecha efectiva del documento")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LegalDocumentSummary(BaseModel):
    """Schema resumido de documento legal (sin contenido completo)"""
    id: UUID
    document_type: str
    version: str
    title: str
    is_active: bool
    effective_date: datetime

    model_config = ConfigDict(from_attributes=True)


class AcceptLegalDocumentRequest(BaseModel):
    """Schema para aceptar un documento legal"""
    document_id: UUID = Field(..., description="ID del documento a aceptar")
    ip_address: Optional[str] = Field(None, max_length=45, description="IP del cliente (opcional)")
    user_agent: Optional[str] = Field(None, max_length=512, description="User agent (opcional)")


class UserLegalAcceptanceResponse(BaseModel):
    """Schema para respuesta de aceptación de documento legal"""
    id: UUID
    user_id: UUID
    document_id: UUID
    accepted_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    document: Optional[LegalDocumentSummary] = None

    model_config = ConfigDict(from_attributes=True)


class AcceptLegalDocumentResponse(BaseModel):
    """Schema para respuesta exitosa de aceptación"""
    message: str
    acceptance: UserLegalAcceptanceResponse


class UserLegalStatusResponse(BaseModel):
    """Schema para el estado de aceptaciones legales del usuario"""
    terms_accepted: bool = Field(..., description="Si aceptó términos y condiciones")
    terms_version: Optional[str] = Field(None, description="Versión aceptada de términos")
    terms_accepted_at: Optional[datetime] = Field(None, description="Fecha de aceptación de términos")
    
    privacy_accepted: bool = Field(..., description="Si aceptó política de privacidad")
    privacy_version: Optional[str] = Field(None, description="Versión aceptada de privacidad")
    privacy_accepted_at: Optional[datetime] = Field(None, description="Fecha de aceptación de privacidad")
    
    current_terms_version: Optional[str] = Field(None, description="Versión actual de términos")
    current_privacy_version: Optional[str] = Field(None, description="Versión actual de privacidad")
    
    needs_update: bool = Field(..., description="Si necesita aceptar nuevas versiones")


# Schemas para admin (crear/actualizar documentos)
class CreateLegalDocumentRequest(BaseModel):
    """Schema para crear un nuevo documento legal"""
    document_type: LegalDocumentType = Field(..., description="Tipo de documento")
    version: str = Field(..., min_length=1, max_length=16, description="Versión (ej: 1.0)")
    title: str = Field(..., min_length=5, max_length=255, description="Título")
    content: str = Field(..., min_length=50, description="Contenido del documento")
    effective_date: datetime = Field(..., description="Fecha desde la cual es efectivo")


class UpdateLegalDocumentRequest(BaseModel):
    """Schema para actualizar un documento legal"""
    title: Optional[str] = Field(None, min_length=5, max_length=255)
    content: Optional[str] = Field(None, min_length=50)
    is_active: Optional[bool] = None
    effective_date: Optional[datetime] = None
