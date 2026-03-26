"""Tests para la configuración."""

import os
import pytest
from pydantic import SecretStr

from payway_sdk.infrastructure.config import PaywayConfig, Environment


class TestPaywayConfig:
    """Tests para PaywayConfig."""

    def test_create_basic(self):
        """Crea configuración básica."""
        config = PaywayConfig(
            public_key=SecretStr("pk_test"),
            private_key=SecretStr("sk_test"),
        )
        assert config.environment == Environment.SANDBOX
        assert config.is_sandbox is True
        assert config.is_production is False

    def test_base_url_sandbox(self):
        """URL correcta para sandbox."""
        config = PaywayConfig(
            public_key=SecretStr("pk_test"),
            private_key=SecretStr("sk_test"),
            environment=Environment.SANDBOX,
        )
        assert "developers.decidir.com" in config.base_url

    def test_base_url_production(self):
        """URL correcta para producción."""
        config = PaywayConfig(
            public_key=SecretStr("pk_live"),
            private_key=SecretStr("sk_live"),
            environment=Environment.PRODUCTION,
        )
        assert "live.decidir.com" in config.base_url
        assert config.is_production is True

    def test_environment_aliases(self):
        """Acepta alias de entorno."""
        config = PaywayConfig(
            public_key=SecretStr("pk_test"),
            private_key=SecretStr("sk_test"),
            environment="dev",  # Alias para sandbox
        )
        assert config.environment == Environment.SANDBOX

        config2 = PaywayConfig(
            public_key=SecretStr("pk_live"),
            private_key=SecretStr("sk_live"),
            environment="prod",  # Alias para production
        )
        assert config2.environment == Environment.PRODUCTION

    def test_auth_headers(self):
        """Genera headers de autenticación."""
        config = PaywayConfig(
            public_key=SecretStr("pk_test"),
            private_key=SecretStr("sk_test"),
        )
        
        # Headers con private key
        private_headers = config.get_auth_headers(use_private_key=True)
        assert private_headers["apikey"] == "sk_test"
        assert private_headers["Content-Type"] == "application/json"
        
        # Headers con public key
        public_headers = config.get_auth_headers(use_private_key=False)
        assert public_headers["apikey"] == "pk_test"

    def test_custom_timeouts(self):
        """Acepta timeouts personalizados."""
        config = PaywayConfig(
            public_key=SecretStr("pk_test"),
            private_key=SecretStr("sk_test"),
            timeout=60.0,
            connect_timeout=15.0,
        )
        assert config.timeout == 60.0
        assert config.connect_timeout == 15.0

    def test_retry_config(self):
        """Configuración de reintentos."""
        config = PaywayConfig(
            public_key=SecretStr("pk_test"),
            private_key=SecretStr("sk_test"),
            max_retries=5,
            retry_delay=2.0,
        )
        assert config.max_retries == 5
        assert config.retry_delay == 2.0

    def test_from_env(self, monkeypatch):
        """Carga desde variables de entorno."""
        monkeypatch.setenv("PAYWAY_PUBLIC_KEY", "pk_from_env")
        monkeypatch.setenv("PAYWAY_PRIVATE_KEY", "sk_from_env")
        monkeypatch.setenv("PAYWAY_ENVIRONMENT", "production")
        
        config = PaywayConfig()
        assert config.public_key.get_secret_value() == "pk_from_env"
        assert config.private_key.get_secret_value() == "sk_from_env"
        assert config.environment == Environment.PRODUCTION
