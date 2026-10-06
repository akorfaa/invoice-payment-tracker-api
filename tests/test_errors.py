import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.errors import register_error_handlers
from app.main import app

client = TestClient(app)


def _assert_error(response, status_code, code):
    """Every error in the API must look like {"error": {"code": ..., "message": ...}}."""
    assert response.status_code == status_code
    body = response.json()
    assert set(body.keys()) == {"error"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str)
    return body["error"]


def _auth_headers(email: str, password: str = "testpass123") -> dict:
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", data={"username": email, "password": password})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_unknown_route_returns_json_404():
    response = client.get("/this-route-does-not-exist")
    _assert_error(response, 404, "not_found")


def test_wrong_method_returns_json_405():
    response = client.delete("/health")
    _assert_error(response, 405, "method_not_allowed")


def test_missing_token_returns_401_and_keeps_www_authenticate_header():
    response = client.get("/users/me")
    _assert_error(response, 401, "unauthorized")
    assert response.headers["www-authenticate"] == "Bearer"


def test_validation_error_lists_each_bad_field():
    response = client.post("/auth/register", json={"email": "not-an-email", "password": "short"})
    error = _assert_error(response, 422, "validation_error")
    fields = [item["field"] for item in error["fields"]]
    assert "body.email" in fields
    assert "body.password" in fields


@pytest.mark.parametrize("password", ["a" * 73, "é" * 40])  # 73 bytes, and 80 bytes in 40 characters
def test_password_over_72_bytes_is_rejected_not_a_500(password):
    response = client.post(
        "/auth/register", json={"email": "long_pw@example.com", "password": password}
    )
    error = _assert_error(response, 422, "validation_error")
    assert error["fields"][0]["message"] == "password must be at most 72 bytes"


def test_login_with_overlong_password_returns_401_not_500():
    client.post(
        "/auth/register",
        json={"email": "login_long_pw@example.com", "password": "correctpassword"},
    )
    response = client.post(
        "/auth/login", data={"username": "login_long_pw@example.com", "password": "a" * 100}
    )
    _assert_error(response, 401, "unauthorized")


def test_login_with_unknown_user_uses_error_envelope():
    response = client.post(
        "/auth/login", data={"username": "nobody@example.com", "password": "whatever123"}
    )
    error = _assert_error(response, 401, "unauthorized")
    assert error["message"] == "Incorrect email or password"


def test_blank_client_name_is_rejected():
    headers = _auth_headers("errors_test_user@example.com")
    response = client.post("/clients/", json={"name": "   "}, headers=headers)
    error = _assert_error(response, 422, "validation_error")
    assert "body.name" in [item["field"] for item in error["fields"]]


# --- Crash handling, tested on a tiny throwaway app (no database needed) ---


def _make_crashy_app() -> FastAPI:
    mini = FastAPI()
    register_error_handlers(mini)

    @mini.get("/boom")
    def boom():
        raise RuntimeError("internal detail: the db password is hunter2")

    @mini.get("/duplicate")
    def duplicate():
        raise IntegrityError("INSERT INTO users ...", {}, Exception("duplicate key value"))

    return mini


# raise_server_exceptions=False makes TestClient behave like a real server:
# it returns the 500 response instead of re-raising the error into the test.
crashy_client = TestClient(_make_crashy_app(), raise_server_exceptions=False)


def test_unhandled_exception_returns_generic_500_without_leaking_details():
    response = crashy_client.get("/boom")
    _assert_error(response, 500, "internal_error")
    assert "hunter2" not in response.text
    assert "RuntimeError" not in response.text


def test_database_integrity_error_returns_409_without_leaking_sql():
    response = crashy_client.get("/duplicate")
    _assert_error(response, 409, "conflict")
    assert "INSERT" not in response.text
    assert "duplicate key" not in response.text