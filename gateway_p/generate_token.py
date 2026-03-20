#!/usr/bin/env python3
"""
Script para generar un token JWT válido para pruebas
"""
import jwt
from datetime import datetime, timedelta, timezone
from uuid import uuid4

# Usar la misma SECRET_KEY de settings.py
SECRET_KEY = "changeme"

# Crear un usuario de prueba
user_id = str(uuid4())
expiration_time = datetime.now(timezone.utc) + timedelta(hours=1)

# Payload del token
payload = {
    "sub": user_id,
    "exp": expiration_time
}

# Generar token
token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

print(f"User ID: {user_id}")
print(f"Token: {token}")
print(f"Expiration: {expiration_time}")
