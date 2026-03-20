from datetime import datetime, timedelta
from typing import Optional, Union, Any
from jose import jwt
from passlib.context import CryptContext
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Context para hash de contraseñas con Argon2
# Argon2 es más seguro que bcrypt y recomendado por OWASP
# Parámetros:
#   - time_cost: iteraciones (3 es estándar)
#   - memory_cost: 65536 KB (64 MB)
#   - parallelism: threads paralelos
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica que la contraseña en texto plano coincida con el hash almacenado.
    
    Args:
        plain_password: Contraseña en texto plano del usuario
        hashed_password: Hash almacenado en la BD
        
    Returns:
        True si coinciden, False en caso contrario
    """
    logger.debug("Verificando contraseña contra hash")
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Genera un hash seguro de la contraseña usando Argon2.
    
    Este hash NO es reversible. Se usa solo para verificación (verify_password).
    
    Args:
        password: Contraseña en texto plano
        
    Returns:
        Hash seguro de la contraseña
    """
    logger.debug("Generando hash de contraseña con Argon2")
    return pwd_context.hash(password)

def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"sub": str(subject), "exp": int(expire.timestamp())}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_email_verification_token(email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.EMAIL_VERIFICATION_EXPIRE_MINUTES)
    to_encode = {"sub": email, "exp": int(expire.timestamp()), "scope": "email_verification"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_email_verification_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("scope") != "email_verification":
            return None
        return payload.get("sub")
    except Exception:
        return None


def verify_access_token(token: str) -> Optional[str]:
    """Verifica el token JWT y retorna el subject (user_id)"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            return None
        return user_id
    except Exception:
        return None


def create_registration_token(email: str) -> str:
    """Crea un token temporal para completar el registro (Step 2)
    
    Este token expira en 24 horas y solo se puede usar en /register/complete
    """
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode = {"sub": email, "exp": int(expire.timestamp()), "scope": "registration"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_registration_token(token: str) -> Optional[str]:
    """Verifica un token de registro y retorna el email
    
    Retorna None si el token es inválido, expirado o no es de scope 'registration'
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("scope") != "registration":
            return None
        return payload.get("sub")
    except Exception:
        return None
