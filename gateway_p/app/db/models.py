from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, Boolean, Index, text, BigInteger
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.payments.types import PaymentState
from app.db.base import Base
from app.domain.models import PaymentStatus


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PaymentRecord(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status"),
        default=PaymentStatus.PENDING,
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(String(255))
    extra_metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, name="extra_metadata", default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    transfer: Mapped[Optional["TransferRecord"]] = relationship(
        back_populates="payment",
        cascade="all, delete-orphan",
        uselist=False,
    )


class TransferRecord(Base):
    __tablename__ = "transfers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    payment_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    source_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bank_accounts.id", ondelete="SET NULL"),
        index=True,
    )
    destination_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bank_accounts.id", ondelete="SET NULL"),
        index=True,
    )
    origin_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        server_default=text("'0000000000'"),
        default="0000000000"
    )
    status: Mapped[PaymentState] = mapped_column(
        Enum(PaymentState, name="transfer_status"),
        default=PaymentState.CREATED,
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    concept: Mapped[Optional[str]] = mapped_column(String(32))
    description: Mapped[Optional[str]] = mapped_column(Text())
    connector_id: Mapped[Optional[str]] = mapped_column(String(64))
    source_address: Mapped[str] = mapped_column(String(64), nullable=False)
    source_address_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_owner_id_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_owner_id: Mapped[str] = mapped_column(String(32), nullable=False)
    source_owner_name: Mapped[Optional[str]] = mapped_column(String(128))
    destination_address: Mapped[str] = mapped_column(String(64), nullable=False)
    destination_address_type: Mapped[str] = mapped_column(String(32), nullable=False)
    destination_owner_id_type: Mapped[str] = mapped_column(String(16), nullable=False)
    destination_owner_id: Mapped[str] = mapped_column(String(32), nullable=False)
    destination_owner_name: Mapped[Optional[str]] = mapped_column(String(128))
    extra_metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, name="extra_metadata", default=dict)
    connector_response: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    payment: Mapped[PaymentRecord] = relationship(back_populates="transfer")
    source_account: Mapped[Optional["BankAccountRecord"]] = relationship(
        back_populates="outgoing_transfers",
        foreign_keys="TransferRecord.source_account_id",
    )
    destination_account: Mapped[Optional["BankAccountRecord"]] = relationship(
        back_populates="incoming_transfers",
        foreign_keys="TransferRecord.destination_account_id",
    )
    events: Mapped[list["TransferEventRecord"]] = relationship(
        back_populates="transfer",
        cascade="all, delete-orphan",
        order_by="TransferEventRecord.created_at",
    )


class TransferEventRecord(Base):
    __tablename__ = "transfer_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transfer_id: Mapped[int] = mapped_column(
        ForeignKey("transfers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[PaymentState] = mapped_column(
        Enum(PaymentState, name="transfer_event_status"),
        nullable=False,
    )
    message: Mapped[Optional[str]] = mapped_column(String(255))
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    transfer: Mapped[TransferRecord] = relationship(back_populates="events")


class WebhookEventRecord(Base):
    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="didit")
    webhook_type: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    vendor_data: Mapped[Optional[str]] = mapped_column(String(255))
    event_timestamp: Mapped[Optional[int]] = mapped_column(BigInteger)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )


