"""Persistencia: PostgreSQL si hay ``DATABASE_URL``; si no, SQLite local.

En producción (Render Free) el disco es efímero, así que las cuentas y los
planes se pierden en cada despliegue si se usa SQLite. Definiendo
``DATABASE_URL`` (Neon, Supabase, Render Postgres, etc.) la app guarda todo
en PostgreSQL y los datos sobreviven a los redeploys.

SQLite sigue siendo el modo por defecto para desarrollo y tests: no requiere
instalar nada ni configurar variables.
"""

from __future__ import annotations

import json
import hashlib
import os
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from . import config

try:  # psycopg solo hace falta cuando se usa PostgreSQL.
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - instalación mínima para SQLite
    psycopg = None
    dict_row = None

try:  # El pool es opcional: sin él se abre una conexión por petición.
    from psycopg_pool import ConnectionPool
except ImportError:  # pragma: no cover
    ConnectionPool = None


def database_url() -> str:
    """URL de PostgreSQL (vacía = usar SQLite local)."""
    return os.environ.get("DATABASE_URL", "").strip()


def using_postgres() -> bool:
    return bool(database_url())


# Errores de unicidad de ambos motores: SQLite y PostgreSQL.
INTEGRITY_ERRORS: tuple[type[Exception], ...] = (sqlite3.IntegrityError,)
if psycopg is not None:  # pragma: no branch - depende del entorno
    INTEGRITY_ERRORS += (psycopg.IntegrityError,)

SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    sport TEXT NOT NULL,
    match TEXT NOT NULL,
    selection TEXT NOT NULL,
    odds REAL NOT NULL,
    edge REAL NOT NULL,
    stake_pct REAL NOT NULL,
    won INTEGER NOT NULL,
    profit REAL NOT NULL,
    clv_pct REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS subscribers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    plan TEXT NOT NULL,
    ts REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    plan TEXT NOT NULL DEFAULT 'free',
    token TEXT UNIQUE NOT NULL,
    stripe_customer_id TEXT,
    created_at REAL NOT NULL,
    telegram_chat_id TEXT,
    link_code TEXT
);
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL,
    match_id TEXT NOT NULL,
    selection TEXT NOT NULL,
    edge REAL NOT NULL,
    sent_at REAL NOT NULL,
    UNIQUE(chat_id, match_id, selection)
);
CREATE TABLE IF NOT EXISTS login_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_hash TEXT UNIQUE NOT NULL,
    email TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    used_at REAL,
    request_ip TEXT
);
CREATE INDEX IF NOT EXISTS idx_login_tokens_email ON login_tokens(email);
CREATE TABLE IF NOT EXISTS kv (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at REAL NOT NULL
);

-- ------------------------------------------------------------- ledger
-- Registro público append-only. Nunca se actualiza ni se borra una fila:
-- cada pick, cierre y resultado se AÑADE con el hash de la fila anterior.
CREATE TABLE IF NOT EXISTS picks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pick_key TEXT UNIQUE NOT NULL,
    event_id TEXT NOT NULL,
    sport_key TEXT NOT NULL,
    created_at REAL NOT NULL,
    event_start REAL,
    sport TEXT NOT NULL,
    league TEXT NOT NULL,
    event TEXT NOT NULL,
    market TEXT NOT NULL,
    selection TEXT NOT NULL,
    selection_label TEXT NOT NULL,
    bookmaker TEXT NOT NULL,
    bet_odds REAL NOT NULL,
    model_prob REAL NOT NULL,
    market_prob REAL NOT NULL,
    edge REAL NOT NULL,
    stake_units REAL NOT NULL,
    model_version TEXT NOT NULL,
    source TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    row_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_picks_created ON picks(created_at);
CREATE INDEX IF NOT EXISTS idx_picks_event ON picks(event_start);
CREATE INDEX IF NOT EXISTS idx_picks_league ON picks(league);

CREATE TABLE IF NOT EXISTS pick_closings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pick_id INTEGER UNIQUE NOT NULL,
    closing_odds REAL NOT NULL,
    closing_at REAL NOT NULL,
    clv_pct REAL NOT NULL,
    prev_hash TEXT NOT NULL,
    row_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pick_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pick_id INTEGER UNIQUE NOT NULL,
    result TEXT NOT NULL,
    profit_units REAL NOT NULL,
    settled_at REAL NOT NULL,
    prev_hash TEXT NOT NULL,
    row_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ledger_anchors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day TEXT UNIQUE NOT NULL,
    picks_head TEXT NOT NULL,
    picks_count INTEGER NOT NULL,
    closings_head TEXT NOT NULL,
    closings_count INTEGER NOT NULL,
    results_head TEXT NOT NULL,
    results_count INTEGER NOT NULL,
    head_hash TEXT NOT NULL,
    published_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS model_versions (
    version TEXT PRIMARY KEY,
    released_at REAL NOT NULL,
    summary TEXT NOT NULL,
    changes TEXT
);

CREATE TABLE IF NOT EXISTS alert_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    name TEXT NOT NULL,
    leagues TEXT NOT NULL DEFAULT '',
    edge_min REAL NOT NULL DEFAULT 0.04,
    odds_min REAL NOT NULL DEFAULT 1.01,
    odds_max REAL NOT NULL DEFAULT 10.0,
    markets TEXT NOT NULL DEFAULT '',
    max_minutes_to_start INTEGER,
    channel_email INTEGER NOT NULL DEFAULT 1,
    channel_telegram INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_alert_rules_email ON alert_rules(email);

