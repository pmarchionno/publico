"""
Router para endpoints de integración con Banco de Comercio (BDC)
"""
import logging
import httpx
import hashlib
import hmac
import json
import random
import string
import time
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID
from pydantic import ValidationError
from fastapi import APIRouter, HTTPException, Depends, status, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.adapters.api.dependencies import get_current_user, get_payment_operation, get_user_repository, get_bank_account_repository
from app.domain.models import User, BankAccount, AccountType, AccountStatus
from app.ports.user_repository import UserRepository
from app.ports.bank_account_repository import BankAccountRepository
from app.auth.security import verify_access_token
from app.core.bdc.auth import get_bdc_auth_service
from app.core.payments.types import PaymentData, PaymentState, TransferParty, TransferPartyOwner, TransferBody
from app.core.payments.operation import PaymentOperation
from app.db.session import get_db_session
from app.db.models import TransferRecord
from app.core.bdc.schemas import (
    BDCTokenCache, 
    BDCAuthFullResponse,
    BDCAccountsResponse,
    BDCAccountInfoResponse,
    BDCAliasCreateRequest,
    BDCAliasEditRequest,
    BDCAliasLookupRequest,
    BDCAliasRemoveRequest,
    BDCGetCvuAccountsRequest,
    BDCGetEntityRequest,
    BDCResponse,
    BDCSubAccountQueryResponse,
    BDCHealthcheckResponse, 
    BDCMovementsRequest,
    BDCMovementsResponse,
    BDCUltimosMovimientosRequest,
    BDCTransferRequest, 
    BDCTransferRequestInput,
    BDCTransferRequestSimpleInput,
    BDCTransferSuccessResponse,
    BDCTransferDetailResponse,
    BDCTransferDetailSimpleResponse,
    BDCUpdateSubAccountRequest,
    BDCUpdateAccountResponse,
    BDCSnpConceptsResponse
)
from app.utils.bdc_client import create_bdc_client
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bdc")


def _calculate_bdc_signature(path: str, payload: Any) -> str:
    if isinstance(payload, str):
        compact_body = payload
    else:
        compact_body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    uri = f"[{path.strip('/')}]"
    message = f"{uri}{compact_body}".encode("utf-8")
    secret = settings.bdc_secret_key.encode("utf-8")
    signature = hmac.new(secret, message, hashlib.sha256).hexdigest()
    logger.info(f'Datos para formar X-SIGNATURE\n bodyObj: {payload} \n compactBody: {compact_body}\n uri: {uri} \n msgencrypt: {message} \nsecret: {secret} \nsignature: {signature}')
    print(f'Datos para formar X-SIGNATURE\n bodyObj: {payload} \n compactBody: {compact_body}\n uri: {uri} \n msgencrypt: {message} \nsecret: {secret} \nsignature: {signature}')
    return signature


def _raise_if_bdc_business_error(
    payload: Any,
    default_message: str,
    *,
    context: str,
    user_id: Optional[UUID] = None,
    http_status_code: int = status.HTTP_400_BAD_REQUEST,
) -> None:
    """
    Verifica si la respuesta del banco contiene un error de negocio.
    Si hay error, lanza HTTPException con la respuesta EXACTA del banco.
    """
    if not isinstance(payload, dict):
        return

    raw_status_code = payload.get("statusCode")
    try:
        status_code_value = int(raw_status_code)
    except (TypeError, ValueError):
        return

    if status_code_value == 0:
        return

    detail = payload.get("message") or default_message
    if user_id is not None:
        logger.warning(
            "%s BDC devolvió error para usuario %s: statusCode=%s message=%s",
            context,
            user_id,
            status_code_value,
            detail,
        )
    else:
        logger.warning(
            "%s BDC devolvió error: statusCode=%s message=%s",
            context,
            status_code_value,
            detail,
        )

    # Devolver la respuesta EXACTA del banco sin transformación
    raise HTTPException(
        status_code=http_status_code,
        detail=payload,  # Respuesta exacta del banco como dict
    )


async def _generate_unique_cbu(bank_account_repository: BankAccountRepository) -> str:
    """
    Genera un número aleatorio de 22 dígitos para CBU/CVU único.
    Valida que sea globalmente único en la entidad.
    """
    import random
    
    max_attempts = 100
    attempt = 0
    
    while attempt < max_attempts:
        # Generar 22 dígitos aleatorios
        cbu = ''.join(str(random.randint(0, 9)) for _ in range(22))
        
        # Validar que sea único
        existing = await bank_account_repository.get_by_cvu_cbu(cbu)
        if not existing:
            logger.info(f"CBU único generado: {cbu}")
            return cbu
        
        attempt += 1
    
    logger.error(f"No se pudo generar CBU único después de {max_attempts} intentos")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Error al generar CBU único para la subcuenta"
    )


async def _generate_alias(user: User, bank_account_repository: BankAccountRepository) -> str:
    """
    Genera un alias único basado en información del usuario.
    Formato: nombre.apellido.pf (máximo 20 caracteres según BDC)
    Si el alias ya existe, agrega un sufijo aleatorio de 4 dígitos.
    """
    import random
    import string
    
    MAX_ALIAS_LENGTH = 20
    RANDOM_SUFFIX_LENGTH = 4
    
    # Obtener nombre y apellido del usuario
    first_name = (user.first_name or "").lower().strip()
    last_name = (user.last_name or "").lower().strip()
    
    # Calcular espacio disponible considerando puntos y sufijo
    # Formato: nombre.apellido.pf (sufijo es .pf = 3 chars)
    suffix = settings.BDC_ALIAS_SUFFIX  # Normalmente ".pf"
    dots = 2  # Un punto entre nombre y apellido, el sufijo ya incluye su punto
    
    # Espacio para nombre + apellido (sin puntos ni sufijo)
    available_space = MAX_ALIAS_LENGTH - len(suffix) - 1  # -1 por el punto entre nombre y apellido
    
    # Si no hay nombre o apellido, usar email
    if not first_name or not last_name:
        email_base = user.email.split("@")[0].lower()[:available_space]
        base_alias = f"{email_base}{suffix}"
    else:
        # Distribuir espacio entre nombre y apellido (50/50)
        max_name_length = available_space // 2
        max_lastname_length = available_space - max_name_length
        
        # Truncar si es necesario
        truncated_first = first_name[:max_name_length]
        truncated_last = last_name[:max_lastname_length]
        
        base_alias = f"{truncated_first}.{truncated_last}{suffix}"
    
    # Asegurar que el alias base no exceda el límite
    if len(base_alias) > MAX_ALIAS_LENGTH:
        base_alias = base_alias[:MAX_ALIAS_LENGTH]
    
    # Validar si el alias ya existe
    alias = base_alias
    existing = await bank_account_repository.get_by_alias(alias)
    
    # Si existe, generar uno con sufijo aleatorio
    max_attempts = 100
    attempt = 0
    while existing and attempt < max_attempts:
        # Para el sufijo random necesitamos espacio adicional: .xxxx (5 chars)
        # Recalcular base_alias más corto para dejar espacio
        if attempt == 0:  # Solo la primera vez
            available_for_base = MAX_ALIAS_LENGTH - len(suffix) - RANDOM_SUFFIX_LENGTH - 2  # -2 por los dos puntos
            if not first_name or not last_name:
                email_base = user.email.split("@")[0].lower()[:available_for_base]
                base_alias = f"{email_base}{suffix}"
            else:
                max_name = available_for_base // 2
                max_last = available_for_base - max_name
                truncated_first = first_name[:max_name]
                truncated_last = last_name[:max_last]
                base_alias = f"{truncated_first}.{truncated_last}{suffix}"
        
        # Generar sufijo aleatorio de 4 dígitos (más compacto)
        random_suffix = ''.join(random.choices(string.digits, k=RANDOM_SUFFIX_LENGTH))
        alias = f"{base_alias}.{random_suffix}"
        
        # Asegurar que no exceda el límite
        if len(alias) > MAX_ALIAS_LENGTH:
            alias = alias[:MAX_ALIAS_LENGTH]
        
        existing = await bank_account_repository.get_by_alias(alias)
        attempt += 1
    
    if attempt >= max_attempts:
        logger.error(f"No se pudo generar alias único después de {max_attempts} intentos")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al generar alias único para la subcuenta"
        )
    
    logger.info(f"Alias único generado para usuario {user.id}: {alias} (longitud: {len(alias)})")
    return alias


@router.post(
    "/auth",
    response_model=BDCAuthFullResponse,
    status_code=status.HTTP_200_OK,
    summary="Endpoint de autenticación",
    tags=["BDC - Autenticacion"],
)
async def bdc_auth():
    """
    Endpoint interno de autenticación.
    """
    try:
        bdc_url = f"{settings.bdc_base_url}/auth"
        logger.info("Solicitando token BDC")
        
        # Preparar las credenciales desde la configuración
        auth_payload = {
            "clientId": settings.bdc_client_id,
            "clientSecret": settings.bdc_client_secret
        }
        
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
        }
        
        async with create_bdc_client() as client:
            response = await client.post(
                bdc_url,
                headers=headers,
                json=auth_payload
            )
            response.raise_for_status()
            
            data = response.json()
            _raise_if_bdc_business_error(
                data,
                "Error al autenticar con BDC",
                context="[AUTH]",
            )
            logger.info(f"BDC auth successful: {data.get('message', 'ok')}")
            
            return BDCAuthFullResponse(**data)
            
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        logger.error(f"Error HTTP en auth BDC: {e.response.status_code} - {error_detail}")
        
        try:
            error_data = e.response.json()
            detail = error_data.get("message", error_detail)
        except Exception:
            detail = error_detail
        
        raise HTTPException(
            status_code=e.response.status_code,
            detail=detail,
        )
    except httpx.RequestError as e:
        logger.error(f"Error de conexión en auth BDC: {type(e).__name__} - {str(e)}")
        logger.info(f"Error de conexión en auth BDC: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo conectar con el servicio BDC: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error inesperado en auth BDC: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al autenticar con BDC: {str(e)}",
        )

