````markdown
# Diagrama de Secuencia - Transferencia Bancaria (PlantUML)

Este diagrama detalla el flujo de una transferencia saliente hacia un banco externo.

Puedes renderizar esta secuencia usando el archivo [docs/puml/transfer_sequence.puml](docs/puml/transfer_sequence.puml).

## Integración con Banco Pagador - Transferencia

### Flujo de secuencia

El detalle de la integración con el banco se encuentra en [docs/puml/transfer_bank_integration.puml](docs/puml/transfer_bank_integration.puml).

### Contrato del Banco (resumen)

- **Endpoint**: `POST /movements/transfer-request`.
- **Seguridad**: Mutual TLS + VPN + encabezados `Authorization: Bearer {token}` y `X-SIGNATURE: HmacSHA256([uri]+payload, secret-key)`.
- **Payload**:
  ```json
  {
    "originId": "12345ABCabc",
    "from": {
      "addressType": "CBU_CVU",
      "address": "4320001010003138730019",
      "owner": {
        "personIdType": "CUI",
        "personId": "1234567890"
      }
    },
    "to": {
      "addressType": "CBU_CVU",
      "address": "4320001010003138730019",
      "owner": {
        "personIdType": "CUI",
        "personId": "1234567890"
      }
    },
    "body": {
      "currencyId": "032",
      "amount": 123.23,
      "description": "description",
      "concept": "VAR"
    }
  }
  ```
- **Respuesta**:
  ```json
  {
    "statusCode": 0,
    "message": "Transferencia creada con exito",
    "time": "Fri, 14 Feb 2025 08:04:25 -0300"
  }
  ```

### Ubicación recomendada para la implementación

- Implementar el conector específico del banco siguiendo la interfaz [app/core/connectors/interface.py](app/core/connectors/interface.py#L1-L43).
- Orquestar la llamada en `PaymentOperation` desde [app/core/payments/operation.py](app/core/payments/operation.py#L26-L47), donde se encadenan `build_request`, `execute_request` y `handle_response`.

````
