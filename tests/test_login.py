from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _register_test_user():
    client.post(
        "/auth/register",
        json={"email": "login_test@example.com", "password": "correctpassword"},
    )


def test_login_success():
    _register_test_user()
    response = client.post(
        "/auth/login",
        data={"username": "login_test@example.com", "password": "correctpassword"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password():
    response = client.post(
        "/auth/login",
        data={"username": "login_test@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_protected_route_without_token():
    response = client.get("/users/me")
    assert response.status_code == 401


def test_protected_route_with_token():
    login_response = client.post(
        "/auth/login",
        data={"username": "login_test@example.com", "password": "correctpassword"},
    )
    token = login_response.json()["access_token"]
    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "login_test@example.com"