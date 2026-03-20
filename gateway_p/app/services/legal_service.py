"""
Servicio para gestión de documentos legales y aceptaciones
"""
import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from app.ports.legal_repository import LegalDocumentRepository
from app.db.models import LegalDocumentRecord, UserLegalAcceptanceRecord

logger = logging.getLogger(__name__)


class LegalDocumentService:
    """Servicio para gestión de documentos legales"""

    def __init__(self, repository: LegalDocumentRepository):
        self.repository = repository

    # ========== Obtener Documentos ==========

    def get_current_terms_and_conditions(self) -> Optional[LegalDocumentRecord]:
        """Obtiene los términos y condiciones actuales"""
        return self.repository.get_active_document_by_type("terms_and_conditions")

    def get_current_privacy_policy(self) -> Optional[LegalDocumentRecord]:
        """Obtiene la política de privacidad actual"""
        return self.repository.get_active_document_by_type("privacy_policy")

    def get_document_by_id(self, document_id: UUID) -> Optional[LegalDocumentRecord]:
        """Obtiene un documento por su ID"""
        return self.repository.get_document_by_id(document_id)

    def get_all_active_documents(self) -> List[LegalDocumentRecord]:
        """Obtiene todos los documentos activos"""
        return self.repository.get_all_active_documents()

    # ========== Aceptaciones de Usuario ==========

    async def accept_document(
        self,
        user_id: UUID,
        document_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> UserLegalAcceptanceRecord:
        """
        Registra la aceptación de un documento legal por parte de un usuario
        
        Raises:
            ValueError: Si el documento no existe o no está activo
        """
        # Verificar que el documento existe y está activo
        document = self.repository.get_document_by_id(document_id)
        if not document:
            raise ValueError("El documento no existe")
        
        if not document.is_active:
            raise ValueError("El documento no está activo")
        
        # Verificar si ya fue aceptado
        existing = self.repository.get_user_acceptance(user_id, document_id)
        if existing:
            logger.info(
                f"Usuario {user_id} ya había aceptado el documento {document_id}"
            )
            return existing
        
        # Crear la aceptación
        acceptance = self.repository.create_acceptance(
            user_id=user_id,
            document_id=document_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        logger.info(
            f"Usuario {user_id} aceptó documento {document_id} "
            f"({document.document_type} v{document.version})"
        )
        
        return acceptance

    def get_user_legal_status(self, user_id: UUID) -> Dict[str, Any]:
        """
        Obtiene el estado completo de aceptaciones legales de un usuario
        
        Retorna información sobre si el usuario ha aceptado las últimas versiones
        de términos y condiciones y política de privacidad.
        """
        # Obtener documentos actuales
        current_terms = self.get_current_terms_and_conditions()
        current_privacy = self.get_current_privacy_policy()
        
        # Obtener últimas aceptaciones del usuario
        terms_acceptance = self.repository.get_user_latest_acceptance_by_type(
            user_id, "terms_and_conditions"
        )
        privacy_acceptance = self.repository.get_user_latest_acceptance_by_type(
            user_id, "privacy_policy"
        )
        
        # Verificar si el usuario aceptó las versiones actuales
        terms_accepted = False
        terms_version = None
        terms_accepted_at = None
        
        if terms_acceptance and current_terms:
            terms_accepted = terms_acceptance.document_id == current_terms.id
            terms_version = terms_acceptance.document.version
            terms_accepted_at = terms_acceptance.accepted_at
        
        privacy_accepted = False
        privacy_version = None
        privacy_accepted_at = None
        
        if privacy_acceptance and current_privacy:
            privacy_accepted = privacy_acceptance.document_id == current_privacy.id
            privacy_version = privacy_acceptance.document.version
            privacy_accepted_at = privacy_acceptance.accepted_at
        
        # Determinar si necesita actualizar
        needs_update = (
            (current_terms and not terms_accepted) or
            (current_privacy and not privacy_accepted)
        )
        
        return {
            "terms_accepted": terms_accepted,
            "terms_version": terms_version,
            "terms_accepted_at": terms_accepted_at,
            "privacy_accepted": privacy_accepted,
            "privacy_version": privacy_version,
            "privacy_accepted_at": privacy_accepted_at,
            "current_terms_version": current_terms.version if current_terms else None,
            "current_privacy_version": current_privacy.version if current_privacy else None,
            "needs_update": needs_update,
        }

    def get_user_acceptances(
        self, user_id: UUID
    ) -> List[UserLegalAcceptanceRecord]:
        """Obtiene todas las aceptaciones de un usuario"""
        return self.repository.get_all_user_acceptances(user_id)

    def has_accepted_all_required_documents(self, user_id: UUID) -> bool:
        """
        Verifica si el usuario ha aceptado todos los documentos legales requeridos
        
        Útil para validar si un usuario puede completar ciertas acciones
        """
        status = self.get_user_legal_status(user_id)
        
        # Ambos deben estar aceptados y no necesitar actualización
        return (
            status["terms_accepted"] and
            status["privacy_accepted"] and
            not status["needs_update"]
        )

    # ========== Administración de Documentos (Admin) ==========

    async def create_document(
        self,
        document_type: str,
        version: str,
        title: str,
        content: str,
        effective_date: datetime,
        deactivate_old: bool = True,
    ) -> LegalDocumentRecord:
        """
        Crea un nuevo documento legal
        
        Args:
            document_type: Tipo de documento (terms_and_conditions, privacy_policy)
            version: Versión del documento
            title: Título
            content: Contenido del documento
            effective_date: Fecha desde la cual es efectivo
            deactivate_old: Si debe desactivar versiones antiguas del mismo tipo
        
        Returns:
            El documento creado
        """
        document = self.repository.create_document(
            document_type=document_type,
            version=version,
            title=title,
            content=content,
            effective_date=effective_date,
        )
        
        # Desactivar versiones antiguas si se solicita
        if deactivate_old:
            count = self.repository.deactivate_old_versions(document_type, document.id)
            if count > 0:
                logger.info(
                    f"Desactivadas {count} versiones antiguas de {document_type}"
                )
        
        logger.info(
            f"Creado documento legal: {document_type} v{version} (ID: {document.id})"
        )
        
        return document

    async def update_document(
        self, document_id: UUID, **kwargs
    ) -> Optional[LegalDocumentRecord]:
        """Actualiza un documento legal existente"""
        document = self.repository.update_document(document_id, **kwargs)
        
        if document:
            logger.info(f"Actualizado documento legal: {document_id}")
        
        return document
