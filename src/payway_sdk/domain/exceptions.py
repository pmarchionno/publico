"""
Excepciones personalizadas del SDK de Payway.

Jerarquía de excepciones:
    PaywayError (base)
    ├── PaywayAuthenticationError - Errores de autenticación (401, 403)
    ├── PaywayValidationError - Errores de validación (400, 422)
    ├── PaywayNotFoundError - Recurso no encontrado (404)
    ├── PaywayConnectionError - Errores de conexión
    ├── PaywayTimeoutError - Timeout en requests
    ├── PaywayRateLimitError - Rate limiting (429)
    └── PaywayServerError - Errores del servidor (5xx)
"""

from typing import Any


class PaywayError(Exception):
    """Excepción base para todos los errores del SDK de Payway."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        self.request_id = request_id

    def __str__(self) -> str:
        parts = [self.message]
        if self.error_code:
            parts.append(f"[{self.error_code}]")
        if self.status_code:
            parts.append(f"(HTTP {self.status_code})")
        if self.request_id:
            parts.append(f"Request ID: {self.request_id}")
        return " ".join(parts)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"status_code={self.status_code}, "
            f"error_code={self.error_code!r}, "
            f"request_id={self.request_id!r})"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convierte la excepción a un diccionario serializable."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "status_code": self.status_code,
            "error_code": self.error_code,
            "details": self.details,
            "request_id": self.request_id,
        }


class PaywayAuthenticationError(PaywayError):
    """Error de autenticación (API keys inválidas o expiradas)."""

    def __init__(
        self,
        message: str = "Error de autenticación con Payway",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)


class PaywayValidationError(PaywayError):
    """Error de validación de datos (parámetros inválidos)."""

    def __init__(
        self,
        message: str = "Datos de entrada inválidos",
        validation_errors: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.validation_errors = validation_errors or []

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["validation_errors"] = self.validation_errors
        return result


class PaywayNotFoundError(PaywayError):
    """Recurso no encontrado (transacción, token, etc.)."""

    def __init__(
        self,
        message: str = "Recurso no encontrado",
        resource_type: str | None = None,
        resource_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.resource_type = resource_type
        self.resource_id = resource_id

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["resource_type"] = self.resource_type
        result["resource_id"] = self.resource_id
        return result


class PaywayConnectionError(PaywayError):
    """Error de conexión con el servidor de Payway."""

    def __init__(
        self,
        message: str = "Error de conexión con Payway",
        original_error: Exception | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.original_error = original_error


class PaywayTimeoutError(PaywayError):
    """Timeout en la comunicación con Payway."""

    def __init__(
        self,
        message: str = "Timeout en la comunicación con Payway",
        timeout_seconds: float | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.timeout_seconds = timeout_seconds


class PaywayRateLimitError(PaywayError):
    """Error por exceder el límite de requests."""

    def __init__(
        self,
        message: str = "Se excedió el límite de requests",
        retry_after: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["retry_after"] = self.retry_after
        return result


class PaywayServerError(PaywayError):
    """Error interno del servidor de Payway."""

    def __init__(
        self,
        message: str = "Error interno del servidor de Payway",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)


class PaywayPaymentDeclinedError(PaywayError):
    """Pago rechazado por el procesador."""

    def __init__(
        self,
        message: str = "Pago rechazado",
        decline_code: str | None = None,
        decline_reason: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.decline_code = decline_code
        self.decline_reason = decline_reason

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["decline_code"] = self.decline_code
        result["decline_reason"] = self.decline_reason
        return result


class PaywayFraudError(PaywayError):
    """Transacción rechazada por detección de fraude."""

    def __init__(
        self,
        message: str = "Transacción rechazada por análisis antifraude",
        fraud_score: float | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.fraud_score = fraud_score
