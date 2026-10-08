"""Smoke test for a deployed copy of the API.

Usage:  python scripts/smoke_test_live.py https://your-service.onrender.com
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

BASE_URL = sys.argv[1].rstrip("/")
EMAIL = f"smoke_{int(time.time())}@example.com"
PASSWORD = "smoke-test-pass-123"


def call(method, path, body=None, form=None, token=None):
    headers = {}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        # Long timeout: a sleeping free-tier service can take about a minute to wake up.
        with urllib.request.urlopen(request, timeout=90) as response:
            raw = response.read()
            return response.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as error:
        raw = error.read()
        return error.code, (json.loads(raw) if raw else None)


def check(label, actual, expected):
    passed = actual == expected
    print(f"[{'PASS' if passed else 'FAIL'}] {label}: got {actual!r}, expected {expected!r}")
    if not passed:
        sys.exit(1)


print(f"Testing {BASE_URL} (the first request may take up to a minute)...")

status, _ = call("GET", "/health/live")
check("GET /health/live", status, 200)

status, body = call("GET", "/health")
check("GET /health (database reachable)", (status, body["database"]), (200, "connected"))

status, _ = call("POST", "/auth/register", body={"email": EMAIL, "password": PASSWORD})
check("register a new user", status, 201)

status, body = call("POST", "/auth/register", body={"email": EMAIL, "password": PASSWORD})
check("register the same email again", (status, body["error"]["code"]), (409, "conflict"))

status, body = call("POST", "/auth/login", form={"username": EMAIL, "password": PASSWORD})
check("log in", status, 200)
token = body["access_token"]

status, _ = call("GET", "/users/me", token=token)
check("GET /users/me with a token", status, 200)

status, _ = call("GET", "/clients/")
check("GET /clients/ without a token", status, 401)

status, client = call("POST", "/clients/", body={"name": "Smoke Test Client"}, token=token)
check("create a client", status, 201)

due = (date.today() + timedelta(days=30)).isoformat()
status, invoice = call(
    "POST",
    "/invoices/",
    body={"client_id": client["id"], "amount": "100.00", "description": "Smoke test", "due_date": due},
    token=token,
)
check("create a 100.00 invoice", status, 201)
payments_path = f"/invoices/{invoice['id']}/payments"

status, _ = call("POST", payments_path, body={"amount": "40.00"}, token=token)
check("pay 40.00", status, 201)

status, current = call("GET", f"/invoices/{invoice['id']}", token=token)
check("invoice is now partially_paid", current["status"], "partially_paid")

status, _ = call("POST", payments_path, body={"amount": "70.00"}, token=token)
check("overpayment (70.00 on a 60.00 balance) is rejected", status, 409)

status, _ = call("POST", payments_path, body={"amount": "60.00"}, token=token)
check("pay the remaining 60.00", status, 201)

status, current = call("GET", f"/invoices/{invoice['id']}", token=token)
check("invoice is now paid", current["status"], "paid")

status, body = call("GET", "/invoices/999999", token=token)
check("missing invoice returns the error envelope", (status, body["error"]["code"]), (404, "not_found"))

print("\nAll checks passed. The deployed API works end to end.")