import os

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app import models  # noqa: F401  (imported so Base knows about every table)
from app.database import Base, get_db
from app.main import app

TEST_DB_NAME = "invoice_tracker_test"  # must match scripts/create_test_db.py


def _test_database_url():
    # app.database has already loaded .env by the time we get here.
    dev_url = make_url(os.environ["DATABASE_URL"])
    test_url = dev_url.set(database=TEST_DB_NAME)
    # Safety rails: the next fixture DROPS every table, so never let it
    # point at the real dev database.
    assert test_url.database != dev_url.database
    assert test_url.database.endswith("_test")
    return test_url


@pytest.fixture(scope="session")
def engine():
    """Runs once per test run: connect to the test DB and build a fresh schema."""
    test_engine = create_engine(_test_database_url())
    try:
        test_engine.connect().close()
    except OperationalError as error:
        pytest.exit(
            "Cannot reach the test database. Did you run: python scripts/create_test_db.py ?\n"
            f"Underlying error: {error.orig}",
            returncode=1,
        )
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture()
def db_connection(engine):
    """One connection and one outer transaction per test. Rolled back at the end."""
    connection = engine.connect()
    outer_transaction = connection.begin()
    yield connection
    outer_transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def use_test_database(db_connection):
    """autouse=True means EVERY test gets this automatically.

    It swaps the app's get_db for one bound to the test transaction. When the
    app calls db.commit() it only commits a savepoint, so the rollback above
    still wipes everything.
    """

    def get_test_db():
        session = Session(
            bind=db_connection,
            join_transaction_mode="create_savepoint",
            autoflush=False,  # same setting as the real SessionLocal
        )
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = get_test_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def fast_password_hashing(monkeypatch):
    """bcrypt is slow on purpose (cost 12). In tests, use the minimum cost (4).

    Production code is untouched. The monkeypatch is undone after each test.
    """
    real_gensalt = bcrypt.gensalt
    monkeypatch.setattr(
        bcrypt, "gensalt", lambda rounds=4, prefix=b"2b": real_gensalt(rounds=4, prefix=prefix)
    )


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def make_headers(client):
    """A factory: call make_headers("a@example.com") to get a logged-in user's auth headers."""

    def _make_headers(email: str, password: str = "testpass123") -> dict:
        registered = client.post("/auth/register", json={"email": email, "password": password})
        assert registered.status_code == 201, registered.text
        login = client.post("/auth/login", data={"username": email, "password": password})
        assert login.status_code == 200, login.text
        return {"Authorization": f"Bearer {login.json()['access_token']}"}

    return _make_headers