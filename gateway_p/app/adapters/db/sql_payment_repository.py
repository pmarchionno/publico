from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PaymentRecord
from app.domain.models import Payment, PaymentStatus
from app.ports.repository import PaymentRepository


class SqlAlchemyPaymentRepository(PaymentRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, payment: Payment) -> Payment:
        record = PaymentRecord(
            id=payment.id,
            amount=Decimal(str(payment.amount)),
            currency=payment.currency,
            status=payment.status,
            description=None,
            extra_metadata={},
        )
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return self._to_domain(record)

    async def get_by_id(self, payment_id: UUID) -> Optional[Payment]:
        stmt = select(PaymentRecord).where(PaymentRecord.id == payment_id)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            return None
        return self._to_domain(record)

    async def update(self, payment: Payment) -> Payment:
        stmt = select(PaymentRecord).where(PaymentRecord.id == payment.id)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            raise ValueError("Payment not found in database")

        record.status = PaymentStatus(payment.status)
        record.amount = Decimal(str(payment.amount))
        record.currency = payment.currency
        record.updated_at = datetime.now(timezone.utc)

        await self.session.flush()
        await self.session.refresh(record)
        return self._to_domain(record)

    def _to_domain(self, record: PaymentRecord) -> Payment:
        return Payment(
            id=record.id,
            amount=float(record.amount),
            currency=record.currency,
            status=PaymentStatus(record.status),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

