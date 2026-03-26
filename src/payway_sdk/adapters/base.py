"""Clase base para servicios."""

from typing import TYPE_CHECKING

from payway_sdk.infrastructure.http_client import HTTPClient
from payway_sdk.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from payway_sdk.infrastructure.config import PaywayConfig


class BaseService:
    """Clase base para todos los servicios del SDK."""

    def __init__(self, http_client: HTTPClient, config: "PaywayConfig") -> None:
        """
        Inicializa el servicio.
        
        Args:
            http_client: Cliente HTTP configurado
            config: Configuración del SDK
        """
        self._http = http_client
        self._config = config
        self._logger = get_logger(f"payway_sdk.{self.__class__.__name__.lower()}")
