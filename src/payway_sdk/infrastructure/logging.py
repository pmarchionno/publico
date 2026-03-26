"""
Logging estructurado para el SDK de Payway.

Usa structlog para logging estructurado con soporte para:
- Contexto de request (request_id, site_id, etc.)
- Enmascaramiento de datos sensibles
- Formato JSON para producción
"""

import logging
import re
import sys
from typing import Any

import structlog


def mask_sensitive_data(data: Any, patterns: dict[str, str] | None = None) -> Any:
    """
    Enmascara datos sensibles en logs.
    
    Args:
        data: Datos a enmascarar (dict, list, str, o cualquier otro)
        patterns: Patrones adicionales para enmascarar (regex -> reemplazo)
    
    Returns:
        Datos con valores sensibles enmascarados
    """
    if patterns is None:
        patterns = {}

    # Patrones por defecto
    sensitive_keys = {
        "card_number", "cardnumber", "pan", "account_number",
        "security_code", "cvv", "cvc", "cvv2",
        "password", "secret", "token", "apikey", "api_key",
        "private_key", "public_key", "authorization",
    }
    
    # Patrones regex para números de tarjeta
    card_pattern = re.compile(r"\b\d{13,19}\b")
    
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            lower_key = key.lower().replace("-", "_").replace(" ", "_")
            if lower_key in sensitive_keys:
                if isinstance(value, str) and len(value) > 4:
                    result[key] = f"***{value[-4:]}" if len(value) > 4 else "****"
                else:
                    result[key] = "****"
            else:
                result[key] = mask_sensitive_data(value, patterns)
        return result
    
    if isinstance(data, list):
        return [mask_sensitive_data(item, patterns) for item in data]
    
    if isinstance(data, str):
        # Enmascarar números de tarjeta en strings
        masked = card_pattern.sub(lambda m: f"****{m.group()[-4:]}", data)
        # Aplicar patrones personalizados
        for pattern, replacement in patterns.items():
            masked = re.sub(pattern, replacement, masked)
        return masked
    
    return data


def add_request_context(
    logger: structlog.BoundLogger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Procesador para agregar contexto del request."""
    # Agregar timestamp ISO si no existe
    if "timestamp" not in event_dict:
        from datetime import datetime
        event_dict["timestamp"] = datetime.utcnow().isoformat()
    
    return event_dict


def setup_logging(
    level: str = "INFO",
    json_format: bool = False,
    mask_sensitive: bool = True,
) -> None:
    """
    Configura el logging estructurado.
    
    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
        json_format: Si True, usa formato JSON (para producción)
        mask_sensitive: Si True, enmascara datos sensibles
    """
    # Configurar logging estándar
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )

    # Procesadores de structlog
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "payway_sdk") -> structlog.BoundLogger:
    """
    Obtiene un logger configurado.
    
    Args:
        name: Nombre del logger
    
    Returns:
        Logger estructurado
    """
    return structlog.get_logger(name)


class LogContext:
    """Context manager para agregar contexto temporal al logging."""

    def __init__(self, **context: Any) -> None:
        self.context = context
        self._token: Any = None

    def __enter__(self) -> "LogContext":
        self._token = structlog.contextvars.bind_contextvars(**self.context)
        return self

    def __exit__(self, *args: Any) -> None:
        if self._token:
            structlog.contextvars.unbind_contextvars(*self.context.keys())


def log_request(
    logger: structlog.BoundLogger,
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    body: Any = None,
    mask: bool = True,
) -> None:
    """Log de un request HTTP."""
    log_data: dict[str, Any] = {
        "method": method,
        "url": url,
    }
    
    if headers:
        log_data["headers"] = mask_sensitive_data(headers) if mask else headers
    
    if body:
        log_data["body"] = mask_sensitive_data(body) if mask else body
    
    logger.debug("HTTP Request", **log_data)


def log_response(
    logger: structlog.BoundLogger,
    status_code: int,
    body: Any = None,
    elapsed_ms: float | None = None,
    mask: bool = True,
) -> None:
    """Log de una respuesta HTTP."""
    log_data: dict[str, Any] = {
        "status_code": status_code,
    }
    
    if elapsed_ms is not None:
        log_data["elapsed_ms"] = round(elapsed_ms, 2)
    
    if body:
        log_data["body"] = mask_sensitive_data(body) if mask else body
    
    logger.debug("HTTP Response", **log_data)