@router.get(
    "/healthcheck",
    response_model=BDCHealthcheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Endpoint de estado de servicio",
    tags=["BDC - Autenticacion"],
)
async def bdc_healthcheck():
    """
    Verifica el estado interno del servicio del Banco de Comercio
    
    Returns:
        BDCHealthcheckResponse: Estado del servicio BDC
    """
    try:
        bdc_url = f"{settings.bdc_base_url}/healthcheck"
        print(f"[HEALTHCHECK] Iniciando consulta a: {bdc_url}")  # Print aparece siempre en Cloud Run
        logger.info(f"[HEALTHCHECK] Consultando BDC healthcheck en: {bdc_url}")
        logger.warning(f"[HEALTHCHECK] SSL Config - cert_path: {settings.bdc_client_cert_path}")
        
        # Usar cliente configurado con SSL y certificados
        logger.info(f"[HEALTHCHECK] Creando cliente BDC... {bdc_url}")
        async with create_bdc_client() as client:
            logger.info(f"[HEALTHCHECK] Cliente creado, enviando GET request...")
            response = await client.get(
                bdc_url,
                headers={"accept": "application/json"}
            )
            logger.info(f"[HEALTHCHECK] Respuesta recibida: {response.status_code}")
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"BDC healthcheck response: {data}")
            
            # Verificar si la respuesta tiene el formato esperado
            if isinstance(data, dict):
                status_code_value = data.get('statusCode')
                
                # Si statusCode no es un entero, el servicio BDC no está disponible
                if not isinstance(status_code_value, int):
                    logger.warning(f"[HEALTHCHECK] BDC retornó respuesta inválida: {data}")
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"Servicio BDC no disponible: {status_code_value or data}",
                    )

            _raise_if_bdc_business_error(
                data,
                "Servicio BDC no disponible",
                context="[HEALTHCHECK]",
                http_status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
            
            return BDCHealthcheckResponse(**data)
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Error HTTP en healthcheck BDC: {e.response.status_code} - {e.response.text}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Servicio BDC no disponible: {e.response.status_code}",
        )
    except httpx.RequestError as e:
        error_msg = f"[HEALTHCHECK] Error de conexión: {type(e).__name__} - {str(e)}"
        print(error_msg)  # Print para asegurar que aparezca en logs
        logger.error(error_msg)
        logger.error(f"[HEALTHCHECK] URL intentada: {bdc_url}")
        logger.error(f"[HEALTHCHECK] Certificados configurados: cert={settings.bdc_client_cert_path}, key={settings.bdc_client_key_path}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo conectar con el servicio BDC: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error inesperado en healthcheck BDC: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al consultar healthcheck BDC: {str(e)}",
        )

@router.get(
    "/accounts",
    response_model=BDCAccountsResponse,
    status_code=status.HTTP_200_OK,
    summary="Endpoint de listado de cuentas",
    tags=["BDC - Cuentas"],
)
async def get_accounts(
    token: str = Query(..., description="Token JWT requerido"),
    user_repository: UserRepository = Depends(get_user_repository),
):
    """
    Obtiene las cuentas asociadas a la entidad en BDC
    
    Requiere token JWT para validación del usuario.
    
    """
    try:
        # Validar JWT y obtener usuario
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

        user = await user_repository.get_by_id(UUID(user_id_str))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        
        logger.info(f"Consultando cuentas BDC para usuario {user.id}")
        
        auth_service = get_bdc_auth_service()
        bdc_token = await auth_service.get_token()
        bdc_url = f"{settings.bdc_base_url}/accounts"
        
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bdc_token}"
        }
        
        async with create_bdc_client() as client:
            response = await client.get(
                bdc_url,
                headers=headers
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info("[GET_ACCOUNTS] JSON recibido desde BDC: %s", json.dumps(data, ensure_ascii=False))
            print(f"[GET_ACCOUNTS] JSON recibido desde BDC: {json.dumps(data, ensure_ascii=False)}")
            _raise_if_bdc_business_error(
                data,
                "Error al obtener cuentas en BDC",
                context="[GET_ACCOUNTS]",
                user_id=user.id,
            )

            accounts_response = BDCAccountsResponse(**data)
            logger.info(f"Cuentas BDC obtenidas exitosamente para usuario {user.id}")
            
            return accounts_response
            
    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        logger.error(f"Error HTTP al obtener cuentas BDC: {e.response.status_code} - {error_detail}")
        
        try:
            error_data = e.response.json()
            detail = error_data.get("message", error_detail)
        except Exception:
            detail = error_detail
        
        raise HTTPException(
            status_code=e.response.status_code,
            detail=detail,
        )
    except httpx.RequestError as e:
        logger.error(f"Error de conexión al obtener cuentas BDC: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo conectar con el servicio BDC: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error inesperado al obtener cuentas BDC: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener cuentas BDC: {str(e)}",
        )

@router.get(
    "/accounts/info/{cbu_cvu_alias}",
    response_model=BDCAccountInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Endpoint de información de una cuenta desde su CBU, CVU o Alias",
    tags=["BDC - Cuentas"],
)
async def get_account_info(
    cbu_cvu_alias: str,
    token: str = Query(..., description="Token JWT requerido"),
    user_repository: UserRepository = Depends(get_user_repository),
):
    """
    Obtiene información de una cuenta desde su CBU, CVU o Alias.
    """
    
    try:
        # Validar JWT y obtener usuario
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

        user = await user_repository.get_by_id(UUID(user_id_str))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        
        auth_service = get_bdc_auth_service()
        bdc_token = await auth_service.get_token()
        bdc_url = f"{settings.bdc_base_url}/accounts/info/{cbu_cvu_alias}"
        logger.info(f"Consultando info de cuenta {cbu_cvu_alias}")
        
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bdc_token}"
        }
        
        async with create_bdc_client() as client:
            response = await client.get(
                bdc_url,
                headers=headers
            )
            response.raise_for_status()
            
            data = response.json()
            _raise_if_bdc_business_error(
                data,
                "Error al obtener información de cuenta en BDC",
                context="[GET_ACCOUNT_INFO]",
                user_id=user.id,
            )

            logger.info("Info de cuenta BDC obtenida exitosamente")
            
            return BDCAccountInfoResponse(**data)
            
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        logger.error(f"Error HTTP al obtener info de cuenta BDC: {e.response.status_code} - {error_detail}")
        
        try:
            error_data = e.response.json()
            detail = error_data.get("message", error_detail)
        except Exception:
            detail = error_detail
        
        raise HTTPException(
            status_code=e.response.status_code,
            detail=detail,
        )
    except httpx.RequestError as e:
        logger.error(f"Error de conexión al obtener info de cuenta BDC: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo conectar con el servicio BDC: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error inesperado al obtener info de cuenta BDC: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener info de cuenta BDC: {str(e)}",
        )

