"""
Utilidad para validar el healthcheck de BDC con certificados.

Implementa exactamente el mismo request que:

  curl -X GET "https://api.bdcconecta.com/healthcheck" \\
    -H "accept: application/json" \\
    --cert <(gcloud secrets versions access latest --secret=api-cert-client-crt) \\
    --key <(gcloud secrets versions access latest --secret=api-cert-client-key) \\
    --cacert <(gcloud secrets versions access latest --secret=api-cert-ca)

En Cloud Run, los certificados vienen de env vars (api_cert_client_crt, api_cert_client_key,
api_cert_ca) inyectados desde Secret Manager.
"""
import asyncio
import logging
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)

# URL exacta del curl que funciona
BDC_HEALTHCHECK_URL = "https://api.bdcconecta.com/healthcheck"


def _log_verbose(msg: str, *args) -> None:
    """Log a nivel INFO y además print para asegurar visibilidad en Cloud Run."""
    logger.info(msg, *args)
    formatted = (msg % args) if args else msg
    print(f"[BDC-HEALTHCHECK] {formatted}", flush=True)


def _check_cert_sources() -> dict:
    """
    Verifica de dónde vienen los certificados: env vars (Cloud Run secrets) o rutas de archivo.
    Returns dict con status de cada fuente.
    """
    from app.utils.bdc_client import _is_pem_content

    result = {
        "source": "unknown",
        "api_cert_client_crt": bool(settings.api_cert_client_crt and settings.api_cert_client_crt.strip()),
        "api_cert_client_key": bool(settings.api_cert_client_key and settings.api_cert_client_key.strip()),
        "api_cert_ca": bool(settings.api_cert_ca and settings.api_cert_ca.strip()),
        "bdc_client_cert_path": bool(settings.bdc_client_cert_path),
        "bdc_client_key_path": bool(settings.bdc_client_key_path),
    }

    # Determinar fuente
    if result["api_cert_client_crt"] and result["api_cert_client_key"]:
        if _is_pem_content(settings.api_cert_client_crt) or _is_pem_content(settings.api_cert_client_key):
            result["source"] = "env_pem"  # Cloud Run: secrets inyectados como env
        else:
            result["source"] = "env_path"  # Rutas en env
    elif result["bdc_client_cert_path"] and result["bdc_client_key_path"]:
        result["source"] = "file_path"
    return result


async def run_bdc_healthcheck(
    base_url: Optional[str] = None,
    timeout: float = 30.0,
    verbose: bool = False,
) -> tuple[bool, Optional[dict], Optional[str]]:
    """
    Ejecuta GET al healthcheck de BDC, equivalente al curl con certificados.

    Args:
        base_url: URL base (ej. https://api.bdcconecta.com). Si None, usa BDC_HEALTHCHECK_URL.
        timeout: Timeout en segundos para la petición.
        verbose: Si True, log detallado de cada paso.

    Returns:
        tuple: (success, response_data, error_message)
    """
    from app.utils.bdc_client import create_bdc_client

    if base_url:
        url = base_url.rstrip("/")
        if not url.endswith("/healthcheck"):
            url = f"{url}/healthcheck"
    else:
        url = BDC_HEALTHCHECK_URL

    try:
        if verbose:
            _log_verbose("Enviando GET a endpoint: %s", url)
            _log_verbose("Headers: accept: application/json")
            _log_verbose("Timeout: %s segundos", timeout)

        async with create_bdc_client() as client:
            response = await client.get(
                url,
                headers={"accept": "application/json"},
                timeout=timeout,
            )

            if verbose:
                _log_verbose("Respuesta recibida: status=%s", response.status_code)
                _log_verbose("Body (primeros 500 chars): %s", response.text[:500] if response.text else "(vacío)")

            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict):
                status_code_value = data.get("statusCode")
                if not isinstance(status_code_value, int):
                    return False, data, f"Respuesta inválida: statusCode={status_code_value}"

            return True, data, None

    except Exception as e:
        error_msg = str(e)
        if verbose:
            import traceback

            _log_verbose("ERROR en petición: %s", error_msg)
            _log_verbose("Traceback: %s", traceback.format_exc())
        else:
            logger.debug("BDC healthcheck falló: %s", error_msg)
        return False, None, error_msg


