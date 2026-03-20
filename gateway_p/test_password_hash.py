"""Test para verificar que el cifrado de contraseñas funciona correctamente con Argon2"""

from app.auth.security import get_password_hash, verify_password


def test_password_hashing():
    """Test que la contraseña se cifra y verifica correctamente"""
    # Contraseña en texto plano
    plain_password = "MiContraseña123!Segura"
    
    # Generar hash
    hashed = get_password_hash(plain_password)
    
    print(f"\n✓ Contraseña original: {plain_password}")
    print(f"✓ Hash generado (Argon2): {hashed}")
    print(f"✓ Longitud del hash: {len(hashed)} caracteres")
    
    # Verificar que el hash NO es la contraseña original
    assert hashed != plain_password, "ERROR: El hash no debe ser igual a la contraseña"
    print("✓ Hash es diferente a contraseña original")
    
    # Verificar que el hash se puede validar
    assert verify_password(plain_password, hashed), "ERROR: No se pudo validar la contraseña"
    print("✓ Validación exitosa con contraseña correcta")
    
    # Verificar que una contraseña incorrecta NO se valida
    assert not verify_password("ContraseñaIncorrecta", hashed), "ERROR: Aceptó contraseña incorrecta"
    print("✓ Rechaza contraseña incorrecta")
    
    # Verificar que hashes diferentes de la misma contraseña son distintos (salt aleatorio)
    hashed2 = get_password_hash(plain_password)
    assert hashed != hashed2, "ERROR: Dos hashes de la misma contraseña deben ser diferentes"
    print("✓ Hashes diferentes para misma contraseña (salt aleatorio)")
    
    # Pero ambos validan la misma contraseña
    assert verify_password(plain_password, hashed2), "ERROR: No valida el segundo hash"
    print("✓ Ambos hashes validan correctamente")
    
    print("\n✅ TODOS LOS TESTS PASARON - Argon2 está configurado correctamente")


if __name__ == "__main__":
    test_password_hashing()
