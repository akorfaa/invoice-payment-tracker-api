from sqlalchemy import text


def test_database_is_empty_at_the_start_of_every_test(db_connection):
    for table in ("users", "clients", "invoices", "payments"):
        count = db_connection.execute(text(f"SELECT count(*) FROM {table}")).scalar()
        assert count == 0, f"{table} has {count} leftover rows from an earlier test"