@router.post(
    "/accounts/get-cvu-accounts",
    response_model=BDCResponse,
    status_code=status.HTTP_200_OK,
    summary="Endpoint de listado de subcuentas",
    tags=["BDC - Subcuentas"],
)
async def get_cvu_accounts(
    request_data: BDCGetCvuAccountsRequest,
    token: str = Query(..., description="Token JWT requerido"),
    user_repository: UserRepository = Depends(get_user_repository),
):
    """
    Obtiene el listado de subcuentas CVU.
    
    Endpoint público que usa token BDC válido.
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

        user = await user_repository.get_by_id(UUID(user_id_str))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        
        auth_service = get_bdc_auth_service()
        bdc_token = await auth_service.get_token()

        payload = request_data.model_dump(exclude_none=True)
        signature = _calculate_bdc_signature("/accounts/get-cvu-accounts", payload)
        
        bdc_url = f"{settings.bdc_base_url}/accounts/get-cvu-accounts"
        logger.info("Consultando listado de subcuentas CVU")
        
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bdc_token}",
            "X-SIGNATURE": signature,
        }
        
        async with create_bdc_client() as client:
            response = await client.post(
                bdc_url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            _raise_if_bdc_business_error(
                data,
                "Error al obtener subcuentas CVU en BDC",
                context="[GET_CVU_ACCOUNTS]",
                user_id=user.id,
            )
            logger.info("Listado de subcuentas CVU obtenido exitosamente")
            
            return BDCResponse(**data)
            
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        logger.error(f"Error HTTP al obtener subcuentas CVU: {e.response.status_code} - {error_detail}")
        
        try:
            error_data = e.response.json()
            detail = error_data.get("message", error_detail)
        except Exception:
            detail = error_detail
        
        raise HTTPException(
            status_code=e.response.status_code,
            detail=detail,
        )
    except httpx.RequestError as e:
        logger.error(f"Error de conexión al obtener subcuentas CVU: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo conectar con el servicio BDC: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error inesperado al obtener subcuentas CVU: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener subcuentas CVU: {str(e)}",
        )
    
@router.post(
    "/sub-account",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Endpoint de creación de subcuenta",
    tags=["BDC - Subcuentas"],
)
async def create_sub_account(
    token: str = Query(..., description="Token JWT requerido"),
    tipo: str = Query('empresa', description="Tipo de cuenta: 'p2p' o 'empresa' (default: 'empresa')"),
    user_repository: UserRepository = Depends(get_user_repository),
    bank_account_repository: BankAccountRepository = Depends(get_bank_account_repository),
):
    """
    Crea una subcuenta en BDC y la persiste en la base de datos.
    
    La APP solo necesita enviar el token JWT para validación e identificación del usuario.
    El servidor genera:
    - originId: numérico único (secuencia interna), con máximo 22 caracteres
    - Alias: basado en nombre.apellido del usuario con sufijo .pf
    
    Returns:
        {
            "statusCode": 0,
            "data": {
                "accountId": "ARG-00432-00100325154",
                "accountType": "CHECKING_ACCOUNT",
                "accountLabel": "ALIAS"
            }
        }
    """
    
    try:
        logger.info("[CREATE_SUB_ACCOUNT] Iniciando creación de subcuenta")
        
        # ====== VALIDAR JWT Y OBTENER USUARIO ======
        raw_token = token
        if not raw_token:
            logger.warning("[CREATE_SUB_ACCOUNT] Token no proporcionado")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token requerido",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.info("[CREATE_SUB_ACCOUNT] Verificando token JWT")
        user_id_str = verify_access_token(raw_token)
        if not user_id_str:
            logger.warning("[CREATE_SUB_ACCOUNT] Token inválido o expirado")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.info(f"[CREATE_SUB_ACCOUNT] Obteniendo usuario: {user_id_str}")
        user = await user_repository.get_by_id(UUID(user_id_str))
        if not user:
            logger.warning(f"[CREATE_SUB_ACCOUNT] Usuario no encontrado: {user_id_str}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        # ====== GENERAR ALIAS ======
        logger.info(f"[CREATE_SUB_ACCOUNT] Generando alias único para usuario {user.id}")
        alias = await _generate_alias(user, bank_account_repository)
        
        # ====== VALIDAR DATOS DEL USUARIO ======
        if not user.cuit_cuil:
            logger.error(f"[CREATE_SUB_ACCOUNT] Usuario {user.id} no tiene CUIT/CUIL")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario debe tener CUIT/CUIL registrado para crear una subcuenta",
            )
        
        # Construir nombre completo del usuario
        if user.first_name and user.last_name:
            person_name = f"{user.first_name} {user.last_name}"
        elif user.full_name:
            person_name = user.full_name
        else:
            # Extraer nombre del email como último recurso
            person_name = user.email.split("@")[0].title()
        
        logger.info(f"[CREATE_SUB_ACCOUNT] Datos del usuario - CUIT: {user.cuit_cuil}, Nombre: {person_name}")
        
        # ====== OBTENER TOKEN BDC Y PREPARAR PAYLOAD ======
        logger.info("[CREATE_SUB_ACCOUNT] Obteniendo token BDC")
        auth_service = get_bdc_auth_service()
        bdc_token = await auth_service.get_token()
        
        # CBU de testing (configurado en settings.bdc_test_cbu)
        test_cbu = settings.bdc_test_cbu
        logger.info(f"[CREATE_SUB_ACCOUNT] Usando CBU de testing: {test_cbu}")

        # OriginId para request a BDC (único y corto)
        request_origin_id = await bank_account_repository.get_next_origin_id()
        request_origin_id_str = str(request_origin_id)
        if len(request_origin_id_str) > 22:
            logger.error(
                "[CREATE_SUB_ACCOUNT] originId excede 22 caracteres: %s",
                request_origin_id_str,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="originId excede el límite máximo de 22 caracteres",
            )
        
        # Armar payload exacto para enviar a BDC
        payload = {
            "originId": request_origin_id_str,
            "cbu": test_cbu,             # CBU hardcodeado para testing
            "label": alias,              # Alias generado
            "currency": "032"           # Código de moneda ARS
        }

        if tipo.strip().lower() == "p2p":
            payload["owner"] = {
                "personIdType": "CUI",
                "personId": user.cuit_cuil,      # CUIT/CUIL del usuario autenticado
                "personName": person_name        # Nombre completo del usuario
            }
        
        logger.info(f"[CREATE_SUB_ACCOUNT] Payload para BDC: {payload}")
        print(f"[CREATE_SUB_ACCOUNT] Payload para BDC: {payload}")  # Print para asegurar que aparezca en logs
        # Calcular firma HMAC
        signature = _calculate_bdc_signature("/sub-account", payload)
        
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bdc_token}",
            "X-SIGNATURE": signature,
        }
        
        # ====== ENVIAR A BDC ======
        logger.info("[CREATE_SUB_ACCOUNT] Enviando solicitud a BDC")
        bdc_url = f"{settings.bdc_base_url}/sub-account"
        
        async with create_bdc_client() as client:
            response = await client.post(
                bdc_url,
                headers=headers,
                json=payload
            )
            
            # Si el token expiró, renovar e intentar de nuevo
            if response.status_code == 401:
                logger.warning("[CREATE_SUB_ACCOUNT] Token BDC rechazado (401), renovando...")
                auth_service.invalidate_cache()
                bdc_token = await auth_service.get_token()
                headers["Authorization"] = f"Bearer {bdc_token}"
                response = await client.post(
                    bdc_url,
                    headers=headers,
                    json=payload,
                )
            
            response.raise_for_status()
            
            bdc_response = response.json()
            
            # Log completo de la respuesta del banco
            logger.info(f"[CREATE_SUB_ACCOUNT] Respuesta BDC COMPLETA: {bdc_response}")
            print(f"[CREATE_SUB_ACCOUNT] ===== RESPUESTA COMPLETA DEL BANCO =====")
            print(f"[CREATE_SUB_ACCOUNT] {json.dumps(bdc_response, indent=2, ensure_ascii=False)}")
            print(f"[CREATE_SUB_ACCOUNT] ============================================")
            
            logger.info(f"[CREATE_SUB_ACCOUNT] Respuesta BDC recibida: statusCode={bdc_response.get('statusCode')}")
            
            # ====== PROCESAR RESPUESTA Y PERSISTIR EN BD ======
            if bdc_response.get("statusCode") == 0 and bdc_response.get("data"):
                bdc_data = bdc_response["data"]
                
                logger.info(f"[CREATE_SUB_ACCOUNT] Persistiendo registro con datos de BDC")

                # Extraer CVU/CBU real desde accountRouting.address (BDC devuelve lista)
                cvu_address = None
                account_routing = bdc_data.get("accountRouting", [])
                if isinstance(account_routing, list):
                    for routing in account_routing:
                        if isinstance(routing, dict) and routing.get("address"):
                            cvu_address = routing.get("address")
                            break
                elif isinstance(account_routing, dict):
                    cvu_address = account_routing.get("address")

                if not cvu_address:
                    logger.error(f"[CREATE_SUB_ACCOUNT] BDC no retornó accountRouting.address válido: {account_routing}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="BDC no devolvió CVU/CBU en accountRouting.address",
                    )

                logger.info(f"[CREATE_SUB_ACCOUNT] CVU/CBU recibido desde BDC: {cvu_address}")

                # Crear el registro local con el CVU real devuelto por BDC
                new_account = BankAccount(
                    user_id=user.id,
                    cvu_cbu=cvu_address,
                    account_type=AccountType.CVU,
                    alias=alias,
                    status=AccountStatus.ACTIVE if bdc_data.get("info", {}).get("status") == "ACTIVE" else AccountStatus.SUSPENDED,
                    currency="ARS",
                    bdc_account_id=bdc_data.get("accountId"),
                    balance=None,
                    origin_id=request_origin_id,
                )

                saved_account = await bank_account_repository.create(new_account)
                logger.info(
                    f"[CREATE_SUB_ACCOUNT] Registro creado en BD - accountId: {bdc_data.get('accountId')}, "
                    f"origin_id: {saved_account.origin_id}, UUID: {saved_account.id}"
                )
                
                logger.info("[CREATE_SUB_ACCOUNT] Subcuenta creada exitosamente")
                return bdc_response
            else:
                logger.warning(f"[CREATE_SUB_ACCOUNT] BDC retornó status no exitoso: {bdc_response}")
                return bdc_response
            
    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        logger.error(f"[CREATE_SUB_ACCOUNT] Error HTTP al crear subcuenta BDC: {e.response.status_code} - {error_detail}")
        
        try:
            error_data = e.response.json()
            detail = error_data.get("message", error_detail)
        except Exception:
            detail = error_detail
        
        raise HTTPException(
            status_code=e.response.status_code,
            detail=detail,
        )
    except httpx.RequestError as e:
        logger.error(f"[CREATE_SUB_ACCOUNT] Error de conexión al crear subcuenta BDC: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo conectar con el servicio BDC: {str(e)}",
        )
    except Exception as e:
        logger.error(f"[CREATE_SUB_ACCOUNT] Error inesperado al crear subcuenta BDC: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear subcuenta BDC: {str(e)}",
        )


@router.get(
    "/sub-account/{origin_id}",
    response_model=BDCSubAccountQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Endpoint de consulta de subcuentas",
    tags=["BDC - Subcuentas"],
)
async def get_sub_account(
    origin_id: str,
    token: str = Query(..., description="Token JWT requerido"),
    user_repository: UserRepository = Depends(get_user_repository),
):
    """
    Consulta una subcuenta por originId.
    
    Endpoint público que usa token BDC válido.
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

        user = await user_repository.get_by_id(UUID(user_id_str))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        auth_service = get_bdc_auth_service()
        bdc_token = await auth_service.get_token()
        
        bdc_url = f"{settings.bdc_base_url}/sub-account/{origin_id}"
        logger.info(f"Consultando subcuenta BDC originId={origin_id}")
        
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {bdc_token}"
        }
        
        async with create_bdc_client() as client:
            response = await client.get(
                bdc_url,
                headers=headers
            )
            response.raise_for_status()
            
            data = response.json()
            _raise_if_bdc_business_error(
                data,
                "Error al consultar subcuenta en BDC",
                context="[GET_SUB_ACCOUNT]",
                user_id=user.id,
            )
            logger.info("Subcuenta BDC consultada exitosamente")
            
            return BDCSubAccountQueryResponse(**data)
            
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        logger.error(f"Error HTTP al consultar subcuenta BDC: {e.response.status_code} - {error_detail}")
        
        try:
            error_data = e.response.json()
            detail = error_data.get("message", error_detail)
        except Exception:
            detail = error_detail
        
        raise HTTPException(
            status_code=e.response.status_code,
            detail=detail,
        )
    except httpx.RequestError as e:
        logger.error(f"Error de conexión al consultar subcuenta BDC: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo conectar con el servicio BDC: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error inesperado al consultar subcuenta BDC: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al consultar subcuenta BDC: {str(e)}",
        )
    
