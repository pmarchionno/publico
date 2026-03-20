import httpx
import asyncio

async def test_connection():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://dashboard.bdcconecta.com/api/sandboxtest/healthcheck",
                headers={"accept": "application/json"},
                timeout=10.0
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {type(e).__name__} - {str(e)}")

asyncio.run(test_connection())
