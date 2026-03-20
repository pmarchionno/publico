"""Tests para endpoints de autenticacion"""
import pytest
from httpx import AsyncClient
from app.api_server.main import app


def _extract_token(verification_link: str) -> str:
    return verification_link.split("token=")[-1]


@pytest.mark.asyncio
async def test_register_verify_complete_and_login():
    """Test full registration flow"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/auth/register",
            json={"email": "test@example.com"},
        )
        assert response.status_code == 200
        verification_link = response.json()["verification_link"]

        token = _extract_token(verification_link)
        verify_resp = await client.get(f"/auth/verify-email?token={token}")
        assert verify_resp.status_code == 200

        complete_resp = await client.post(
            "/auth/register/complete",
            json={
                "email": "test@example.com",
                "password": "securepass123",
                "dni": "12345678",
                "first_name": "Test",
                "last_name": "User",
                "gender": "masculino",
                "cuit_cuil": "20123456789",
                "phone": "+5491112345678",
                "nationality": "Argentina",
                "occupation": "Developer",
                "marital_status": "Single",
                "location": "Buenos Aires",
            },
        )
        assert complete_resp.status_code == 200

        login_resp = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "securepass123"},
        )
        assert login_resp.status_code == 200
        data = login_resp.json()
        assert "access_token" in data


@pytest.mark.asyncio
async def test_register_duplicate_verified_email():
    """Test duplicate verified email"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/auth/register",
            json={"email": "dup@example.com"},
        )
        token = _extract_token(response.json()["verification_link"])
        await client.get(f"/auth/verify-email?token={token}")

        response2 = await client.post(
            "/auth/register",
            json={"email": "dup@example.com"},
        )
        assert response2.status_code == 400


@pytest.mark.asyncio
async def test_login_requires_password_and_verification():
    """Login should fail before completion"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post(
            "/auth/register",
            json={"email": "nologin@example.com"},
        )
        response = await client.post(
            "/auth/login",
            json={"email": "nologin@example.com", "password": "securepass123"},
        )
        assert response.status_code == 401
