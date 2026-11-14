"""Beta cerrada: cupo duro de 10 cuentas con contador en BD.

Dos capas de protección:
1. Python  → ``db.create_user`` lanza ``BetaCapReached`` (mensaje amable).
2. BD      → el trigger ``users_beta_cap`` bloquea el INSERT aunque se
             salte Python (carrera entre peticiones).
"""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app import auth, config, db
from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _fill_users(n: int, prefix: str = "beta") -> None:
    conn = db.connect()
    try:
        for i in range(n):
            db.create_user(conn, f"{prefix}{i}@test.com")
    finally:
        conn.close()


def test_lifespan_writes_cap_to_db(client):
    """El arranque replica el cupo de config en la tabla kv."""
    conn = db.connect()
    try:
        assert db.beta_cap(conn) == config.BETA_MAX_USERS == 10
        status = db.beta_status(conn)
    finally:
        conn.close()
    assert status["cap"] == 10
    assert status["used"] == 0
    assert status["remaining"] == 10
    assert status["full"] is False


def test_health_reports_beta_status(client):
    body = client.get("/api/health").json()
    assert body["beta"] == {"cap": 10, "used": 0, "remaining": 10,
                            "full": False}


def test_register_blocked_when_cap_full(client):
    _fill_users(10)
    r = client.post("/api/auth/register",
                    json={"email": "nuevo@test.com", "password": "secret123"})
    assert r.status_code == 403
    detail = r.json()["detail"]
    assert detail["error"] == "beta_full"
    assert detail["cap"] == 10 and detail["used"] == 10
    # No se creó la cuenta.
    conn = db.connect()
    try:
        assert db.get_user_by_email(conn, "nuevo@test.com") is None
        assert db.beta_status(conn)["used"] == 10
    finally:
        conn.close()


def test_existing_account_still_logs_in_when_full(client):
    conn = db.connect()
    try:
        db.create_user(conn, "viejo@test.com")
        db.set_user_password(conn, "viejo@test.com",
                             auth.hash_password("secret123"))
    finally:
        conn.close()
    _fill_users(9, prefix="otro")
    r = client.post("/api/auth/login",
                    json={"email": "viejo@test.com", "password": "secret123"})
    assert r.status_code == 200, r.text
    # La cuenta existente no consume cupo extra ni se bloquea.
    assert db.beta_status(db.connect())["used"] == 10


def test_trigger_blocks_insert_even_if_python_is_skipped(client):
    """La segunda capa (BD) corta el INSERT directo, sin pasar por Python."""
    _fill_users(10)
    conn = db.connect()
    try:
        with pytest.raises(sqlite3.IntegrityError,
                           match="beta_full: cupo de beta lleno"):
            conn.execute(
                "INSERT INTO users (email, plan, token, created_at) "
                "VALUES ('directo@test.com', 'free', 'tok', 0)")
        assert db.get_user_by_email(conn, "directo@test.com") is None
    finally:
        conn.close()


def test_subscribe_free_goes_to_waitlist_when_full(client):
    _fill_users(10)
    r = client.post("/api/subscribe",
                    json={"email": "espera@test.com", "plan": "free"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["plan"] == "waitlist"
    assert body["waitlist"] is True
    assert body["activated"] is False
    conn = db.connect()
    try:
        # No hay cuenta nueva: el cupo sigue intacto.
        assert db.get_user_by_email(conn, "espera@test.com") is None
        assert db.beta_status(conn)["used"] == 10
        row = conn.execute(
            "SELECT plan FROM subscribers WHERE email=?",
            ("espera@test.com",)).fetchone()
    finally:
        conn.close()
    assert row["plan"] == "waitlist"


def test_cap_zero_disables_the_limit(client):
    """BETA_MAX_USERS=0 desactiva el cupo (sin límite)."""
    conn = db.connect()
    try:
        db.ensure_beta_cap(conn, 0)
        assert db.beta_status(conn)["full"] is False
        for i in range(12):
            db.create_user(conn, f"sinlimite{i}@test.com")
        assert db.beta_status(conn)["used"] == 12
    finally:
        conn.close()


def test_config_reads_env_default():
    assert config.BETA_MAX_USERS == 10
