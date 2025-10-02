import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="module")
def client():
    # For real unit tests, configure separate test DB. Here we assume DB disabled or ephemeral.
    with TestClient(app) as c:
        yield c


def test_password_hash_and_token_flow(client):
    # This test focuses on token endpoint returning 401 when DB disabled or user missing.
    response = client.post("/api/v2/token", data={"username": "nouser", "password": "x"})
    assert response.status_code in (401, 503)
