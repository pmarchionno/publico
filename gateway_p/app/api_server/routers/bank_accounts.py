"""
Router para endpoints de cuentas bancarias
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Header, Query
from uuid import UUID

from app.adapters.api.dependencies import get_current_user, get_session, get_user_repository
from app.domain.models import User, BankAccount, AccountStatus, AccountType
from app.ports.user_repository import UserRepository
from app.auth.security import verify_access_token
from app.auth.bank_account_schemas import (
    BankAccountCreate,
    BankAccountUpdate,
    BankAccountResponse,
    BankAccountListResponse,
    BankAccountBalanceRequest,
    BankAccountBalanceResponse,
    BankAccountBalanceListResponse
)
from app.ports.bank_account_repository import BankAccountRepository
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bank-accounts", tags=["bank-accounts"])


async def get_account_repository(
    session: AsyncSession = Depends(get_session)
) -> BankAccountRepository:
    """Dependency para obtener el repositorio de cuentas"""
    return BankAccountRepository(session)


@router.post(
    "",
    response_model=BankAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_bank_account(
    account_data: BankAccountCreate,
    token: Optional[str] = Query(None, description="Token JWT si no se usa Authorization"),
    repo: BankAccountRepository = Depends(get_account_repository),
    user_repository: UserRepository = Depends(get_user_repository),
):
    """
    Crea una nueva cuenta bancaria para el usuario autenticado
    
    - **cvu_cbu**: CVU o CBU de 22 dígitos
    - **account_type**: Tipo de cuenta (CBU o CVU)
    - **alias**: Alias opcional para la cuenta
    - **is_primary**: Marcar como cuenta principal (desmarca otras)
    - **currency**: Moneda de la cuenta (ARS, USD)
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

        # Verificar si el CVU/CBU ya existe
        existing = await repo.get_by_cvu_cbu(account_data.cvu_cbu)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una cuenta con el CVU/CBU {account_data.cvu_cbu}"
            )
        
        # Crear el modelo de dominio
        account = BankAccount(
            user_id=user.id,
            cvu_cbu=account_data.cvu_cbu,
            account_type=AccountType(account_data.account_type),
            alias=account_data.alias,
            is_primary=account_data.is_primary,
            bdc_account_id=account_data.bdc_account_id,
            currency=account_data.currency,
            status=AccountStatus.ACTIVE,
            balance=1000000000.00,  # Saldo inicial (puede ser actualizado luego)
        )
        
        # Guardar en la base de datos
        created_account = await repo.create(account)
        
        logger.info(f"Cuenta bancaria creada: {created_account.id} para usuario {user.id}")
        
        return BankAccountResponse.model_validate(created_account)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error al crear cuenta bancaria: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear la cuenta bancaria"
        )


@router.get(
    "",
    response_model=BankAccountListResponse,
)
async def list_user_accounts(
    current_user: User = Depends(get_current_user),
    repo: BankAccountRepository = Depends(get_account_repository),
):
    """
    Lista todas las cuentas bancarias del usuario autenticado
    
    Retorna las cuentas ordenadas por:
    1. Cuenta principal primero
    2. Fecha de creación
    """
    try:
        accounts = await repo.get_user_accounts(current_user.id)
        
        return BankAccountListResponse(
            accounts=[BankAccountResponse.model_validate(acc) for acc in accounts],
            total=len(accounts)
        )
        
    except Exception as e:
        logger.error(f"Error al listar cuentas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener las cuentas"
        )