CREATE TABLE IF NOT EXISTS alert_deliveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id INTEGER NOT NULL,
    email TEXT NOT NULL,
    channel TEXT NOT NULL,
    match_id TEXT NOT NULL,
    selection TEXT NOT NULL,
    league TEXT NOT NULL,
    event TEXT NOT NULL,
    selection_label TEXT NOT NULL,
    bookmaker TEXT NOT NULL,
    odds REAL NOT NULL,
    edge REAL NOT NULL,
    event_start REAL,
    status TEXT NOT NULL,
    detail TEXT,
    sent_at REAL NOT NULL,
    UNIQUE(rule_id, channel, match_id, selection)
);
CREATE INDEX IF NOT EXISTS idx_alert_deliveries_email
    ON alert_deliveries(email, sent_at DESC);
"""

# Equivalente para PostgreSQL (mismas tablas y columnas).
PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
    id BIGSERIAL PRIMARY KEY,
    ts DOUBLE PRECISION NOT NULL,
    sport TEXT NOT NULL,
    match TEXT NOT NULL,
    selection TEXT NOT NULL,
    odds DOUBLE PRECISION NOT NULL,
    edge DOUBLE PRECISION NOT NULL,
    stake_pct DOUBLE PRECISION NOT NULL,
    won INTEGER NOT NULL,
    profit DOUBLE PRECISION NOT NULL,
    clv_pct DOUBLE PRECISION NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS subscribers (
    id BIGSERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    plan TEXT NOT NULL,
    ts DOUBLE PRECISION NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    plan TEXT NOT NULL DEFAULT 'free',
    token TEXT UNIQUE NOT NULL,
    stripe_customer_id TEXT,
    created_at DOUBLE PRECISION NOT NULL,
    telegram_chat_id TEXT,
    link_code TEXT,
    stripe_subscription_id TEXT,
    sub_current_period_end DOUBLE PRECISION,
    sub_cancel_at_period_end INTEGER DEFAULT 0,
    password_hash TEXT
);
CREATE TABLE IF NOT EXISTS alerts (
    id BIGSERIAL PRIMARY KEY,
    chat_id TEXT NOT NULL,
    match_id TEXT NOT NULL,
    selection TEXT NOT NULL,
    edge DOUBLE PRECISION NOT NULL,
    sent_at DOUBLE PRECISION NOT NULL,
    UNIQUE(chat_id, match_id, selection)
);
CREATE TABLE IF NOT EXISTS login_tokens (
    id BIGSERIAL PRIMARY KEY,
    token_hash TEXT UNIQUE NOT NULL,
    email TEXT NOT NULL,
    created_at DOUBLE PRECISION NOT NULL,
    expires_at DOUBLE PRECISION NOT NULL,
    used_at DOUBLE PRECISION,
    request_ip TEXT
);
CREATE INDEX IF NOT EXISTS idx_login_tokens_email ON login_tokens(email);
CREATE TABLE IF NOT EXISTS kv (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at DOUBLE PRECISION NOT NULL
);

-- ------------------------------------------------------------- ledger
CREATE TABLE IF NOT EXISTS picks (
    id BIGSERIAL PRIMARY KEY,
    pick_key TEXT UNIQUE NOT NULL,
    event_id TEXT NOT NULL,
    sport_key TEXT NOT NULL,
    created_at DOUBLE PRECISION NOT NULL,
    event_start DOUBLE PRECISION,
    sport TEXT NOT NULL,
    league TEXT NOT NULL,
    event TEXT NOT NULL,
    market TEXT NOT NULL,
    selection TEXT NOT NULL,
    selection_label TEXT NOT NULL,
    bookmaker TEXT NOT NULL,
    bet_odds DOUBLE PRECISION NOT NULL,
    model_prob DOUBLE PRECISION NOT NULL,
    market_prob DOUBLE PRECISION NOT NULL,
    edge DOUBLE PRECISION NOT NULL,
    stake_units DOUBLE PRECISION NOT NULL,
    model_version TEXT NOT NULL,
    source TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    row_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_picks_created ON picks(created_at);
CREATE INDEX IF NOT EXISTS idx_picks_event ON picks(event_start);
CREATE INDEX IF NOT EXISTS idx_picks_league ON picks(league);

CREATE TABLE IF NOT EXISTS pick_closings (
    id BIGSERIAL PRIMARY KEY,
    pick_id BIGINT UNIQUE NOT NULL,
    closing_odds DOUBLE PRECISION NOT NULL,
    closing_at DOUBLE PRECISION NOT NULL,
    clv_pct DOUBLE PRECISION NOT NULL,
    prev_hash TEXT NOT NULL,
    row_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pick_results (
    id BIGSERIAL PRIMARY KEY,
    pick_id BIGINT UNIQUE NOT NULL,
    result TEXT NOT NULL,
    profit_units DOUBLE PRECISION NOT NULL,
    settled_at DOUBLE PRECISION NOT NULL,
    prev_hash TEXT NOT NULL,
    row_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ledger_anchors (
    id BIGSERIAL PRIMARY KEY,
    day TEXT UNIQUE NOT NULL,
    picks_head TEXT NOT NULL,
    picks_count INTEGER NOT NULL,
    closings_head TEXT NOT NULL,
    closings_count INTEGER NOT NULL,
    results_head TEXT NOT NULL,
    results_count INTEGER NOT NULL,
    head_hash TEXT NOT NULL,
    published_at DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS model_versions (
    version TEXT PRIMARY KEY,
    released_at DOUBLE PRECISION NOT NULL,
    summary TEXT NOT NULL,
    changes TEXT
);

CREATE TABLE IF NOT EXISTS alert_rules (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    name TEXT NOT NULL,
    leagues TEXT NOT NULL DEFAULT '',
    edge_min DOUBLE PRECISION NOT NULL DEFAULT 0.04,
    odds_min DOUBLE PRECISION NOT NULL DEFAULT 1.01,
    odds_max DOUBLE PRECISION NOT NULL DEFAULT 10.0,
    markets TEXT NOT NULL DEFAULT '',
    max_minutes_to_start INTEGER,
    channel_email INTEGER NOT NULL DEFAULT 1,
    channel_telegram INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at DOUBLE PRECISION NOT NULL,
    updated_at DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_alert_rules_email ON alert_rules(email);

CREATE TABLE IF NOT EXISTS alert_deliveries (
    id BIGSERIAL PRIMARY KEY,
    rule_id BIGINT NOT NULL,
    email TEXT NOT NULL,
    channel TEXT NOT NULL,
    match_id TEXT NOT NULL,
    selection TEXT NOT NULL,
    league TEXT NOT NULL,
    event TEXT NOT NULL,
    selection_label TEXT NOT NULL,
    bookmaker TEXT NOT NULL,
    odds DOUBLE PRECISION NOT NULL,
    edge DOUBLE PRECISION NOT NULL,
    event_start DOUBLE PRECISION,
    status TEXT NOT NULL,
    detail TEXT,
    sent_at DOUBLE PRECISION NOT NULL,
    UNIQUE(rule_id, channel, match_id, selection)
);
CREATE INDEX IF NOT EXISTS idx_alert_deliveries_email
    ON alert_deliveries(email, sent_at DESC);
"""

