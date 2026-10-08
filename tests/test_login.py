from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.security import ALGORITHM, SECRET_KEY

EMAIL = "login_test@example.com"
PASSWORD = "correctpassword"


@pytest.fixture()
def registered_user(client):
    response = client.post("/auth/register", json={"email": EMAIL, "password": PASSWORD})
    assert response.status_code == 201


def _token(subject: str, lifetime: timedelta) -> str:
    payload = {"sub": subject, "exp": datetime.now(timezone.utc) + lifetime}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def test_login_success(client, registered_user):
    response = client.post("/auth/login", data={"username": EMAIL, "password": PASSWORD})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password(client, registered_user):
    response = client.post("/auth/login", data={"username": EMAIL, "password": "wrongpassword"})
    assert response.status_code == 401


def test_login_unknown_email_gives_same_error_as_wrong_password(client, registered_user):
    wrong_password = client.post("/auth/login", data={"username": EMAIL, "password": "nope12345"})
    unknown_email = client.post(
        "/auth/login", data={"username": "nobody@example.com", "password": "nope12345"}
    )
    # Same status and same message: the API doesn't reveal which emails are registered.
    assert unknown_email.status_code == wrong_password.status_code == 401
    assert unknown_email.json() == wrong_password.json()


def test_protected_route_without_token(client):
    assert client.get("/users/me").status_code == 401


def test_protected_route_with_token(client, registered_user):
    login = client.post("/auth/login", data={"username": EMAIL, "password": PASSWORD})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == EMAIL


def test_garbage_token_is_rejected(client):
    response = client.get("/users/me", headers={"Authorization": "Bearer not.a.real.token"})
    assert response.status_code == 401


def test_expired_token_is_rejected(client, registered_user):
    expired = _token(EMAIL, timedelta(minutes=-1))
    response = client.get("/users/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


def test_valid_token_for_unknown_user_is_rejected(client):
    # Correctly signed and not expired, but nobody with this email exists
    # (think: an account that was deleted after the token was issued).
    ghost = _token("ghost@example.com", timedelta(minutes=5))
    response = client.get("/users/me", headers={"Authorization": f"Bearer {ghost}"})
    assert response.status_code == 401