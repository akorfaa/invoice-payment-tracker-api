import os

import psycopg2
from dotenv import load_dotenv
from sqlalchemy.engine import make_url

load_dotenv()

TEST_DB_NAME = "invoice_tracker_test"  # must match tests/conftest.py

dev_url = make_url(os.environ["DATABASE_URL"])
# psycopg2 wants a plain "postgresql://" address, not SQLAlchemy's "postgresql+psycopg2://"
dsn = dev_url.set(drivername="postgresql").render_as_string(hide_password=False)

connection = psycopg2.connect(dsn)
connection.autocommit = True  # CREATE DATABASE cannot run inside a transaction
with connection.cursor() as cursor:
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB_NAME,))
    if cursor.fetchone():
        print(f"Database {TEST_DB_NAME} already exists - nothing to do.")
    else:
        cursor.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
        print(f"Created database {TEST_DB_NAME}.")
connection.close()