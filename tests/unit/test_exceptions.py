"""Tests para las excepciones del SDK."""

import pytest

from payway_sdk.domain.exceptions import (
    PaywayError,
    PaywayAuthenticationError,
    PaywayValidationError,
    PaywayNotFoundError,
    PaywayConnectionError,
    PaywayTimeoutError,
    PaywayRateLimitError,
    PaywayServerError,
)


class TestPaywayError:
    """Tests para la excepción base."""

    def test_basic_error(self):
        """Crea un error básico."""
        error = PaywayError("Algo salió mal")
        assert str(error) == "Algo salió mal"
        assert error.message == "Algo salió mal"
        assert error.status_code is None

    def test_error_with_details(self):
        """Crea un error con todos los detalles."""
        error = PaywayError(
            message="Error de prueba",
            status_code=400,
            error_code="invalid_param",
            details={"field": "amount"},
            request_id="req-123",
        )
        assert error.status_code == 400
        assert error.error_code == "invalid_param"
        assert error.request_id == "req-123"
        assert "invalid_param" in str(error)
        assert "HTTP 400" in str(error)

    def test_to_dict(self):
        """Convierte error a diccionario."""
        error = PaywayError(
            message="Test",
            status_code=500,
            error_code="server_error",
            request_id="req-456",
        )
        result = error.to_dict()
        assert result["error_type"] == "PaywayError"
        assert result["message"] == "Test"
        assert result["status_code"] == 500
        assert result["error_code"] == "server_error"


class TestPaywayAuthenticationError:
    """Tests para errores de autenticación."""

    def test_default_message(self):
        """Usa mensaje por defecto."""
        error = PaywayAuthenticationError()
        assert "autenticación" in error.message.lower()

    def test_custom_message(self):
        """Acepta mensaje personalizado."""
        error = PaywayAuthenticationError(
            message="API key inválida",
            status_code=401,
        )
        assert error.message == "API key inválida"
        assert error.status_code == 401


class TestPaywayValidationError:
    """Tests para errores de validación."""

    def test_with_validation_errors(self):
        """Incluye errores de validación detallados."""
        error = PaywayValidationError(
            message="Datos inválidos",
            validation_errors=[
                {"field": "amount", "message": "Debe ser mayor a 0"},
                {"field": "token", "message": "Token expirado"},
            ],
            status_code=400,
        )
        assert len(error.validation_errors) == 2
        result = error.to_dict()
        assert "validation_errors" in result
        assert len(result["validation_errors"]) == 2


class TestPaywayNotFoundError:
    """Tests para errores de recurso no encontrado."""

    def test_with_resource_info(self):
        """Incluye información del recurso."""
        error = PaywayNotFoundError(
            message="Pago no encontrado",
            resource_type="payment",
            resource_id="12345",
            status_code=404,
        )
        assert error.resource_type == "payment"
        assert error.resource_id == "12345"
        result = error.to_dict()
        assert result["resource_type"] == "payment"


class TestPaywayConnectionError:
    """Tests para errores de conexión."""

    def test_with_original_error(self):
        """Guarda el error original."""
        original = ConnectionError("Network unreachable")
        error = PaywayConnectionError(
            message="No se pudo conectar",
            original_error=original,
        )
        assert error.original_error is original


class TestPaywayTimeoutError:
    """Tests para errores de timeout."""

    def test_with_timeout(self):
        """Incluye el timeout configurado."""
        error = PaywayTimeoutError(
            message="Timeout de conexión",
            timeout_seconds=30.0,
        )
        assert error.timeout_seconds == 30.0


class TestPaywayRateLimitError:
    """Tests para errores de rate limiting."""

    def test_with_retry_after(self):
        """Incluye el tiempo de espera."""
        error = PaywayRateLimitError(
            message="Demasiadas requests",
            retry_after=60,
            status_code=429,
        )
        assert error.retry_after == 60
        result = error.to_dict()
        assert result["retry_after"] == 60


class TestPaywayServerError:
    """Tests para errores del servidor."""

    def test_default_message(self):
        """Usa mensaje por defecto."""
        error = PaywayServerError(status_code=500)
        assert "servidor" in error.message.lower()
