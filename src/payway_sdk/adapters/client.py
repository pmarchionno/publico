"""
Cliente principal de Payway SDK.

Este es el punto de entrada principal para usar el SDK.
Agrupa todos los servicios y maneja la configuración.
"""

from types import TracebackType
from typing import Any, Self

from pydantic import SecretStr

from payway_sdk.adapters.healthcheck import HealthService
from payway_sdk.adapters.payments import PaymentService
from payway_sdk.adapters.refunds import RefundService
from payway_sdk.adapters.tokens import TokenService
from payway_sdk.infrastructure.config import Environment, PaywayConfig
from payway_sdk.infrastructure.http_client import HTTPClient
from payway_sdk.infrastructure.logging import get_logger, setup_logging

logger = get_logger("payway_sdk")


class PaywayClient:
    """
    Cliente principal para interactuar con Payway API.
    
    Uso básico:
        >>> from payway_sdk import PaywayClient
        >>> 
        >>> # Con credenciales explícitas
        >>> client = PaywayClient(
        ...     public_key="pk_test_xxx",
        ...     private_key="sk_test_xxx",
        ... )
        >>> 
        >>> # Con variables de entorno (PAYWAY_PUBLIC_KEY, PAYWAY_PRIVATE_KEY)
        >>> client = PaywayClient()
        >>> 
        >>> # Uso con async context manager
        >>> async with PaywayClient() as client:
        ...     token = await client.tokens.create(card_data)
        ...     payment = await client.payments.create(payment_data)
    
    Servicios disponibles:
        - client.tokens: Tokenización de tarjetas
        - client.payments: Procesamiento de pagos
        - client.refunds: Devoluciones
        - client.health: Healthcheck
    
    Attributes:
        tokens: Servicio de tokenización
        payments: Servicio de pagos
        refunds: Servicio de devoluciones
        health: Servicio de healthcheck
        config: Configuración del cliente
    """

    def __init__(
        self,
        public_key: str | None = None,
        private_key: str | None = None,
        environment: Environment | str = Environment.SANDBOX,
        config: PaywayConfig | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Inicializa el cliente de Payway.
        
        Args:
            public_key: API key pública (para tokenización)
            private_key: API key privada (para operaciones de backend)
            environment: Entorno ("sandbox" o "production")
            config: Configuración personalizada (sobreescribe otros parámetros)
            **kwargs: Argumentos adicionales para PaywayConfig
        
        Raises:
            ValueError: Si faltan las credenciales
        """
        if config:
            self._config = config
        else:
            # Construir configuración desde parámetros o variables de entorno
            config_kwargs: dict[str, Any] = kwargs.copy()
            
            if public_key:
                config_kwargs["public_key"] = SecretStr(public_key)
            if private_key:
                config_kwargs["private_key"] = SecretStr(private_key)
            if environment:
                if isinstance(environment, str):
                    environment = Environment(environment.lower())
                config_kwargs["environment"] = environment

            try:
                self._config = PaywayConfig(**config_kwargs)  # type: ignore[arg-type]
            except Exception as e:
                raise ValueError(
                    "Faltan credenciales. Proporciona public_key y private_key "
                    "o configura PAYWAY_PUBLIC_KEY y PAYWAY_PRIVATE_KEY"
                ) from e

        # Configurar logging
        setup_logging(
            level=self._config.log_level,
            json_format=self._config.is_production,
            mask_sensitive=self._config.mask_sensitive_data,
        )

        # Crear cliente HTTP
        self._http_client = HTTPClient(self._config)

        # Inicializar servicios
        self._tokens = TokenService(self._http_client, self._config)
        self._payments = PaymentService(self._http_client, self._config)
        self._refunds = RefundService(self._http_client, self._config)
        self._health = HealthService(self._http_client, self._config)

        logger.info(
            "PaywayClient inicializado",
            environment=self._config.environment.value,
            base_url=self._config.base_url,
        )

    # Propiedades para acceder a servicios

    @property
    def tokens(self) -> TokenService:
        """Servicio de tokenización de tarjetas."""
        return self._tokens

    @property
    def payments(self) -> PaymentService:
        """Servicio de pagos."""
        return self._payments

    @property
    def refunds(self) -> RefundService:
        """Servicio de devoluciones."""
        return self._refunds

    @property
    def health(self) -> HealthService:
        """Servicio de healthcheck."""
        return self._health

    @property
    def config(self) -> PaywayConfig:
        """Configuración del cliente."""
        return self._config

    # Context manager

    async def __aenter__(self) -> Self:
        """Entrada del async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Salida del async context manager."""
        await self.close()

    def __enter__(self) -> Self:
        """Entrada del context manager síncrono."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Salida del context manager síncrono."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.close())
            else:
                loop.run_until_complete(self.close())
        except RuntimeError:
            asyncio.run(self.close())

    async def close(self) -> None:
        """Cierra las conexiones del cliente."""
        logger.debug("Cerrando conexiones del cliente")
        await self._http_client.close()

    # Métodos de conveniencia

    @classmethod
    def from_env(cls, **overrides: Any) -> "PaywayClient":
        """
        Crea un cliente desde variables de entorno.
        
        Las variables esperadas son:
        - PAYWAY_PUBLIC_KEY
        - PAYWAY_PRIVATE_KEY
        - PAYWAY_ENVIRONMENT (opcional, default: sandbox)
        
        Args:
            **overrides: Valores que sobreescriben las variables de entorno
        
        Returns:
            PaywayClient configurado
        """
        return cls(**overrides)

    @classmethod
    def sandbox(
        cls,
        public_key: str,
        private_key: str,
        **kwargs: Any,
    ) -> "PaywayClient":
        """
        Crea un cliente para el entorno sandbox.
        
        Args:
            public_key: API key pública de sandbox
            private_key: API key privada de sandbox
            **kwargs: Configuración adicional
        
        Returns:
            PaywayClient configurado para sandbox
        """
        return cls(
            public_key=public_key,
            private_key=private_key,
            environment=Environment.SANDBOX,
            **kwargs,
        )

    @classmethod
    def production(
        cls,
        public_key: str,
        private_key: str,
        **kwargs: Any,
    ) -> "PaywayClient":
        """
        Crea un cliente para producción.
        
        Args:
            public_key: API key pública de producción
            private_key: API key privada de producción
            **kwargs: Configuración adicional
        
        Returns:
            PaywayClient configurado para producción
        """
        return cls(
            public_key=public_key,
            private_key=private_key,
            environment=Environment.PRODUCTION,
            **kwargs,
        )

    def __repr__(self) -> str:
        return (
            f"PaywayClient("
            f"environment={self._config.environment.value!r}, "
            f"base_url={self._config.base_url!r})"
        )
