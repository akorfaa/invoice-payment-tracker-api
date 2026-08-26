from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_register_new_user():
    response = client.post(
        "/auth/register",
        json={"email":"pytest_user1@example.com", "password":"testpass123"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "pytest_user1@example.com"
    assert "hashed_password" not in body
    assert "password" not in body

def test_register_duplicate_email_rejected():
    client.post(
        "/auth/register",
        json={"email": "pytest_user2@example.com", "password": "testpass123"},
    )
    response = client.post(
        "/auth/register",
        json={"email":"pytest_user2@example.com", "password": "testpass123"}
    )
    assert response.status_code == 400