# Columnas añadidas con el tiempo (migración ligera para BD ya creadas).
# Nota: SQLite no permite añadir columnas UNIQUE por ALTER; la unicidad del
# código de vinculación se garantiza con un índice único creado abajo.
_USER_COLUMNS = ("telegram_chat_id TEXT", "link_code TEXT",
                 "stripe_subscription_id TEXT",
                 "sub_current_period_end REAL",
                 "sub_cancel_at_period_end INTEGER DEFAULT 0",
                 "password_hash TEXT")

_PG_USER_COLUMNS = ("telegram_chat_id TEXT", "link_code TEXT",
                    "stripe_subscription_id TEXT",
                    "sub_current_period_end DOUBLE PRECISION",
                    "sub_cancel_at_period_end INTEGER DEFAULT 0",
                    "password_hash TEXT")

_SEED_SQL = """INSERT INTO history
    (ts, sport, match, selection, odds, edge, stake_pct, won, profit, clv_pct)
    VALUES (?,?,?,?,?,?,?,?,?,?)"""


class _PostgresConnection:
    """Adapta psycopg al subconjunto de la API de sqlite3 que usa la app.

    La app usa ``?`` como marcador de parámetros; PostgreSQL usa ``%s``.
    """

    def __init__(self, raw, pool=None) -> None:
        self._raw = raw
        self._pool = pool

    @staticmethod
    def _sql(sql: str) -> str:
        return sql.replace("?", "%s")

    def execute(self, sql: str, params: tuple | list = ()):
        return self._raw.execute(self._sql(sql), tuple(params))

    def executemany(self, sql: str, seq):
        cur = self._raw.cursor()
        cur.executemany(self._sql(sql), [tuple(p) for p in seq])
        return cur

    def commit(self) -> None:
        self._raw.commit()

    def rollback(self) -> None:
        self._raw.rollback()

    def close(self) -> None:
        if self._pool is not None:
            # Devuelve la conexión al pool en vez de cerrarla.
            self._pool.putconn(self._raw)
        else:
            self._raw.close()


def _pg_statements(script: str) -> list[str]:
    return [part.strip() for part in script.split(";") if part.strip()]


def connect(db_path: Path | None = None):
    """Conexión a PostgreSQL (si ``DATABASE_URL``) o SQLite local."""
    if db_path is None and using_postgres():
        return _connect_postgres()
    path = Path(db_path or config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


_pg_lock = threading.Lock()
_pg_ready = False
_pg_pool = None


def _connect_postgres() -> _PostgresConnection:
    """Conexión (del pool si está disponible) con el esquema garantizado."""
    global _pg_pool, _pg_ready
    if psycopg is None:  # pragma: no cover - solo si falta la dependencia
        raise RuntimeError(
            "DATABASE_URL está definida pero falta psycopg. "
            "Ejecuta: pip install -r requirements.txt")

    with _pg_lock:
        if _pg_pool is None and ConnectionPool is not None:
            _pg_pool = ConnectionPool(
                database_url(), min_size=1, max_size=5,
                kwargs={"row_factory": dict_row},
                check=ConnectionPool.check_connection,
                timeout=10, open=True)

    if _pg_pool is not None:
        raw = _pg_pool.getconn()
        conn = _PostgresConnection(raw, pool=_pg_pool)
    else:  # sin psycopg_pool instalado: conexión directa
        conn = _PostgresConnection(
            psycopg.connect(database_url(), row_factory=dict_row))

    if not _pg_ready:
        with _pg_lock:
            if not _pg_ready:
                try:
                    _init_postgres(conn)
                except psycopg.Error:
                    # Otra instancia pudo crear el esquema en paralelo.
                    conn.rollback()
                    _init_postgres(conn)
                _pg_ready = True
    return conn


def _init_postgres(conn: _PostgresConnection) -> None:
    for statement in _pg_statements(PG_SCHEMA):
        conn.execute(statement)
    _migrate_postgres(conn)
    conn.commit()


def _migrate_postgres(conn: _PostgresConnection) -> None:
    """Migración idempotente de PostgreSQL (ADD COLUMN IF NOT EXISTS)."""
    for column in _PG_USER_COLUMNS:
        conn.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {column}")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_link_code "
                 "ON users(link_code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_tg_chat "
                 "ON users(telegram_chat_id)")


