from uuid import UUID
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domain.models import User
from app.db.models import UserRecord
from app.ports.user_repository import UserRepository


class SQLUserRepository(UserRepository):
    """Implementación: Repositorio de usuarios con SQLAlchemy"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user: User, password: Optional[str]) -> User:
        """Crea un nuevo usuario en la BD"""
        user_record = UserRecord(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            first_name=user.first_name,
            last_name=user.last_name,
            dni=user.dni,
            gender=user.gender,
            cuit_cuil=user.cuit_cuil,
            phone=user.phone,
            nationality=user.nationality,
            occupation=user.occupation,
            marital_status=user.marital_status,
            location=user.location,
            password=password,
            is_active=user.is_active,
            is_email_verified=user.is_email_verified,
        )
        self.session.add(user_record)
        await self.session.commit()
        await self.session.refresh(user_record)
        return self._to_domain(user_record)

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Obtiene usuario por ID"""
        result = await self.session.execute(
            select(UserRecord).where(UserRecord.id == user_id)
        )
        record = result.scalars().first()
        return self._to_domain(record) if record else None

    async def get_by_email(
        self, email: str
    ) -> Optional[tuple[User, Optional[str], Optional[str], Optional[datetime]]]:
        """Obtiene usuario, contraseña y token de registro por email"""
        result = await self.session.execute(
            select(UserRecord).where(UserRecord.email == email)
        )
        record = result.scalars().first()
        if record:
            return (
                self._to_domain(record),
                record.password,
                record.registration_token,
                record.registration_token_expires_at,
            )
        return None

    async def update(self, user: User) -> User:
        """Actualiza un usuario existente"""
        result = await self.session.execute(
            select(UserRecord).where(UserRecord.id == user.id)
        )
        record = result.scalars().first()
        if not record:
            raise ValueError(f"Usuario {user.id} no encontrado")

        record.full_name = user.full_name
        record.first_name = user.first_name
        record.last_name = user.last_name
        record.dni = user.dni
        record.gender = user.gender
        record.cuit_cuil = user.cuit_cuil
        record.phone = user.phone
        record.nationality = user.nationality
        record.occupation = user.occupation
        record.marital_status = user.marital_status
        record.location = user.location
        record.is_active = user.is_active
        record.is_email_verified = user.is_email_verified
        record.is_kyc_verified = user.is_kyc_verified
        
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return self._to_domain(record)

    async def delete(self, user_id: UUID) -> bool:
        """Elimina un usuario"""
        result = await self.session.execute(
            select(UserRecord).where(UserRecord.id == user_id)
        )
        record = result.scalars().first()
        if record:
            await self.session.delete(record)
            await self.session.commit()
            return True
        return False

    async def exists_by_email(self, email: str) -> bool:
        """Verifica si un email ya existe"""
        result = await self.session.execute(
            select(UserRecord).where(UserRecord.email == email)
        )
        return result.scalars().first() is not None

    async def set_email_verified(self, email: str, is_verified: bool) -> User:
        """Actualiza el estado de verificacion de email"""
        result = await self.session.execute(
            select(UserRecord).where(UserRecord.email == email)
        )
        record = result.scalars().first()
        if not record:
            raise ValueError(f"Usuario con email {email} no encontrado")

        record.is_email_verified = is_verified
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return self._to_domain(record)

    async def update_registration_token(
        self,
        email: str,
        token: str,
        expires_at: datetime,
    ) -> None:
        """Guarda token de registro temporal para el email"""
        result = await self.session.execute(
            select(UserRecord).where(UserRecord.email == email)
        )
        record = result.scalars().first()
        if not record:
            raise ValueError(f"Usuario con email {email} no encontrado")

        record.registration_token = token
        record.registration_token_expires_at = expires_at
        self.session.add(record)
        await self.session.commit()

    async def clear_registration_token(self, email: str) -> None:
        """Limpia token de registro temporal para el email"""
        result = await self.session.execute(
            select(UserRecord).where(UserRecord.email == email)
        )
        record = result.scalars().first()
        if not record:
            raise ValueError(f"Usuario con email {email} no encontrado")

        record.registration_token = None
        record.registration_token_expires_at = None
        self.session.add(record)
        await self.session.commit()

    async def complete_registration(
        self,
        email: str,
        user: User,
        password: str,
    ) -> User:
        """Completa el registro con datos de perfil"""
        result = await self.session.execute(
            select(UserRecord).where(UserRecord.email == email)
        )
        record = result.scalars().first()
        if not record:
            raise ValueError(f"Usuario con email {email} no encontrado")

        record.full_name = user.full_name
        record.first_name = user.first_name
        record.last_name = user.last_name
        record.dni = user.dni
        record.gender = user.gender
        record.cuit_cuil = user.cuit_cuil
        record.phone = user.phone
        record.nationality = user.nationality
        record.occupation = user.occupation
        record.marital_status = user.marital_status
        record.location = user.location
        record.password = password
        record.is_active = user.is_active
        record.is_email_verified = user.is_email_verified
        # Preservar el token de registro para auditoría/historial
        # record.registration_token = None
        # record.registration_token_expires_at = None

        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return self._to_domain(record)

    async def update_password(self, email: str, hashed_password: str) -> None:
        """Actualiza la contraseña de un usuario"""
        result = await self.session.execute(
            select(UserRecord).where(UserRecord.email == email)
        )
        record = result.scalars().first()
        if not record:
            raise ValueError(f"Usuario con email {email} no encontrado")
        
        record.password = hashed_password
        self.session.add(record)
        await self.session.commit()

    @staticmethod
    def _to_domain(record: UserRecord) -> User:
        """Convierte UserRecord a User (domain model)"""
        return User(
            id=record.id,
            email=record.email,
            full_name=record.full_name,
            first_name=record.first_name,
            last_name=record.last_name,
            dni=record.dni,
            gender=record.gender,
            cuit_cuil=record.cuit_cuil,
            phone=record.phone,
            nationality=record.nationality,
            occupation=record.occupation,
            marital_status=record.marital_status,
            location=record.location,
            is_active=record.is_active,
            is_email_verified=record.is_email_verified,
            is_kyc_verified=record.is_kyc_verified,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
