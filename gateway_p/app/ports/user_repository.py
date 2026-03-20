from abc import ABC, abstractmethod
from uuid import UUID
from typing import Optional
from datetime import datetime
from app.domain.models import User


class UserRepository(ABC):
    """Puerto: Interfaz para acceso a datos de usuarios"""

    @abstractmethod
    async def create(self, user: User, password: Optional[str]) -> User:
        """Crea un nuevo usuario"""
        pass

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Obtiene usuario por ID"""
        pass

    @abstractmethod
    async def get_by_email(
        self, email: str
    ) -> Optional[tuple[User, Optional[str], Optional[str], Optional[datetime]]]:
        """Obtiene usuario, contraseña y token de registro por email"""
        pass

    @abstractmethod
    async def set_email_verified(self, email: str, is_verified: bool) -> User:
        """Actualiza el estado de verificacion de email"""
        pass

    @abstractmethod
    async def update_registration_token(
        self,
        email: str,
        token: str,
        expires_at: datetime,
    ) -> None:
        """Guarda token de registro temporal para el email"""
        pass

    @abstractmethod
    async def clear_registration_token(self, email: str) -> None:
        """Limpia token de registro temporal para el email"""
        pass

    @abstractmethod
    async def complete_registration(
        self,
        email: str,
        user: User,
        password: str,
    ) -> User:
        """Completa el registro con datos de perfil"""
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        """Actualiza un usuario existente"""
        pass

    @abstractmethod
    async def update_password(self, email: str, hashed_password: str) -> None:
        """Actualiza la contraseña de un usuario"""
        pass

    @abstractmethod
    async def delete(self, user_id: UUID) -> bool:
        """Elimina un usuario"""
        pass

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool:
        """Verifica si un email ya existe"""
        pass
