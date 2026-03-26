"""
Ejemplo básico de uso del SDK de Payway.

Este ejemplo muestra cómo:
1. Tokenizar una tarjeta
2. Procesar un pago
3. Realizar una devolución

Para ejecutar:
    1. Copia .env.example a .env
    2. Configura tus credenciales de prueba
    3. python examples/basic_usage.py
"""

import asyncio
from decimal import Decimal

from payway_sdk import (
    PaywayClient,
    CardData,
    CardHolder,
    PaymentRequest,
    Customer,
    PaywayValidationError,
    PaywayError,
)


async def main():
    """Ejemplo completo de flujo de pago."""
    
    # Crear cliente (usa variables de entorno o parámetros)
    # Las credenciales pueden venir de:
    # - Variables de entorno: PAYWAY_PUBLIC_KEY, PAYWAY_PRIVATE_KEY
    # - Archivo .env
    # - Parámetros explícitos
    
    async with PaywayClient(
        public_key="pk_test_your_key",  # Reemplazar con tu key
        private_key="sk_test_your_key",  # Reemplazar con tu key
        environment="sandbox",
    ) as client:
        
        # ===========================================================
        # 1. TOKENIZAR TARJETA
        # ===========================================================
        print("\n1. Tokenizando tarjeta...")
        
        try:
            # Datos de tarjeta de prueba de Payway
            card_data = CardData(
                card_number="4111111111111111",  # Visa de prueba
                card_expiration_month="12",
                card_expiration_year="25",
                security_code="123",
                card_holder=CardHolder(
                    name="Juan Perez",
                    identification_type="DNI",
                    identification_number="12345678",
                ),
            )
            
            token = await client.tokens.create(card_data)
            
            print(f"   ✓ Token creado: {token.id}")
            print(f"   BIN: {token.bin}")
            print(f"   Últimos 4: {token.last_four_digits}")
            
        except PaywayValidationError as e:
            print(f"   ✗ Error de validación: {e.message}")
            for error in e.validation_errors:
                print(f"     - {error}")
            return
        
        # ===========================================================
        # 2. PROCESAR PAGO
        # ===========================================================
        print("\n2. Procesando pago...")
        
        try:
            # Crear request de pago
            payment_request = PaymentRequest(
                site_transaction_id="ORDER-" + str(hash(token.id))[-8:],
                token=token.id,
                payment_method_id=1,  # 1 = Visa
                amount=Decimal("1500.00"),  # $1500 ARS
                currency="ARS",
                installments=1,
                description="Compra de prueba",
                customer=Customer(
                    email="cliente@example.com",
                    first_name="Juan",
                    last_name="Perez",
                    identification_type="DNI",
                    identification_number="12345678",
                ),
            )
            
            payment = await client.payments.create(payment_request)
            
            if payment.is_approved:
                print(f"   ✓ Pago aprobado!")
                print(f"   ID: {payment.id}")
                print(f"   Código de autorización: {payment.authorization_code}")
                print(f"   Ticket: {payment.ticket}")
            else:
                print(f"   ✗ Pago rechazado")
                print(f"   Estado: {payment.status}")
                print(f"   Detalles: {payment.status_details}")
                return
            
        except PaywayError as e:
            print(f"   ✗ Error en el pago: {e}")
            return
        
        # ===========================================================
        # 3. CONSULTAR PAGO
        # ===========================================================
        print("\n3. Consultando pago...")
        
        payment_info = await client.payments.get(payment.id)
        print(f"   Estado actual: {payment_info.status}")
        print(f"   Monto: ${payment_info.amount / 100:.2f}")  # Convertir centavos
        
        # ===========================================================
        # 4. DEVOLUCIÓN (opcional)
        # ===========================================================
        print("\n4. Realizando devolución parcial...")
        
        try:
            # Devolución parcial del 50%
            refund = await client.refunds.create(
                payment_id=payment.id,
                amount=Decimal("750.00"),  # 50% de $1500
                reason="Devolución parcial de prueba",
            )
            
            print(f"   ✓ Devolución creada!")
            print(f"   ID: {refund.id}")
            print(f"   Estado: {refund.status}")
            
        except PaywayError as e:
            print(f"   ✗ Error en devolución: {e}")

        # ===========================================================
        # 5. VERIFICAR ESTADO FINAL
        # ===========================================================
        print("\n5. Estado final del pago...")
        
        final_payment = await client.payments.get(payment.id)
        print(f"   Estado: {final_payment.status}")
        
        # Listar todas las devoluciones
        refunds = await client.refunds.list(payment.id)
        if refunds:
            print(f"   Devoluciones: {len(refunds)}")
            for r in refunds:
                print(f"     - ID: {r.id}, Monto: ${r.amount / 100:.2f}, Estado: {r.status}")


if __name__ == "__main__":
    asyncio.run(main())