@router.patch(
    "/sub-account/{cvu}",
    response_model=BDCUpdateAccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Endpoint de Edicion de Alias",
    tags=["BDC - Subcuentas"],
)
async def update_account_alias_cvu(
    cvu: str,
    account_data: BDCUpdateSubAccountRequest,
    token: str = Query(..., description="Token JWT requerido"),
    user_repository: UserRepository = Depends(get_user_repository),
    bank_account_repository: BankAccountRepository = Depends(get_bank_account_repository),
):
    """
    Actualiza el alias de una subcuenta en el Banco de Comercio
    
    Permite modificar el alias/etiqueta o el estado de una cuenta identificada por su CVU.
    El alias debe seguir el formato de palabras separadas por puntos.
    
    Args:
        cvu: Código de CVU de la subcuenta a actualizar
        account_data: Datos de actualización (estado y/o nuevo alias)
        current_user: Usuario autenticado
    
    Returns:
        BDCUpdateAccountResponse: Información de la cuenta actualizada
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

        user = await user_repository.get_by_id(UUID(user_id_str))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        
        auth_service = get_bdc_auth_service()
        bdc_token = await auth_service.get_token()
        
        # Construir URL del endpoint
        bdc_url = f"{settings.bdc_base_url}/sub-account/{cvu}"
        logger.info(f"Actualizando alias de cuenta {cvu}")
        if account_data.accountLabel:
            logger.debug(f"Nuevo alias: {account_data.accountLabel}")
        if account_data.status:
            logger.debug(f"Nuevo estado: {account_data.status}")
        
        # Convertir el modelo a dict excluyendo valores None para evitar
        # discrepancias entre el body enviado y el usado para X-SIGNATURE.
        payload = account_data.model_dump(exclude_none=True)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe enviar al menos un campo para actualizar (status o accountLabel)",
            )

        signature = _calculate_bdc_signature(f"/sub-account/{cvu}", payload)

        # Preparar headers con autenticación
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bdc_token}",
            "X-SIGNATURE": signature,
        }
        
        # Realizar la petición con SSL y certificados configurados
        async with create_bdc_client() as client:
            response = await client.patch(
                bdc_url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            _raise_if_bdc_business_error(
                result,
                "Error al actualizar subcuenta en BDC",
                context="[UPDATE_SUB_ACCOUNT]",
                user_id=user.id,
            )
            logger.info(f"Alias actualizado exitosamente para CVU {cvu}: {result.get('data', {}).get('accountLabel')}")
            
            # Persistir los cambios en la base de datos
            if result.get('statusCode') == 0 and account_data.status:
                try:
                    # Buscar la cuenta por CVU en la BD
                    logger.info(f"Buscando cuenta en BD con CVU: {cvu}")
                    db_account = await bank_account_repository.get_by_cvu_cbu(cvu)
                    if db_account:
                        logger.info(f"Cuenta encontrada en BD con ID {db_account.id}")
                        logger.info(f"Status recibido de BDC: {account_data.status}")
                        
                        # Convertir el status de string a enum (BDC envía mayúscula, enum usa minúscula)
                        status_value = account_data.status.lower()
                        logger.info(f"Status convertido para BD: {status_value}")
                        
                        # Validar que sea un status válido
                        valid_statuses = [s.value for s in AccountStatus]
                        if status_value not in valid_statuses:
                            logger.warning(f"Status inválido '{status_value}'. Valores válidos: {valid_statuses}")
                            status_value = AccountStatus.SUSPENDED.value
                        
                        logger.info(f"Actualizando status en BD para cuenta {cvu}: {status_value}")
                        result_update = await bank_account_repository.update(
                            db_account.id,
                            status=status_value
                        )
                        if result_update:
                            logger.info(f"✓ Status persistido en BD para cuenta {cvu}: {result_update.status}")
                        else:
                            logger.error(f"✗ Fallo al actualizar cuenta en BD con ID {db_account.id}")
                    else:
                        logger.warning(f"✗ No se encontró cuenta en BD con CVU'{cvu}'")
                        logger.debug(f"Búsqueda realizada con CVU: {cvu}")
                except Exception as db_error:
                    logger.exception(f"✗ Error al persistir cambios en BD para CVU {cvu}")
                    logger.error(f"Detalles: {str(db_error)}")
                    # No lanzar excepción, ya que el cambio en BDC fue exitoso
            else:
                logger.info(f"Validación de persistencia: statusCode={result.get('statusCode')}, status={account_data.status}")
            
            try:
                return BDCUpdateAccountResponse(**result)
            except ValidationError:
                bank_status = result.get("statusCode") if isinstance(result, dict) else None
                bank_message = result.get("message") if isinstance(result, dict) else None
                bank_time = result.get("time") if isinstance(result, dict) else None
                logger.error(
                    "Respuesta BDC inválida al actualizar subcuenta. statusCode=%s message=%s payload=%s",
                    bank_status,
                    bank_message,
                    result,
                )

                bank_status_text = str(bank_status) if bank_status is not None else "N/A"
                bank_message_text = bank_message or "Sin mensaje"
                detail = f"Error en BDC (statusCode={bank_status_text}): {bank_message_text}"
                if bank_time:
                    detail = f"{detail} [{bank_time}]"

                raise HTTPException(
                    status_code=(
                        status.HTTP_400_BAD_REQUEST
                        if isinstance(bank_status, int) and bank_status != 0
                        else status.HTTP_502_BAD_GATEWAY
                    ),
                    detail=detail,
                )

    except HTTPException:
        raise
            
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        logger.error(f"Error HTTP al actualizar alias BDC: {e.response.status_code} - {error_detail}")
        
        # Si es 404, la cuenta no existe
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subcuenta con CVU '{cvu}' no encontrada",
            )
        
        # Intentar parsear el error de BDC
        try:
            error_data = e.response.json()
            detail = error_data.get("message", error_detail)
        except:
            detail = error_detail
        
        raise HTTPException(
            status_code=e.response.status_code,
            detail=detail,
        )
    
    except httpx.RequestError as e:
        logger.error(f"Error de conexión al actualizar alias BDC: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo conectar con el servicio BDC: {str(e)}",
        )
    
    except Exception as e:
        logger.error(f"Error inesperado al actualizar alias BDC: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el alias de la cuenta: {str(e)}",
        )

@router.post(
    "/movements/{cbu_cvu_alias}",
    response_model=BDCMovementsResponse,
    status_code=status.HTTP_200_OK,
    summary="Endpoint de listado de movimientos",
    tags=["BDC - Movimientos"],
)
async def get_movements(
    cbu_cvu_alias: str,
    request_data: BDCMovementsRequest,
    token: str = Query(..., description="Token JWT requerido"),
    user_repository: UserRepository = Depends(get_user_repository),
):
    """
    Obtiene el listado de movimientos de una cuenta por CBU, CVU o Alias.
    
    Requiere token JWT para autenticación.
    """
    
    try:
        # Validar JWT y obtener usuario
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

        user = await user_repository.get_by_id(UUID(user_id_str))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        
        # Obtener token de autenticación con BDC
        auth_service = get_bdc_auth_service()
        bdc_token = await auth_service.get_token()
        
        bdc_url = f"{settings.bdc_base_url}/movements/{cbu_cvu_alias}"
        logger.info(f"Consultando movimientos BDC para cuenta {cbu_cvu_alias} del usuario {user.id}")
        
        # Preparar payload y calcular firma HMAC
        payload = request_data.model_dump()
        payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        signature = _calculate_bdc_signature(f"movements/{cbu_cvu_alias}", payload_json)
        
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bdc_token}",
            "X-SIGNATURE": signature,
        }
        
        logger.info(f"Payload JSON para BDC: {payload_json}")
        print(f"Payload JSON para BDC: {payload_json}")  # Print para asegurar que aparezca en logs
        logger.info(f"Headers para BDC: {headers}")
        print(f"Headers para BDC: {headers}")  # Print para asegurar que aparezca en logs
        
        async with create_bdc_client() as client:
            response = await client.post(
                bdc_url,
                headers=headers,
                content=payload_json
            )
            
            # Si el token expiró, renovar e intentar de nuevo
            if response.status_code == 401:
                logger.warning("Token BDC rechazado (401), renovando...")
                auth_service.invalidate_cache()
                bdc_token = await auth_service.get_token()
                headers["Authorization"] = f"Bearer {bdc_token}"
                response = await client.post(
                    bdc_url,
                    headers=headers,
                    content=payload_json,
                )
            
            response.raise_for_status()
            
            bdc_response = response.json()
            _raise_if_bdc_business_error(
                bdc_response,
                "Error al obtener movimientos en BDC",
                context="[GET_MOVEMENTS]",
                user_id=user.id,
            )
            logger.info(f"Movimientos BDC obtenidos exitosamente para usuario {user.id}")
            return BDCMovementsResponse(**bdc_response)
            
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        logger.error(f"Error HTTP al obtener movimientos BDC: {e.response.status_code} - {error_detail}")
        
        try:
            error_data = e.response.json()
            detail = error_data.get("message", error_detail)
        except Exception:
            detail = error_detail
        
        raise HTTPException(
            status_code=e.response.status_code,
            detail=detail,
        )
    except httpx.RequestError as e:
        logger.error(f"Error de conexión al obtener movimientos BDC: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo conectar con el servicio BDC: {str(e)}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado al obtener movimientos BDC: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener movimientos BDC: {str(e)}",
        )

@router.post(
    "/global/data/get-entity",
    response_model=BDCResponse,
    status_code=status.HTTP_200_OK,
    summary="Endpoint de información de entidad",
    tags=["BDC - Información Personal"],
)
async def get_entity_data(
    request_data: BDCGetEntityRequest,
    token: str = Query(..., description="Token JWT requerido"),
    user_repository: UserRepository = Depends(get_user_repository),
):
    """
    Obtiene información personal de una entidad desde su CBU/CVU o Alias.
    
    Requiere token JWT para autenticación del usuario.
    """
    try:
        # Validar JWT y obtener usuario
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

        user = await user_repository.get_by_id(UUID(user_id_str))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        
        # Obtener token de autenticación con BDC
        auth_service = get_bdc_auth_service()
        bdc_token = await auth_service.get_token()

        bdc_url = f"{settings.bdc_base_url}/global/data/get-entity"
        logger.info(f"Consultando información de entidad para usuario {user.id}")
        
        payload = request_data.model_dump()
        signature = _calculate_bdc_signature("/global/data/get-entity", payload)

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bdc_token}",
            "X-SIGNATURE": signature,
        }

        async with create_bdc_client() as client:
            response = await client.post(
                bdc_url,
                headers=headers,
                json=payload,
            )

            if response.status_code == 401:
                logger.warning("Token BDC rechazado (401), renovando...")
                auth_service.invalidate_cache()
                bdc_token = await auth_service.get_token()
                headers["Authorization"] = f"Bearer {bdc_token}"
                response = await client.post(
                    bdc_url,
                    headers=headers,
                    json=payload,
                )

            response.raise_for_status()
            data = response.json()
            _raise_if_bdc_business_error(
                data,
                "Error al obtener información de entidad en BDC",
                context="[GET_ENTITY_DATA]",
                user_id=user.id,
            )
            logger.info(f"Información de entidad obtenida exitosamente para usuario {user.id}")

            return BDCResponse(**data)

    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        logger.error(f"Error HTTP al obtener información de entidad BDC: {e.response.status_code} - {error_detail}")

        try:
            error_data = e.response.json()
            detail = error_data.get("message", error_detail)
        except Exception:
            detail = error_detail

        raise HTTPException(
            status_code=e.response.status_code,
            detail=detail,
        )
    except httpx.RequestError as e:
        logger.error(f"Error de conexión al obtener información de entidad BDC: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo conectar con el servicio BDC: {str(e)}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado al obtener información de entidad BDC: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener información de entidad BDC: {str(e)}",
        )


@router.post(
    "/apiV1/ultimosMovimientos",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Endpoint apiV1/ultimosMovimientos",
    tags=["BDC - Movimientos"],
)
async def get_ultimos_movimientos(
    request_data: BDCUltimosMovimientosRequest,
    token: str = Query(..., description="Token JWT requerido"),
    user_repository: UserRepository = Depends(get_user_repository),
):
    """
    Reenvía la solicitud de últimos movimientos al endpoint legacy de BDC.
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

        user = await user_repository.get_by_id(UUID(user_id_str))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        auth_service = get_bdc_auth_service()
        bdc_token = await auth_service.get_token()
        bdc_url = f"{settings.bdc_base_url}/apiV1/ultimosMovimientos"
        payload = request_data.model_dump()

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bdc_token}",
        }

        async with create_bdc_client() as client:
            response = await client.post(
                bdc_url,
                headers=headers,
                json=payload,
            )

            if response.status_code == 401:
                logger.warning("Token BDC rechazado (401) en apiV1/ultimosMovimientos, renovando...")
                auth_service.invalidate_cache()
                bdc_token = await auth_service.get_token()
                headers["Authorization"] = f"Bearer {bdc_token}"
                response = await client.post(
                    bdc_url,
                    headers=headers,
                    json=payload,
                )

            response.raise_for_status()
            result = response.json()
            _raise_if_bdc_business_error(
                result,
                "Error al obtener últimos movimientos en BDC",
                context="[ULTIMOS_MOVIMIENTOS]",
                user_id=user.id,
            )
            return result

    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        logger.error(
            "Error HTTP en apiV1/ultimosMovimientos BDC: %s - %s",
            e.response.status_code,
            error_detail,
        )
        try:
            error_data = e.response.json()
            detail = error_data.get("message", error_detail)
        except Exception:
            detail = error_detail
        raise HTTPException(
            status_code=e.response.status_code,
            detail=detail,
        )
    except httpx.RequestError as e:
        logger.error(
            "Error de conexión en apiV1/ultimosMovimientos BDC: %s - %s",
            type(e).__name__,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo conectar con el servicio BDC: {str(e)}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error inesperado en apiV1/ultimosMovimientos: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener últimos movimientos: {str(e)}",
        )


