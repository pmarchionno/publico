"""
Ejemplo de manejo de errores con el SDK de Payway.

Este ejemplo muestra cómo manejar los diferentes tipos de errores
que puede lanzar el SDK.
"""

import asyncio
from decimal import Decimal

from payway_sdk import (
    PaywayClient,
    PaymentRequest,
    # Excepciones
    PaywayError,
    PaywayAuthenticationError,
    PaywayValidationError,
    PaywayNotFoundError,
    PaywayConnectionError,
    PaywayTimeoutError,
    PaywayRateLimitError,
    PaywayServerError,
)


async def process_payment_safely(client: PaywayClient, payment_data: dict) -> dict:
    """
    Procesa un pago con manejo completo de errores.
    
    Returns:
        dict con el resultado: {"success": bool, "data": ..., "error": ...}
    """
    try:
        payment = await client.payments.create(payment_data)
        
        if payment.is_approved:
            return {
                "success": True,
                "data": {
                    "payment_id": payment.id,
                    "authorization_code": payment.authorization_code,
                    "ticket": payment.ticket,
                },
            }
        else:
            return {
                "success": False,
                "error": {
                    "type": "payment_rejected",
                    "status": payment.status.value if payment.status else None,
                    "details": payment.status_details,
                },
            }

    except PaywayAuthenticationError as e:
        # API keys inválidas o expiradas
        return {
            "success": False,
            "error": {
                "type": "authentication_error",
                "message": "Error de autenticación con Payway",
                "details": e.to_dict(),
            },
        }

    except PaywayValidationError as e:
        # Datos inválidos (token expirado, monto inválido, etc.)
        return {
            "success": False,
            "error": {
                "type": "validation_error",
                "message": e.message,
                "validation_errors": e.validation_errors,
                "request_id": e.request_id,
            },
        }

    except PaywayNotFoundError as e:
        # Token no encontrado
        return {
            "success": False,
            "error": {
                "type": "not_found",
                "message": e.message,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
            },
        }

    except PaywayTimeoutError as e:
        # Timeout - la transacción puede haber sido procesada
        # IMPORTANTE: verificar el estado antes de reintentar
        return {
            "success": False,
            "error": {
                "type": "timeout",
                "message": "Timeout en la comunicación. Verificar estado del pago.",
                "timeout_seconds": e.timeout_seconds,
                "request_id": e.request_id,
                "should_verify": True,
            },
        }

    except PaywayConnectionError as e:
        # Error de conexión - se puede reintentar
        return {
            "success": False,
            "error": {
                "type": "connection_error",
                "message": "Error de conexión con Payway",
                "can_retry": True,
            },
        }

    except PaywayRateLimitError as e:
        # Demasiadas requests
        return {
            "success": False,
            "error": {
                "type": "rate_limit",
                "message": "Se excedió el límite de requests",
                "retry_after": e.retry_after,
            },
        }

    except PaywayServerError as e:
        # Error del servidor de Payway
        return {
            "success": False,
            "error": {
                "type": "server_error",
                "message": "Error en los servidores de Payway",
                "request_id": e.request_id,
                "can_retry": True,
            },
        }

    except PaywayError as e:
        # Cualquier otro error de Payway
        return {
            "success": False,
            "error": {
                "type": "unknown_error",
                "message": str(e),
                "details": e.to_dict(),
            },
        }

    except Exception as e:
        # Error inesperado
        return {
            "success": False,
            "error": {
                "type": "unexpected_error",
                "message": str(e),
            },
        }


async def main():
    """Demo de manejo de errores."""
    
    async with PaywayClient(
        public_key="pk_test_xxx",
        private_key="sk_test_xxx",
        environment="sandbox",
    ) as client:
        
        # Intentar un pago con token inválido
        result = await process_payment_safely(client, {
            "site_transaction_id": "TEST-ERROR-001",
            "token": "invalid_token",
            "payment_method_id": 1,
            "amount": "100.00",
            "installments": 1,
        })
        
        if result["success"]:
            print(f"Pago exitoso: {result['data']}")
        else:
            print(f"Error: {result['error']['type']}")
            print(f"Mensaje: {result['error'].get('message')}")


if __name__ == "__main__":
    asyncio.run(main())
