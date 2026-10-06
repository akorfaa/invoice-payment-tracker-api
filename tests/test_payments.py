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


def _create_client(headers: dict) -> int:
    return client.post("/clients/", json={"name": "Test Client"}, headers=headers).json()["id"]


def _create_invoice(headers: dict, client_id: int, amount: str = "100.00", **overrides) -> dict:
    payload = {
        "client_id": client_id,
        "amount": amount,
        "description": "Consulting",
        "issue_date": date.today().isoformat(),
        "due_date": (date.today() + timedelta(days=30)).isoformat(),
    }
    payload.update(overrides)
    response = client.post("/invoices/", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


def _setup(email: str, amount: str = "100.00"):
    headers = _auth_headers(email)
    invoice = _create_invoice(headers, _create_client(headers), amount=amount)
    return headers, invoice["id"]


def _pay(headers: dict, invoice_id: int, amount: str, **extra):
    return client.post(
        f"/invoices/{invoice_id}/payments",
        json={"amount": amount, **extra},
        headers=headers,
    )


def _get_invoice(headers: dict, invoice_id: int) -> dict:
    return client.get(f"/invoices/{invoice_id}", headers=headers).json()


def test_partial_payment_marks_invoice_partially_paid():
    headers, invoice_id = _setup("payment_user1@example.com")
    response = _pay(headers, invoice_id, "40.00", method="mobile_money", reference="MOMO-123")
    assert response.status_code == 201
    assert Decimal(response.json()["amount"]) == Decimal("40.00")

    invoice = _get_invoice(headers, invoice_id)
    assert invoice["status"] == "partially_paid"
    assert Decimal(invoice["amount_paid"]) == Decimal("40.00")
    assert Decimal(invoice["balance_due"]) == Decimal("60.00")


def test_installments_add_up_to_paid():
    headers, invoice_id = _setup("payment_user2@example.com")
    assert _pay(headers, invoice_id, "40.00").status_code == 201
    assert _pay(headers, invoice_id, "60.00").status_code == 201

    invoice = _get_invoice(headers, invoice_id)
    assert invoice["status"] == "paid"
    assert Decimal(invoice["balance_due"]) == Decimal("0")

    listed = client.get(f"/invoices/{invoice_id}/payments", headers=headers).json()
    assert [Decimal(p["amount"]) for p in listed] == [Decimal("40.00"), Decimal("60.00")]


def test_overpayment_rejected():
    headers, invoice_id = _setup("payment_user3@example.com")
    assert _pay(headers, invoice_id, "100.01").status_code == 409
    assert _pay(headers, invoice_id, "60.00").status_code == 201
    assert _pay(headers, invoice_id, "50.00").status_code == 409

    invoice = _get_invoice(headers, invoice_id)
    assert invoice["status"] == "partially_paid"
    assert Decimal(invoice["amount_paid"]) == Decimal("60.00")


def test_cannot_pay_an_already_paid_invoice():
    headers, invoice_id = _setup("payment_user4@example.com")
    assert _pay(headers, invoice_id, "100.00").status_code == 201
    assert _pay(headers, invoice_id, "1.00").status_code == 409


@pytest.mark.parametrize(
    "extra",
    [
        {"amount": "0"},
        {"amount": "-5.00"},
        {"amount": "1.234"},
        {"paid_on": (date.today() + timedelta(days=1)).isoformat()},
        {"paid_on": (date.today() - timedelta(days=1)).isoformat()},
        {"method": "bitcoin"},
    ],
)
def test_payment_validation_rejects_bad_input(extra):
    headers, invoice_id = _setup("payment_user5@example.com")
    body = {"amount": "10.00", **extra}
    response = client.post(f"/invoices/{invoice_id}/payments", json=body, headers=headers)
    assert response.status_code == 422


def test_deleting_a_payment_recalculates_status():
    headers, invoice_id = _setup("payment_user6@example.com")
    first = _pay(headers, invoice_id, "40.00").json()
    second = _pay(headers, invoice_id, "60.00").json()
    assert _get_invoice(headers, invoice_id)["status"] == "paid"

    url = f"/invoices/{invoice_id}/payments"
    assert client.delete(f"{url}/{second['id']}", headers=headers).status_code == 204
    assert _get_invoice(headers, invoice_id)["status"] == "partially_paid"

    assert client.delete(f"{url}/{first['id']}", headers=headers).status_code == 204
    invoice = _get_invoice(headers, invoice_id)
    assert invoice["status"] == "unpaid"
    assert Decimal(invoice["balance_due"]) == Decimal("100.00")


def test_cannot_touch_another_users_payments():
    headers_a, invoice_id = _setup("payment_user_a@example.com")
    headers_b = _auth_headers("payment_user_b@example.com")
    payment = _pay(headers_a, invoice_id, "10.00").json()
    url = f"/invoices/{invoice_id}/payments"

    assert _pay(headers_b, invoice_id, "10.00").status_code == 404
    assert client.get(url, headers=headers_b).status_code == 404
    assert client.delete(f"{url}/{payment['id']}", headers=headers_b).status_code == 404

    assert len(client.get(url, headers=headers_a).json()) == 1


def test_cannot_delete_invoice_that_has_payments():
    headers, invoice_id = _setup("payment_user7@example.com")
    payment = _pay(headers, invoice_id, "10.00").json()

    assert client.delete(f"/invoices/{invoice_id}", headers=headers).status_code == 409

    client.delete(f"/invoices/{invoice_id}/payments/{payment['id']}", headers=headers)
    assert client.delete(f"/invoices/{invoice_id}", headers=headers).status_code == 204


def test_invoice_amount_changes_respect_payments():
    headers, invoice_id = _setup("payment_user8@example.com")
    _pay(headers, invoice_id, "60.00")
    url = f"/invoices/{invoice_id}"

    assert client.put(url, json={"amount": "50.00"}, headers=headers).status_code == 409

    exact = client.put(url, json={"amount": "60.00"}, headers=headers)
    assert exact.status_code == 200
    assert exact.json()["status"] == "paid"

    raised = client.put(url, json={"amount": "200.00"}, headers=headers)
    assert raised.json()["status"] == "partially_paid"
    assert Decimal(raised.json()["balance_due"]) == Decimal("140.00")


def test_overdue_only_applies_while_a_balance_remains():
    headers = _auth_headers("payment_user9@example.com")
    invoice = _create_invoice(
        headers, _create_client(headers), issue_date="2020-01-01", due_date="2020-01-31"
    )
    assert invoice["is_overdue"] is True

    _pay(headers, invoice["id"], "10.00")
    assert _get_invoice(headers, invoice["id"])["is_overdue"] is True

    _pay(headers, invoice["id"], "90.00")
    assert _get_invoice(headers, invoice["id"])["is_overdue"] is False