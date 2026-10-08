"""Checks that an embedded PostgreSQL can run on this machine (no admin, no installer)."""
from pathlib import Path

import pgserver
from sqlalchemy import create_engine, text

data_dir = Path(__file__).resolve().parent.parent / ".pgdata"

print("Starting embedded PostgreSQL (the first run unpacks files, so it can take a minute)...")
server = pgserver.get_server(data_dir)
uri = server.get_uri()
print("Connection address:", uri)

engine = create_engine(uri)
with engine.connect() as connection:
    print(connection.execute(text("SELECT version()")).scalar())
print("OK - embedded PostgreSQL works on this machine.")