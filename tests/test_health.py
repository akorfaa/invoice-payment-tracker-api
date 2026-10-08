from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app


def _broken_db():
    raise RuntimeError("database is down")
    yield  # makes this a generator, like the real get_db


def test_liveness_check_works_even_when_the_database_is_down(client):
    app.dependency_overrides[get_db] = _broken_db
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_deep_health_check_fails_when_the_database_is_down():
    app.dependency_overrides[get_db] = _broken_db
    quiet_client = TestClient(app, raise_server_exceptions=False)
    response = quiet_client.get("/health")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"