@router.post(
    "/balance",
    response_model=BankAccountBalanceListResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtiene el saldo de cuenta(s) del usuario",
)
async def get_account_balance(
    request_data: BankAccountBalanceRequest,
    token: Optional[str] = Query(None, description="Token JWT si no se usa Authorization"),
    repo: BankAccountRepository = Depends(get_account_repository),
    user_repository: UserRepository = Depends(get_user_repository),
):
    """
    Retorna el saldo de una o todas las cuentas del usuario autenticado.

    - Si se envía **cvu_cbu**: retorna solo esa cuenta
    - Si NO se envía **cvu_cbu**: retorna todas las cuentas del usuario
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

        balances = []

        # Si se especifica un CVU/CBU, retornar solo esa cuenta
        if request_data.cvu_cbu:
            account = await repo.get_by_cvu_cbu(request_data.cvu_cbu)

            if not account:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Cuenta no encontrada",
                )

            if account.status != AccountStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Cuenta no encontrada",
                )

            if account.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para acceder a esta cuenta",
                )

            balance = await repo.calculate_balance(account.cvu_cbu)
            balances.append(
                BankAccountBalanceResponse(
                    account_id=account.id,
                    cvu_cbu=account.cvu_cbu,
                    alias=account.alias,
                    balance=float(balance),
                    currency=account.currency,
                )
            )
        else:
            # Si no se especifica CVU/CBU, retornar todas las cuentas del usuario
            accounts = await repo.get_user_accounts(user.id)

            for account in accounts:
                if account.status != AccountStatus.ACTIVE:
                    continue
                balance = await repo.calculate_balance(account.cvu_cbu)
                balances.append(
                    BankAccountBalanceResponse(
                        account_id=account.id,
                        cvu_cbu=account.cvu_cbu,
                        alias=account.alias,
                        balance=float(balance),
                        currency=account.currency,
                    )
                )

        return BankAccountBalanceListResponse(
            accounts=balances,
            total=len(balances)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener saldo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener el saldo",
        )


@router.get(
    "/{account_id}",
    response_model=BankAccountResponse,
)
async def get_bank_account(
    account_id: UUID,
    current_user: User = Depends(get_current_user),
    repo: BankAccountRepository = Depends(get_account_repository),
):
    """
    Obtiene los detalles de una cuenta bancaria específica
    
    Solo se pueden consultar las cuentas propias del usuario autenticado.
    """
    try:
        account = await repo.get_by_id(account_id)
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cuenta {account_id} no encontrada"
            )
        
        # Verificar que la cuenta pertenezca al usuario
        if account.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para acceder a esta cuenta"
            )
        
        return BankAccountResponse.model_validate(account)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener cuenta: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener la cuenta"
        )


@router.patch(
    "/{account_id}",
    response_model=BankAccountResponse,
)
async def update_bank_account(
    account_id: UUID,
    account_data: BankAccountUpdate,
    current_user: User = Depends(get_current_user),
    repo: BankAccountRepository = Depends(get_account_repository),
):
    """
    Actualiza una cuenta bancaria
    
    Permite actualizar:
    - **alias**: Nuevo alias
    - **status**: Estado (active, suspended, closed)
    - **is_primary**: Marcar/desmarcar como principal
    - **balance**: Actualizar saldo
    """
    try:
        # Verificar que la cuenta existe y pertenece al usuario
        account = await repo.get_by_id(account_id)
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cuenta {account_id} no encontrada"
            )
        
        if account.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para modificar esta cuenta"
            )
        
        # Actualizar solo los campos proporcionados
        update_data = account_data.model_dump(exclude_unset=True)
        updated_account = await repo.update(account_id, **update_data)
        
        logger.info(f"Cuenta {account_id} actualizada por usuario {current_user.id}")
        
        return BankAccountResponse.model_validate(updated_account)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al actualizar cuenta: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar la cuenta"
        )


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_bank_account(
    account_id: UUID,
    current_user: User = Depends(get_current_user),
    repo: BankAccountRepository = Depends(get_account_repository),
):
    """
    Elimina una cuenta bancaria
    
    Solo se pueden eliminar las cuentas propias del usuario autenticado.
    """
    try:
        # Verificar que la cuenta existe y pertenece al usuario
        account = await repo.get_by_id(account_id)
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cuenta {account_id} no encontrada"
            )
        
        if account.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para eliminar esta cuenta"
            )
        
        await repo.delete(account_id)
        
        logger.info(f"Cuenta {account_id} eliminada por usuario {current_user.id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar cuenta: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar la cuenta"
        )


@router.get(
    "/primary/me",
    response_model=BankAccountResponse,
)
async def get_primary_account(
    current_user: User = Depends(get_current_user),
    repo: BankAccountRepository = Depends(get_account_repository),
):
    """
    Obtiene la cuenta principal del usuario autenticado
    
    Retorna la cuenta marcada como principal o HTTP 404 si no tiene ninguna.
    """
    try:
        account = await repo.get_primary_account(current_user.id)
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No tienes una cuenta principal configurada"
            )
        
        return BankAccountResponse.model_validate(account)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener cuenta principal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener la cuenta principal"
        )
