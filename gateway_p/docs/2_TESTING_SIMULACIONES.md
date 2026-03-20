# Guía de Simulación de Escenarios de Prueba

Esta guía detalla los flujos principales para probar la billetera digital.

## Pre-requisitos
- API corriendo en `http://localhost:8000`
- Herramienta: `curl` o Postman.

---

## 1. Onboarding (KYC)
El registro de usuario inicia el proceso de validación de identidad.

**Endpoint Simulado:** `POST /kyc/verify`
```json
{
  "customer_id": "cus_123",
  "provider": "mock_provider",
  "identity_data": {
    "first_name": "Juan",
    "last_name": "Perez",
    "dob": "1990-01-01",
    "national_id": "12345678",
    "country": "AR"
  }
}
```
**Prueba de Éxito:** Verificar que retorna `verification_id` y status `PENDING` o `VERIFIED`.

---

## 2. Carga de Saldo (Cash-in)
Simula el ingreso de dinero desde una cuenta bancaria externa a la billetera.

**Endpoint Simulado:** `POST /payments/cashin`
```json
{
  "amount": 10000,
  "currency": "ARS",
  "customer_id": "cus_123",
  "method": "TRANSFER",
  "source_account": "CBU_EXTERNO"
}
```

---

## 3. Asociación de Tarjeta
Vinculación de una tarjeta de crédito/débito para fondear la billetera.

**Endpoint Simulado:** `POST /customers/{id}/cards`
```json
{
  "pan": "4111111111111111",
  "exp_month": 12,
  "exp_year": 2030,
  "holder_name": "JUAN PEREZ"
}
```
**Verificación:** El sistema debe tokenizar la tarjeta contra el Gateway y guardar solo el token.

---

## 4. Transferencia a Terceros (P2P / CBU)
Envío de dinero.

**Endpoint Simulado:** `POST /payments/transfer`
```json
{
  "source_customer_id": "cus_123",
  "amount": 500,
  "currency": "ARS",
  "destination": {
    "type": "CBU",
    "value": "0000000000000000000000"
  }
}
```

---

## 5. Recepción de Transferencia
Normalmente esto entra vía Webhook desde el Banco proveedor.

**Simulación de Webhook:** `POST /webhooks/bank/notification`
```json
{
  "event": "TRANSFER_RECEIVED",
  "amount": 2000,
  "cbu_dest": "MI_CVU_VIRTUAL",
  "tx_id": "banco_tx_999"
}
```

---

## 6. Operación Fallida (Simulación)
Para probar resiliencia y manejo de errores.

**Escenario:** El banco rechaza la transacción por falta de fondos.
1. Iniciar pago: `POST /payments`
2. El `MockConnector` debe estar configurado para fallar si el `amount` es, por ejemplo, `999999`.
3. **Verificación:** La respuesta debe ser HTTP 4xx/5xx o 200 con `status: "FAILED"` y `reason: "INSUFFICIENT_FUNDS"`.

---

## 7. Repetir pruebas automáticas dentro del entorno Docker
Para ejecutar los tests end-to-end (incluyendo el flujo de transferencias contra el stub del conector) dentro del contenedor `api` ya levantado con `docker compose`:

```bash
docker compose -f gateway_p/docker-compose.yml exec -e PYTHONPATH=/app api pytest tests/test_api.py
```

Esto asegura que las dependencias (`fastapi`, `httpx`, etc.) y las configuraciones (`BDC_*`) cargadas en el contenedor se utilicen de forma consistente con el entorno de despliegue.