class UserRecord(Base):
    """Modelo SQLAlchemy para usuarios"""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    first_name: Mapped[Optional[str]] = mapped_column(String(128))
    last_name: Mapped[Optional[str]] = mapped_column(String(128))
    dni: Mapped[Optional[str]] = mapped_column(String(32))
    gender: Mapped[Optional[str]] = mapped_column(String(16))
    cuit_cuil: Mapped[Optional[str]] = mapped_column(String(32))
    phone: Mapped[Optional[str]] = mapped_column(String(32))
    nationality: Mapped[Optional[str]] = mapped_column(String(64))
    occupation: Mapped[Optional[str]] = mapped_column(String(64))
    marital_status: Mapped[Optional[str]] = mapped_column(String(32))
    location: Mapped[Optional[str]] = mapped_column(String(255))
    password: Mapped[Optional[str]] = mapped_column(String(255))
    registration_token: Mapped[Optional[str]] = mapped_column(String(512))
    registration_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_kyc_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    __table_args__ = (
        Index("idx_user_email", "email"),
        Index("idx_user_is_active", "is_active"),
        Index("idx_user_is_kyc_verified", "is_kyc_verified"),
    )

    # Relacion con aceptaciones legales
    legal_acceptances: Mapped[list["UserLegalAcceptanceRecord"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    
    # Relacion con cuentas bancarias
    bank_accounts: Mapped[list["BankAccountRecord"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class BankAccountRecord(Base):
    """Modelo para cuentas bancarias de usuarios"""
    __tablename__ = "bank_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    origin_id: Mapped[int] = mapped_column(
        autoincrement=True,
        unique=True,
        nullable=False,
        server_default=text("nextval('bank_accounts_origin_id_seq')"),
        comment="ID numérico autoincremental para integración con BDC"
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    cvu_cbu: Mapped[str] = mapped_column(
        String(22),
        unique=True,
        index=True,
        nullable=False,
        comment="CVU o CBU de 22 dígitos"
    )
    account_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Tipo de cuenta: CBU, CVU"
    )
    alias: Mapped[Optional[str]] = mapped_column(
        String(64),
        comment="Alias de la cuenta (ej: alias.ejemplo.cuenta)"
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="active",
        comment="Estado: active, suspended, closed"
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Indica si es la cuenta principal del usuario"
    )
    bdc_account_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        comment="ID de la cuenta en el sistema BDC"
    )
    currency: Mapped[str] = mapped_column(
        String(8),
        default="ARS",
        nullable=False,
        comment="Moneda de la cuenta: ARS, USD"
    )
    balance: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 2),
        comment="Saldo actual (si se sincroniza)"
    )
    extra_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        comment="Metadatos adicionales"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    __table_args__ = (
        Index("idx_bank_account_user", "user_id"),
        Index("idx_bank_account_status", "status"),
        Index("idx_bank_account_user_primary", "user_id", "is_primary"),
    )

    # Relación con usuario
    user: Mapped[UserRecord] = relationship(back_populates="bank_accounts")
    outgoing_transfers: Mapped[list[TransferRecord]] = relationship(
        back_populates="source_account",
        foreign_keys="TransferRecord.source_account_id",
    )
    incoming_transfers: Mapped[list[TransferRecord]] = relationship(
        back_populates="destination_account",
        foreign_keys="TransferRecord.destination_account_id",
    )


class LegalDocumentRecord(Base):
    """Modelo para documentos legales (términos, políticas, etc.)"""
    __tablename__ = "legal_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Tipo: terms_and_conditions, privacy_policy, etc."
    )
    version: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Versión del documento (ej: 1.0, 2.1)"
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text(), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    effective_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Fecha desde la cual es efectivo"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    __table_args__ = (
        Index("idx_legal_doc_type_active", "document_type", "is_active"),
        Index("idx_legal_doc_type_version", "document_type", "version", unique=True),
    )

    # Relacion con aceptaciones
    acceptances: Mapped[list["UserLegalAcceptanceRecord"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class UserLegalAcceptanceRecord(Base):
    """Modelo para rastrear aceptaciones de documentos legales por usuarios"""
    __tablename__ = "user_legal_acceptances"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("legal_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
        comment="Fecha y hora de aceptación"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        comment="IP desde donde se aceptó (IPv4 o IPv6)"
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(512),
        comment="User agent del navegador/app"
    )

    __table_args__ = (
        Index("idx_user_acceptance_user", "user_id"),
        Index("idx_user_acceptance_document", "document_id"),
        Index("idx_user_acceptance_user_doc", "user_id", "document_id"),
    )

    # Relaciones
    user: Mapped[UserRecord] = relationship(back_populates="legal_acceptances")
    document: Mapped[LegalDocumentRecord] = relationship(back_populates="acceptances")
