import logging
from uuid import UUID
from typing import List
from decimal import Decimal

from app.domain.models import BankAccount
from app.ports.bank_account_repository import BankAccountRepository
from app.auth.schemas import BankAccountWithBalanceResponse

logger = logging.getLogger(__name__)


class BankAccountService:
    """Servicio para gestionar cuentas bancarias"""

    def __init__(self, bank_account_repository: BankAccountRepository):
        logger.info("Inicializando BankAccountService con BankAccountRepository: %s", type(bank_account_repository).__name__)
        self.repository = bank_account_repository

    async def get_user_accounts_with_balance(self, user_id: UUID) -> List[BankAccountWithBalanceResponse]:
        """
        Obtiene todas las cuentas del usuario con sus saldos calculados
        
        Retorna una lista de BankAccountWithBalanceResponse con estructura:
        {
            "id": UUID,
            "cvu_cbu": str,
            "alias": str,
            "account_type": str,
            "balance": Decimal,
            "currency": str,
            "status": str,
            "is_primary": bool
        }
        """
        accounts = await self.repository.get_user_accounts(user_id)
        
        accounts_with_balance = []
        for account in accounts:
            balance = await self.repository.calculate_balance(account.cvu_cbu)
            
            account_response = BankAccountWithBalanceResponse(
                id=str(account.id),
                cvu_cbu=account.cvu_cbu,
                alias=account.alias,
                account_type=account.account_type,
                balance=float(balance),
                currency=account.currency,
                status=account.status,
                is_primary=account.is_primary,
                created_at=account.created_at.isoformat() if account.created_at else None,
            )
            accounts_with_balance.append(account_response)
        
        return accounts_with_balance

    async def get_primary_account_with_balance(self, user_id: UUID) -> BankAccountWithBalanceResponse | None:
        """
        Obtiene la cuenta principal del usuario con su saldo
        """
        account = await self.repository.get_primary_account(user_id)
        
        if not account:
            return None
        
        balance = await self.repository.calculate_balance(account.cvu_cbu)
        
        return BankAccountWithBalanceResponse(
            id=str(account.id),
            cvu_cbu=account.cvu_cbu,
            alias=account.alias,
            account_type=account.account_type,
            balance=float(balance),
            currency=account.currency,
            status=account.status,
            is_primary=account.is_primary,
            created_at=account.created_at.isoformat() if account.created_at else None,
        )