@router.post(
    "/transfer-request",
    response_model=BDCTransferSuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Endpoint de envío de transferencia (simplificado y seguro)",
    tags=["BDC - Transferencias"],
)
async def create_transfer_request(
    transfer_input: BDCTransferRequestSimpleInput,
    token: Optional[str] = Query(None, description="Token JWT si no se usa Authorization"),
    payment_operation: PaymentOperation = Depends(get_payment_operation),
    user_repository: UserRepository = Depends(get_user_repository),
    bank_account_repository: BankAccountRepository = Depends(get_bank_account_repository),
):
    """
    Crea una solicitud de transferencia en el Banco de Comercio
    
    **Seguridad mejorada**: La APP solo envía:
    - CBU/CVU destino
    - Monto
    - Descripción/concepto (opcional)
    
    El servidor completa automáticamente:
    - **FROM**: Datos de la cuenta del usuario autenticado (token JWT)
    - **TO**: Datos consultados del destinatario desde BDC
    
    Esto evita que se falseen datos de origen o destino.
    
    **Nota**: El `originId` se genera automáticamente en la base de datos
    
    Returns:
        BDCTransferSuccessResponse: Confirmación de la transferencia creada
    """
    # Log INICIAL para verificar que estamos entrando al método
    print("[TRANSFER-REQUEST] Iniciando endpoint de transferencia")
    logger.info("[TRANSFER-REQUEST] Iniciando endpoint de transferencia")
    
    try:
        # ====== VALIDAR JWT Y OBTENER USUARIO ======
        raw_token = token
        logger.info("[TRANSFER-REQUEST] Validando token JWT")
        if not raw_token:
            logger.warning("[TRANSFER-REQUEST] Token no proporcionado")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token requerido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.info("[TRANSFER-REQUEST] Verificando token JWT")
        user_id_str = verify_access_token(raw_token)
        if not user_id_str:
            logger.warning("[TRANSFER-REQUEST] Token inválido o expirado")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.info(f"[TRANSFER-REQUEST] Obteniendo usuario: {user_id_str}")
        user = await user_repository.get_by_id(UUID(user_id_str))
        if not user:
            logger.warning(f"[TRANSFER-REQUEST] Usuario no encontrado: {user_id_str}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        # ====== OBTENER CUENTA ORIGEN DEL USUARIO AUTENTICADO ======
        logger.info(f"[TRANSFER-REQUEST] Buscando cuenta del usuario {user.id}")
        
        # Intentar obtener la cuenta principal del usuario
        source_account = await bank_account_repository.get_primary_account(user.id)
        
        if not source_account:
            # Si no hay cuenta principal, buscar la primera activa
            logger.info(f"[TRANSFER-REQUEST] No hay cuenta principal, buscando cuentas activas")
            user_accounts = await bank_account_repository.get_user_accounts(user.id)
            
            if not user_accounts:
                logger.error(f"[TRANSFER-REQUEST] Usuario {user.id} no tiene cuentas registradas")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El usuario no tiene cuentas bancarias registradas"
                )
            
            # Buscar la primera cuenta activa
            for account in user_accounts:
                if account.status == AccountStatus.ACTIVE:
                    source_account = account
                    break
            
            if not source_account:
                logger.error(f"[TRANSFER-REQUEST] Usuario {user.id} no tiene cuentas activas")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El usuario no tiene cuentas activas para transferir"
                )
        
        logger.info(f"[TRANSFER-REQUEST] Cuenta origen: {source_account.cvu_cbu}")
        
        # Validar que el usuario tenga CUIT/CUIL
        if not user.cuit_cuil:
            logger.error(f"[TRANSFER-REQUEST] Usuario {user.id} no tiene CUIT/CUIL")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario debe tener CUIT/CUIL registrado para realizar transferencias"
            )
        
        # ====== CONSULTAR INFORMACIÓN DEL DESTINATARIO DESDE BDC ======
        logger.info(f"[TRANSFER-REQUEST] Consultando información del destinatario: {transfer_input.destinationCbuCvu}")
        
        auth_service = get_bdc_auth_service()
        bdc_token = await auth_service.get_token()
        
        bdc_info_url = f"{settings.bdc_base_url}/accounts/info/{transfer_input.destinationCbuCvu}"
        
        async with create_bdc_client() as client:
            info_response = await client.get(
                bdc_info_url,
                headers={
                    "accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {bdc_token}"
                }
            )
            
            if info_response.status_code == 401:
                logger.warning("[TRANSFER-REQUEST] Token BDC expirado al consultar destinatario, renovando...")
                auth_service.invalidate_cache()
                bdc_token = await auth_service.get_token()
                info_response = await client.get(
                    bdc_info_url,
                    headers={
                        "accept": "application/json",
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {bdc_token}"
                    }
                )
            
            if info_response.status_code != 200:
                logger.error(f"[TRANSFER-REQUEST] Error al consultar destinatario: {info_response.status_code} - {info_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No se pudo verificar la cuenta destino: {transfer_input.destinationCbuCvu}"
                )
            
            destination_info = info_response.json()
            
            if destination_info.get("statusCode") != 0:
                logger.error(f"[TRANSFER-REQUEST] BDC no encontró la cuenta destino: {destination_info}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La cuenta destino no existe o no es válida"
                )
            
            dest_data = destination_info.get("data", {})
            dest_account_routing = dest_data.get("accountRouting", {})
            dest_owners = dest_data.get("owners", [])
            
            # BDC devuelve una lista de owners, tomamos el primero
            if not dest_owners:
                logger.error(f"[TRANSFER-REQUEST] BDC no retornó propietarios para la cuenta: {transfer_input.destinationCbuCvu}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se pudo obtener información del propietario de la cuenta destino"
                )
            
            dest_owner = dest_owners[0]
            logger.info(f"[TRANSFER-REQUEST] Destinatario encontrado: {dest_owner.get('id')} ({dest_owner.get('displayName', 'N/A')})")
        
        # ====== VALIDAR MONTO ======
        logger.info("[TRANSFER-REQUEST] Validando monto")
        try:
            transfer_amount = Decimal(str(transfer_input.amount))
        except Exception as e:
            logger.error(f"[TRANSFER-REQUEST] Monto inválido: {transfer_input.amount} - {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_AMOUNT_FORMAT",
                    "message": f"Monto inválido: {transfer_input.amount}",
                    "error": str(e)
                },
            )
        
        if transfer_amount <= 0:
            logger.warning(f"[TRANSFER-REQUEST] Monto no positivo: {transfer_amount}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_TRANSFER_AMOUNT",
                    "message": "El monto de transferencia debe ser mayor a cero",
                    "amount": str(transfer_amount)
                },
            )
        transfer_amount = transfer_amount.quantize(Decimal("0.01"))
        
        # ====== VERIFICAR SALDO DISPONIBLE ======
        logger.info(f"[TRANSFER-REQUEST] Verificando saldo disponible para monto: {transfer_amount}")
        available_balance = await bank_account_repository.calculate_balance(
            source_account.cvu_cbu
        )
        logger.info(f"[TRANSFER-REQUEST] Saldo disponible: {available_balance}")
        
        if transfer_amount > available_balance:
            logger.warning(f"[TRANSFER-REQUEST] Fondos insuficientes: {transfer_amount} > {available_balance}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INSUFFICIENT_FUNDS",
                    "message": "Saldo insuficiente para realizar la transferencia",
                    "required": str(transfer_amount),
                    "available": str(available_balance)
                },
            )
        
        # ====== CONSTRUIR DATOS COMPLETOS DE TRANSFERENCIA ======
        logger.info("[TRANSFER-REQUEST] Construyendo datos de transferencia con información verificada")
        
        # FROM: Datos del usuario autenticado y su cuenta
        from_data = TransferParty(
            addressType="CBU_CVU",
            address=source_account.cvu_cbu,
            owner=TransferPartyOwner(
                personIdType="CUI",
                personId=user.cuit_cuil,
                personName=getattr(user, "full_name", None)
            )
        )

        # TO: Datos obtenidos de BDC
        to_data = TransferParty(
            addressType=dest_account_routing.get("scheme", "CBU_CVU"),
            address=dest_account_routing.get("address", transfer_input.destinationCbuCvu),
            owner=TransferPartyOwner(
                personIdType=dest_owner.get("idType", "CUI"),
                personId=dest_owner.get("id"),
                personName=dest_owner.get("displayName")
            )
        )

        if not to_data.owner.person_id:
            logger.error(f"[TRANSFER-REQUEST] BDC no retornó ID del propietario: {dest_owner}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo obtener el ID del propietario de la cuenta destino"
            )

        logger.info(f"[TRANSFER-REQUEST] FROM: {from_data.address} - TO: {to_data.address}")

        # ====== CREAR REGISTRO EN BD PRIMERO PARA OBTENER ID AUTOINCREMENTAL ======
        logger.info("[TRANSFER-REQUEST] Creando registro en BD antes de enviar a BDC")

        # No incluir origin_id: la base de datos lo generará automáticamente
        payment_data = PaymentData(
            source=from_data,
            destination=to_data,
            body=TransferBody(
                amount=transfer_amount,
                currencyId=transfer_input.currencyId,
                description=transfer_input.description,
                concept=transfer_input.concept
            ),
            status=PaymentState.CREATED,
            metadata={}
        )
        
        # Guardar en la base de datos para obtener el ID autoincremental
        if not payment_operation or not payment_operation.transfer_repository:
            logger.error("[TRANSFER-REQUEST] payment_operation o transfer_repository no disponible")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Servicio de transferencias no disponible"
            )

        saved_payment = await payment_operation.transfer_repository.save(payment_data)
        logger.info(f"[TRANSFER-REQUEST] Transferencia persistida en BD con payment_id: {saved_payment.payment_id}")

        # Usar el origin_id generado por la base de datos (como int)
        origin_id = saved_payment.origin_id
        logger.info(f"[TRANSFER-REQUEST] Transfer origin_id autoincremental: {origin_id}")
        
        # ====== PREPARAR Y ENVIAR REQUEST A BDC ======
        bdc_url = f"{settings.bdc_base_url}/movements/transfer-request"
        logger.info(f"[TRANSFER-REQUEST] URL BDC: {bdc_url}")

        # Construir payload completo para BDC con originId como int
        transfer_body = TransferBody(
            amount=transfer_amount,
            currencyId=transfer_input.currencyId,
            description=transfer_input.description,
            concept=transfer_input.concept
        ).model_dump(by_alias=True)
        # Asegurar que amount sea float con dos decimales y separador '.'
        transfer_body["amount"] = float(f"{transfer_body['amount']:.2f}")

        # Serializar parties sin personName
        def party_payload(party):
            party_dict = party.model_dump(by_alias=True)
            if "owner" in party_dict:
                owner = party_dict["owner"]
                owner.pop("personName", None)
                party_dict["owner"] = owner
            return party_dict

        from_payload = party_payload(from_data)
        from_payload["address"] = transfer_input.originCbuCvu 

        payload = {
            "originId": str(origin_id),
            "from": from_payload,
            "to": party_payload(to_data),
            "body": transfer_body
        }
        
        logger.info(f"[TRANSFER-REQUEST] Payload a enviar a BDC: {payload}")
        print(f"[TRANSFER-REQUEST] Payload para BDC: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        logger.info(f"[TRANSFER-REQUEST] transfer_body dict: {transfer_body}")
        print(f"[TRANSFER-REQUEST] transfer_body dict: {json.dumps(transfer_body, indent=2, ensure_ascii=False)}")
        
        # Obtener token BDC
        bdc_token = await auth_service.get_token()
        
        # ====== ENVIAR A BDC ======
        logger.info("[TRANSFER-REQUEST] Enviando POST a BDC")
        async with create_bdc_client() as client:
            max_duplicate_retries = 2
            duplicate_retry = 0

            while True:
                signature = _calculate_bdc_signature("/movements/transfer-request", payload)
                headers = {
                    "accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {bdc_token}",
                    "X-SIGNATURE": signature,
                }

                response = await client.post(
                    bdc_url,
                    headers=headers,
                    json=payload
                )

                # Si el token expiró, renovar e intentar de nuevo
                if response.status_code == 401:
                    logger.warning("[TRANSFER-REQUEST] Token BDC rechazado (401), renovando...")
                    auth_service.invalidate_cache()
                    bdc_token = await auth_service.get_token()
                    continue

                logger.info(f"[TRANSFER-REQUEST] Respuesta BDC status: {response.status_code}")
                response.raise_for_status()

                result = response.json()
                logger.info(f"[TRANSFER-REQUEST] Respuesta BDC COMPLETA (raw): {response.text}")
                logger.info(f"[TRANSFER-REQUEST] Respuesta BDC COMPLETA (parsed): {result}")
                print("[TRANSFER-REQUEST] ===== RESPUESTA COMPLETA DEL BANCO (raw) =====")
                print(response.text)
                print("[TRANSFER-REQUEST] ===== RESPUESTA COMPLETA DEL BANCO (parsed) =====")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                print("[TRANSFER-REQUEST] ===============================================")

                is_duplicate_origin = (
                    result.get("statusCode") == 3
                    and "origin id duplicado" in (result.get("message") or "").lower()
                )
                if is_duplicate_origin and duplicate_retry < max_duplicate_retries:
                    duplicate_retry += 1
                    new_origin_id = f"{int(time.time() * 1000)}{random.randint(1000, 9999)}"
                    logger.warning(
                        "[TRANSFER-REQUEST] OriginId duplicado en BDC. Reintento %s/%s con originId=%s",
                        duplicate_retry,
                        max_duplicate_retries,
                        new_origin_id,
                    )
                    payload["originId"] = new_origin_id
                    saved_payment.origin_id = new_origin_id
                    saved_payment = await payment_operation.transfer_repository.save(saved_payment)
                    continue

                if result.get("statusCode") == 0:
                    logger.info(f"[TRANSFER-REQUEST] Transferencia creada exitosamente en BDC: {result.get('message')}")
                else:
                    logger.warning(
                        "[TRANSFER-REQUEST] BDC respondió con statusCode=%s message=%s",
                        result.get("statusCode"),
                        result.get("message"),
                    )

                # Persistir respuesta del banco como metadata de la transferencia
                try:
                    saved_payment.metadata["connector_response"] = result
                    saved_payment.metadata["bdc_status"] = result.get("statusCode")
                    await payment_operation.transfer_repository.save(saved_payment)
                except Exception as db_error:
                    logger.error(f"[TRANSFER-REQUEST] Error al actualizar transferencia en BD: {str(db_error)}")

                # Nota: No agregamos updatedBalance - la APP debe calcular el saldo
                # a partir del saldo previo y el monto transferido si lo necesita
                logger.info("[TRANSFER-REQUEST] Respuesta del banco sin modificaciones")

                _raise_if_bdc_business_error(
                    result,
                    "Error al crear transferencia en BDC",
                    context="[TRANSFER-REQUEST]",
                    user_id=user.id,
                )
                return BDCTransferSuccessResponse(**result)
            
    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        logger.error(f"[TRANSFER-REQUEST] Error HTTP en BDC: {e.response.status_code} - {error_detail}")
        
        # Intentar parsear el error de BDC
        try:
            error_data = e.response.json()
            detail = error_data.get("message", error_detail)
        except:
            detail = error_detail
        
        raise HTTPException(
            status_code=e.response.status_code,
            detail=detail,
        )
    except httpx.RequestError as e:
        logger.error(f"[TRANSFER-REQUEST] Error de conexión con BDC: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo conectar con el servicio BDC: {str(e)}",
        )
    except Exception as e:
        logger.error(f"[TRANSFER-REQUEST] Error inesperado: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar la transferencia: {str(e)}",
        )

@router.get(
    "/movements/transfer-request/{origin_id}",
    response_model=BDCTransferDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Endpoint de consulta de transferencia",
    tags=["BDC - Transferencias"],
)
async def get_transfer_status(
    origin_id: str,
    token: Optional[str] = Query(None, description="Token JWT si no se usa Authorization"),
    user_repository: UserRepository = Depends(get_user_repository),
):
    """
    Consulta el estado de una transferencia por su originId
    
    Este endpoint permite verificar:
    - El estado actual de la transferencia (PENDING, COMPLETED, FAILED)
    - Los detalles de la solicitud original
    - La respuesta detallada del banco (si está disponible)
    - Información de evaluación y códigos de respuesta
    
    Args:
        origin_id: ID único de la transferencia (originId) usado al crearla
        current_user: Usuario autenticado
    
    Returns:
        BDCTransferDetailResponse: Estado y detalles completos de la transferencia
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

        user = await user_repository.get_by_id(UUID(user_id_str))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        # Obtener token de autenticación con BDC
        auth_service = get_bdc_auth_service()
        bdc_token = await auth_service.get_token()
        
        # Construir URL del endpoint
        bdc_url = f"{settings.bdc_base_url}/movements/transfer-request/{origin_id}"
        logger.info(f"Consultando estado de transferencia {origin_id} para usuario {user.id}")
        
        # Preparar headers con autenticación
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {bdc_token}"
        }
        
        # Realizar la petición con SSL y certificados configurados
        async with create_bdc_client() as client:
            response = await client.get(
                bdc_url,
                headers=headers
            )
            
            # Si el token expiró, renovar e intentar de nuevo
            if response.status_code == 401:
                logger.warning(f"Token BDC expirado al consultar transferencia {origin_id}, renovando...")
                auth_service.invalidate_cache()
                bdc_token = await auth_service.get_token()
                headers["Authorization"] = f"Bearer {bdc_token}"
                response = await client.get(
                    bdc_url,
                    headers=headers
                )
            
            response.raise_for_status()
            
            result = response.json()
            
            # Log de la respuesta completa para debug
            logger.info(f"[GET-TRANSFER] Respuesta completa de BDC: {json.dumps(result, indent=2, ensure_ascii=False)}")

            _raise_if_bdc_business_error(
                result,
                "Error al consultar transferencia en BDC",
                context="[GET-TRANSFER]",
                user_id=user.id,
            )
            
            # Parsear la respuesta con el schema
            transfer_response = BDCTransferDetailResponse(**result)
            
            # Si BDC retorna error (statusCode != 0), registrar el mensaje
            if transfer_response.statusCode != 0:
                logger.warning(f"Transferencia {origin_id} no encontrada o con error: {transfer_response.message}")
                logger.info(f"Transferencia {origin_id} estado: ERROR (statusCode={transfer_response.statusCode})")
            else:
                # Intentar obtener el estado de diferentes lugares
                estado = "UNKNOWN"
                if transfer_response.data:
                    if transfer_response.data.estado:
                        estado = transfer_response.data.estado
                    elif transfer_response.data.response:
                        # La respuesta de BDC contiene información del objeto con estado
                        if transfer_response.data.response.objeto and transfer_response.data.response.objeto.estado:
                            objeto_estado = transfer_response.data.response.objeto.estado.codigo
                            if objeto_estado == "EN CURSO":
                                estado = "PENDING"
                            else:
                                estado = objeto_estado
                        # Si hay respuesta exitosa del banco (código 00), considerar completada
                        elif transfer_response.data.response.respuesta and transfer_response.data.response.respuesta.codigo == "00":
                            estado = "COMPLETED"
                    
                logger.info(f"Transferencia {origin_id} estado: {estado}")
            
            return transfer_response
            
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        logger.error(f"Error HTTP al consultar transferencia BDC: {e.response.status_code} - {error_detail}")
        
        # Si es 404, la transferencia no existe
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transferencia con originId '{origin_id}' no encontrada",
            )
        
        # Intentar parsear el error de BDC
        try:
            error_data = e.response.json()
            detail = error_data.get("message", error_detail)
        except:
            detail = error_detail
        
        raise HTTPException(
            status_code=e.response.status_code,
            detail=detail,
        )
    
    except httpx.RequestError as e:
        logger.error(f"Error de conexión al consultar transferencia BDC: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo conectar con el servicio BDC: {str(e)}",
        )
    
    except Exception as e:
        logger.error(f"Error inesperado al consultar transferencia BDC: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al consultar la transferencia: {str(e)}",
        )

@router.get(
    "/snp-concepts",
    response_model=BDCSnpConceptsResponse,
    status_code=status.HTTP_200_OK,
    summary="Endpoint de listado de conceptos SNP para transferencias",
    tags=["BDC - Transferencias"],
)
async def get_snp_concepts(
    token: str = Query(..., description="Token JWT requerido"),
    user_repository: UserRepository = Depends(get_user_repository),
):
    """
    Obtiene el listado de conceptos SNP válidos para realizar transferencias.
    
    Los conceptos SNP son códigos predefinidos que clasifican el motivo de la transferencia.
    
    Requiere token JWT para autenticación del usuario.
    
    Returns:
        BDCSnpConceptsResponse: Lista de conceptos disponibles
    """
    try:
        # Validar JWT y obtener usuario
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

        user = await user_repository.get_by_id(UUID(user_id_str))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        
        # Obtener token de autenticación con BDC
        auth_service = get_bdc_auth_service()
        bdc_token = await auth_service.get_token()
        
        bdc_url = f"{settings.bdc_base_url}/get-snp-concepts"
        logger.info(f"Consultando conceptos SNP para usuario {user.id}")
        
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bdc_token}"
        }
        
        async with create_bdc_client() as client:
            response = await client.get(
                bdc_url,
                headers=headers
            )
            
            # Si el token expiró, renovar e intentar de nuevo
            if response.status_code == 401:
                logger.warning("Token BDC rechazado (401), renovando...")
                auth_service.invalidate_cache()
                bdc_token = await auth_service.get_token()
                headers["Authorization"] = f"Bearer {bdc_token}"
                response = await client.get(
                    bdc_url,
                    headers=headers
                )
            
            response.raise_for_status()
            
            data = response.json()
            _raise_if_bdc_business_error(
                data,
                "Error al obtener conceptos SNP en BDC",
                context="[GET_SNP_CONCEPTS]",
                user_id=user.id,
            )
            logger.info(f"Conceptos SNP obtenidos exitosamente para usuario {user.id}")
            
            return BDCSnpConceptsResponse(**data)
            
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        logger.error(f"Error HTTP al obtener conceptos SNP: {e.response.status_code} - {error_detail}")
        
        try:
            error_data = e.response.json()
            detail = error_data.get("message", error_detail)
        except Exception:
            detail = error_detail
        
        raise HTTPException(
            status_code=e.response.status_code,
            detail=detail,
        )
    except httpx.RequestError as e:
        logger.error(f"Error de conexión al obtener conceptos SNP: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo conectar con el servicio BDC: {str(e)}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado al obtener conceptos SNP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener conceptos SNP: {str(e)}",
        )


@router.post(
    "/alias",
    response_model=BDCResponse,
    status_code=status.HTTP_200_OK,
    summary="Endpoint de consulta de alias",
    tags=["BDC - Alias"],
)
async def lookup_alias(
    request_data: BDCAliasLookupRequest,
    token: Optional[str] = Query(None, description="Token JWT si no se usa Authorization"),
    user_repository: UserRepository = Depends(get_user_repository),
):
    """
    Consulta un alias en BDC.

    Requiere token BDC y firma HMAC (X-SIGNATURE).
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
                detail="Token invalido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = await user_repository.get_by_id(UUID(user_id_str))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        
        auth_service = get_bdc_auth_service()
        bdc_token = await auth_service.get_token()

        bdc_url = f"{settings.bdc_base_url}/alias"
        payload = request_data.model_dump()
        signature = _calculate_bdc_signature("/alias", payload)

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bdc_token}",
            "X-SIGNATURE": signature,
        }

        async with create_bdc_client() as client:
            response = await client.post(
                bdc_url,
                headers=headers,
                json=payload,
            )

            if response.status_code == 401:
                logger.warning("Token BDC rechazado (401), renovando...")
                auth_service.invalidate_cache()
                bdc_token = await auth_service.get_token()
                headers["Authorization"] = f"Bearer {bdc_token}"
                response = await client.post(
                    bdc_url,
                    headers=headers,
                    json=payload,
                )

            response.raise_for_status()
            data = response.json()
            _raise_if_bdc_business_error(
                data,
                "Error al consultar alias en BDC",
                context="[ALIAS_LOOKUP]",
                user_id=user.id,
            )
            logger.info("Consulta de alias BDC exitosa")

            return BDCResponse(**data)

    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        logger.error(f"Error HTTP al consultar alias BDC: {e.response.status_code} - {error_detail}")

        try:
            error_data = e.response.json()
            detail = error_data.get("message", error_detail)
        except Exception:
            detail = error_detail

        raise HTTPException(
            status_code=e.response.status_code,
            detail=detail,
        )
    except httpx.RequestError as e:
        logger.error(f"Error de conexión al consultar alias BDC: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo conectar con el servicio BDC: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error inesperado al consultar alias BDC: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al consultar alias BDC: {str(e)}",
        )


