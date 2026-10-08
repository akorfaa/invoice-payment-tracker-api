import os
from pathlib import Path

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app import models  # noqa: F401  (imported so Base knows about every table)
from app.database import Base, get_db
from app.main import app

TEST_DB_NAME = "invoice_tracker_test"
LOCAL_PG_DATA_DIR = Path(__file__).resolve().parent.parent / ".pgdata"


def _start_local_postgres():
    """Start a Postgres that lives in ./.pgdata (no install, no admin rights).

    Returns the server object (keep it referenced so it keeps running) and the
    URL of the test database inside it.
    """
    import pgserver  # imported here so it's only needed when we actually use it

    server = pgserver.get_server(LOCAL_PG_DATA_DIR)
    admin_url = make_url(server.get_uri())

    # CREATE DATABASE cannot run inside a transaction, hence AUTOCOMMIT.
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": TEST_DB_NAME}
        ).scalar()
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin_engine.dispose()

    return server, admin_url.set(database=TEST_DB_NAME)


@pytest.fixture(scope="session")
def engine():
    """Runs once per test run: get a test database and build a fresh schema in it."""
    explicit_url = os.getenv("TEST_DATABASE_URL")
    if explicit_url:
        server, test_url = None, make_url(explicit_url)
    else:
        server, test_url = _start_local_postgres()

    # Safety rail: the lines below DROP every table, so only ever run them
    # against a database whose name says it's for testing.
    assert test_url.database.endswith("_test"), (
        f"Refusing to run: test database name must end with '_test', got {test_url.database!r}"
    )

    test_engine = create_engine(test_url)
    try:
        test_engine.connect().close()
    except OperationalError as error:
        pytest.exit(f"Cannot reach the test database.\nUnderlying error: {error.orig}", returncode=1)

    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()
    # `server` is still referenced here, so the local Postgres stays up for the
    # whole test run and shuts down when the run ends.


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