from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _auth_headers(email: str, password: str = "testpass123") -> dict:
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", data={"username": email, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_client():
    headers = _auth_headers("client_test_user1@example.com")
    response = client.post("/clients/", json={"name": "Acme Corp", "email": "acme@example.com"}, headers=headers)
    assert response.status_code == 201
    assert response.json()["name"] == "Acme Corp"


def test_list_clients_only_shows_own():
    headers_a = _auth_headers("client_test_user_a@example.com")
    headers_b = _auth_headers("client_test_user_b@example.com")

    client.post("/clients/", json={"name": "A's Client"}, headers=headers_a)
    client.post("/clients/", json={"name": "B's Client"}, headers=headers_b)

    response = client.get("/clients/", headers=headers_a)
    names = [c["name"] for c in response.json()]
    assert "A's Client" in names
    assert "B's Client" not in names


def test_cannot_view_another_users_client():
    headers_a = _auth_headers("client_test_user_c@example.com")
    headers_b = _auth_headers("client_test_user_d@example.com")

    created = client.post("/clients/", json={"name": "Secret Client"}, headers=headers_a)
    client_id = created.json()["id"]

    response = client.get(f"/clients/{client_id}", headers=headers_b)
    assert response.status_code == 404


def test_cannot_update_another_users_client():
    headers_a = _auth_headers("client_test_user_e@example.com")
    headers_b = _auth_headers("client_test_user_f@example.com")

    created = client.post("/clients/", json={"name": "Original Name"}, headers=headers_a)
    client_id = created.json()["id"]

    response = client.put(f"/clients/{client_id}", json={"name": "Hacked Name"}, headers=headers_b)
    assert response.status_code == 404


def test_cannot_delete_another_users_client():
    headers_a = _auth_headers("client_test_user_g@example.com")
    headers_b = _auth_headers("client_test_user_h@example.com")

    created = client.post("/clients/", json={"name": "Protected Client"}, headers=headers_a)
    client_id = created.json()["id"]

    response = client.delete(f"/clients/{client_id}", headers=headers_b)
    assert response.status_code == 404