def _migrate(conn: sqlite3.Connection) -> None:
    """Añade columnas nuevas a tablas existentes (idempotente)."""
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
    for column in _USER_COLUMNS:
        name = column.split()[0]
        if name not in existing:
            conn.execute(f"ALTER TABLE users ADD COLUMN {column}")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_link_code "
                 "ON users(link_code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_tg_chat "
                 "ON users(telegram_chat_id)")
    conn.commit()


def kv_set(key: str, value: str) -> None:
    """Guarda un valor texto (p. ej. el último parte de cuotas en vivo)."""
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO kv (key, value, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
            "updated_at = excluded.updated_at",
            (key, value, time.time()))
        conn.commit()
    finally:
        conn.close()


def kv_get(key: str) -> tuple[str, float] | None:
    """Lee un valor guardado con :func:`kv_set`; ``None`` si no existe."""
    conn = connect()
    try:
        row = conn.execute(
            "SELECT value, updated_at FROM kv WHERE key = ?",
            (key,)).fetchone()
        if row is None:
            return None
        return row["value"], float(row["updated_at"])
    finally:
        conn.close()


def seed_history(conn: sqlite3.Connection) -> int:
    """Carga el historial de demostración si la tabla está vacía."""
    row = conn.execute("SELECT COUNT(*) AS n FROM history").fetchone()
    if row["n"]:
        return 0
    try:
        with open(config.HISTORY_PATH, "r", encoding="utf-8") as fh:
            rows: list[dict[str, Any]] = json.load(fh)
    except FileNotFoundError:
        return 0
    payload = [(r.get("ts", 0.0), r["sport"], r.get("match", ""), r["selection"],
                r["odds"], r.get("edge", 0.0), r.get("stake_pct", 1.0),
                int(r.get("won", 0)), r.get("profit", 0.0),
                r.get("clv_pct", 0.0)) for r in rows]
    conn.executemany(_SEED_SQL, payload)
    conn.commit()
    return len(payload)


def fetch_history(conn: sqlite3.Connection, sport: str | None = None) -> list[dict]:
    """Historial (si está vacío se carga el dataset de demostración)."""
    seed_history(conn)
    if sport:
        cur = conn.execute(
            "SELECT * FROM history WHERE sport=? ORDER BY ts", (sport,))
    else:
        cur = conn.execute("SELECT * FROM history ORDER BY ts")
    return [dict(r) for r in cur.fetchall()]


def add_subscriber(conn, email: str, plan: str) -> dict:
    try:
        conn.execute("INSERT INTO subscribers (email, plan, ts) VALUES (?,?,?)",
                     (email.strip().lower(), plan, time.time()))
        conn.commit()
        return {"ok": True, "email": email.strip().lower(), "plan": plan}
    except INTEGRITY_ERRORS:
        # PostgreSQL aborta la transacción tras un error: hay que deshacerla
        # antes de seguir con el UPDATE.
        conn.rollback()
        conn.execute("UPDATE subscribers SET plan=? WHERE email=?",
                     (plan, email.strip().lower()))
        conn.commit()
        return {"ok": True, "email": email.strip().lower(), "plan": plan,
                "updated": True}


# ------------------------------------------------------------------ usuarios
def _normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(conn: sqlite3.Connection, email: str) -> dict | None:
    row = conn.execute("SELECT * FROM users WHERE email=?",
                       (_normalize_email(email),)).fetchone()
    return dict(row) if row else None


def get_user_by_token(conn: sqlite3.Connection, token: str) -> dict | None:
    if not token:
        return None
    row = conn.execute("SELECT * FROM users WHERE token=?", (token,)).fetchone()
    return dict(row) if row else None


def create_user(conn: sqlite3.Connection, email: str,
                plan: str = "free") -> dict:
    """Crea (o recupera) el usuario y garantiza que tenga token.

    Importante: si el usuario **ya existe** se devuelve tal cual está en la
    BD (con su plan actual). El argumento ``plan`` solo se usa al crear una
    cuenta nueva; nunca degrada a un usuario que ya pagó.
    """
    email = _normalize_email(email)
    existing = get_user_by_email(conn, email)
    if existing:
        return existing
    if plan not in ("free", "premium"):
        raise ValueError(f"plan inválido: {plan}")
    token = secrets.token_urlsafe(24)
    try:
        conn.execute(
            "INSERT INTO users (email, plan, token, created_at) VALUES (?,?,?,?)",
            (email, plan, token, time.time()))
        conn.commit()
    except INTEGRITY_ERRORS:
        # Otra petición creó la cuenta al mismo tiempo: se devuelve la suya.
        conn.rollback()
    return get_user_by_email(conn, email) or {}


def set_user_plan(conn: sqlite3.Connection, email: str, plan: str) -> None:
    """Activa/desactiva el plan (lo llama Stripe webhook o el modo demo)."""
    if plan not in ("free", "premium"):
        raise ValueError(f"plan inválido: {plan}")
    conn.execute("UPDATE users SET plan=? WHERE email=?",
                 (plan, _normalize_email(email)))
    conn.commit()


def set_user_password(conn: sqlite3.Connection, email: str,
                     password_hash: str) -> None:
    """Guarda (o reemplaza) el hash de contraseña del usuario."""
    conn.execute("UPDATE users SET password_hash=? WHERE email=?",
                 (password_hash, _normalize_email(email)))
    conn.commit()


def get_password_hash(conn: sqlite3.Connection, email: str) -> str | None:
    row = conn.execute(
        "SELECT password_hash FROM users WHERE email=?",
        (_normalize_email(email),)).fetchone()
    return (row["password_hash"] if row else None)


