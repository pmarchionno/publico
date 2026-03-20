from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile, Query, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
import requests
import logging

from config.settings import settings
from app.auth.security import verify_access_token
from app.adapters.api.dependencies import get_user_repository
from app.ports.user_repository import UserRepository
from app.auth.schemas import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["kyc"])

class VerificationSessionRequest(BaseModel):
    isIframe: bool = False
    vendor_data: EmailStr


class UpdateKYCStatusRequest(BaseModel):
    """Request para actualizar el estado de verificación KYC"""
    is_kyc_verified: bool


class UpdateKYCStatusResponse(BaseModel):
    """Response al actualizar el estado KYC"""
    message: str
    user: UserResponse


@router.get("/")
async def get_kyc_status():
    return {"message": "KYC module"}

@router.post("/session")
async def create_verification_session(
    isIframe: bool = Form(False, description="Whether to use iframe mode"),
    vendor_data: str = Form(..., description="Vendor data to associate with the verification"),
):
    """Create a verification session"""
    try:
        # Aquí irían credenciales del usuario autenticado
        # Por ahora usamos values de ejemplo
        # user_email = "user@example.com"  # En producción: obtener del JWT
        
        if not vendor_data:
            print("vendor_data is missing in the request")
            raise HTTPException(status_code=400, detail="vendor_data is required")

        url = f"{settings.DIDIT_BASE_URL}/session/"

        body = {
            'workflow_id': settings.DIDIT_WORKFLOW_ID,
            'vendor_data': vendor_data,
        }

        if not isIframe:
            body['callback'] = settings.DIDIT_CALLBACK_URL

        print("Creating verification session:", {
            'url': url,
            'workflow_id': settings.DIDIT_WORKFLOW_ID,
            'vendor_data': body['vendor_data'],
            'callback': settings.DIDIT_CALLBACK_URL,
            'isIframe': isIframe,
        })

        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': settings.DIDIT_API_KEY,
        }

        response = requests.post(url, json=body, headers=headers)
        data = response.json()

        print("Didit API response:", {
            'status': response.status_code,
            'data': data,
        })

        if response.status_code == 201:
            return data
        else:
            error_message = data.get('message') or data.get('error') or data.get('detail') or str(data)
            print(f"Error creating session: {error_message}")
            raise HTTPException(status_code=response.status_code, detail=error_message)

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="An error occurred")

@router.post("/reset")
async def reset_verification():
    """Reset user's verification status"""
    try:
        # TODO: Conectar con BD real
        return {"message": "Verification status reset"}

    except Exception as e:
        print(f"Error resetting verification: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset verification status")


