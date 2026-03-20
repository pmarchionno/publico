# Guía de Integración con Servicio de KYC

El módulo de KYC permite conectar múltiples proveedores de validación de identidad.

## Interface `KYCProvider`
Ubicación: `app/core/kyc/service.py`

Debes implementar dos métodos principales:
- `verify_identity`: Envía los datos para inicio de validación.
- `check_status`: Consulta el estado de una validación existente.

## Pasos para Integrar "Proveedor Y"

### 1. Crear el Proveedor
Crear `app/core/kyc/providers/provider_y.py`:

```python
from app.core.kyc.service import KYCProvider, VerificationResult, KYCStatus

class ProviderY(KYCProvider):
    async def verify_identity(self, data: IdentityData) -> VerificationResult:
        # Lógica de llamada a API externa
        response = await call_external_api(data)
        
        return VerificationResult(
            verification_id=response["id"],
            status=map_status(response["state"]),
            provider_reference=response["ref"]
        )

    async def check_status(self, vid: str) -> VerificationResult:
        # Polling o consulta puntual
        ...
```

### 2. Mapeo de Estados
Es crucial normalizar los estados del proveedor a nuestro Enum `KYCStatus`:
- `Verified` -> `KYCStatus.VERIFIED`
- `Reviewing` -> `KYCStatus.PENDING`
- `Rejected` -> `KYCStatus.REJECTED`
- `SoftFail` -> `KYCStatus.MORE_INFO_NEEDED`

### 3. Webhooks de KYC
Al igual que en pagos, la mayoría de proveedores KYC funcionan asíncronamente.
- Endpoint: `POST /kyc/webhooks/{provider}`
- El servicio `KYCService` debe tener un método `process_webhook(provider, payload)` que actualice el estado del usuario en la base de datos local.
