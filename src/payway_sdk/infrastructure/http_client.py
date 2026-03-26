"""
Cliente HTTP robusto con retry, backoff y manejo de errores.

Características:
- Timeout configurable
- Reintentos con exponential backoff
- Logging estructurado
- Manejo de errores con excepciones específicas
- Soporte async con httpx
"""

import time
import uuid
from typing import Any, TypeVar

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from payway_sdk.domain.exceptions import (
    PaywayAuthenticationError,
    PaywayConnectionError,
    PaywayNotFoundError,
    PaywayRateLimitError,
    PaywayServerError,
    PaywayTimeoutError,
    PaywayValidationError,
)
from payway_sdk.infrastructure.config import PaywayConfig
from payway_sdk.infrastructure.logging import (
    get_logger,
    log_request,
    log_response,
    mask_sensitive_data,
)

T = TypeVar("T")
logger = get_logger("payway_sdk.http")


class HTTPClient:
    """Cliente HTTP robusto para comunicación con Payway."""

    def __init__(self, config: PaywayConfig) -> None:
        """
        Inicializa el cliente HTTP.
        
        Args:
            config: Configuración del SDK
        """
        self.config = config
        self._client: httpx.AsyncClient | None = None
        self._sync_client: httpx.Client | None = None

    async def _get_async_client(self) -> httpx.AsyncClient:
        """Obtiene o crea el cliente async."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=httpx.Timeout(
                    timeout=self.config.timeout,
                    connect=self.config.connect_timeout,
                ),
                follow_redirects=True,
                http2=True,
            )
        return self._client

    def _get_sync_client(self) -> httpx.Client:
        """Obtiene o crea el cliente síncrono."""
        if self._sync_client is None or self._sync_client.is_closed:
            self._sync_client = httpx.Client(
                base_url=self.config.base_url,
                timeout=httpx.Timeout(
                    timeout=self.config.timeout,
                    connect=self.config.connect_timeout,
                ),
                follow_redirects=True,
                http2=True,
            )
        return self._sync_client

    async def close(self) -> None:
        """Cierra las conexiones del cliente."""
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None

    def _generate_request_id(self) -> str:
        """Genera un ID único para el request."""
        return str(uuid.uuid4())

    def _handle_error_response(
        self,
        response: httpx.Response,
        request_id: str,
    ) -> None:
        """
        Procesa respuestas de error y lanza la excepción apropiada.
        
        Args:
            response: Respuesta HTTP
            request_id: ID del request para trazabilidad
        
        Raises:
            PaywayAuthenticationError: Para errores 401, 403
            PaywayValidationError: Para errores 400, 422
            PaywayNotFoundError: Para errores 404
            PaywayRateLimitError: Para errores 429
            PaywayServerError: Para errores 5xx
        """
        status = response.status_code
        
        try:
            error_data = response.json()
        except Exception:
            error_data = {"message": response.text}

        error_message = error_data.get("message", f"Error HTTP {status}")
        error_code = error_data.get("code") or error_data.get("error_type")
        
        base_kwargs: dict[str, Any] = {
            "status_code": status,
            "error_code": error_code,
            "details": error_data,
            "request_id": request_id,
        }

        if status == 401 or status == 403:
            raise PaywayAuthenticationError(
                message=error_message or "Error de autenticación",
                **base_kwargs,
            )

        if status == 400 or status == 422:
            validation_errors = error_data.get("validation_errors", [])
            raise PaywayValidationError(
                message=error_message or "Datos de entrada inválidos",
                validation_errors=validation_errors,
                **base_kwargs,
            )

        if status == 404:
            raise PaywayNotFoundError(
                message=error_message or "Recurso no encontrado",
                **base_kwargs,
            )

        if status == 429:
            retry_after = response.headers.get("Retry-After")
            raise PaywayRateLimitError(
                message=error_message or "Rate limit excedido",
                retry_after=int(retry_after) if retry_after else None,
                **base_kwargs,
            )

        if status >= 500:
            raise PaywayServerError(
                message=error_message or "Error interno del servidor",
                **base_kwargs,
            )

    def _create_retry_decorator(self) -> Any:
        """Crea el decorador de retry según la configuración."""
        return retry(
            stop=stop_after_attempt(self.config.max_retries + 1),
            wait=wait_exponential(
                multiplier=self.config.retry_delay,
                max=self.config.retry_max_delay,
            ),
            retry=retry_if_exception_type(
                (
                    httpx.ConnectError,
                    httpx.ConnectTimeout,
                    PaywayServerError,
                    PaywayRateLimitError,
                )
            ),
            reraise=True,
        )

    async def request(
        self,
        method: str,
        path: str,
        use_private_key: bool = True,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Realiza un request HTTP async.
        
        Args:
            method: Método HTTP (GET, POST, PUT, DELETE)
            path: Path del endpoint (sin URL base)
            use_private_key: Si True, usa la API key privada
            json: Body JSON del request
            params: Query parameters
            **kwargs: Argumentos adicionales para httpx
        
        Returns:
            Respuesta parseada como dict
        
        Raises:
            PaywayError: Para cualquier error de la API
        """
        request_id = self._generate_request_id()
        headers = self.config.get_auth_headers(use_private_key)
        headers["X-Request-ID"] = request_id
        
        url = path.lstrip("/")
        start_time = time.time()

        if self.config.log_requests:
            log_request(
                logger,
                method=method,
                url=f"{self.config.base_url}/{url}",
                headers=headers,
                body=json,
                mask=self.config.mask_sensitive_data,
            )

        retry_decorator = self._create_retry_decorator()

        @retry_decorator
        async def _do_request() -> httpx.Response:
            client = await self._get_async_client()
            return await client.request(
                method=method,
                url=url,
                headers=headers,
                json=json,
                params=params,
                **kwargs,
            )

        try:
            response = await _do_request()
        except httpx.ConnectError as e:
            raise PaywayConnectionError(
                message="Error de conexión con Payway",
                original_error=e,
                request_id=request_id,
            ) from e
        except httpx.TimeoutException as e:
            raise PaywayTimeoutError(
                message="Timeout en la comunicación con Payway",
                timeout_seconds=self.config.timeout,
                request_id=request_id,
            ) from e

        elapsed_ms = (time.time() - start_time) * 1000

        if self.config.log_requests:
            try:
                response_body = response.json()
            except Exception:
                response_body = response.text
            log_response(
                logger,
                status_code=response.status_code,
                body=response_body,
                elapsed_ms=elapsed_ms,
                mask=self.config.mask_sensitive_data,
            )

        if response.status_code >= 400:
            self._handle_error_response(response, request_id)

        try:
            return response.json()  # type: ignore[no-any-return]
        except Exception:
            return {"raw_response": response.text}

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """GET request."""
        return await self.request("GET", path, params=params, **kwargs)

    async def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """POST request."""
        return await self.request("POST", path, json=json, **kwargs)

    async def put(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """PUT request."""
        return await self.request("PUT", path, json=json, **kwargs)

    async def delete(
        self,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """DELETE request."""
        return await self.request("DELETE", path, **kwargs)

    # Métodos síncronos para compatibilidad

    def request_sync(
        self,
        method: str,
        path: str,
        use_private_key: bool = True,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Versión síncrona de request."""
        request_id = self._generate_request_id()
        headers = self.config.get_auth_headers(use_private_key)
        headers["X-Request-ID"] = request_id

        url = path.lstrip("/")
        start_time = time.time()

        if self.config.log_requests:
            log_request(
                logger,
                method=method,
                url=f"{self.config.base_url}/{url}",
                headers=headers,
                body=json,
                mask=self.config.mask_sensitive_data,
            )

        try:
            client = self._get_sync_client()
            response = client.request(
                method=method,
                url=url,
                headers=headers,
                json=json,
                params=params,
                **kwargs,
            )
        except httpx.ConnectError as e:
            raise PaywayConnectionError(
                message="Error de conexión con Payway",
                original_error=e,
                request_id=request_id,
            ) from e
        except httpx.TimeoutException as e:
            raise PaywayTimeoutError(
                message="Timeout en la comunicación con Payway",
                timeout_seconds=self.config.timeout,
                request_id=request_id,
            ) from e

        elapsed_ms = (time.time() - start_time) * 1000

        if self.config.log_requests:
            try:
                response_body = response.json()
            except Exception:
                response_body = response.text
            log_response(
                logger,
                status_code=response.status_code,
                body=response_body,
                elapsed_ms=elapsed_ms,
                mask=self.config.mask_sensitive_data,
            )

        if response.status_code >= 400:
            self._handle_error_response(response, request_id)

        try:
            return response.json()  # type: ignore[no-any-return]
        except Exception:
            return {"raw_response": response.text}

    def get_sync(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """GET síncrono."""
        return self.request_sync("GET", path, params=params, **kwargs)

    def post_sync(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """POST síncrono."""
        return self.request_sync("POST", path, json=json, **kwargs)