@router.post(
    "/alias-create",
    response_model=BDCResponse,
    status_code=status.HTTP_200_OK,
    summary="Endpoint de creacion de alias",
    tags=["BDC - Alias"],
)
async def create_alias(
    request_data: BDCAliasCreateRequest,
    token: str = Query(..., description="Token JWT requerido"),
    user_repository: UserRepository = Depends(get_user_repository),
    bank_account_repository: BankAccountRepository = Depends(get_bank_account_repository),
):
    """
    Crea un alias en BDC.

    Requiere JWT para identificar usuario y firma HMAC (X-SIGNATURE).
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
                detail="Token invalido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = await user_repository.get_by_id(UUID(user_id_str))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        auth_service = get_bdc_auth_service()
        bdc_token = await auth_service.get_token()

        bdc_url = f"{settings.bdc_base_url}/alias-create"
        payload = request_data.model_dump()
        signature = _calculate_bdc_signature("/alias-create", payload)

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bdc_token}",
            "X-SIGNATURE": signature,
        }

        async with create_bdc_client() as client:
            response = await client.post(
                bdc_url,
                headers=headers,
                json=payload,
            )

            if response.status_code == 401:
                logger.warning("Token BDC rechazado (401), renovando...")
                auth_service.invalidate_cache()
                bdc_token = await auth_service.get_token()
                headers["Authorization"] = f"Bearer {bdc_token}"
                response = await client.post(
                    bdc_url,
                    headers=headers,
                    json=payload,
                )

            response.raise_for_status()
            data = response.json()
            _raise_if_bdc_business_error(
                data,
                "Error al crear alias en BDC",
                context="[ALIAS_CREATE]",
                user_id=user.id,
            )
            logger.info(f"Alias creado en BDC para usuario {user.id}")

            if data.get("statusCode") == 0:
                account = await bank_account_repository.get_by_cvu_cbu(request_data.cbuCuenta)
                if account:
                    await bank_account_repository.update(
                        account.id,
                        alias=request_data.valorAliasCVU,
                    )
                else:
                    logger.warning(
                        "No se encontro cuenta para actualizar alias: %s",
                        request_data.cbuCuenta,
                    )

            return BDCResponse(**data)

    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        logger.error(f"Error HTTP al crear alias BDC: {e.response.status_code} - {error_detail}")

        try:
            error_data = e.response.json()
            detail = error_data.get("message", error_detail)
        except Exception:
            detail = error_detail

        raise HTTPException(
            status_code=e.response.status_code,
            detail=detail,
        )
    except httpx.RequestError as e:
        logger.error(f"Error de conexion al crear alias BDC: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo conectar con el servicio BDC: {str(e)}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado al crear alias BDC: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear alias BDC: {str(e)}",
        )

@router.patch(
    "/alias-edit",
    response_model=BDCResponse,
    status_code=status.HTTP_200_OK,
    summary="Endpoint de edicion de alias",
    tags=["BDC - Alias"],
)
async def edit_alias(
    request_data: BDCAliasEditRequest,
    token: str = Query(..., description="Token JWT requerido"),
    user_repository: UserRepository = Depends(get_user_repository),
    bank_account_repository: BankAccountRepository = Depends(get_bank_account_repository),
):
    """
    Edita un alias en BDC.

    Requiere JWT para identificar usuario y firma HMAC (X-SIGNATURE).
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
                detail="Token invalido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = await user_repository.get_by_id(UUID(user_id_str))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        auth_service = get_bdc_auth_service()
        bdc_token = await auth_service.get_token()

        # Si llega payload del endpoint PATCH /sub-account/{cvu}, guiar al endpoint correcto.
        if request_data.accountLabel and not request_data.aliasNuevo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Payload inválido para /bdc/alias-edit. "
                    "Para actualizar accountLabel use PATCH /bdc/sub-account/{cvu} "
                    "con body {'accountLabel': '<alias>'}."
                ),
            )

        missing_fields = [
            field_name
            for field_name, field_value in {
                "cuitTitular": request_data.cuitTitular,
                "cbuCuenta": request_data.cbuCuenta,
                "aliasNuevo": request_data.aliasNuevo,
            }.items()
            if not field_value
        ]
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Campos requeridos para /bdc/alias-edit: "
                    + ", ".join(missing_fields)
                ),
            )

        alias_anterior = request_data.aliasAnterior
        if not alias_anterior:
            account = await bank_account_repository.get_by_cvu_cbu(request_data.cbuCuenta)
            if account and account.alias:
                alias_anterior = account.alias
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="aliasAnterior es requerido si la cuenta no tiene alias en base local",
                )

        bdc_url = f"{settings.bdc_base_url}/alias-edit"
        payload = {
            "cuitTitular": request_data.cuitTitular,
            "cbuCuenta": request_data.cbuCuenta,
            "aliasNuevo": request_data.aliasNuevo,
            "aliasAnterior": alias_anterior,
        }
        signature = _calculate_bdc_signature("/alias-edit", payload)

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bdc_token}",
            "X-SIGNATURE": signature,
        }

        async with create_bdc_client() as client:
            response = await client.post(
                bdc_url,
                headers=headers,
                json=payload,
            )

            if response.status_code == 401:
                logger.warning("Token BDC rechazado (401), renovando...")
                auth_service.invalidate_cache()
                bdc_token = await auth_service.get_token()
                headers["Authorization"] = f"Bearer {bdc_token}"
                response = await client.post(
                    bdc_url,
                    headers=headers,
                    json=payload,
                )

            response.raise_for_status()
            data = response.json()
            _raise_if_bdc_business_error(
                data,
                "Error al editar alias en BDC",
                context="[ALIAS_EDIT]",
                user_id=user.id,
            )
            logger.info(f"Alias editado en BDC para usuario {user.id}")

            if data.get("statusCode") == 0:
                account = await bank_account_repository.get_by_cvu_cbu(request_data.cbuCuenta)
                if account:
                    await bank_account_repository.update(
                        account.id,
                        alias=request_data.aliasNuevo,
                    )
                else:
                    logger.warning(
                        "No se encontro cuenta para actualizar alias: %s",
                        request_data.cbuCuenta,
                    )

            return BDCResponse(**data)

    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        logger.error(f"Error HTTP al editar alias BDC: {e.response.status_code} - {error_detail}")

        try:
            error_data = e.response.json()
            detail = error_data.get("message", error_detail)
        except Exception:
            detail = error_detail

        raise HTTPException(
            status_code=e.response.status_code,
            detail=detail,
        )
    except httpx.RequestError as e:
        logger.error(f"Error de conexion al editar alias BDC: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo conectar con el servicio BDC: {str(e)}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado al editar alias BDC: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al editar alias BDC: {str(e)}",
        )

