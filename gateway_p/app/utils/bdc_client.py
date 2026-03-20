"""
Utilidad para crear clientes HTTP configurados para BDC

Soporta certificados de dos formas:
1. Rutas de archivo (desarrollo local): bdc_client_cert_path, bdc_client_key_path
2. Contenido PEM en variables de entorno (Cloud Run): api_cert_client_crt, api_cert_client_key, api_cert_ca

En Cloud Run, los secretos se inyectan como variables de entorno con el contenido PEM directo.
"""
import httpx
import ssl
import tempfile
import atexit
from typing import Optional, Union
import os
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Cache de archivos temporales creados desde contenido PEM (Cloud Run)
# Se limpian al salir del proceso
_temp_cert_files: list[str] = []


def _is_pem_content(value: str) -> bool:
    """Indica si el valor es contenido PEM (no una ruta de archivo)."""
    return value and "-----BEGIN" in value.strip()


def _ensure_file_path(value: str, label: str) -> Optional[str]:
    """
    Convierte valor en ruta de archivo usable por httpx/ssl.
    Si es contenido PEM, crea archivo temporal. Si es ruta, valida que exista.
    """
    if not value or not value.strip():
        return None
    value = value.strip()

    if _is_pem_content(value):
        try:
            fd, path = tempfile.mkstemp(suffix=".pem", prefix=f"bdc_{label}_")
            with os.fdopen(fd, "w") as f:
                f.write(value)
            _temp_cert_files.append(path)
            logger.debug(f"Certificado {label} cargado desde variable de entorno (PEM content)")
            return path
        except Exception as e:
            logger.error(f"Error al crear archivo temporal para {label}: {e}")
            raise
    else:
        if not os.path.exists(value):
            raise FileNotFoundError(f"{label} no encontrado: {value}")
        return value


def get_bdc_ssl_config() -> tuple[Union[bool, str, ssl.SSLContext], Optional[str], Optional[tuple]]:
    """
    Obtiene la configuración SSL para conexiones con BDC.

    Soporta certificados desde:
    - Rutas de archivo (bdc_client_cert_path, bdc_client_key_path)
    - Variables de entorno con contenido PEM (api_cert_client_crt, api_cert_client_key, api_cert_ca)
      Usado en Cloud Run cuando los secretos se mapean como env vars.

    Returns:
        tuple: (verify, ca_cert, client_cert)
            - verify: bool, str (path) o ssl.SSLContext
            - ca_cert: str o None
            - client_cert: tuple o None - (cert_path, key_path) para mTLS
    """
    # Sandbox/test sin certificados
    if "sandbox" in settings.bdc_base_url.lower() or "sandboxtest" in settings.bdc_base_url.lower():
        if not (settings.api_cert_client_crt and settings.api_cert_client_key):
            logger.warning("Usando BDC en modo sandbox/test sin verificación SSL")
            return False, None, None

    # Prioridad para Cloud Run: api_cert_* (contenido PEM desde secretos)
    # Luego: bdc_client_cert_path / bdc_client_key_path (rutas locales)
    cert_source = settings.api_cert_client_crt or settings.bdc_client_cert_path
    key_source = settings.api_cert_client_key or settings.bdc_client_key_path
    ca_source = settings.api_cert_ca or None

    if not cert_source or not key_source:
        if "sandbox" in settings.bdc_base_url.lower() or "sandboxtest" in settings.bdc_base_url.lower():
            return False, None, None
        logger.warning("BDC sin certificados configurados - desactivando verificación SSL (NO RECOMENDADO EN PRODUCCIÓN)")
        return False, None, None

    cert_path = _ensure_file_path(cert_source, "client_crt")
    key_path = _ensure_file_path(key_source, "client_key")
    ca_path = _ensure_file_path(ca_source, "ca") if ca_source else None

    if not cert_path or not key_path:
        return True, None, None

    client_cert = (cert_path, key_path)

    # Para el CA: usar CAs del sistema + CA custom de BDC.
    # create_default_context(cafile=...) REEMPLAZA los CAs y provoca "unable to get local issuer certificate".
    # Usar load_verify_locations() para AÑADIR nuestra CA a los CAs por defecto.
    if ca_path:
        ctx = ssl.create_default_context()
        ctx.load_verify_locations(cafile=ca_path)
        ctx.load_cert_chain(certfile=cert_path, keyfile=key_path)
        logger.info(f"Configuración SSL BDC: mTLS + CA custom añadida (verify=system+{ca_path})")
        return ctx, ca_path, client_cert

    logger.info(f"Configuración SSL BDC: cert={cert_path}, key={key_path}")
    return True, None, client_cert


def _cleanup_temp_certs():
    """Elimina archivos temporales de certificados al salir."""
    for path in _temp_cert_files:
        try:
            if os.path.exists(path):
                os.unlink(path)
                logger.debug(f"Certificado temporal eliminado: {path}")
        except Exception as e:
            logger.warning(f"Error al eliminar certificado temporal {path}: {e}")


atexit.register(_cleanup_temp_certs)


def create_bdc_client() -> httpx.AsyncClient:
    """
    Crea un cliente HTTP configurado correctamente para BDC.

    En Cloud Run, usa las variables de entorno api_cert_client_crt, api_cert_client_key
    y api_cert_ca (contenido PEM desde secretos) para mTLS y verificación de la CA custom.
    """
    verify, ca_cert, client_cert = get_bdc_ssl_config()

    client_config: dict = {
        "verify": verify,
        "timeout": 30.0,
    }

    # Si verify es SSLContext, el client cert ya está cargado en el contexto
    if isinstance(verify, ssl.SSLContext):
        pass  # No agregar cert, ya está en el SSLContext
    elif client_cert:
        client_config["cert"] = client_cert

    logger.debug(f"Cliente BDC configurado: verify={type(verify).__name__}, cert={bool(client_cert)}")
    return httpx.AsyncClient(**client_config)
