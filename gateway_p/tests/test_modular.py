from fastapi.testclient import TestClient
from app.api_server.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "api_server"

def test_payments_module_loaded():
    response = client.get("/payments/")
    assert response.status_code == 200

def test_kyc_module_loaded():
    response = client.get("/kyc/")
    assert response.status_code == 200