@router.post(
    "/alias-remove",
    response_model=BDCResponse,
    status_code=status.HTTP_200_OK,
    summary="Endpoint de eliminacion de alias",
    tags=["BDC - Alias"],
)
async def remove_alias(
    request_data: BDCAliasRemoveRequest,
    token: str = Query(..., description="Token JWT requerido"),
    user_repository: UserRepository = Depends(get_user_repository),
    bank_account_repository: BankAccountRepository = Depends(get_bank_account_repository),
):
    """
    Elimina un alias en BDC.

    Requiere JWT para identificar usuario y firma HMAC (X-SIGNATURE).
    Si la operacion es exitosa, blanquea el alias en la base de datos local.
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
                detail="Token invalido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = await user_repository.get_by_id(UUID(user_id_str))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        auth_service = get_bdc_auth_service()
        bdc_token = await auth_service.get_token()

        bdc_url = f"{settings.bdc_base_url}/alias-remove"
        payload = request_data.model_dump()
        signature = _calculate_bdc_signature("/alias-remove", payload)

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bdc_token}",
            "X-SIGNATURE": signature,
        }

        async with create_bdc_client() as client:
            response = await client.post(
                bdc_url,
                headers=headers,
                json=payload,
            )

            if response.status_code == 401:
                logger.warning("Token BDC rechazado (401), renovando...")
                auth_service.invalidate_cache()
                bdc_token = await auth_service.get_token()
                headers["Authorization"] = f"Bearer {bdc_token}"
                response = await client.post(
                    bdc_url,
                    headers=headers,
                    json=payload,
                )

            response.raise_for_status()
            data = response.json()
            _raise_if_bdc_business_error(
                data,
                "Error al eliminar alias en BDC",
                context="[ALIAS_REMOVE]",
                user_id=user.id,
            )
            logger.info(f"Alias eliminado en BDC para usuario {user.id}")

            if data.get("statusCode") == 0:
                account = await bank_account_repository.get_by_cvu_cbu(request_data.cbuCuenta)
                if account:
                    await bank_account_repository.update(
                        account.id,
                        alias=None,
                    )
                    logger.info(f"Alias blanqueado en BD para cuenta {request_data.cbuCuenta}")
                else:
                    logger.warning(
                        "No se encontro cuenta para blanquear alias: %s",
                        request_data.cbuCuenta,
                    )

            return BDCResponse(**data)

    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        logger.error(f"Error HTTP al eliminar alias BDC: {e.response.status_code} - {error_detail}")

        try:
            error_data = e.response.json()
            detail = error_data.get("message", error_detail)
        except Exception:
            detail = error_detail

        raise HTTPException(
            status_code=e.response.status_code,
            detail=detail,
        )
    except httpx.RequestError as e:
        logger.error(f"Error de conexion al eliminar alias BDC: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo conectar con el servicio BDC: {str(e)}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado al eliminar alias BDC: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar alias BDC: {str(e)}",
        )
    

































@router.get(
    "/auth/status",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    tags=["BDC - Autenticacion"],
)
async def get_bdc_auth_status(
    current_user: User = Depends(get_current_user),
):
    """
    Obtiene el estado actual de autenticación con Banco de Comercio
    
    Información útil para debugging y monitoreo:
    - Si hay token en cache
    - Cuándo expira
    - Si está por expirar
    
    Requiere: Token JWT en header Authorization: Bearer <token>
    """
    auth_service = get_bdc_auth_service()
    cache_info = auth_service.get_cache_info()
    
    return {
        "status": "ok",
        "bdc_auth": cache_info,
        "user_id": str(current_user.id),
    }


@router.post(
    "/auth/refresh",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    tags=["BDC - Autenticacion"],
)
async def refresh_bdc_token(
    current_user: User = Depends(get_current_user),
):
    """
    Fuerza la renovación del token de autenticación con BDC
    
    Útil si quieres asegurar que el siguiente request use un token fresco.
    Normalmente el servicio renueva automáticamente si es necesario.
    
    Requiere: Token JWT en header Authorization: Bearer <token>
    """
    try:
        auth_service = get_bdc_auth_service()
        auth_service.invalidate_cache()
        
        # Obtener nuevo token
        new_token = await auth_service.get_token()
        
        logger.info(f"Token BDC renovado por usuario {current_user.id}")
        
        return {
            "status": "refreshed",
            "message": "Token de BDC renovado exitosamente",
            "cache_info": auth_service.get_cache_info(),
        }
    except Exception as e:
        logger.error(f"Error al renovar token BDC: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al renovar token BDC: {str(e)}",
        )