def has_password(conn: sqlite3.Connection, email: str) -> bool:
    return bool(get_password_hash(conn, email))
    """Activa/desactiva el plan (lo llama Stripe webhook o el modo demo)."""
    if plan not in ("free", "premium"):
        raise ValueError(f"plan inválido: {plan}")
    conn.execute("UPDATE users SET plan=? WHERE email=?",
                 (plan, _normalize_email(email)))
    conn.commit()


# ------------------------------------------------------- suscripción Stripe
def user_by_stripe_ids(conn: sqlite3.Connection, *, customer_id: str | None = None,
                       subscription_id: str | None = None) -> dict | None:
    """Usuario dueño de un customer/subscription de Stripe (cualquiera de los dos)."""
    row = None
    if subscription_id:
        row = conn.execute(
            "SELECT * FROM users WHERE stripe_subscription_id=?",
            (subscription_id,)).fetchone()
    if row is None and customer_id:
        row = conn.execute(
            "SELECT * FROM users WHERE stripe_customer_id=?",
            (customer_id,)).fetchone()
    return dict(row) if row else None


def save_stripe_ids(conn: sqlite3.Connection, email: str,
                    customer_id: str | None = None,
                    subscription_id: str | None = None) -> None:
    """Guarda los IDs de Stripe del checkout (customer + subscription)."""
    sets, params = [], []
    if customer_id:
        sets.append("stripe_customer_id=?")
        params.append(customer_id)
    if subscription_id:
        sets.append("stripe_subscription_id=?")
        params.append(subscription_id)
    if not sets:
        return
    params.append(_normalize_email(email))
    conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE email=?", params)
    conn.commit()


def set_subscription_state(conn: sqlite3.Connection, user_id: int, *,
                           plan: str,
                           period_end: float | None = None,
                           cancel_at_period_end: bool | None = None) -> None:
    """Actualiza plan + estado de la suscripción en una sola escritura."""
    conn.execute(
        "UPDATE users SET plan=?, sub_current_period_end=?, "
        "sub_cancel_at_period_end=? WHERE id=?",
        (plan,
         period_end if period_end is not None else None,
         int(cancel_at_period_end) if cancel_at_period_end is not None else 0,
         user_id))
    conn.commit()


# --------------------------------------------------------------- telegram
def ensure_link_code(conn: sqlite3.Connection, email: str) -> str:
    """Código corto para vincular Telegram (no es el token de sesión)."""
    user = get_user_by_email(conn, email)
    if not user:
        user = create_user(conn, email, plan="free")
    if user.get("link_code"):
        return str(user["link_code"])
    for _ in range(20):
        code = secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:10]
        try:
            conn.execute("UPDATE users SET link_code=? WHERE email=?",
                         (code, _normalize_email(email)))
            conn.commit()
            return code
        except INTEGRITY_ERRORS:
            conn.rollback()
            continue  # colisión: otro usuario tiene ese código
    raise RuntimeError("no se pudo generar un código de vinculación")


def link_telegram(conn: sqlite3.Connection, code: str,
                  chat_id: str) -> dict | None:
    """Vincula un chat de Telegram con el usuario dueño de ``code``."""
    row = conn.execute("SELECT * FROM users WHERE link_code=?",
                       (str(code).strip(),)).fetchone()
    if not row:
        return None
    conn.execute("UPDATE users SET telegram_chat_id=? WHERE id=?",
                 (str(chat_id), row["id"]))
    conn.commit()
    return dict(row)


def unlink_telegram(conn: sqlite3.Connection, chat_id: str) -> int:
    cur = conn.execute("UPDATE users SET telegram_chat_id=NULL "
                       "WHERE telegram_chat_id=?", (str(chat_id),))
    conn.commit()
    return cur.rowcount


def user_by_chat(conn: sqlite3.Connection, chat_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM users WHERE telegram_chat_id=?",
                       (str(chat_id),)).fetchone()
    return dict(row) if row else None


def users_with_telegram(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT id, email, plan, telegram_chat_id FROM users "
        "WHERE telegram_chat_id IS NOT NULL ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def alert_already_sent(conn: sqlite3.Connection, chat_id: str, match_id: str,
                       selection: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM alerts WHERE chat_id=? AND match_id=? AND selection=?",
        (str(chat_id), match_id, selection)).fetchone()
    return row is not None


def alert_mark_sent(conn: sqlite3.Connection, chat_id: str, match_id: str,
                    selection: str, edge: float) -> bool:
    """Registra el alert enviado (call once el envío fue exitoso).

    Devuelve False si ya se enviaba antes (nunca duplica).
    """
    try:
        conn.execute(
            "INSERT INTO alerts (chat_id, match_id, selection, edge, sent_at) "
            "VALUES (?,?,?,?,?)",
            (str(chat_id), match_id, selection, edge, time.time()))
        conn.commit()
        return True
    except INTEGRITY_ERRORS:
        conn.rollback()
        return False


def alerts_reset(conn: sqlite3.Connection, chat_id: str | None = None) -> int:
    """Borra el historial de alertas (para reenviar / mantenimiento)."""
    if chat_id is None:
        cur = conn.execute("DELETE FROM alerts")
    else:
        cur = conn.execute("DELETE FROM alerts WHERE chat_id=?", (str(chat_id),))
    conn.commit()
    return cur.rowcount


# ------------------------------------------------------- enlaces de acceso
# Solo se guarda el hash SHA-256 del enlace: quien lea la BD no puede usarlo.
def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_login_token(conn, email: str, *, ttl_seconds: int = 1200,
                       request_ip: str | None = None) -> str:
    """Crea un enlace de un solo uso y anula los pendientes del mismo correo."""
    email = _normalize_email(email)
    now = time.time()
    token = secrets.token_urlsafe(32)
    conn.execute(
        "UPDATE login_tokens SET used_at=? WHERE email=? AND used_at IS NULL",
        (now, email))
    conn.execute(
        "INSERT INTO login_tokens "
        "(token_hash, email, created_at, expires_at, request_ip) "
        "VALUES (?,?,?,?,?)",
        (_hash_token(token), email, now, now + ttl_seconds, request_ip))
    conn.commit()
    return token


