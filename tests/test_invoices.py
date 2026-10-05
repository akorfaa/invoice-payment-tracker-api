from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _auth_headers(email: str, password: str = "testpass123") -> dict:
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", data={"username": email, "password": password})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_client(headers: dict, name: str = "Test Client") -> int:
    return client.post("/clients/", json={"name": name}, headers=headers).json()["id"]


def _invoice_payload(client_id: int, **overrides) -> dict:
    payload = {
        "client_id": client_id,
        "amount": "250.00",
        "description": "Website design",
        "issue_date": date.today().isoformat(),
        "due_date": (date.today() + timedelta(days=30)).isoformat(),
    }
    payload.update(overrides)
    return payload


def _create_invoice(headers: dict, client_id: int, **overrides) -> dict:
    response = client.post("/invoices/", json=_invoice_payload(client_id, **overrides), headers=headers)
    assert response.status_code == 201
    return response.json()


def test_create_invoice():
    headers = _auth_headers("invoice_user1@example.com")
    cid = _create_client(headers)
    body = _create_invoice(headers, cid)
    assert Decimal(body["amount"]) == Decimal("250.00")
    assert body["status"] == "unpaid"
    assert body["is_overdue"] is False


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount": "0"},
        {"amount": "-5.00"},
        {"amount": "10.123"},
        {"description": ""},
        {"issue_date": "2020-02-01", "due_date": "2020-01-01"},
    ],
)
def test_invoice_validation_rejects_bad_input(overrides):
    headers = _auth_headers("invoice_user2@example.com")
    cid = _create_client(headers)
    response = client.post("/invoices/", json=_invoice_payload(cid, **overrides), headers=headers)
    assert response.status_code == 422


def test_past_due_invoice_is_overdue():
    headers = _auth_headers("invoice_user3@example.com")
    cid = _create_client(headers)
    body = _create_invoice(headers, cid, issue_date="2020-01-01", due_date="2020-01-31")
    assert body["status"] == "unpaid"
    assert body["is_overdue"] is True


def test_cannot_create_invoice_for_another_users_client():
    headers_a = _auth_headers("invoice_user_a1@example.com")
    headers_b = _auth_headers("invoice_user_b1@example.com")
    client_a = _create_client(headers_a)
    response = client.post("/invoices/", json=_invoice_payload(client_a), headers=headers_b)
    assert response.status_code == 404


def test_list_only_shows_own_invoices_and_filters_by_client():
    headers_a = _auth_headers("invoice_user_a2@example.com")
    headers_b = _auth_headers("invoice_user_b2@example.com")
    a_client_1 = _create_client(headers_a, "A1")
    a_client_2 = _create_client(headers_a, "A2")
    _create_invoice(headers_a, a_client_1)
    _create_invoice(headers_a, a_client_2)

    filtered = client.get(f"/invoices/?client_id={a_client_1}", headers=headers_a).json()
    assert len(filtered) == 1
    assert filtered[0]["client_id"] == a_client_1

    others_view = client.get(f"/invoices/?client_id={a_client_1}", headers=headers_b)
    assert others_view.status_code == 200
    assert others_view.json() == []


def test_cannot_touch_another_users_invoice():
    headers_a = _auth_headers("invoice_user_a3@example.com")
    headers_b = _auth_headers("invoice_user_b3@example.com")
    cid = _create_client(headers_a)
    invoice = _create_invoice(headers_a, cid, description="Original")
    url = f"/invoices/{invoice['id']}"

    assert client.get(url, headers=headers_b).status_code == 404
    assert client.put(url, json={"description": "Hacked"}, headers=headers_b).status_code == 404
    assert client.delete(url, headers=headers_b).status_code == 404

    still_there = client.get(url, headers=headers_a)
    assert still_there.status_code == 200
    assert still_there.json()["description"] == "Original"


def test_update_invoice():
    headers = _auth_headers("invoice_user4@example.com")
    cid = _create_client(headers)
    invoice = _create_invoice(headers, cid)
    url = f"/invoices/{invoice['id']}"

    ok = client.put(url, json={"amount": "300.00"}, headers=headers)
    assert ok.status_code == 200
    assert Decimal(ok.json()["amount"]) == Decimal("300.00")

    early_due = client.put(url, json={"due_date": "2000-01-01"}, headers=headers)
    assert early_due.status_code == 422

    null_amount = client.put(url, json={"amount": None}, headers=headers)
    assert null_amount.status_code == 422


def test_delete_invoice():
    headers = _auth_headers("invoice_user5@example.com")
    cid = _create_client(headers)
    invoice = _create_invoice(headers, cid)
    url = f"/invoices/{invoice['id']}"

    assert client.delete(url, headers=headers).status_code == 204
    assert client.get(url, headers=headers).status_code == 404


def test_cannot_delete_client_that_has_invoices():
    headers = _auth_headers("invoice_user6@example.com")
    cid = _create_client(headers)
    invoice = _create_invoice(headers, cid)

    assert client.delete(f"/clients/{cid}", headers=headers).status_code == 409

    client.delete(f"/invoices/{invoice['id']}", headers=headers)
    assert client.delete(f"/clients/{cid}", headers=headers).status_code == 204