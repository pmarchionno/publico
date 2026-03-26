"""
Ejemplo de uso síncrono del SDK de Payway.

Para código que no es async, el SDK ofrece métodos síncronos.
"""

from decimal import Decimal

from payway_sdk import PaywayClient, CardData, CardHolder, PaymentRequest


def main():
    """Ejemplo síncrono de pago."""
    
    # Crear cliente
    client = PaywayClient(
        public_key="pk_test_your_key",
        private_key="sk_test_your_key",
        environment="sandbox",
    )
    
    try:
        # 1. Tokenizar (síncrono)
        print("Tokenizando tarjeta...")
        
        card = CardData(
            card_number="4111111111111111",
            card_expiration_month="12",
            card_expiration_year="25",
            security_code="123",
            card_holder=CardHolder(name="Test User"),
        )
        
        token = client.tokens.create_sync(card)
        print(f"Token: {token.id}")
        
        # 2. Pagar (síncrono)
        print("Procesando pago...")
        
        payment = client.payments.create_sync({
            "site_transaction_id": "SYNC-ORDER-001",
            "token": token.id,
            "payment_method_id": 1,
            "amount": "100.00",
            "installments": 1,
        })
        
        if payment.is_approved:
            print(f"¡Pago aprobado! ID: {payment.id}")
        else:
            print(f"Pago rechazado: {payment.status}")
        
        # 3. Devolución (síncrono)
        print("Realizando devolución...")
        
        refund = client.refunds.create_sync(
            payment_id=payment.id,
            amount=Decimal("50.00"),
        )
        print(f"Devolución: {refund.id}")
        
    finally:
        # Importante: cerrar el cliente al terminar
        import asyncio
        asyncio.run(client.close())


if __name__ == "__main__":
    main()