@router.patch(
    "/verify-status",
    response_model=UpdateKYCStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Actualizar estado de verificación KYC del usuario",
    responses={
        401: {"description": "Token inválido o expirado"},
        404: {"description": "Usuario no encontrado"},
        500: {"description": "Error interno del servidor"},
    },
)
async def update_kyc_verification_status(
    request_data: UpdateKYCStatusRequest,
    token: str = Query(..., description="Token JWT del usuario autenticado"),
    user_repository: UserRepository = Depends(get_user_repository),
):
    """
    Actualiza el estado de verificación KYC de un usuario
    
    Este endpoint permite marcar a un usuario como verificado o no verificado
    después de completar el proceso KYC con el proveedor (Didit u otro).
    
    Requiere:
    - Token JWT válido del usuario
    - Nuevo estado de verificación (true/false)
    
    Returns:
        UpdateKYCStatusResponse: Mensaje de confirmación y datos actualizados del usuario
    """
    try:
        # Validar token JWT
        user_id_str = verify_access_token(token)
        if not user_id_str:
            logger.warning("Token JWT inválido o expirado")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Buscar usuario
        user = await user_repository.get_by_id(UUID(user_id_str))
        if not user:
            logger.warning(f"Usuario no encontrado: {user_id_str}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        
        logger.info(
            f"Actualizando estado KYC del usuario {user.email}: "
            f"{user.is_kyc_verified} -> {request_data.is_kyc_verified}"
        )
        
        # Actualizar estado KYC del usuario
        user.is_kyc_verified = request_data.is_kyc_verified
        updated_user = await user_repository.update(user)
        
        if not updated_user:
            logger.error(f"Error al actualizar usuario {user_id_str}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al actualizar el estado de verificación KYC",
            )
        
        verification_status = "verificado" if request_data.is_kyc_verified else "no verificado"
        logger.info(f"Usuario {updated_user.email} marcado como {verification_status}")
        
        return UpdateKYCStatusResponse(
            message=f"Estado de verificación KYC actualizado exitosamente: {verification_status}",
            user=UserResponse.model_validate(updated_user),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado al actualizar estado KYC: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar estado de verificación KYC: {str(e)}",
        )


### Standalone APIS
@router.post("/id-verification")
async def verify_identity_document(
    front_image: UploadFile = File(..., description="Front side image of the identity document"),
    back_image: Optional[UploadFile] = File(..., description="Back side image of the identity document"),
    perform_document_liveness: bool = Form(False, description="Whether to perform document liveness check"),
    minimum_age: Optional[int] = Form(None, ge=1, le=120, description="Minimum age required (1-120)"),
    vendor_data: str = Form(..., description="Vendor data to associate with the verification")
):
    """
    Verify identity document by uploading images
    
    - **front_image**: Front side of ID document (required). Max 5MB. Formats: JPEG, PNG, WebP, TIFF, PDF
    - **back_image**: Back side of ID document (optional). Max 5MB. Formats: JPEG, PNG, WebP, TIFF, PDF
    - **perform_document_liveness**: Check if image is not a screened copy (default: false)
    - **minimum_age**: Minimum age required (1-120). Users under this age will be declined
    - **vendor_data**: String to associate with the verification (e.g. user ID or email)
    """
    try:
        # Validate file types
        allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/tiff', 'application/pdf']
        
        if front_image.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid front_image format. Allowed: JPEG, PNG, WebP, TIFF, PDF"
            )
        
        if back_image and back_image.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid back_image format. Allowed: JPEG, PNG, WebP, TIFF, PDF"
            )
        
        if not vendor_data:
            raise HTTPException(status_code=400, detail="vendor_data is required")
        
        # Read file contents
        front_content = await front_image.read()
        
        # Validate file size (5MB = 5 * 1024 * 1024 bytes)
        max_size = 5 * 1024 * 1024
        if len(front_content) > max_size:
            raise HTTPException(status_code=400, detail="front_image exceeds 5MB limit")
        
        # Prepare files for multipart upload
        files = {
            'front_image': (front_image.filename, front_content, front_image.content_type)
        }
        
        if back_image:
            back_content = await back_image.read()
            if len(back_content) > max_size:
                raise HTTPException(status_code=400, detail="back_image exceeds 5MB limit")
            files['back_image'] = (back_image.filename, back_content, back_image.content_type)
        
        # Prepare form data
        data = {
            'perform_document_liveness': str(perform_document_liveness).lower()
        }
        
        if minimum_age is not None:
            data['minimum_age'] = str(minimum_age)
        
        if vendor_data:
            data['vendor_data'] = vendor_data
            
        # Make request to Didit API
        url = f"{settings.DIDIT_BASE_URL}/id-verification/"
        headers = {
            'accept': 'application/json',
            'X-API-Key': settings.DIDIT_API_KEY,
        }
        
        print("Submitting ID verification:", {
            'url': url,
            'front_image': front_image.filename,
            'back_image': back_image.filename if back_image else None,
            'perform_document_liveness': perform_document_liveness,
            'minimum_age': minimum_age,
            'vendor_data': vendor_data,
        })
        
        response = requests.post(url, headers=headers, files=files, data=data)
        
        print("Didit API response:", {
            'status': response.status_code,
            'response': response.text[:500]  # Log first 500 chars
        })
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            try:
                error_data = response.json()
                error_message = error_data.get('message') or error_data.get('error') or str(error_data)
            except:
                error_message = response.text
            
            print(f"Error from Didit API: {error_message}")
            raise HTTPException(status_code=response.status_code, detail=error_message)
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing ID verification: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process ID verification: {str(e)}")
