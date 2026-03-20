import httpx
import asyncio

async def test_connections():
    urls = [
        "https://www.google.com",
        "https://dashboard.bdcconecta.com/api/sandboxtest/healthcheck"
    ]
    
    for url in urls:
        try:
            print(f"\nProbando: {url}")
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(url, timeout=10.0)
                print(f"✅ Status: {response.status_code}")
                print(f"Response: {response.text[:100]}")
        except Exception as e:
            print(f"❌ Error: {type(e).__name__} - {str(e)}")

asyncio.run(test_connections())