def consume_login_token(conn, token: str) -> str | None:
    """Valida y quema el enlace. Devuelve el email o ``None`` si no sirve."""
    if not token:
        return None
    now = time.time()
    row = conn.execute(
        "SELECT * FROM login_tokens WHERE token_hash=? AND used_at IS NULL",
        (_hash_token(token),)).fetchone()
    if not row or float(row["expires_at"]) < now:
        return None
    conn.execute("UPDATE login_tokens SET used_at=? WHERE id=?", (now, row["id"]))
    conn.commit()
    return str(row["email"])


def peek_login_token(conn, token: str) -> str | None:
    """Email del enlace si sigue vigente (sin quemarlo)."""
    if not token:
        return None
    row = conn.execute(
        "SELECT email, expires_at FROM login_tokens "
        "WHERE token_hash=? AND used_at IS NULL",
        (_hash_token(token),)).fetchone()
    if not row or float(row["expires_at"]) < time.time():
        return None
    return str(row["email"])


def count_login_requests(conn, *, email: str | None = None,
                         ip: str | None = None, since: float = 0) -> int:
    """Peticiones de enlace recientes (límite anti-abuso)."""
    if email:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM login_tokens "
            "WHERE email=? AND created_at>=?",
            (_normalize_email(email), since)).fetchone()
    else:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM login_tokens "
            "WHERE request_ip=? AND created_at>=?",
            (ip, since)).fetchone()
    return int(row["n"]) if row else 0


def purge_login_tokens(conn, older_than: float | None = None) -> int:
    """Limpia enlaces caducados (mantenimiento)."""
    cur = conn.execute("DELETE FROM login_tokens WHERE expires_at < ?",
                       (older_than or time.time(),))
    conn.commit()
    return cur.rowcount or 0


# ---------------------------------------------------------------------------
# Ledger append-only: picks, cierres, resultados y anclas diarias.
# Los nombres de tabla son constantes internas (nunca entrada del usuario).
# ---------------------------------------------------------------------------
_LEDGER_TABLES = frozenset({"picks", "pick_closings", "pick_results"})

# Filtros de resultado aceptados por ``ledger_pick_rows``.
_RESULT_FILTERS = {"won", "lost", "push", "void", "pending"}


def ledger_last_hash(conn, table: str) -> str:
    """Hash de la última fila de la cadena (cadena vacía si no hay filas)."""
    if table not in _LEDGER_TABLES:
        raise ValueError(f"tabla de ledger desconocida: {table}")
    row = conn.execute(
        f"SELECT row_hash FROM {table} ORDER BY id DESC LIMIT 1").fetchone()
    return str(row["row_hash"]) if row else ""


def ledger_insert(conn, table: str, values: dict) -> bool:
    """Añade una fila. ``False`` si ya existía (idempotente por clave única).

    Nunca hace UPDATE ni DELETE: si la fila existe, se ignora el intento.
    """
    if table not in _LEDGER_TABLES:
        raise ValueError(f"tabla de ledger desconocida: {table}")
    columns = list(values)
    sql = (f"INSERT INTO {table} ({', '.join(columns)}) "
           f"VALUES ({', '.join('?' for _ in columns)})")
    try:
        conn.execute(sql, tuple(values[c] for c in columns))
        conn.commit()
        return True
    except INTEGRITY_ERRORS:
        conn.rollback()
        return False


def ledger_rows(conn, table: str) -> list[dict]:
    """Todas las filas en orden de inserción (para verificar la cadena)."""
    if table not in _LEDGER_TABLES:
        raise ValueError(f"tabla de ledger desconocida: {table}")
    rows = conn.execute(f"SELECT * FROM {table} ORDER BY id ASC").fetchall()
    return [dict(r) for r in rows]


def ledger_released_match_ids(conn, before_ts: float) -> set[str]:
    """``match_id`` publicados en el registro antes de ``before_ts`` (epoch).

    Es la base del retraso del plan Free: lo que no está publicado (o es más
    reciente) no se sirve. No hay caché en memoria que pueda desincronizarse.
    """
    rows = conn.execute(
        "SELECT event_id FROM picks WHERE created_at <= ?",
        (float(before_ts),)).fetchall()
    return {str(row["event_id"]) for row in rows}


def ledger_pick_rows(conn, *, league: str | None = None,
                     sport: str | None = None,
                     edge_min: float | None = None,
                     edge_max: float | None = None,
                     market: str | None = None,
                     result: str | None = None,
                     date_from: float | None = None,
                     date_to: float | None = None,
                     limit: int = 100, offset: int = 0) -> tuple[list[dict], int]:
    """Picks con su cierre y resultado, filtrados y paginados.

    Devuelve ``(filas, total)``. El total es el de la vista filtrada, para
    paginar sin engañar al usuario.
    """
    where, params = [], []
    if league:
        where.append("p.league = ?")
        params.append(league)
    if sport:
        where.append("p.sport = ?")
        params.append(sport)
    if edge_min is not None:
        where.append("p.edge >= ?")
        params.append(float(edge_min))
    if edge_max is not None:
        where.append("p.edge <= ?")
        params.append(float(edge_max))
    if market:
        where.append("p.market = ?")
        params.append(market)
    if date_from is not None:
        where.append("p.event_start >= ?")
        params.append(float(date_from))
    if date_to is not None:
        where.append("p.event_start <= ?")
        params.append(float(date_to))
    if result in _RESULT_FILTERS:
        if result == "pending":
            where.append("r.id IS NULL")
        else:
            where.append("r.result = ?")
            params.append(result)

    base = ("FROM picks p "
            "LEFT JOIN pick_closings c ON c.pick_id = p.id "
            "LEFT JOIN pick_results r ON r.pick_id = p.id")
    clause = f" WHERE {' AND '.join(where)}" if where else ""
    total_row = conn.execute(f"SELECT COUNT(*) AS n {base}{clause}",
                             tuple(params)).fetchone()
    rows = conn.execute(
        "SELECT p.*, c.closing_odds, c.closing_at, c.clv_pct, "
        "r.result, r.profit_units, r.settled_at "
        f"{base}{clause} ORDER BY p.event_start DESC, p.id DESC "
        "LIMIT ? OFFSET ?",
        tuple(params) + (int(limit), int(offset))).fetchall()
    return [dict(r) for r in rows], int(total_row["n"])


