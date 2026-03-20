#!/bin/bash
# Script de prueba del nuevo endpoint sin originId

echo "=================================================="
echo "TEST 1: Request válido sin originId"
echo "=================================================="

curl -X POST "http://localhost:8000/bdc/movements/transfer-request" \
  -H "Content-Type: application/json" \
  -d '{
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
      "amount": 1000.50,
      "currencyId": "ARS",
      "concept": "Pago de servicio",
      "description": "Transferencia de prueba"
    }
  }' | python -m json.tool

echo -e "\n\n=================================================="
echo "TEST 2: Request con personId vacío"
echo "=================================================="

curl -X POST "http://localhost:8000/bdc/movements/transfer-request" \
  -H "Content-Type: application/json" \
  -d '{
    "from": {
      "addressType": "CVU",
      "address": "1234567890123456789012",
      "owner": {
        "personIdType": "DNI",
        "personId": ""
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
  }' | python -m json.tool

echo -e "\n\n=================================================="
echo "TEST 3: Request con monto negativo"
echo "=================================================="

curl -X POST "http://localhost:8000/bdc/movements/transfer-request" \
  -H "Content-Type: application/json" \
  -d '{
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
      "amount": -500.00,
      "currencyId": "ARS",
      "concept": "Pago de servicio",
      "description": "Transferencia de prueba"
    }
  }' | python -m json.tool
