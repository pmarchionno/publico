"""
Repositorio para operaciones con cuentas bancarias
"""
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BankAccountRecord, TransferRecord
from app.domain.models import BankAccount
from app.core.payments.types import PaymentState


class BankAccountRepository:
    """Repositorio para gestionar cuentas bancarias"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, account: BankAccount) -> BankAccount:
        """Crea una nueva cuenta bancaria"""
        create_payload = {
            "id": account.id,
            "user_id": account.user_id,
            "cvu_cbu": account.cvu_cbu,
            "account_type": account.account_type.value,
            "alias": account.alias,
            "status": account.status.value,
            "is_primary": account.is_primary,
            "bdc_account_id": account.bdc_account_id,
            "currency": account.currency,
            "balance": account.balance,
        }

        # Permitir origin_id explícito cuando venga preasignado
        if account.origin_id is not None:
            create_payload["origin_id"] = account.origin_id

        db_account = BankAccountRecord(
            **create_payload,
        )
        
        # Si es cuenta principal, desmarcar otras cuentas del usuario
        if account.is_primary:
            await self._unset_other_primary_accounts(account.user_id)
        
        self.session.add(db_account)
        await self.session.commit()
        await self.session.refresh(db_account)
        
        return BankAccount.model_validate(db_account)

    async def get_next_origin_id(self) -> int:
        """Obtiene un origin_id único para bank_accounts."""
        try:
            result = await self.session.execute(
                text("SELECT nextval('bank_accounts_origin_id_seq')")
            )
            next_origin_id = result.scalar_one()
            return int(next_origin_id)
        except Exception:
            # Fallback para entornos sin secuencia explícita
            result = await self.session.execute(
                select(func.max(BankAccountRecord.origin_id))
            )
            current_max = result.scalar() or 0
            return int(current_max) + 1
    
    async def get_by_id(self, account_id: UUID) -> Optional[BankAccount]:
        """Obtiene una cuenta por su ID"""
        result = await self.session.execute(
            select(BankAccountRecord).where(BankAccountRecord.id == account_id)
        )
        db_account = result.scalar_one_or_none()
        
        if db_account:
            return BankAccount.model_validate(db_account)
        return None
    
    async def get_by_cvu_cbu(self, cvu_cbu: str) -> Optional[BankAccount]:
        """Obtiene una cuenta por su CVU/CBU"""
        result = await self.session.execute(
            select(BankAccountRecord).where(BankAccountRecord.cvu_cbu == cvu_cbu)
        )
        db_account = result.scalar_one_or_none()
        
        if db_account:
            return BankAccount.model_validate(db_account)
        return None
    
    async def get_by_alias(self, alias: str) -> Optional[BankAccount]:
        """Obtiene una cuenta por su alias"""
        result = await self.session.execute(
            select(BankAccountRecord).where(BankAccountRecord.alias == alias)
        )
        db_account = result.scalar_one_or_none()
        
        if db_account:
            return BankAccount.model_validate(db_account)
        return None
    
    async def get_user_accounts(self, user_id: UUID) -> List[BankAccount]:
        """Obtiene todas las cuentas de un usuario"""
        result = await self.session.execute(
            select(BankAccountRecord)
            .where(BankAccountRecord.user_id == user_id)
            .order_by(BankAccountRecord.is_primary.desc(), BankAccountRecord.created_at)
        )
        db_accounts = result.scalars().all()
        
        return [BankAccount.model_validate(acc) for acc in db_accounts]
    
    async def get_primary_account(self, user_id: UUID) -> Optional[BankAccount]:
        """Obtiene la cuenta principal de un usuario"""
        result = await self.session.execute(
            select(BankAccountRecord)
            .where(
                BankAccountRecord.user_id == user_id,
                BankAccountRecord.is_primary == True
            )
        )
        db_account = result.scalar_one_or_none()
        
        if db_account:
            return BankAccount.model_validate(db_account)
        return None
    
    async def update(self, account_id: UUID, **kwargs) -> Optional[BankAccount]:
        """Actualiza una cuenta bancaria"""
        result = await self.session.execute(
            select(BankAccountRecord).where(BankAccountRecord.id == account_id)
        )
        db_account = result.scalar_one_or_none()
        
        if not db_account:
            return None
        
        # Si se marca como principal, desmarcar otras
        if kwargs.get('is_primary') is True:
            await self._unset_other_primary_accounts(db_account.user_id, exclude_id=account_id)
        
        for key, value in kwargs.items():
            if value is not None and hasattr(db_account, key):
                setattr(db_account, key, value)
        
        await self.session.commit()
        await self.session.refresh(db_account)
        
        return BankAccount.model_validate(db_account)
    
    async def delete(self, account_id: UUID) -> bool:
        """Elimina una cuenta bancaria"""
        result = await self.session.execute(
            select(BankAccountRecord).where(BankAccountRecord.id == account_id)
        )
        db_account = result.scalar_one_or_none()
        
        if not db_account:
            return False
        
        await self.session.delete(db_account)
        await self.session.commit()
        
        return True
    
    async def _unset_other_primary_accounts(self, user_id: UUID, exclude_id: Optional[UUID] = None):
        """Desmarca todas las cuentas principales de un usuario excepto una"""
        query = select(BankAccountRecord).where(
            BankAccountRecord.user_id == user_id,
            BankAccountRecord.is_primary == True
        )
        
        if exclude_id:
            query = query.where(BankAccountRecord.id != exclude_id)
        
        result = await self.session.execute(query)
        accounts = result.scalars().all()
        
        for account in accounts:
            account.is_primary = False
        
        await self.session.commit()

    async def calculate_balance(self, cvu_cbu: str) -> Decimal:
        """
        Calcula el saldo de una cuenta basándose en:
        1. El balance inicial almacenado en bank_accounts
        2. Las transferencias (dinero entrante menos dinero saliente)
        
        Fórmula: balance_inicial + dinero_entrante - dinero_saliente
        """
        # Obtener el balance inicial de la cuenta
        account = await self.get_by_cvu_cbu(cvu_cbu)
        initial_balance = account.balance or Decimal("0.00") if account else Decimal("0.00")
        
        # Dinero entrante (cuando la cuenta es destino)
        incoming = await self.session.execute(
            select(func.sum(TransferRecord.amount))
            .where(
                TransferRecord.destination_address == cvu_cbu
            )
        )
        incoming_amount = incoming.scalar() or Decimal("0.00")
        
        # Dinero saliente (cuando la cuenta es origen)
        outgoing = await self.session.execute(
            select(func.sum(TransferRecord.amount))
            .where(
                TransferRecord.source_address == cvu_cbu
            )
        )
        outgoing_amount = outgoing.scalar() or Decimal("0.00")
        
        # Saldo total = balance_inicial + transferencias_netas
        return initial_balance + incoming_amount - outgoing_amount
