"""
Servicio de tokenización de tarjetas.

Este servicio maneja la tokenización de tarjetas de crédito/débito.
Los tokens son de un solo uso y deben usarse inmediatamente para pagos.

Endpoints:
    POST /tokens - Crear un token
    GET /tokens/{token_id} - Obtener información de un token
    DELETE /tokens/{token_id} - Eliminar un token
"""

from typing import Any

from payway_sdk.adapters.base import BaseService
from payway_sdk.domain.models import CardData, CardTokenResponse


class TokenService(BaseService):
    """Servicio para tokenización de tarjetas."""

    async def create(
        self,
        card_data: CardData | dict[str, Any],
    ) -> CardTokenResponse:
        """
        Crea un token para una tarjeta.
        
        El token puede usarse luego para realizar pagos sin enviar
        los datos completos de la tarjeta.
        
        Args:
            card_data: Datos de la tarjeta (CardData o dict)
        
        Returns:
            CardTokenResponse con el token generado
        
        Raises:
            PaywayValidationError: Si los datos de la tarjeta son inválidos
            PaywayError: Para otros errores
        
        Example:
            >>> token = await client.tokens.create(CardData(
            ...     card_number="4111111111111111",
            ...     card_expiration_month="12",
            ...     card_expiration_year="25",
            ...     security_code="123",
            ...     card_holder=CardHolder(name="Juan Perez")
            ... ))
            >>> print(token.id)
        """
        if isinstance(card_data, CardData):
            payload = card_data.model_dump(mode="json", by_alias=True, exclude_none=True)
        else:
            # Validar datos si vienen como dict
            validated = CardData.model_validate(card_data)
            payload = validated.model_dump(mode="json", by_alias=True, exclude_none=True)

        self._logger.info(
            "Creando token de tarjeta",
            bin=payload.get("card_number", "")[:6],
        )

        response = await self._http.post(
            "/tokens",
            json=payload,
            use_private_key=False,  # Tokenización usa API key pública
        )

        result = CardTokenResponse.model_validate(response)
        
        self._logger.info(
            "Token creado exitosamente",
            token_id=result.id,
            bin=result.bin,
        )

        return result

    async def get(self, token_id: str) -> CardTokenResponse:
        """
        Obtiene información de un token existente.
        
        Args:
            token_id: ID del token
        
        Returns:
            CardTokenResponse con la información del token
        
        Raises:
            PaywayNotFoundError: Si el token no existe
        """
        self._logger.debug("Obteniendo información del token", token_id=token_id)
        
        response = await self._http.get(f"/tokens/{token_id}")
        
        return CardTokenResponse.model_validate(response)

    async def delete(self, token_id: str) -> bool:
        """
        Elimina un token.
        
        Args:
            token_id: ID del token a eliminar
        
        Returns:
            True si se eliminó correctamente
        
        Raises:
            PaywayNotFoundError: Si el token no existe
        """
        self._logger.info("Eliminando token", token_id=token_id)
        
        await self._http.delete(f"/tokens/{token_id}")
        
        self._logger.info("Token eliminado", token_id=token_id)
        return True

    # Métodos síncronos

    def create_sync(
        self,
        card_data: CardData | dict[str, Any],
    ) -> CardTokenResponse:
        """Versión síncrona de create()."""
        if isinstance(card_data, CardData):
            payload = card_data.model_dump(mode="json", by_alias=True, exclude_none=True)
        else:
            validated = CardData.model_validate(card_data)
            payload = validated.model_dump(mode="json", by_alias=True, exclude_none=True)

        self._logger.info(
            "Creando token de tarjeta (sync)",
            bin=payload.get("card_number", "")[:6],
        )

        response = self._http.post_sync(
            "/tokens",
            json=payload,
            use_private_key=False,
        )

        return CardTokenResponse.model_validate(response)

    def get_sync(self, token_id: str) -> CardTokenResponse:
        """Versión síncrona de get()."""
        response = self._http.get_sync(f"/tokens/{token_id}")
        return CardTokenResponse.model_validate(response)
