"""
Servicio de autenticación con Banco de Comercio (BDC)
Gestiona tokenización, caching y renovación automática
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
import httpx

from config.settings import settings
from app.core.bdc.schemas import BDCAuthRequest, BDCTokenCache, BDCResponse
from app.utils.bdc_client import create_bdc_client

logger = logging.getLogger(__name__)


class BDCAuthService:
    """Servicio para gestionar autenticación con BDC API"""

    def __init__(self):
        self._token_cache: Optional[BDCTokenCache] = None
        self.api_key = settings.bdc_client_id
        self.api_secret = settings.bdc_client_secret
        self.base_url = settings.bdc_base_url
        self.auth_path = "/auth"
        self.healthcheck_path = "/healthcheck"
        # Buffer de tiempo para renovar token antes de expirar (segundos)
        self.refresh_buffer = 60
        
        # Validar configuración
        if not self.api_key or not self.api_secret:
            logger.warning(
                "BDC credentials not configured. "
                "Set BDC_CLIENT_ID and BDC_CLIENT_SECRET environment variables."
            )

    async def get_token(self) -> str:
        """
        Obtiene un token válido de BDC.
        
        Si existe un token en cache y sigue siendo válido (con buffer), lo retorna.
        Si no, requiere uno nuevo de la API de BDC.
        
        Returns:
            Token de acceso válido para usar en requests a BDC
        
        Raises:
            HTTPException: Si falla la autenticación con BDC
        """
        # Verificar si tenemos token en cache y sigue siendo válido
        if self._token_cache and not self._token_cache.is_expiring_soon(self.refresh_buffer):
            logger.debug("Usando token en cache")
            return self._token_cache.access_token
        
        # Token no existe o está por expirar, obtener uno nuevo
        logger.info("Token expirado o próximo a expirar, solicitando uno nuevo")
        return await self._refresh_token()

    async def _refresh_token(self) -> str:
        """
        Obtiene un nuevo token de la API de BDC
        
        Returns:
            Nuevo token de acceso
        
        Raises:
            httpx.HTTPError: Si falla la solicitud
            ValueError: Si la respuesta no contiene token válido
        """
        # Validar credenciales
        if not self.api_key or not self.api_secret:
            raise ValueError(
                "BDC credentials not configured. "
                "Set BDC_CLIENT_ID and BDC_CLIENT_SECRET environment variables."
            )
        
        try:
            auth_payload = BDCAuthRequest(
                clientId=self.api_key,
                clientSecret=self.api_secret
            )
            
            logger.info(f"Solicitando nuevo token a {self.base_url}{self.auth_path}")
            
            async with create_bdc_client() as client:
                url = f"{self.base_url}{self.auth_path}"
                response = await client.post(
                    url,
                    json=auth_payload.model_dump(),
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                data = response.json()
                logger.debug(f"Respuesta de BDC: {data}")
                
                # Parsear respuesta
                bdc_response = BDCResponse(**data)
                
                if bdc_response.statusCode != 0:
                    error_msg = f"BDC auth failed: {bdc_response.message}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                if not bdc_response.data or "accessToken" not in bdc_response.data:
                    raise ValueError("No access token in BDC response")
                
                access_token = bdc_response.data["accessToken"]
                expires_in = bdc_response.data.get("expiresIn", 3600)
                
                # Cachear el token
                now = datetime.now(timezone.utc)
                self._token_cache = BDCTokenCache(
                    access_token=access_token,
                    expires_at=now + timedelta(seconds=expires_in),
                    created_at=now
                )
                
                logger.info(
                    f"Token obtenido exitosamente. "
                    f"Expira en {expires_in} segundos "
                    f"(a las {self._token_cache.expires_at})"
                )
                
                return access_token
        
        except httpx.HTTPError as e:
            logger.error(f"Error de comunicación con BDC: {e}")
            raise
        except (ValueError, KeyError) as e:
            logger.error(f"Error al procesar respuesta de BDC: {e}")
            raise

    def get_cached_token(self) -> Optional[str]:
        """
        Obtiene el token en cache sin renovación.
        
        Útil para verificación sin requests adicionales.
        
        Returns:
            Token si está en cache y válido, None si no existe o está expirado
        """
        if self._token_cache and not self._token_cache.is_expired():
            return self._token_cache.access_token
        return None

    def invalidate_cache(self):
        """Invalida el cache de tokens (útil después de recibir 401)"""
        logger.warning("Invalidando cache de tokens")
        self._token_cache = None

    def get_cache_info(self) -> dict:
        """Retorna información del cache para debugging"""
        if not self._token_cache:
            return {"cached": False}
        
        now = datetime.now(timezone.utc)
        expires_in = (self._token_cache.expires_at - now).total_seconds()
        
        return {
            "cached": True,
            "created_at": self._token_cache.created_at.isoformat(),
            "expires_at": self._token_cache.expires_at.isoformat(),
            "expires_in_seconds": max(0, int(expires_in)),
            "is_expired": self._token_cache.is_expired(),
            "is_expiring_soon": self._token_cache.is_expiring_soon(self.refresh_buffer),
        }

    async def healthcheck(self) -> dict:
        """
        Realiza un healthcheck contra BDC API
        
        Returns:
            dict con statusCode y time desde BDC
        
        Raises:
            httpx.HTTPError: Si falla la comunicación
        """
        url = f"{self.base_url}{self.healthcheck_path}"
        try:
            logger.info(f"Realizando healthcheck a {url}")
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                data = response.json()
                logger.debug(f"Respuesta de healthcheck: {data}")
                
                # Validar que es una respuesta válida
                if "statusCode" not in data or "time" not in data:
                    raise ValueError("Respuesta de healthcheck incompleta")
                
                logger.info("Healthcheck exitoso")
                return data
        
        except httpx.ConnectError as e:
            error_msg = f"No se puede conectar a {url}: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        except httpx.TimeoutException as e:
            error_msg = f"Timeout al conectar a {url}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        except httpx.HTTPStatusError as e:
            error_msg = f"BDC respondió con error {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        except httpx.HTTPError as e:
            error_msg = f"Error de comunicación con {url}: {type(e).__name__} - {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        except (ValueError, KeyError) as e:
            logger.error(f"Error al procesar respuesta de healthcheck: {e}")
            raise


# Instancia global del servicio
_bdc_auth_service: Optional[BDCAuthService] = None


def get_bdc_auth_service() -> BDCAuthService:
    """Factory para obtener la instancia del servicio de autenticación BDC"""
    global _bdc_auth_service
    if _bdc_auth_service is None:
        _bdc_auth_service = BDCAuthService()
    return _bdc_auth_service
