from typing import Optional, AsyncGenerator
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging

from app.adapters.db.memory_transfer_repository import InMemoryTransferRepository
from app.adapters.db.sql_user_repository import SQLUserRepository
from app.core.connectors.banco_comercio import BancoComercioConnector
from app.core.connectors.interface import ConnectorIntegration
from app.core.connectors.mock_banco_comercio import MockBancoComercioConnector
from app.core.payments.operation import PaymentOperation
from app.services.payment_service import PaymentService
from app.services.user_service import UserService
from app.services.email_service import EmailService
from app.services.legal_service import LegalDocumentService
from app.services.bank_account_service import BankAccountService
from app.ports.user_repository import UserRepository
from app.ports.legal_repository import LegalDocumentRepository
from app.ports.bank_account_repository import BankAccountRepository
from app.db.session import get_db_session
from app.domain.models import User
from config.settings import settings
from app.auth.security import verify_access_token

# Stub for dependency injection. 
# This will be overridden in main.py but serves as the dependency token.
async def get_payment_service() -> PaymentService:
    raise NotImplementedError("Dependency not explicitly overridden")


# Alias para consistencia con otros servicios
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Obtiene sesión de BD async"""
    async for session in get_db_session():
        yield session


def get_email_service() -> EmailService:
    """Retorna instancia del servicio de email"""
    return EmailService()


async def get_user_repository(session: AsyncSession = Depends(get_session)) -> UserRepository:
    """Inyecta el repositorio de usuarios"""
    return SQLUserRepository(session)


async def get_user_service(
    repository: UserRepository = Depends(get_user_repository),
    email_service: EmailService = Depends(get_email_service),
) -> UserService:
    """Inyecta el servicio de usuarios"""
    return UserService(repository, email_service)


async def get_legal_repository(session: AsyncSession = Depends(get_session)) -> LegalDocumentRepository:
    """Inyecta el repositorio de documentos legales"""
    return LegalDocumentRepository(session)


async def get_legal_service(
    repository: LegalDocumentRepository = Depends(get_legal_repository),
) -> LegalDocumentService:
    """Inyecta el servicio de documentos legales"""
    return LegalDocumentService(repository)


async def get_bank_account_repository(session: AsyncSession = Depends(get_session)) -> BankAccountRepository:
    """Inyecta el repositorio de cuentas bancarias"""
    return BankAccountRepository(session)


async def get_bank_account_service(
    repository: BankAccountRepository = Depends(get_bank_account_repository),
) -> BankAccountService:
    """Inyecta el servicio de cuentas bancarias"""
    return BankAccountService(repository)


_transfer_repository = InMemoryTransferRepository()


def get_payment_operation() -> PaymentOperation:
    return PaymentOperation(transfer_repository=_transfer_repository)

_connector_instance: Optional[ConnectorIntegration] = None


def _build_connector() -> ConnectorIntegration:
    mode = settings.transfer_connector_mode.lower()
    if mode == "mock":
        return MockBancoComercioConnector()
    if mode in {"banco_comercio", "live", "prod"}:
        return BancoComercioConnector()
    raise ValueError(f"Unsupported transfer connector mode: {settings.transfer_connector_mode}")


def get_transfer_connector() -> ConnectorIntegration:
    global _connector_instance
    if _connector_instance is None:
        _connector_instance = _build_connector()
    return _connector_instance


def get_banco_comercio_connector() -> ConnectorIntegration:
    return get_transfer_connector()


async def get_current_user(
    request: Request,
    repository: UserRepository = Depends(get_user_repository),
) -> User:
    """Obtiene el usuario actual desde el token JWT en header Authorization"""
    logger = logging.getLogger(__name__)
    
    # Extraer el header Authorization directamente desde request.headers
    authorization = request.headers.get("Authorization")
    logger.info(f"Authorization header recibido: {authorization}")
    logger.info(f"Todos los headers: {dict(request.headers)}")
    
    bearer_token = None
    if authorization:
        parts = authorization.split()
        logger.info(f"Parts del header: {parts}")
        if len(parts) == 2 and parts[0].lower() == "bearer":
            bearer_token = parts[1]
            logger.info(f"Token extraído: {bearer_token[:20]}...")
    else:
        logger.warning("El header Authorization es None o vacío")

    if not bearer_token:
        logger.warning("No se encontró bearer token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar el token
    user_id_str = verify_access_token(bearer_token)
    logger.info(f"User ID del token: {user_id_str}")
    
    if not user_id_str:
        logger.error("Token inválido o expirado")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Obtener al usuario desde la BD
    try:
        user_id = UUID(user_id_str)
        user = await repository.get_by_id(user_id)
        if not user:
            logger.error(f"Usuario no encontrado: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no encontrado",
            )
        logger.info(f"Usuario autenticado: {user.email}")
        return user
    except (ValueError, Exception) as e:
        logger.error(f"Error al procesar token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )
