"""Conexión a PostgreSQL: adaptador, selección de motor y esquema.

No hay servidor PostgreSQL en CI, así que el adaptador se ejercita contra un
SQLite real (que habla el mismo subconjunto de SQL que usa la app) y se
comprueba que el esquema de PostgreSQL no contiene sintaxis de SQLite.
"""

import sqlite3

import pytest

from app import db


class _FakeRaw:
    """Imita la parte de psycopg que usa el adaptador (devuelve dicts)."""

    def __init__(self, path):
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self.rolled_back = 0
        self.committed = 0

    def execute(self, sql, params=()):
        return self._conn.execute(sql.replace("%s", "?"), params)

    def executemany(self, sql, seq):
        return self._conn.executemany(sql.replace("%s", "?"), seq)

    def commit(self):
        self.committed += 1
        self._conn.commit()

    def rollback(self):
        self.rolled_back += 1
        self._conn.rollback()

    def close(self):
        self._conn.close()


@pytest.fixture()
def pg_conn(tmp_path):
    raw = _FakeRaw(tmp_path / "fake_pg.db")
    conn = db._PostgresConnection(raw)
    # BIGSERIAL no es una clave autoincremental en SQLite: solo para el doble.
    for statement in db._pg_statements(db.PG_SCHEMA):
        conn.execute(statement.replace("BIGSERIAL", "INTEGER"))
    conn.commit()
    yield conn
    conn.close()


def test_placeholders_are_translated():
    assert db._PostgresConnection._sql(
        "SELECT * FROM users WHERE email=? AND token=?") == \
        "SELECT * FROM users WHERE email=%s AND token=%s"


def test_pg_schema_has_no_sqlite_syntax():
    for forbidden in ("AUTOINCREMENT", "REAL ", "sqlite_"):
        assert forbidden not in db.PG_SCHEMA
    assert "BIGSERIAL" in db.PG_SCHEMA
    assert "DOUBLE PRECISION" in db.PG_SCHEMA


def test_connect_uses_sqlite_without_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert db.using_postgres() is False
    conn = db.connect()
    try:
        assert isinstance(conn, sqlite3.Connection)
    finally:
        conn.close()


def test_connect_uses_postgres_when_database_url_set(monkeypatch):
    sentinel = object()
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.setattr(db, "_connect_postgres", lambda: sentinel)
    assert db.using_postgres() is True
    assert db.connect() is sentinel


def test_adapter_supports_user_lifecycle(pg_conn):
    user = db.create_user(pg_conn, "Pg@Test.com")
    assert user["email"] == "pg@test.com" and user["plan"] == "free"
    assert user["token"]
    # Volver a "crear" la cuenta no cambia el plan.
    db.set_user_plan(pg_conn, "pg@test.com", "premium")
    again = db.create_user(pg_conn, "pg@test.com")
    assert again["plan"] == "premium"
    assert db.get_user_by_token(pg_conn, again["token"])["email"] == "pg@test.com"


def test_adapter_duplicate_subscriber_updates_after_rollback(pg_conn):
    db.add_subscriber(pg_conn, "sub@test.com", "free")
    result = db.add_subscriber(pg_conn, "sub@test.com", "premium")
    assert result["updated"] is True
    row = pg_conn.execute(
        "SELECT plan FROM subscribers WHERE email=?", ("sub@test.com",)).fetchone()
    assert row["plan"] == "premium"


def test_adapter_duplicate_alert_returns_false(pg_conn):
    assert db.alert_mark_sent(pg_conn, "chat1", "m1", "home", 0.05) is True
    assert db.alert_mark_sent(pg_conn, "chat1", "m1", "home", 0.05) is False


def test_adapter_subscription_state(pg_conn):
    user = db.create_user(pg_conn, "state@test.com")
    db.save_stripe_ids(pg_conn, user["email"], customer_id="cus_1",
                       subscription_id="sub_1")
    db.set_subscription_state(pg_conn, user["id"], plan="premium",
                              period_end=1900000000, cancel_at_period_end=True)
    found = db.user_by_stripe_ids(pg_conn, customer_id="cus_1")
    assert found["email"] == "state@test.com"
    assert found["plan"] == "premium"
    assert found["sub_current_period_end"] == 1900000000
    assert found["sub_cancel_at_period_end"] == 1
