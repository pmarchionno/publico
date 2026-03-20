import logging
from uuid import UUID
from typing import Optional
from datetime import datetime, timedelta, timezone
from threading import Thread
from app.domain.models import User
from app.ports.user_repository import UserRepository
from app.auth.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_email_verification_token,
    verify_email_verification_token,
    create_registration_token,
)
from config.settings import settings

logger = logging.getLogger(__name__)


class UserService:
    """Servicio de usuarios"""

    def __init__(self, user_repository: UserRepository, email_service=None):
        logger.info("Inicializando UserService con UserRepository: %s y EmailService: %s", type(user_repository).__name__, type(email_service).__name__ if email_service else "None")
        print(f"DEBUG: Inicializando UserService con UserRepository: {type(user_repository).__name__} y EmailService: {type(email_service).__name__} si existe")
        self.repository = user_repository
        self.email_service = email_service

    async def start_email_registration(self, email: str, code: str) -> str:
        """Step 1: create pending user and send verification email."""
        result = await self.repository.get_by_email(email)
        logger.info("Iniciando registro para email: %s, resultado de búsqueda: %s", email, "encontrado" if result else "no encontrado") 
        print(f"DEBUG: Iniciando registro para email: {email}, resultado de búsqueda: {'encontrado' if result else 'no encontrado'}")
        if result:
            user, _, __, ___ = result
            if user.is_email_verified:
                logger.warning("Email ya verificado: %s", email)
                print(f"DEBUG: Email ya verificado: {email}")
                raise ValueError(f"El email {email} ya esta verificado")
        else:
            user = User(email=email, is_active=True, is_email_verified=False)
            try:
                logger.info("Creando usuario pendiente para email: %s", email)
                print(f"DEBUG: Creando usuario pendiente para email: {email}")
                await self.repository.create(user, None)
            except Exception as exc:
                logger.exception("Error al crear usuario pendiente para email: %s", email)
                raise ValueError("No se pudo crear el usuario. Intente nuevamente.") from exc

        # Enviar email en un thread de fondo para no bloquear la respuesta
        logger.info("[BREVO/USER_SERVICE] Preparando envío de email de verificación a %s", email)
        if self.email_service:
            logger.info("[BREVO/USER_SERVICE] EmailService disponible - iniciando envío en background para %s", email)
            minutes = '60'
            first_name = user.first_name if result and user.first_name else 'Hola'

            def send_email_background():
                import asyncio
                try:
                    logger.info("[BREVO/USER_SERVICE] Thread background iniciado - enviando email a %s", email)
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    success = loop.run_until_complete(
                        self.email_service.send_verification_email(email, code, minutes, first_name)
                    )
                    if success:
                        logger.info("[BREVO/USER_SERVICE] ✅ Servidor procesó correctamente - email enviado a Brevo OK para %s", email)
                    else:
                        logger.warning("[BREVO/USER_SERVICE] ⚠️ Envío falló (Brevo/EmailService retornó False) para %s", email)
                except Exception as e:
                    logger.error("[BREVO/USER_SERVICE] ❌ Error en envío background para %s: %s", email, str(e), exc_info=True)

            thread = Thread(target=send_email_background, daemon=True)
            thread.start()
            logger.info("[BREVO/USER_SERVICE] Thread de envío lanzado - el servidor procesará el mail de forma asíncrona para %s", email)
        
        # Retornar el código para desarrollo
        return code

    async def start_email_registration_token(self, email: str, code: str) -> str:
        """Step 1: create pending user and send verification email."""
        result = await self.repository.get_by_email(email)
        logger.info("Iniciando registro para email: %s, resultado de búsqueda: %s", email, "encontrado" if result else "no encontrado") 
        print(f"DEBUG: Iniciando registro para email: {email}, resultado de búsqueda: {'encontrado' if result else 'no encontrado'}")
        if result:
            user, _, __, ___ = result
            if user.is_email_verified:
                raise ValueError(f"El email {email} ya esta verificado")
        else:
            user = User(email=email, is_active=True, is_email_verified=False)
            await self.repository.create(user, None)

        token = create_email_verification_token(email)
        verification_link = f"{settings.EMAIL_VERIFICATION_BASE_URL}?token={token}"
        
        # Enviar email si el servicio está disponible
        if self.email_service:
            await self.email_service.send_verification_email(email, verification_link)
        
        return verification_link
    
    async def verify_email(self, token: str) -> User:
        """Verify email using token and mark as verified."""
        email = verify_email_verification_token(token)
        if not email:
            raise ValueError("Token invalido o expirado")

        result = await self.repository.get_by_email(email)
        if not result:
            raise ValueError("Usuario no encontrado")

        return await self.repository.set_email_verified(email, True)

    async def check_email_status(self, email: str) -> dict:
        """Check if email exists and is verified.
        
        Si el email está verificado y no tiene contraseña, retorna un token
        temporal de registro que se puede usar en /register/complete
        """
        result = await self.repository.get_by_email(email)
        
        if not result:
            return {
                "exists": False,
                "is_verified": False,
                "can_complete_registration": False,
                "registration_token": None,
            }
        
        user, hashed_password, stored_token, stored_expires_at = result
        has_password = hashed_password is not None
        
        # Si está verificado y no tiene contraseña, generar token temporal
        registration_token = None
        can_complete = user.is_email_verified and not has_password
        if can_complete:
            now = datetime.now(timezone.utc)
            expires_at = None
            if stored_expires_at is not None:
                expires_at = (
                    stored_expires_at
                    if stored_expires_at.tzinfo is not None
                    else stored_expires_at.replace(tzinfo=timezone.utc)
                )

            if stored_token and expires_at and expires_at > now:
                registration_token = stored_token
            else:
                registration_token = create_registration_token(email)
                expires_at = now + timedelta(hours=24)
                await self.repository.update_registration_token(
                    email,
                    registration_token,
                    expires_at,
                )
        
        return {
            "exists": True,
            "is_verified": user.is_email_verified,
            "can_complete_registration": can_complete,
            "registration_token": registration_token,
        }

    async def complete_registration(
        self,
        email: str,
        # registration_token: str,
        password: str,
        dni: str,
        first_name: str,
        last_name: str,
        gender: str,
        cuit_cuil: str,
        phone: str,
        nationality: str,
        occupation: str,
        marital_status: str,
        location: str,
        is_kyc_verified: bool,
    ) -> User:
        """Step 2: complete user profile after email verification."""
        result = await self.repository.get_by_email(email)
        if not result:
            raise ValueError("Usuario no encontrado")

        user, hashed_password, stored_token, stored_expires_at = result
        # if not user.is_email_verified:
        #     raise ValueError("Email no verificado")

        if hashed_password is not None:
            raise ValueError("El registro ya fue completado")

        # if not stored_token or not stored_expires_at:
        #     raise ValueError("Token de registro invalido o expirado")
        # 
        # stored_expires_at = (
        #     stored_expires_at
        #     if stored_expires_at.tzinfo is not None
        #     else stored_expires_at.replace(tzinfo=timezone.utc)
        # )
        # now = datetime.now(timezone.utc)
        # if stored_expires_at <= now:
        #     raise ValueError("Token de registro invalido o expirado")

        # if stored_token != registration_token:
        #     raise ValueError("Token de registro invalido o expirado")

        if len(password) < 8:
            raise ValueError("La contraseña debe tener minimo 8 caracteres")

        full_name = f"{first_name} {last_name}".strip()
        updated_user = User(
            id=user.id,
            email=email,
            full_name=full_name,
            first_name=first_name,
            last_name=last_name,
            dni=dni,
            gender=gender,
            cuit_cuil=cuit_cuil,
            phone=phone,
            nationality=nationality,
            occupation=occupation,
            marital_status=marital_status,
            location=location,
            is_active=True,
            is_email_verified=True,
            created_at=user.created_at,
            updated_at=user.updated_at,
            is_kyc_verified=is_kyc_verified,
        )

        password_len = len(password)
        password_bytes_len = len(password.encode("utf-8"))
        logger.info(
            "Hashing password (len=%s, bytes=%s)",
            password_len,
            password_bytes_len,
        )
        hashed_password = get_password_hash(password)
        # return updated_user
        completed_user = await self.repository.complete_registration(email, updated_user, hashed_password)
        # Enviar email de bienvenida
        if self.email_service:
            await self.email_service.send_welcome_email(email, first_name)
        
        return completed_user

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Autentica un usuario y retorna su información si es válido"""
        result = await self.repository.get_by_email(email)
        if not result:
            return None

        user, hashed_password, _, __ = result

        if not hashed_password:
            return None

        if not user.is_email_verified:
            return None

        # Verificar contraseña
        if not verify_password(password, hashed_password):
            return None

        # Verificar que el usuario está activo
        if not user.is_active:
            return None

        return user

    async def get_user(self, user_id: UUID) -> Optional[User]:
        """Obtiene información de un usuario"""
        return await self.repository.get_by_id(user_id)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Obtiene un usuario por email"""
        result = await self.repository.get_by_email(email)
        if result:
            user, _, __, ___ = result
            return user
        return None

    async def update_user(self, user: User) -> User:
        """Actualiza la información de un usuario"""
        return await self.repository.update(user)
    
    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
    ) -> bool:
        """Cambia la contraseña de un usuario"""
        # Obtener usuario
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise ValueError("Usuario no encontrado")
        
        # Verificar contraseña actual
        result = await self.repository.get_by_email(user.email)
        if not result:
            raise ValueError("Usuario no encontrado")
        
        _, hashed_password, __, ___ = result
        if not hashed_password or not verify_password(current_password, hashed_password):
            raise ValueError("Contraseña actual incorrecta")
        
        # Validar nueva contraseña
        if len(new_password) < 8:
            raise ValueError("La nueva contraseña debe tener mínimo 8 caracteres")
        
        # Actualizar contraseña
        new_hashed_password = get_password_hash(new_password)
        await self.repository.update_password(user.email, new_hashed_password)
        
        return True

    async def change_password_by_email(
        self,
        email: str,
        current_password: str,
        new_password: str,
    ) -> bool:
        """Cambia la contraseña de un usuario por email (sin auth)."""
        result = await self.repository.get_by_email(email)
        if not result:
            raise ValueError("Usuario no encontrado")

        _, hashed_password, __, ___ = result
        if not hashed_password or not verify_password(current_password, hashed_password):
            raise ValueError("Contraseña actual incorrecta")

        if len(new_password) < 8:
            raise ValueError("La nueva contraseña debe tener mínimo 8 caracteres")

        new_hashed_password = get_password_hash(new_password)
        await self.repository.update_password(email, new_hashed_password)

        return True

    async def deactivate_user(self, user_id: UUID) -> bool:
        """Desactiva un usuario"""
        user = await self.repository.get_by_id(user_id)
        if not user:
            return False
        
        user.is_active = False
        await self.repository.update(user)
        return True

    def create_user_token(self, user_id: str) -> str:
        """Crea un token JWT para el usuario"""
        return create_access_token(subject=user_id)
