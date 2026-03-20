"""
Repositorio para gestión de documentos legales y aceptaciones
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import Session, selectinload

from app.db.models import LegalDocumentRecord, UserLegalAcceptanceRecord


class LegalDocumentRepository:
    """Repositorio para documentos legales y aceptaciones"""

    def __init__(self, session: Session):
        self.session = session

    # ========== Documentos Legales ==========
    
    def get_active_document_by_type(
        self, document_type: str
    ) -> Optional[LegalDocumentRecord]:
        """Obtiene el documento activo de un tipo específico"""
        stmt = (
            select(LegalDocumentRecord)
            .where(
                and_(
                    LegalDocumentRecord.document_type == document_type,
                    LegalDocumentRecord.is_active == True,
                )
            )
            .order_by(desc(LegalDocumentRecord.effective_date))
            .limit(1)
        )
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()

    def get_document_by_id(self, document_id: UUID) -> Optional[LegalDocumentRecord]:
        """Obtiene un documento por ID"""
        stmt = select(LegalDocumentRecord).where(
            LegalDocumentRecord.id == document_id
        )
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()

    def get_all_active_documents(self) -> List[LegalDocumentRecord]:
        """Obtiene todos los documentos activos"""
        stmt = (
            select(LegalDocumentRecord)
            .where(LegalDocumentRecord.is_active == True)
            .order_by(
                LegalDocumentRecord.document_type,
                desc(LegalDocumentRecord.effective_date),
            )
        )
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    def create_document(
        self,
        document_type: str,
        version: str,
        title: str,
        content: str,
        effective_date: datetime,
    ) -> LegalDocumentRecord:
        """Crea un nuevo documento legal"""
        document = LegalDocumentRecord(
            document_type=document_type,
            version=version,
            title=title,
            content=content,
            effective_date=effective_date,
            is_active=True,
        )
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document

    def update_document(
        self, document_id: UUID, **kwargs
    ) -> Optional[LegalDocumentRecord]:
        """Actualiza un documento legal"""
        document = self.get_document_by_id(document_id)
        if not document:
            return None

        for key, value in kwargs.items():
            if value is not None and hasattr(document, key):
                setattr(document, key, value)

        self.session.commit()
        self.session.refresh(document)
        return document

    def deactivate_old_versions(self, document_type: str, except_id: UUID) -> int:
        """Desactiva versiones antiguas de un tipo de documento, excepto la especificada"""
        stmt = (
            select(LegalDocumentRecord)
            .where(
                and_(
                    LegalDocumentRecord.document_type == document_type,
                    LegalDocumentRecord.id != except_id,
                    LegalDocumentRecord.is_active == True,
                )
            )
        )
        result = self.session.execute(stmt)
        documents = result.scalars().all()
        
        count = 0
        for doc in documents:
            doc.is_active = False
            count += 1
        
        self.session.commit()
        return count

    # ========== Aceptaciones de Usuario ==========

    def get_user_acceptance(
        self, user_id: UUID, document_id: UUID
    ) -> Optional[UserLegalAcceptanceRecord]:
        """Obtiene una aceptación específica de un usuario"""
        stmt = (
            select(UserLegalAcceptanceRecord)
            .options(selectinload(UserLegalAcceptanceRecord.document))
            .where(
                and_(
                    UserLegalAcceptanceRecord.user_id == user_id,
                    UserLegalAcceptanceRecord.document_id == document_id,
                )
            )
        )
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()

    def get_user_latest_acceptance_by_type(
        self, user_id: UUID, document_type: str
    ) -> Optional[UserLegalAcceptanceRecord]:
        """Obtiene la última aceptación de un usuario para un tipo de documento"""
        stmt = (
            select(UserLegalAcceptanceRecord)
            .join(UserLegalAcceptanceRecord.document)
            .where(
                and_(
                    UserLegalAcceptanceRecord.user_id == user_id,
                    LegalDocumentRecord.document_type == document_type,
                )
            )
            .order_by(desc(UserLegalAcceptanceRecord.accepted_at))
            .limit(1)
            .options(selectinload(UserLegalAcceptanceRecord.document))
        )
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()

    def get_all_user_acceptances(
        self, user_id: UUID
    ) -> List[UserLegalAcceptanceRecord]:
        """Obtiene todas las aceptaciones de un usuario"""
        stmt = (
            select(UserLegalAcceptanceRecord)
            .where(UserLegalAcceptanceRecord.user_id == user_id)
            .order_by(desc(UserLegalAcceptanceRecord.accepted_at))
            .options(selectinload(UserLegalAcceptanceRecord.document))
        )
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    def create_acceptance(
        self,
        user_id: UUID,
        document_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> UserLegalAcceptanceRecord:
        """Crea una nueva aceptación de documento legal"""
        acceptance = UserLegalAcceptanceRecord(
            user_id=user_id,
            document_id=document_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(acceptance)
        self.session.commit()
        self.session.refresh(acceptance)
        
        # Cargar la relación del documento
        stmt = (
            select(UserLegalAcceptanceRecord)
            .where(UserLegalAcceptanceRecord.id == acceptance.id)
            .options(selectinload(UserLegalAcceptanceRecord.document))
        )
        result = self.session.execute(stmt)
        return result.scalar_one()

    def has_accepted_document(self, user_id: UUID, document_id: UUID) -> bool:
        """Verifica si un usuario ya aceptó un documento específico"""
        return self.get_user_acceptance(user_id, document_id) is not None

    def has_accepted_latest_version(
        self, user_id: UUID, document_type: str
    ) -> bool:
        """Verifica si el usuario aceptó la última versión activa de un tipo de documento"""
        # Obtener documento activo
        active_doc = self.get_active_document_by_type(document_type)
        if not active_doc:
            return True  # Si no hay documento activo, se considera aceptado
        
        # Verificar si el usuario lo aceptó
        return self.has_accepted_document(user_id, active_doc.id)
