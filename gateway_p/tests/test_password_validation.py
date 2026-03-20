"""
Tests para validación de requisitos de contraseña
"""
import pytest
from pydantic import ValidationError
from app.auth.schemas import UserCompleteProfileRequest


class TestPasswordValidation:
    """Test suite para validaciones de contraseña"""
    
    def get_valid_request_data(self, password: str = "ValidPass123!") -> dict:
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
    
    def test_password_valid_with_all_requirements(self):
        """Test: contraseña válida con todos los requisitos"""
        valid_passwords = [
            "SecurePass123!",
            "MyP@ssw0rd",
            "C0mpl3x#Pass",
            "Test123$",
            "Abcd123!"
        ]
        
        for password in valid_passwords:
            data = self.get_valid_request_data(password)
            request = UserCompleteProfileRequest(**data)
            assert request.password == password
    
    def test_password_missing_uppercase(self):
        """Test: contraseña sin mayúscula debe fallar"""
        data = self.get_valid_request_data("lowercase123!")
        
        with pytest.raises(ValidationError) as exc_info:
            UserCompleteProfileRequest(**data)
        
        errors = exc_info.value.errors()
        assert any("mayúscula" in str(error.get("msg", "")).lower() for error in errors)
    
    def test_password_missing_number(self):
        """Test: contraseña sin número debe fallar"""
        data = self.get_valid_request_data("PasswordOnly!")
        
        with pytest.raises(ValidationError) as exc_info:
            UserCompleteProfileRequest(**data)
        
        errors = exc_info.value.errors()
        assert any("número" in str(error.get("msg", "")).lower() for error in errors)
    
    def test_password_missing_special_char(self):
        """Test: contraseña sin símbolo especial debe fallar"""
        data = self.get_valid_request_data("Password123")
        
        with pytest.raises(ValidationError) as exc_info:
            UserCompleteProfileRequest(**data)
        
        errors = exc_info.value.errors()
        assert any("símbolo" in str(error.get("msg", "")).lower() for error in errors)
    
    def test_password_too_short(self):
        """Test: contraseña muy corta debe fallar"""
        data = self.get_valid_request_data("Abc1!")
        
        with pytest.raises(ValidationError) as exc_info:
            UserCompleteProfileRequest(**data)
        
        errors = exc_info.value.errors()
        # Debería fallar por ser menor a 8 caracteres
        assert len(errors) > 0
    
    def test_password_various_special_chars(self):
        """Test: diferentes símbolos especiales válidos"""
        special_chars = "!@#$%^&*()_+-=[]{}|;:',.<>?/"
        
        for char in special_chars:
            password = f"Password123{char}"
            data = self.get_valid_request_data(password)
            request = UserCompleteProfileRequest(**data)
            assert request.password == password
    
    def test_password_max_length(self):
        """Test: contraseña con 72 caracteres (límite bcrypt)"""
        # Crear una contraseña válida de exactamente 72 caracteres
        password = "A1!" + "a" * 69  # 3 + 69 = 72 caracteres
        data = self.get_valid_request_data(password)
        request = UserCompleteProfileRequest(**data)
        assert len(request.password) == 72
    
    def test_password_exceeds_byte_limit(self):
        """Test: contraseña que excede 72 bytes debe fallar"""
        # Crear una contraseña que exceda 72 bytes
        password = "A1!" + "a" * 70  # 73 caracteres
        data = self.get_valid_request_data(password)
        
        with pytest.raises(ValidationError) as exc_info:
            UserCompleteProfileRequest(**data)
        
        errors = exc_info.value.errors()
        assert any("bytes" in str(error.get("msg", "")).lower() for error in errors)
    
    def test_password_all_requirements_missing(self):
        """Test: contraseña sin ningún requisito debe fallar"""
        data = self.get_valid_request_data("simple")
        
        with pytest.raises(ValidationError) as exc_info:
            UserCompleteProfileRequest(**data)
        
        # Debería tener múltiples errores
        errors = exc_info.value.errors()
        assert len(errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
