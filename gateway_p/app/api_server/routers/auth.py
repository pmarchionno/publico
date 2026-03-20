from app.auth.schemas import ErrorResponse, AccountClosureFormResponse
# Endpoint para solicitar cierre de cuenta
import logging
import json
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status, Request, Header, Query, Body
from fastapi.responses import HTMLResponse
from app.services.user_service import UserService
from app.services.bank_account_service import BankAccountService
from app.adapters.api.dependencies import get_user_service, get_current_user, get_bank_account_service
from app.auth.security import verify_registration_token, verify_access_token
from app.auth.schemas import (
    UserRegisterEmailRequest,
    UserRegisterEmailResponse,
    EmailVerificationResponse,
    EmailStatusRequest,
    EmailStatusResponse,
    UserCompleteProfileRequest,
    UserLoginRequest,
    TokenResponse,
    RefreshTokenResponse,
    UserResponse,
    ChangePasswordRequest,
    ChangePasswordWithTokenRequest,
    ChangePasswordResponse,
    ErrorResponse,
    UserAccountsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _verification_result_html(success: bool, message: str) -> str:
    header_color = "#10B981" if success else "#DC2626"
    title = "Email verificado" if success else "No se pudo verificar"
    icon = "✅" if success else "⚠️"

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - PagoFlex</title>
    <style>
        body {{ margin: 0; padding: 0; background: #f3f4f6; font-family: Arial, sans-serif; color: #1f2937; }}
        .wrapper {{ max-width: 640px; margin: 40px auto; padding: 0 16px; }}
        .card {{ background: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.08); }}
        .header {{ background: {header_color}; color: #ffffff; padding: 24px; text-align: center; font-size: 32px; }}
        .content {{ padding: 32px; }}
        .content h1 {{ margin: 0 0 12px; font-size: 28px; }}
        .content p {{ margin: 0; line-height: 1.6; font-size: 16px; color: #4b5563; }}
        .footer {{ text-align: center; padding: 20px; color: #6b7280; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="card">
            <div class="header">{icon}</div>
            <div class="content">
                <h1>{title}</h1>
                <p>{message}</p>
            </div>
        </div>
        <div class="footer">© 2026 PagoFlex - Gateway de Pagos</div>
    </div>
</body>
</html>
"""


@router.post(
    "/register",
    response_model=UserRegisterEmailResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Email ya verificado o datos invalidos"},
    },
)
async def register_email(
    request: UserRegisterEmailRequest,
    service: UserService = Depends(get_user_service),
):
    """
    Step 1: recibe email y code, y envia codigo de verificacion
    """
    logger.info("[BREVO/REGISTER] POST /auth/register recibido - email=%s", request.email)
    try:
        code = await service.start_email_registration(request.email, request.code)
        logger.info("[BREVO/REGISTER] start_email_registration OK - email=%s (envío de mail en background)", request.email)

        # Solo retornar codigo en desarrollo (cuando EMAIL está deshabilitado)
        from config.settings import settings
        response_code = None if settings.EMAIL_ENABLED else code

        return UserRegisterEmailResponse(
            message="Se envio el correo de verificacion" if settings.EMAIL_ENABLED else "Correo de verificacion generado (EMAIL deshabilitado)",
            code=response_code,
        )
    except ValueError as e:
        logger.warning("[BREVO/REGISTER] Error de validación - email=%s error=%s", request.email, str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("[BREVO/REGISTER] Error inesperado - email=%s error=%s", request.email, str(e), exc_info=True)
        raise


@router.get(
    "/verify-email",
    response_model=EmailVerificationResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Token invalido o expirado"},
    },
)
async def verify_email(
    request: Request,
    token: str,
    service: UserService = Depends(get_user_service),
):
    """
    Marca el email como verificado usando un token
    """
    accept_header = request.headers.get("accept", "").lower()
    wants_html = "text/html" in accept_header

    try:
        await service.verify_email(token)
        if wants_html:
            return HTMLResponse(
                content=_verification_result_html(
                    success=True,
                    message="Tu correo fue validado correctamente. Ya puedes continuar con tu registro.",
                ),
                status_code=status.HTTP_200_OK,
            )
        return EmailVerificationResponse(message="Email verificado")
    except ValueError as e:
        if wants_html:
            return HTMLResponse(
                content=_verification_result_html(
                    success=False,
                    message=str(e),
                ),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/check-email",
    response_model=EmailStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def check_email(
    request: EmailStatusRequest,
    service: UserService = Depends(get_user_service),
):
    """
    Consulta el estado de verificacion de un email y obtiene un token temporal
    
    Retorna:
    - exists: si el email esta registrado
    - is_verified: si el email fue verificado
    - can_complete_registration: si puede completar el registro
    - registration_token: token temporal (24 horas) para usar en /register/complete
    
    Este endpoint DEBE ejecutarse antes de /register/complete para obtener un token válido
    """
    status_info = await service.check_email_status(request.email)
    return EmailStatusResponse(**status_info)


@router.post(
    "/register/complete",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Email no verificado o datos invalidos"},
        401: {"model": ErrorResponse, "description": "Token de registro inválido o expirado"},
    },
)
async def complete_registration(
    request: UserCompleteProfileRequest,
    service: UserService = Depends(get_user_service),
):
    """
    Step 2: completa el perfil despues de verificar email.
    
    Requiere:
    - email: Email verificado desde /verify-email
    - registration_token: Token obtenido desde /check-email (válido por 24 horas)
    - Resto de datos personales
    
    Retorna automaticamente un token JWT para la nueva sesion.
    El token de registro se invalida al establecer la contraseña.
    """
    try:
        # Validar que el token de registro sea válido y corresponda al email
        # return "Completing registration for email: %s with token: %s" % (request.email, request.registration_token)
        # raw = await request.body()
        # logger.info("register/complete raw_len=%s", len(raw))
        # try:
        #     data = json.loads(raw)
        #     logger.info(
        #         "register/complete keys=%s password_len=%s password_bytes=%s",
        #         list(data.keys()),
        #         len(data.get("password", "")),
        #         len(data.get("password", "").encode("utf-8")),
        #     )
        # except Exception as e:
        #     logger.warning("register/complete body not json: %s", e)

        # *** Comentado por cambio de estrategia: ahora el token de registro se valida directamente en el service.complete_registration, que lanza excepciones claras de email/token inválidos o expirados. Esto simplifica la lógica del endpoint y centraliza la validación en el service.
        # token_email = verify_registration_token(request.registration_token)
        # if not token_email:
        #     raise HTTPException(
        #         status_code=status.HTTP_401_UNAUTHORIZED,
        #         detail="Token de registro inválido o expirado. Por favor, ejecuta /check-email nuevamente",
        #     )
        
        # if token_email.lower() != request.email.lower():
        #     raise HTTPException(
        #         status_code=status.HTTP_401_UNAUTHORIZED,
        #         detail="El email del token no coincide con el email proporcionado",
        #     )
        # *** FIN

        user = await service.complete_registration(
            email=request.email,
            # registration_token=request.registration_token,
            password=request.password,
            dni=request.dni,
            first_name=request.first_name,
            last_name=request.last_name,
            gender=request.gender,
            cuit_cuil=request.cuit_cuil,
            phone=request.phone,
            nationality=request.nationality,
            occupation=request.occupation,
            marital_status=request.marital_status,
            location=request.location,
            is_kyc_verified=request.is_kyc_verified
        )
        
        # return "Token email: %s, Request email: %s" % (token_email, request.password)
        # Generar token automaticamente para la nueva sesion
        access_token = service.create_user_token(str(user.id))
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Error en complete_registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Credenciales invalidas"},
    },
)
async def login(
    request: UserLoginRequest,
    service: UserService = Depends(get_user_service),
):
    """
    Inicia sesion y retorna un token JWT

    - **email**: Correo electronico registrado
    - **password**: Password
    """
    user = await service.authenticate_user(
        email=request.email,
        password=request.password,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales invalidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = service.create_user_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "No autorizado"},
    },
)
async def get_current_user_info(
    current_user = Depends(get_current_user),
):
    """
    Obtiene todos los datos del usuario autenticado
    
    Requiere: Token JWT en header Authorization: Bearer <token>
    """
    return UserResponse.model_validate(current_user)


@router.get(
    "/accounts",
    response_model=UserAccountsResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "No autorizado"},
    },
)
async def get_user_accounts(
    # authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None, description="Token JWT si no se usa Authorization"),
    bank_account_service: BankAccountService = Depends(get_bank_account_service),
):
    """
    Obtiene todas las cuentas bancarias del usuario autenticado con sus saldos calculados
    
    Requiere: Token JWT en header Authorization: Bearer <token>
    
    Retorna:
    - Lista de cuentas con sus datos y saldo calculado basado en transferencias
    - Cada cuenta incluye: id, cvu_cbu, alias, account_type, balance, currency, status, is_primary
    """
    try:
        raw_token = token
        # if not raw_token and authorization:
        #     parts = authorization.split()
        #     raw_token = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else authorization

        if not raw_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token requerido",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id_str = verify_access_token(raw_token)
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        accounts = await bank_account_service.get_user_accounts_with_balance(UUID(user_id_str))

        return UserAccountsResponse(
            accounts=accounts,
            total_accounts=len(accounts),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener cuentas del usuario: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener las cuentas",
        )


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Token inválido o expirado"},
    },
)
async def refresh_token(
    current_user = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """
    Renovar el token de acceso
    
    Requiere: Token JWT válido en header Authorization: Bearer <token>
    Retorna: Nuevo token de acceso válido por otros 30 minutos
    """
    # Generar nuevo token para el usuario actual
    new_access_token = service.create_user_token(str(current_user.id))
    
    return RefreshTokenResponse(
        access_token=new_access_token,
        token_type="bearer",
        user=UserResponse.model_validate(current_user),
    )


@router.post(
    "/change-password-auth",
    response_model=ChangePasswordResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Datos inválidos o contraseñas no coinciden"},
        401: {"model": ErrorResponse, "description": "Token inválido o expirado"},
        404: {"model": ErrorResponse, "description": "Usuario no encontrado"},
    },
)
async def change_password_with_token(
    password_data: ChangePasswordWithTokenRequest,
    token: Optional[str] = Query(None, description="Token JWT si no se usa Authorization"),
    service: UserService = Depends(get_user_service),
):
    """
    Cambia la contraseña del usuario autenticado usando token JWT.

    Requiere:
    - token JWT válido
    - current_password
    - new_password
    - confirm_password
    """
    try:
        raw_token = token
        if not raw_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token requerido",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id_str = verify_access_token(raw_token)
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if password_data.new_password != password_data.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La nueva contraseña y su confirmación no coinciden",
            )

        await service.change_password(
            user_id=UUID(user_id_str),
            current_password=password_data.current_password,
            new_password=password_data.new_password,
        )

        return ChangePasswordResponse(
            message="Contraseña actualizada exitosamente",
        )
    except HTTPException:
        raise
    except ValueError as e:
        error_text = str(e)
        if "usuario no encontrado" in error_text.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_text,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_text,
        )
    except Exception as e:
        logger.error(f"Error inesperado al cambiar contraseña con token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al cambiar la contraseña",
        )


@router.post(
    "/change-password",
    response_model=ChangePasswordResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Contraseña actual incorrecta o nueva contraseña inválida"},
    },
)
async def change_password(
    password_data: ChangePasswordRequest,
    service: UserService = Depends(get_user_service),
):
    """
    Cambiar la contraseña del usuario autenticado
    
    Requiere:
    - email: Correo electrónico
    - current_password: Contraseña actual
    - new_password: Nueva contraseña (mínimo 8 caracteres)
    - confirm_password: Confirmación de la nueva contraseña (debe coincidir)
    
    Retorna: Mensaje de confirmación
    """
    try:
        await service.change_password_by_email(
            email=password_data.email,
            current_password=password_data.current_password,
            new_password=password_data.new_password,
        )
        
        return ChangePasswordResponse(
            message="Contraseña actualizada exitosamente"
        )
    except ValueError as e:
        logger.error(f"Error al cambiar contraseña: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error inesperado al cambiar contraseña: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al cambiar la contraseña",
        )

@router.post(
    "/account-closure",
    response_model=AccountClosureFormResponse,
    status_code=status.HTTP_200_OK,
    tags=["auth"],
    summary="Solicitar cierre de cuenta",
    responses={
        401: {"model": ErrorResponse, "description": "Token inválido o expirado"},
    },
)
async def account_closure(
    token: str = Body(..., embed=True, description="Token JWT de autenticación"),
    user_service: UserService = Depends(get_user_service),
):
    """
    Permite al usuario solicitar el cierre de su cuenta. Requiere token JWT válido.
    Retorna un formulario para que la app lo renderice.
    """
    from app.auth.security import verify_access_token
    user_id = verify_access_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )
    # Obtener datos del usuario
    user = await user_service.repository.get_by_id(UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return AccountClosureFormResponse(
        email=user.email,
        name=name,
        app_options=["Sivep", "Pagoflex"],
        motivo=""
    )