async def run_bdc_healthchecks_main_thread(
    count: int = 5,
    interval_seconds: float = 1.0,
    base_url: Optional[str] = None,
) -> None:
    """
    Ejecuta healthchecks BDC en el main thread (bloquea startup).
    Logging muy verboso para diagnosticar en Cloud Run.

    1. Verifica fuentes de certificados (env vars = secrets inyectados en Cloud Run)
    2. Intenta con env vars (api_cert_*) primero, luego rutas de archivo (bdc_client_*)
    3. Log detallado de endpoint, petición, respuesta y errores.
    """
    url = base_url or BDC_HEALTHCHECK_URL
    if base_url and not url.endswith("/healthcheck"):
        url = f"{base_url.rstrip('/')}/healthcheck"

    _log_verbose("=== Iniciando BDC healthcheck (main thread, verboso) ===")
    _log_verbose("Endpoint objetivo: %s", url)

    # 1. Verificar fuentes de certificados
    cert_status = _check_cert_sources()
    _log_verbose("--- Fuente de certificados ---")
    _log_verbose("api_cert_client_crt (env/secrets): %s", "presente" if cert_status["api_cert_client_crt"] else "vacío")
    _log_verbose("api_cert_client_key (env/secrets): %s", "presente" if cert_status["api_cert_client_key"] else "vacío")
    _log_verbose("api_cert_ca (env/secrets): %s", "presente" if cert_status["api_cert_ca"] else "vacío")
    _log_verbose("bdc_client_cert_path (archivo): %s", cert_status["bdc_client_cert_path"] or "no configurado")
    _log_verbose("bdc_client_key_path (archivo): %s", cert_status["bdc_client_key_path"] or "no configurado")
    _log_verbose("Fuente usada: %s (env_pem=Cloud Run secrets, file_path=rutas locales)", cert_status["source"])

    if cert_status["source"] == "unknown":
        _log_verbose("ADVERTENCIA: No hay certificados configurados. El healthcheck fallará.")

    # 2. Ejecutar healthchecks
    _log_verbose("--- Ejecutando %s healthchecks (1 cada %s seg) ---", count, interval_seconds)

    for i in range(count):
        _log_verbose(">>> Healthcheck #%s/%s", i + 1, count)
        success, data, error = await run_bdc_healthcheck(base_url=base_url, verbose=True)
        if success:
            _log_verbose("OK #%s/%s: %s", i + 1, count, data)
        else:
            _log_verbose("FALLO #%s/%s: %s", i + 1, count, error)

        if i < count - 1 and interval_seconds > 0:
            _log_verbose("Esperando %s segundos antes del siguiente...", interval_seconds)
            await asyncio.sleep(interval_seconds)

    _log_verbose("=== BDC healthchecks completados ===")


async def run_bdc_healthchecks_background(
    count: int = 5,
    interval_seconds: float = 1.0,
    base_url: Optional[str] = None,
) -> None:
    """
    Ejecuta múltiples healthchecks BDC en background con intervalo entre intentos.

    Útil para validación al inicio de la instancia sin bloquear el startup.
    Usa la misma URL que el curl: https://api.bdcconecta.com/healthcheck

    Args:
        count: Número de healthchecks a ejecutar.
        interval_seconds: Segundos entre cada intento.
        base_url: URL base o URL completa. Si None, usa BDC_HEALTHCHECK_URL.
    """
    logger.info(
        "[STARTUP] Ejecutando %s healthchecks BDC de prueba en background (%s/s)...",
        count,
        int(1 / interval_seconds) if interval_seconds > 0 else 0,
    )

    for i in range(count):
        success, data, error = await run_bdc_healthcheck(base_url=base_url)
        if success:
            logger.info("[STARTUP] BDC healthcheck #%s/%s OK: %s", i + 1, count, data)
        else:
            logger.warning("[STARTUP] BDC healthcheck #%s/%s falló: %s", i + 1, count, error)

        if i < count - 1 and interval_seconds > 0:
            await asyncio.sleep(interval_seconds)

    logger.info("[STARTUP] BDC healthchecks de prueba completados")
