from datetime import date, timedelta
from decimal import Decimal

import pytest

# Every request Bob can try against Alice's records. The {placeholders} are
# filled with the real IDs of Alice's data when the test runs.
ATTACKS = [
    ("GET", "/clients/{client_id}", None),
    ("PUT", "/clients/{client_id}", {"name": "Hacked"}),
    ("DELETE", "/clients/{client_id}", None),
    ("GET", "/invoices/{invoice_id}", None),
    ("PUT", "/invoices/{invoice_id}", {"description": "Hacked"}),
    ("DELETE", "/invoices/{invoice_id}", None),
    ("GET", "/invoices/{invoice_id}/payments", None),
    ("POST", "/invoices/{invoice_id}/payments", {"amount": "10.00"}),
    ("DELETE", "/invoices/{invoice_id}/payments/{payment_id}", None),
]

# Every protected endpoint, called with NO token at all.
PROTECTED_ENDPOINTS = [
    ("GET", "/users/me", None),
    ("GET", "/clients/", None),
    ("POST", "/clients/", {"name": "x"}),
    ("GET", "/clients/1", None),
    ("PUT", "/clients/1", {"name": "x"}),
    ("DELETE", "/clients/1", None),
    ("GET", "/invoices/", None),
    ("POST", "/invoices/", {"client_id": 1, "amount": "1.00", "description": "x", "due_date": "2030-01-01"}),
    ("GET", "/invoices/1", None),
    ("PUT", "/invoices/1", {"description": "x"}),
    ("DELETE", "/invoices/1", None),
    ("GET", "/invoices/1/payments", None),
    ("POST", "/invoices/1/payments", {"amount": "1.00"}),
    ("DELETE", "/invoices/1/payments/1", None),
]


@pytest.fixture()
def alice(client, make_headers):
    """Alice owns one client, one invoice (100.00) and one payment (40.00)."""
    headers = make_headers("alice@example.com")

    created_client = client.post("/clients/", json={"name": "Alice Client"}, headers=headers)
    assert created_client.status_code == 201

    invoice = client.post(
        "/invoices/",
        json={
            "client_id": created_client.json()["id"],
            "amount": "100.00",
            "description": "Consulting work",
            "due_date": (date.today() + timedelta(days=30)).isoformat(),
        },
        headers=headers,
    )
    assert invoice.status_code == 201

    payment = client.post(
        f"/invoices/{invoice.json()['id']}/payments", json={"amount": "40.00"}, headers=headers
    )
    assert payment.status_code == 201

    return {
        "headers": headers,
        "client_id": created_client.json()["id"],
        "invoice_id": invoice.json()["id"],
        "payment_id": payment.json()["id"],
    }


@pytest.fixture()
def bob_headers(make_headers):
    return make_headers("bob@example.com")


def test_bob_cannot_read_change_or_delete_anything_of_alices(client, alice, bob_headers):
    """Bob tries every endpoint against Alice's records. All must be 404, and nothing may change."""
    wrong = []
    for method, path, body in ATTACKS:
        url = path.format(**alice)
        response = client.request(method, url, json=body, headers=bob_headers)
        # 404, not 403: we never confirm to Bob that Alice's record exists.
        if response.status_code != 404:
            wrong.append(f"{method} {url} returned {response.status_code}, expected 404")
    assert not wrong, "Cross-user access was NOT blocked:\n" + "\n".join(wrong)

    # A 404 isn't enough on its own: prove none of the attacks quietly changed anything.
    headers = alice["headers"]
    alice_client = client.get(f"/clients/{alice['client_id']}", headers=headers)
    assert alice_client.status_code == 200
    assert alice_client.json()["name"] == "Alice Client"

    invoice = client.get(f"/invoices/{alice['invoice_id']}", headers=headers).json()
    assert invoice["description"] == "Consulting work"
    assert invoice["status"] == "partially_paid"
    assert Decimal(invoice["amount_paid"]) == Decimal("40.00")

    payments = client.get(f"/invoices/{alice['invoice_id']}/payments", headers=headers).json()
    assert len(payments) == 1


def test_bob_cannot_create_an_invoice_under_alices_client(client, alice, bob_headers):
    payload = {
        "client_id": alice["client_id"],
        "amount": "10.00",
        "description": "Sneaky",
        "due_date": (date.today() + timedelta(days=30)).isoformat(),
    }
    response = client.post("/invoices/", json=payload, headers=bob_headers)
    assert response.status_code == 404

    alices_invoices = client.get("/invoices/", headers=alice["headers"]).json()
    assert len(alices_invoices) == 1


def test_bobs_lists_never_contain_alices_records(client, alice, bob_headers):
    assert client.get("/clients/", headers=bob_headers).json() == []
    assert client.get("/invoices/", headers=bob_headers).json() == []
    filtered = client.get(f"/invoices/?client_id={alice['client_id']}", headers=bob_headers)
    assert filtered.status_code == 200
    assert filtered.json() == []


def test_every_protected_endpoint_requires_a_token(client):
    wrong = []
    for method, path, body in PROTECTED_ENDPOINTS:
        response = client.request(method, path, json=body)
        if response.status_code != 401:
            wrong.append(f"{method} {path} returned {response.status_code}, expected 401")
    assert not wrong, "Endpoints reachable without a token:\n" + "\n".join(wrong)