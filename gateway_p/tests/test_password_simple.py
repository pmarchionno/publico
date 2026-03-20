"""
Script simple para probar las validaciones de contraseña
"""
import sys
sys.path.insert(0, 'd:\\proyectos\\odoo\\pagoflex\\gateway_p')

from app.auth.schemas import UserCompleteProfileRequest
from pydantic import ValidationError


def get_valid_request_data(password: str = "ValidPass123!") -> dict:
    """Genera datos válidos de request para testing"""
    return {
        "email": "test@example.com",
        "registration_token": "dummy_token_for_testing",
        "password": password,
        "dni": "12345678",
        "first_name": "Juan",
        "last_name": "Pérez",
        "gender": "masculino",
        "cuit_cuil": "20123456789",
        "phone": "+543812345678",
        "nationality": "Argentina",
        "occupation": "Engineer",
        "marital_status": "Single",
        "location": "Buenos Aires"
    }


def test_password(password: str, expected_to_pass: bool, test_name: str):
    """Prueba una contraseña y reporta resultado"""
    try:
        data = get_valid_request_data(password)
        request = UserCompleteProfileRequest(**data)
        if expected_to_pass:
            print(f"✅ PASS: {test_name}")
            return True
        else:
            print(f"❌ FAIL: {test_name} - Se esperaba error pero pasó")
            return False
    except ValidationError as e:
        if not expected_to_pass:
            error_msg = str(e.errors()[0].get('msg', ''))
            print(f"✅ PASS: {test_name} - Error esperado: {error_msg}")
            return True
        else:
            print(f"❌ FAIL: {test_name} - Error inesperado:")
            for error in e.errors():
                print(f"   - {error.get('msg', 'Error desconocido')}")
            return False


def main():
    print("\n🔐 PRUEBAS DE VALIDACIÓN DE CONTRASEÑA\n")
    print("=" * 70)
    
    tests_passed = 0
    tests_total = 0
    
    # Tests de contraseñas válidas
    print("\n✅ CONTRASEÑAS VÁLIDAS (deberían pasar):\n")
    
    valid_passwords = [
        ("SecurePass123!", "Contraseña con todos los requisitos"),
        ("MyP@ssw0rd", "Contraseña con @"),
        ("C0mpl3x#Pass", "Contraseña con #"),
        ("Test123$", "Contraseña corta pero válida"),
        ("Abcd123!", "Contraseña simple válida"),
    ]
    
    for password, description in valid_passwords:
        tests_total += 1
        if test_password(password, True, description):
            tests_passed += 1
    
    # Tests de contraseñas inválidas
    print("\n❌ CONTRASEÑAS INVÁLIDAS (deberían fallar):\n")
    
    invalid_passwords = [
        ("lowercase123!", "Sin mayúscula"),
        ("UPPERCASE123!", "Sin minúscula (implícito)"),
        ("PasswordOnly!", "Sin número"),
        ("Password123", "Sin símbolo especial"),
        ("Abc1!", "Muy corta (menos de 8 caracteres)"),
        ("simple", "Sin mayúscula, número ni símbolo"),
        ("nouppercas3!", "Sin mayúscula"),
    ]
    
    for password, description in invalid_passwords:
        tests_total += 1
        if test_password(password, False, description):
            tests_passed += 1
    
    # Resumen
    print("\n" + "=" * 70)
    print(f"\n📊 RESUMEN: {tests_passed}/{tests_total} tests pasaron")
    
    if tests_passed == tests_total:
        print("✅ TODAS LAS VALIDACIONES FUNCIONAN CORRECTAMENTE\n")
        return 0
    else:
        print(f"❌ {tests_total - tests_passed} tests fallaron\n")
        return 1


if __name__ == "__main__":
    exit(main())
