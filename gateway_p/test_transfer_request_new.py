#!/usr/bin/env python3
"""
Script para probar el nuevo endpoint /movements/transfer-request sin originId
y con validaciones detalladas en el endpoint
"""
import httpx
import json
import jwt
from datetime import datetime, timedelta, timezone
from uuid import UUID

# Configuración
API_URL = "http://localhost:8000"
SECRET_KEY = "test_secret_key_for_testing_purposes_12345"

def create_test_token(user_id: str) -> str:
    """Crea un JWT de prueba válido"""
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token

# Token de usuario de prueba
test_user_id = "21f6f191-f9a7-43e4-9dd5-c5365d925905"
test_token = create_test_token(test_user_id)

print(f"Token de prueba: {test_token}\n")

# Test 1: Solicitud VÁLIDA (sin originId)
print("=" * 80)
print("TEST 1: Solicitud válida (SIN originId, que debe ser generado automáticamente)")
print("=" * 80)

payload_valid = {
    "from": {
        "addressType": "CVU",
        "address": "1234567890123456789012",
        "owner": {
            "personIdType": "DNI",
            "personId": "30123456789"  # DNI válido
        }
    },
    "to": {
        "addressType": "CVU",
        "address": "9876543210987654321098",
        "owner": {
            "personIdType": "DNI",
            "personId": "40987654321"  # DNI válido
        }
    },
    "body": {
        "amount": 1000.50,
        "currencyId": "ARS",
        "concept": "Pago de servicio",
        "description": "Transferencia de prueba"
    }
}

print(f"Payload enviado:\n{json.dumps(payload_valid, indent=2)}\n")

try:
    response = httpx.post(
        f"{API_URL}/bdc/movements/transfer-request",
        json=payload_valid,
        params={"token": test_token},
        timeout=10.0
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response:\n{json.dumps(response.json(), indent=2)}\n")
except Exception as e:
    print(f"Error: {e}\n")

# Test 2: Solicitud INVÁLIDA - personId vacío en origen
print("=" * 80)
print("TEST 2: Solicitud INVÁLIDA (personId vacío en origen)")
print("=" * 80)

payload_empty_person_id = {
    "from": {
        "addressType": "CVU",
        "address": "1234567890123456789012",
        "owner": {
            "personIdType": "DNI",
            "personId": ""  # VACÍO - debe fallar
        }
    },
    "to": {
        "addressType": "CVU",
        "address": "9876543210987654321098",
        "owner": {
            "personIdType": "DNI",
            "personId": "40987654321"
        }
    },
    "body": {
        "amount": 1000.50,
        "currencyId": "ARS",
        "concept": "Pago de servicio",
        "description": "Transferencia de prueba"
    }
}

print(f"Payload enviado:\n{json.dumps(payload_empty_person_id, indent=2)}\n")

try:
    response = httpx.post(
        f"{API_URL}/bdc/movements/transfer-request",
        json=payload_empty_person_id,
        params={"token": test_token},
        timeout=10.0
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response:\n{json.dumps(response.json(), indent=2)}\n")
except Exception as e:
    print(f"Error: {e}\n")

# Test 3: Solicitud INVÁLIDA - monto negativo
print("=" * 80)
print("TEST 3: Solicitud INVÁLIDA (monto negativo)")
print("=" * 80)

payload_negative_amount = {
    "from": {
        "addressType": "CVU",
        "address": "1234567890123456789012",
        "owner": {
            "personIdType": "DNI",
            "personId": "30123456789"
        }
    },
    "to": {
        "addressType": "CVU",
        "address": "9876543210987654321098",
        "owner": {
            "personIdType": "DNI",
            "personId": "40987654321"
        }
    },
    "body": {
        "amount": -500.00,  # NEGATIVO - debe fallar
        "currencyId": "ARS",
        "concept": "Pago de servicio",
        "description": "Transferencia de prueba"
    }
}

print(f"Payload enviado:\n{json.dumps(payload_negative_amount, indent=2)}\n")

try:
    response = httpx.post(
        f"{API_URL}/bdc/movements/transfer-request",
        json=payload_negative_amount,
        params={"token": test_token},
        timeout=10.0
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response:\n{json.dumps(response.json(), indent=2)}\n")
except Exception as e:
    print(f"Error: {e}\n")

# Test 4: Solicitud INVÁLIDA - falta el token
print("=" * 80)
print("TEST 4: Solicitud INVÁLIDA (sin token)")
print("=" * 80)

print(f"Payload enviado:\n{json.dumps(payload_valid, indent=2)}\n")

try:
    response = httpx.post(
        f"{API_URL}/bdc/movements/transfer-request",
        json=payload_valid,
        timeout=10.0
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response:\n{json.dumps(response.json(), indent=2)}\n")
except Exception as e:
    print(f"Error: {e}\n")

print("=" * 80)
print("Pruebas completadas")
print("=" * 80)
