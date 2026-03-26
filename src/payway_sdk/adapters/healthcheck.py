"""
Servicio de healthcheck.

Verifica el estado de la conexión con Payway.
"""

from datetime import datetime
from typing import Any

from payway_sdk.adapters.base import BaseService
from payway_sdk.domain.models import HealthCheckResponse, HealthStatus


class HealthService(BaseService):
    """Servicio para verificar el estado del sistema."""

    async def check(self) -> HealthCheckResponse:
        """
        Verifica el estado de la conexión con Payway.
        
        Returns:
            HealthCheckResponse con el estado del servicio
        
        Example:
            >>> health = await client.health.check()
            >>> if health.status == HealthStatus.HEALTHY:
            ...     print("Payway operativo")
        """
        self._logger.debug("Verificando estado del servicio")
        
        try:
            # Intentar obtener información del servicio
            # Algunos endpoints comunes para healthcheck
            response = await self._http.get("/healthcheck")
            
            return HealthCheckResponse(
                status=HealthStatus.HEALTHY,
                timestamp=datetime.utcnow(),
                version=response.get("version"),
                services=response.get("services"),
            )
        except Exception as e:
            self._logger.warning("Healthcheck fallido", error=str(e))
            
            return HealthCheckResponse(
                status=HealthStatus.UNHEALTHY,
                timestamp=datetime.utcnow(),
                services={"error": str(e)},
            )

    async def ping(self) -> bool:
        """
        Ping simple para verificar conectividad.
        
        Returns:
            True si el servicio responde, False en caso contrario
        """
        try:
            health = await self.check()
            return health.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
        except Exception:
            return False

    def check_sync(self) -> HealthCheckResponse:
        """Versión síncrona de check()."""
        self._logger.debug("Verificando estado del servicio (sync)")
        
        try:
            response = self._http.get_sync("/healthcheck")
            
            return HealthCheckResponse(
                status=HealthStatus.HEALTHY,
                timestamp=datetime.utcnow(),
                version=response.get("version"),
                services=response.get("services"),
            )
        except Exception as e:
            self._logger.warning("Healthcheck fallido", error=str(e))
            
            return HealthCheckResponse(
                status=HealthStatus.UNHEALTHY,
                timestamp=datetime.utcnow(),
                services={"error": str(e)},
            )

    def ping_sync(self) -> bool:
        """Versión síncrona de ping()."""
        try:
            health = self.check_sync()
            return health.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
        except Exception:
            return False
