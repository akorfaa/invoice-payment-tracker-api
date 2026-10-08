from datetime import date, datetime, timedelta, timezone

from jose import jwt

from app.security import ALGORITHM, SECRET_KEY


def test_root_and_health(client):
    assert client.get("/").status_code == 200
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "database": "connected"}


def test_update_client_changes_only_the_fields_sent(client, make_headers):
    headers = make_headers("edge_update@example.com")
    created = client.post(
        "/clients/", json={"name": "Old Name", "phone": "0201234567"}, headers=headers
    ).json()

    response = client.put(f"/clients/{created['id']}", json={"name": "New Name"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["phone"] == "0201234567"  # not sent, so not touched

    fetched = client.get(f"/clients/{created['id']}", headers=headers).json()
    assert fetched["name"] == "New Name"


def test_deleting_a_payment_that_does_not_exist_returns_404(client, make_headers):
    headers = make_headers("edge_payment@example.com")
    client_id = client.post("/clients/", json={"name": "C"}, headers=headers).json()["id"]
    invoice = client.post(
        "/invoices/",
        json={
            "client_id": client_id,
            "amount": "100.00",
            "description": "Consulting",
            "due_date": (date.today() + timedelta(days=30)).isoformat(),
        },
        headers=headers,
    ).json()

    response = client.delete(f"/invoices/{invoice['id']}/payments/999999", headers=headers)
    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Payment not found"


def test_validly_signed_token_without_a_subject_is_rejected(client):
    payload = {"exp": datetime.now(timezone.utc) + timedelta(minutes=5)}  # no "sub" claim
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401