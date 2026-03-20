"""
Router para endpoints de documentos legales (términos y condiciones, políticas de privacidad)
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, status, Request
from typing import List

from app.services.legal_service import LegalDocumentService
from app.adapters.api.dependencies import get_legal_service, get_current_user
from app.domain.models import User
from app.auth.legal_schemas import (
    LegalDocumentResponse,
    LegalDocumentSummary,
    AcceptLegalDocumentRequest,
    AcceptLegalDocumentResponse,
    UserLegalAcceptanceResponse,
    UserLegalStatusResponse,
)
from app.auth.schemas import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/legal", tags=["legal"])


@router.get(
    "/terms",
    response_model=LegalDocumentResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "No hay términos y condiciones disponibles"},
    },
)
async def get_terms_and_conditions(
    service: LegalDocumentService = Depends(get_legal_service),
):
    """
    Obtiene los términos y condiciones actuales (versión activa)
    
    Este endpoint es público y no requiere autenticación.
    """
    document = service.get_current_terms_and_conditions()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay términos y condiciones disponibles",
        )
    
    return LegalDocumentResponse.model_validate(document)


@router.get(
    "/privacy",
    response_model=LegalDocumentResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "No hay política de privacidad disponible"},
    },
)
async def get_privacy_policy(
    service: LegalDocumentService = Depends(get_legal_service),
):
    """
    Obtiene la política de privacidad actual (versión activa)
    
    Este endpoint es público y no requiere autenticación.
    """
    document = service.get_current_privacy_policy()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay política de privacidad disponible",
        )
    
    return LegalDocumentResponse.model_validate(document)


@router.get(
    "/documents",
    response_model=List[LegalDocumentSummary],
    status_code=status.HTTP_200_OK,
)
async def get_all_active_documents(
    service: LegalDocumentService = Depends(get_legal_service),
):
    """
    Obtiene lista resumida de todos los documentos legales activos
    
    Útil para mostrar al usuario qué documentos debe aceptar.
    Este endpoint es público y no requiere autenticación.
    """
    documents = service.get_all_active_documents()
    return [LegalDocumentSummary.model_validate(doc) for doc in documents]


@router.post(
    "/accept",
    response_model=AcceptLegalDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "No autorizado"},
        404: {"model": ErrorResponse, "description": "Documento no encontrado"},
        400: {"model": ErrorResponse, "description": "Documento no activo"},
    },
)
async def accept_legal_document(
    request: AcceptLegalDocumentRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    service: LegalDocumentService = Depends(get_legal_service),
):
    """
    Registra la aceptación de un documento legal por parte del usuario autenticado
    
    Requiere: Token JWT en header Authorization: Bearer <token>
    
    Automáticamente registra:
    - La fecha y hora de aceptación
    - La IP del cliente (si está disponible)
    - El User-Agent (si está disponible)
    """
    try:
        # Obtener IP y User-Agent del request
        ip_address = request.ip_address or http_request.client.host if http_request.client else None
        user_agent = request.user_agent or http_request.headers.get("user-agent")
        
        acceptance = await service.accept_document(
            user_id=current_user.id,
            document_id=request.document_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        return AcceptLegalDocumentResponse(
            message="Documento aceptado exitosamente",
            acceptance=UserLegalAcceptanceResponse.model_validate(acceptance),
        )
    
    except ValueError as e:
        error_msg = str(e)
        if "no existe" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )


@router.get(
    "/status",
    response_model=UserLegalStatusResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "No autorizado"},
    },
)
async def get_user_legal_status(
    current_user: User = Depends(get_current_user),
    service: LegalDocumentService = Depends(get_legal_service),
):
    """
    Obtiene el estado de aceptaciones legales del usuario autenticado
    
    Indica:
    - Si ha aceptado términos y condiciones (y qué versión)
    - Si ha aceptado política de privacidad (y qué versión)
    - Si necesita aceptar nuevas versiones
    - Las versiones actuales disponibles
    
    Requiere: Token JWT en header Authorization: Bearer <token>
    """
    status_info = service.get_user_legal_status(current_user.id)
    return UserLegalStatusResponse(**status_info)


@router.get(
    "/acceptances",
    response_model=List[UserLegalAcceptanceResponse],
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "No autorizado"},
    },
)
async def get_user_acceptances(
    current_user: User = Depends(get_current_user),
    service: LegalDocumentService = Depends(get_legal_service),
):
    """
    Obtiene el historial completo de aceptaciones del usuario autenticado
    
    Muestra todas las versiones de documentos que el usuario ha aceptado,
    útil para auditoría y trazabilidad.
    
    Requiere: Token JWT en header Authorization: Bearer <token>
    """
    acceptances = service.get_user_acceptances(current_user.id)
    return [UserLegalAcceptanceResponse.model_validate(acc) for acc in acceptances]