def ledger_pending_closings(conn, *, until_ts: float,
                            after_ts: float) -> list[dict]:
    """Picks sin cierre cuyo evento empieza dentro de la ventana."""
    rows = conn.execute(
        "SELECT p.* FROM picks p "
        "LEFT JOIN pick_closings c ON c.pick_id = p.id "
        "WHERE c.id IS NULL AND p.event_start IS NOT NULL "
        "AND p.event_start <= ? AND p.event_start >= ? "
        "ORDER BY p.event_start ASC",
        (float(until_ts), float(after_ts))).fetchall()
    return [dict(r) for r in rows]


def ledger_pending_results(conn, *, before_ts: float,
                           after_ts: float) -> list[dict]:
    """Picks sin resultado cuyo evento ya empezó (y no es demasiado viejo)."""
    rows = conn.execute(
        "SELECT p.* FROM picks p "
        "LEFT JOIN pick_results r ON r.pick_id = p.id "
        "WHERE r.id IS NULL AND p.event_start IS NOT NULL "
        "AND p.event_start <= ? AND p.event_start >= ? "
        "ORDER BY p.event_start ASC",
        (float(before_ts), float(after_ts))).fetchall()
    return [dict(r) for r in rows]


def ledger_settled(conn) -> list[dict]:
    """Picks con resultado, ordenados por asentamiento (para ROI/drawdown)."""
    rows = conn.execute(
        "SELECT p.*, c.closing_odds, c.clv_pct, r.result, r.profit_units, "
        "r.settled_at FROM picks p "
        "JOIN pick_results r ON r.pick_id = p.id "
        "LEFT JOIN pick_closings c ON c.pick_id = p.id "
        "ORDER BY r.settled_at ASC, r.id ASC").fetchall()
    return [dict(r) for r in rows]


def ledger_counts(conn) -> dict:
    """Número de filas de cada cadena y último hash (para el ancla diaria)."""
    out = {}
    for table, prefix in (("picks", "picks"), ("pick_closings", "closings"),
                          ("pick_results", "results")):
        row = conn.execute(
            f"SELECT COUNT(*) AS n, "
            f"(SELECT row_hash FROM {table} ORDER BY id DESC LIMIT 1) AS head "
            f"FROM {table}").fetchone()
        out[f"{prefix}_count"] = int(row["n"])
        out[f"{prefix}_head"] = str(row["head"] or "")
    return out


def ledger_anchor_save(conn, values: dict) -> bool:
    """Publica el ancla del día. Idempotente: un día, un ancla."""
    try:
        conn.execute(
            "INSERT INTO ledger_anchors (day, picks_head, picks_count, "
            "closings_head, closings_count, results_head, results_count, "
            "head_hash, published_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (values["day"], values["picks_head"], values["picks_count"],
             values["closings_head"], values["closings_count"],
             values["results_head"], values["results_count"],
             values["head_hash"], values["published_at"]))
        conn.commit()
        return True
    except INTEGRITY_ERRORS:
        conn.rollback()
        return False


