"""
Configuración del SDK de Payway.

Soporta configuración por:
- Variables de entorno
- Archivo .env
- Parámetros explícitos

Variables de entorno soportadas:
    PAYWAY_PUBLIC_KEY - API key pública para tokenización
    PAYWAY_PRIVATE_KEY - API key privada para operaciones
    PAYWAY_ENVIRONMENT - "sandbox" o "production"
    PAYWAY_TIMEOUT - Timeout en segundos
    PAYWAY_MAX_RETRIES - Máximo de reintentos
    PAYWAY_LOG_LEVEL - Nivel de logging
"""

from enum import Enum
from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Entornos disponibles."""

    SANDBOX = "sandbox"
    PRODUCTION = "production"
    DEVELOPMENT = "development"  # Alias para sandbox


class PaywayConfig(BaseSettings):
    """Configuración del cliente Payway."""

    model_config = SettingsConfigDict(
        env_prefix="PAYWAY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Credenciales
    public_key: SecretStr = Field(
        ...,
        description="API key pública (para tokenización desde frontend)",
    )
    private_key: SecretStr = Field(
        ...,
        description="API key privada (para operaciones de backend)",
    )
    site_id: str | None = Field(
        default=None,
        description="ID del sitio/comercio",
    )

    # Entorno
    environment: Environment = Field(
        default=Environment.SANDBOX,
        description="Entorno de ejecución",
    )

    # URLs base
    sandbox_url: str = Field(
        default="https://developers.decidir.com/api/v2",
        description="URL del entorno sandbox",
    )
    production_url: str = Field(
        default="https://live.decidir.com/api/v2",
        description="URL del entorno de producción",
    )

    # HTTP Client
    timeout: float = Field(
        default=30.0,
        ge=1.0,
        le=120.0,
        description="Timeout en segundos para requests",
    )
    connect_timeout: float = Field(
        default=10.0,
        ge=1.0,
        le=60.0,
        description="Timeout de conexión en segundos",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Número máximo de reintentos",
    )
    retry_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=30.0,
        description="Delay inicial entre reintentos (exponential backoff)",
    )
    retry_max_delay: float = Field(
        default=30.0,
        ge=1.0,
        le=120.0,
        description="Delay máximo entre reintentos",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Nivel de logging (DEBUG, INFO, WARNING, ERROR)",
    )
    log_requests: bool = Field(
        default=False,
        description="Log de requests/responses (cuidado con datos sensibles)",
    )

    # Features
    validate_responses: bool = Field(
        default=True,
        description="Validar respuestas contra modelos Pydantic",
    )
    mask_sensitive_data: bool = Field(
        default=True,
        description="Enmascarar datos sensibles en logs",
    )

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, v: str) -> str:
        """Normaliza el valor del entorno."""
        if isinstance(v, str):
            v = v.lower().strip()
            if v in ("dev", "development", "test"):
                return Environment.SANDBOX.value
            if v in ("prod", "production", "live"):
                return Environment.PRODUCTION.value
        return v

    @property
    def base_url(self) -> str:
        """Retorna la URL base según el entorno."""
        if self.environment == Environment.PRODUCTION:
            return self.production_url.rstrip("/")
        return self.sandbox_url.rstrip("/")

    @property
    def is_production(self) -> bool:
        """Indica si está en producción."""
        return self.environment == Environment.PRODUCTION

    @property
    def is_sandbox(self) -> bool:
        """Indica si está en sandbox."""
        return self.environment in (Environment.SANDBOX, Environment.DEVELOPMENT)

    def get_auth_headers(self, use_private_key: bool = True) -> dict[str, str]:
        """Genera los headers de autenticación."""
        key = self.private_key if use_private_key else self.public_key
        return {
            "apikey": key.get_secret_value(),
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Cache-Control": "no-cache",
        }

    def get_public_auth_headers(self) -> dict[str, str]:
        """Headers de autenticación con API key pública."""
        return self.get_auth_headers(use_private_key=False)


@lru_cache
def get_default_config() -> PaywayConfig:
    """Obtiene la configuración por defecto (singleton cacheado)."""
    return PaywayConfig()  # type: ignore[call-arg]
