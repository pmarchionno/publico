"""Tests de integración para el servicio de tokens."""

import pytest
import respx
from httpx import Response

from payway_sdk import PaywayClient, CardData, CardHolder


@pytest.mark.asyncio
class TestTokenService:
    """Tests de integración para TokenService."""

    async def test_create_token(self, client, mock_api, sample_card_data, sample_token_response):
        """Crea un token exitosamente."""
        mock_api.post("/tokens").mock(
            return_value=Response(200, json=sample_token_response)
        )

        token = await client.tokens.create(sample_card_data)

        assert token.id == "token_abc123"
        assert token.bin == "411111"
        assert token.last_four_digits == "1111"

    async def test_create_token_with_model(self, client, mock_api, sample_token_response):
        """Crea un token usando el modelo CardData."""
        mock_api.post("/tokens").mock(
            return_value=Response(200, json=sample_token_response)
        )

        card = CardData(
            card_number="4111111111111111",
            card_expiration_month="12",
            card_expiration_year="25",
            security_code="123",
            card_holder=CardHolder(name="Juan Perez"),
        )

        token = await client.tokens.create(card)
        assert token.id == "token_abc123"

    async def test_get_token(self, client, mock_api, sample_token_response):
        """Obtiene información de un token."""
        mock_api.get("/tokens/token_abc123").mock(
            return_value=Response(200, json=sample_token_response)
        )

        token = await client.tokens.get("token_abc123")
        assert token.id == "token_abc123"

    async def test_delete_token(self, client, mock_api):
        """Elimina un token."""
        mock_api.delete("/tokens/token_abc123").mock(
            return_value=Response(200, json={})
        )

        result = await client.tokens.delete("token_abc123")
        assert result is True

    async def test_create_token_validation_error(self, client, mock_api):
        """Maneja error de validación."""
        mock_api.post("/tokens").mock(
            return_value=Response(400, json={
                "message": "Número de tarjeta inválido",
                "code": "invalid_card_number",
                "validation_errors": [
                    {"field": "card_number", "message": "Luhn check failed"}
                ]
            })
        )

        from payway_sdk import PaywayValidationError

        with pytest.raises(PaywayValidationError) as exc_info:
            await client.tokens.create({
                "card_number": "1234",  # Inválido
                "card_expiration_month": "12",
                "card_expiration_year": "25",
                "security_code": "123",
                "card_holder": {"name": "Test"},
            })

        assert exc_info.value.status_code == 400