def ledger_anchor_latest(conn) -> dict | None:
    row = conn.execute(
        "SELECT * FROM ledger_anchors ORDER BY day DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def ledger_anchor_list(conn, limit: int = 30) -> list[dict]:
    """Anclas publicadas, la más reciente primero."""
    rows = conn.execute(
        "SELECT * FROM ledger_anchors ORDER BY day DESC LIMIT ?",
        (int(limit),)).fetchall()
    return [dict(row) for row in rows]


def ledger_anchor_on(conn, day: str) -> dict | None:
    row = conn.execute("SELECT * FROM ledger_anchors WHERE day=?",
                       (day,)).fetchone()
    return dict(row) if row else None


def model_versions_list(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM model_versions ORDER BY released_at DESC").fetchall()
    return [dict(r) for r in rows]


def seed_model_version(conn, version: str, summary: str,
                       released_at: float | None = None,
                       changes: str | None = None) -> bool:
    """Registra una versión del modelo (idempotente)."""
    try:
        conn.execute(
            "INSERT INTO model_versions (version, released_at, summary, changes) "
            "VALUES (?,?,?,?) ON CONFLICT (version) DO NOTHING",
            (version, released_at or time.time(), summary, changes))
        conn.commit()
        return True
    except INTEGRITY_ERRORS:
        conn.rollback()
        return False


def clear_history(conn) -> int:
    """Vacía el historial de backtest/demostración.

    La producción solo puede mostrar el registro real (tabla ``picks``):
    mientras existan las filas simuladas, cualquier ROI es una invención.
    """
    cur = conn.execute("DELETE FROM history")
    conn.commit()
    return cur.rowcount or 0


# ------------------------------------------------------ reglas de alertas
_LIST_SEP = "||"


def _pack_list(items: list[str] | None) -> str:
    if not items:
        return ""
    cleaned = [str(x).strip() for x in items if str(x).strip()]
    return _LIST_SEP.join(dict.fromkeys(cleaned))


def _unpack_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [x.strip() for x in str(raw).split(_LIST_SEP) if x.strip()]


def _format_rule(row) -> dict:
    d = dict(row)
    return {
        "id": int(d["id"]),
        "email": str(d["email"]),
        "name": str(d["name"]),
        "leagues": _unpack_list(d.get("leagues")),
        "edge_min": float(d["edge_min"]),
        "odds_min": float(d["odds_min"]),
        "odds_max": float(d["odds_max"]),
        "markets": _unpack_list(d.get("markets")),
        "max_minutes_to_start": (int(d["max_minutes_to_start"])
                                 if d.get("max_minutes_to_start") is not None
                                 else None),
        "channel_email": bool(d.get("channel_email")),
        "channel_telegram": bool(d.get("channel_telegram")),
        "enabled": bool(d.get("enabled")),
        "created_at": float(d["created_at"]),
        "updated_at": float(d["updated_at"]),
    }


def alert_rules_for_user(conn, email: str) -> list[dict]:
    email = _normalize_email(email)
    rows = conn.execute(
        "SELECT * FROM alert_rules WHERE email=? ORDER BY id ASC",
        (email,)).fetchall()
    return [_format_rule(r) for r in rows]


def alert_rules_active(conn) -> list[dict]:
    """Reglas activas con el plan y el chat de Telegram de su cuenta."""
    rows = conn.execute(
        "SELECT r.*, u.plan, u.telegram_chat_id "
        "FROM alert_rules r "
        "JOIN users u ON u.email = r.email "
        "WHERE r.enabled = 1 "
        "ORDER BY r.id ASC").fetchall()
    out = []
    for r in rows:
        item = _format_rule(r)
        raw = dict(r)
        item["plan"] = str(raw.get("plan") or "free")
        item["telegram_chat_id"] = raw.get("telegram_chat_id")
        out.append(item)
    return out


def alert_rule_create(conn, email: str, *, name: str,
                      leagues: list[str] | None = None,
                      edge_min: float = 0.04,
                      odds_min: float = 1.01,
                      odds_max: float = 10.0,
                      markets: list[str] | None = None,
                      max_minutes_to_start: int | None = None,
                      channel_email: bool = True,
                      channel_telegram: bool = False,
                      enabled: bool = True) -> dict:
    email = _normalize_email(email)
    now = time.time()
    conn.execute(
        "INSERT INTO alert_rules "
        "(email, name, leagues, edge_min, odds_min, odds_max, markets, "
        "max_minutes_to_start, channel_email, channel_telegram, enabled, "
        "created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (email, name.strip(), _pack_list(leagues), float(edge_min),
         float(odds_min), float(odds_max), _pack_list(markets),
         int(max_minutes_to_start) if max_minutes_to_start is not None else None,
         1 if channel_email else 0, 1 if channel_telegram else 0,
         1 if enabled else 0, now, now))
    conn.commit()
    row = conn.execute(
        "SELECT * FROM alert_rules WHERE email=? ORDER BY id DESC LIMIT 1",
        (email,)).fetchone()
    return _format_rule(row)


def alert_rule_set_enabled(conn, email: str, rule_id: int,
                           enabled: bool) -> dict | None:
    email = _normalize_email(email)
    now = time.time()
    cur = conn.execute(
        "UPDATE alert_rules SET enabled=?, updated_at=? WHERE id=? AND email=?",
        (1 if enabled else 0, now, int(rule_id), email))
    conn.commit()
    if not cur.rowcount:
        return None
    row = conn.execute(
        "SELECT * FROM alert_rules WHERE id=? AND email=?",
        (int(rule_id), email)).fetchone()
    return _format_rule(row) if row else None


def alert_rule_delete(conn, email: str, rule_id: int) -> bool:
    email = _normalize_email(email)
    cur = conn.execute(
        "DELETE FROM alert_rules WHERE id=? AND email=?",
        (int(rule_id), email))
    conn.commit()
    return bool(cur.rowcount)


def alert_delivery_exists(conn, rule_id: int, channel: str,
                          match_id: str, selection: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM alert_deliveries "
        "WHERE rule_id=? AND channel=? AND match_id=? AND selection=?",
        (int(rule_id), str(channel), str(match_id), str(selection))).fetchone()
    return row is not None


def alert_delivery_record(conn, *, rule_id: int, email: str, channel: str,
                          match_id: str, selection: str, league: str,
                          event: str, selection_label: str, bookmaker: str,
                          odds: float, edge: float,
                          event_start: float | None = None,
                          status: str = "sent",
                          detail: str | None = None) -> bool:
    """Guarda un envío de alerta (idempotente por regla+canal+partido+pick)."""
    try:
        conn.execute(
            "INSERT INTO alert_deliveries "
            "(rule_id, email, channel, match_id, selection, league, event, "
            "selection_label, bookmaker, odds, edge, event_start, status, "
            "detail, sent_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (int(rule_id), _normalize_email(email), str(channel),
             str(match_id), str(selection), str(league), str(event),
             str(selection_label), str(bookmaker), float(odds), float(edge),
             float(event_start) if event_start is not None else None,
             str(status), detail, time.time()))
        conn.commit()
        return True
    except INTEGRITY_ERRORS:
        conn.rollback()
        return False


def alert_deliveries_for_user(conn, email: str, limit: int = 50) -> list[dict]:
    email = _normalize_email(email)
    rows = conn.execute(
        "SELECT * FROM alert_deliveries WHERE email=? "
        "ORDER BY sent_at DESC, id DESC LIMIT ?",
        (email, int(limit))).fetchall()
    return [dict(r) for r in rows]
