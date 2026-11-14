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
    published_at REAL NOT NULL,
    ots_proof TEXT,
    ots_calendar TEXT,
    ots_submitted_at REAL
);

CREATE TABLE IF NOT EXISTS model_versions (
    version TEXT PRIMARY KEY,
    released_at REAL NOT NULL,
    summary TEXT NOT NULL,
    changes TEXT
);

CREATE TABLE IF NOT EXISTS market_line_moves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pick_id INTEGER NOT NULL,
    match_id TEXT NOT NULL,
    league TEXT NOT NULL,
    entry_odds REAL NOT NULL,
    odds_5min REAL,
    odds_15min REAL,
    odds_30min REAL,
    measured_at_5 REAL,
    measured_at_15 REAL,
    measured_at_30 REAL,
    move_5min_pct REAL,
    move_15min_pct REAL,
    move_30min_pct REAL,
    source TEXT NOT NULL DEFAULT 'live',
    created_at REAL NOT NULL,
    UNIQUE(pick_id)
);
CREATE INDEX IF NOT EXISTS idx_market_line_moves_league
    ON market_line_moves(league);

CREATE TABLE IF NOT EXISTS subscriber_caps (
    league TEXT PRIMARY KEY,
    cap INTEGER NOT NULL,
    occupied INTEGER NOT NULL DEFAULT 0,
    updated_at REAL NOT NULL
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
    channel_push INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_alert_rules_email ON alert_rules(email);

CREATE TABLE IF NOT EXISTS push_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    endpoint TEXT UNIQUE NOT NULL,
    p256dh TEXT NOT NULL DEFAULT '',
    auth TEXT NOT NULL DEFAULT '',
    user_agent TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_push_subscriptions_email
    ON push_subscriptions(email);

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

-- Triggers append-only: ni siquiera el administrador puede editar o borrar
-- filas de picks, pick_closings ni pick_results. Solo INSERT permitido.
CREATE TRIGGER IF NOT EXISTS picks_no_update
BEFORE UPDATE ON picks
BEGIN
    SELECT RAISE(ABORT, 'picks is append-only: UPDATE not allowed');
END;

CREATE TRIGGER IF NOT EXISTS picks_no_delete
BEFORE DELETE ON picks
BEGIN
    SELECT RAISE(ABORT, 'picks is append-only: DELETE not allowed');
END;

CREATE TRIGGER IF NOT EXISTS pick_closings_no_update
BEFORE UPDATE ON pick_closings
BEGIN
    SELECT RAISE(ABORT, 'pick_closings is append-only: UPDATE not allowed');
END;

CREATE TRIGGER IF NOT EXISTS pick_closings_no_delete
BEFORE DELETE ON pick_closings
BEGIN
    SELECT RAISE(ABORT, 'pick_closings is append-only: DELETE not allowed');
END;

CREATE TRIGGER IF NOT EXISTS pick_results_no_update
BEFORE UPDATE ON pick_results
BEGIN
    SELECT RAISE(ABORT, 'pick_results is append-only: UPDATE not allowed');
END;

CREATE TRIGGER IF NOT EXISTS pick_results_no_delete
BEFORE DELETE ON pick_results
BEGIN
    SELECT RAISE(ABORT, 'pick_results is append-only: DELETE not allowed');
END;

-- Trigger anti-retroactivo: created_at no puede ser posterior a event_start.
CREATE TRIGGER IF NOT EXISTS picks_created_before_start
BEFORE INSERT ON picks
WHEN NEW.event_start IS NOT NULL AND NEW.created_at > NEW.event_start
BEGIN
    SELECT RAISE(ABORT, 'picks: created_at posterior a event_start (retroactivo)');
END;

-- Beta cerrada: cupo duro de cuentas nuevas. El límite vive en kv
-- ``beta_max_users`` (0 o ausente = sin límite) para cambiarlo sin migrar.
CREATE TRIGGER IF NOT EXISTS users_beta_cap
BEFORE INSERT ON users
WHEN (SELECT COALESCE(CAST(value AS INTEGER), 0)
      FROM kv WHERE key = 'beta_max_users') > 0
 AND (SELECT COUNT(*) FROM users)
     >= (SELECT COALESCE(CAST(value AS INTEGER), 0)
         FROM kv WHERE key = 'beta_max_users')
BEGIN
    SELECT RAISE(ABORT, 'beta_full: cupo de beta lleno');
END;
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
    published_at DOUBLE PRECISION NOT NULL,
    ots_proof TEXT,
    ots_calendar TEXT,
    ots_submitted_at DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS model_versions (
    version TEXT PRIMARY KEY,
    released_at DOUBLE PRECISION NOT NULL,
    summary TEXT NOT NULL,
    changes TEXT
);

CREATE TABLE IF NOT EXISTS market_line_moves (
    id BIGSERIAL PRIMARY KEY,
    pick_id BIGINT NOT NULL,
    match_id TEXT NOT NULL,
    league TEXT NOT NULL,
    entry_odds DOUBLE PRECISION NOT NULL,
    odds_5min DOUBLE PRECISION,
    odds_15min DOUBLE PRECISION,
    odds_30min DOUBLE PRECISION,
    measured_at_5 DOUBLE PRECISION,
    measured_at_15 DOUBLE PRECISION,
    measured_at_30 DOUBLE PRECISION,
    move_5min_pct DOUBLE PRECISION,
    move_15min_pct DOUBLE PRECISION,
    move_30min_pct DOUBLE PRECISION,
    source TEXT NOT NULL DEFAULT 'live',
    created_at DOUBLE PRECISION NOT NULL,
    UNIQUE(pick_id)
);
CREATE INDEX IF NOT EXISTS idx_market_line_moves_league
    ON market_line_moves(league);

CREATE TABLE IF NOT EXISTS subscriber_caps (
    league TEXT PRIMARY KEY,
    cap INTEGER NOT NULL,
    occupied INTEGER NOT NULL DEFAULT 0,
    updated_at DOUBLE PRECISION NOT NULL
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
    channel_push INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at DOUBLE PRECISION NOT NULL,
    updated_at DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_alert_rules_email ON alert_rules(email);

CREATE TABLE IF NOT EXISTS push_subscriptions (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    endpoint TEXT UNIQUE NOT NULL,
    p256dh TEXT NOT NULL DEFAULT '',
    auth TEXT NOT NULL DEFAULT '',
    user_agent TEXT NOT NULL DEFAULT '',
    created_at DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_push_subscriptions_email
    ON push_subscriptions(email);

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
    conn.execute("ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS "
                 "channel_push INTEGER DEFAULT 0")
    conn.execute("ALTER TABLE ledger_anchors ADD COLUMN IF NOT EXISTS "
                 "ots_proof TEXT")
    conn.execute("ALTER TABLE ledger_anchors ADD COLUMN IF NOT EXISTS "
                 "ots_calendar TEXT")
    conn.execute("ALTER TABLE ledger_anchors ADD COLUMN IF NOT EXISTS "
                 "ots_submitted_at DOUBLE PRECISION")
    conn.execute("ALTER TABLE picks ADD COLUMN IF NOT EXISTS "
                 "sport_key TEXT NOT NULL DEFAULT ''")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS market_line_moves ("
        "id BIGSERIAL PRIMARY KEY, pick_id BIGINT NOT NULL, "
        "match_id TEXT NOT NULL, league TEXT NOT NULL, entry_odds REAL NOT NULL, "
        "odds_5min DOUBLE PRECISION, odds_15min DOUBLE PRECISION, "
        "odds_30min DOUBLE PRECISION, measured_at_5 DOUBLE PRECISION, "
        "measured_at_15 DOUBLE PRECISION, measured_at_30 DOUBLE PRECISION, "
        "move_5min_pct DOUBLE PRECISION, move_15min_pct DOUBLE PRECISION, "
        "move_30min_pct DOUBLE PRECISION, source TEXT NOT NULL DEFAULT 'live', "
        "created_at DOUBLE PRECISION NOT NULL, UNIQUE(pick_id))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS subscriber_caps ("
        "league TEXT PRIMARY KEY, cap INTEGER NOT NULL, "
        "occupied INTEGER NOT NULL DEFAULT 0, updated_at DOUBLE PRECISION NOT NULL)"
    )
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_link_code "
                 "ON users(link_code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_tg_chat "
                 "ON users(telegram_chat_id)")
    # Trigger anti-retroactivo
    conn.execute("""CREATE OR REPLACE FUNCTION prevent_retroactive_pick()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.event_start IS NOT NULL AND NEW.created_at > NEW.event_start THEN
                RAISE EXCEPTION 'picks: created_at posterior a event_start (retroactivo)';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;""")
    conn.execute("""DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'picks_created_before_start') THEN
            CREATE TRIGGER picks_created_before_start BEFORE INSERT ON picks
                FOR EACH ROW EXECUTE FUNCTION prevent_retroactive_pick();
        END IF;
    END $$;""")
    # Append-only triggers
    conn.execute("""CREATE OR REPLACE FUNCTION prevent_modify_append_only()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Table %% is append-only: %% not allowed', TG_TABLE_NAME, TG_OP;
        END;
        $$ LANGUAGE plpgsql;""")
    for table in ("picks", "pick_closings", "pick_results"):
        for op in ("update", "delete"):
            trig_name = f"{table}_no_{op}"
            conn.execute(f"""DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = '{trig_name}') THEN
                    CREATE TRIGGER {trig_name} BEFORE {op.upper()} ON {table}
                        FOR EACH ROW EXECUTE FUNCTION prevent_modify_append_only();
                END IF;
            END $$;""")
    # Beta cerrada: cupo duro de cuentas nuevas (kv 'beta_max_users').
    conn.execute("""CREATE OR REPLACE FUNCTION prevent_beta_user_overflow()
        RETURNS TRIGGER AS $$
        DECLARE cap INTEGER;
        BEGIN
            SELECT COALESCE(CAST(value AS INTEGER), 0) INTO cap
              FROM kv WHERE key = 'beta_max_users';
            IF cap > 0 AND (SELECT COUNT(*) FROM users) >= cap THEN
                RAISE EXCEPTION 'beta_full: cupo de beta lleno'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;""")
    conn.execute("""DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'users_beta_cap') THEN
            CREATE TRIGGER users_beta_cap BEFORE INSERT ON users
                FOR EACH ROW EXECUTE FUNCTION prevent_beta_user_overflow();
        END IF;
    END $$;""")


def _migrate(conn: sqlite3.Connection) -> None:
    """Añade columnas nuevas a tablas existentes (idempotente)."""
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
    for column in _USER_COLUMNS:
        name = column.split()[0]
        if name not in existing:
            conn.execute(f"ALTER TABLE users ADD COLUMN {column}")
    rule_cols = {
        row["name"] for row in conn.execute("PRAGMA table_info(alert_rules)")}
    if "channel_push" not in rule_cols:
        conn.execute(
            "ALTER TABLE alert_rules ADD COLUMN channel_push INTEGER DEFAULT 0")
    anchor_cols = {
        row["name"] for row in conn.execute("PRAGMA table_info(ledger_anchors)")}
    for col_def in ("ots_proof TEXT", "ots_calendar TEXT",
                    "ots_submitted_at REAL"):
        if col_def.split()[0] not in anchor_cols:
            conn.execute(f"ALTER TABLE ledger_anchors ADD COLUMN {col_def}")
    # Migración: asegurar que picks tenga sport_key
    pick_cols = {row["name"] for row in conn.execute("PRAGMA table_info(picks)")}
    if "sport_key" not in pick_cols:
        conn.execute("ALTER TABLE picks ADD COLUMN sport_key TEXT NOT NULL DEFAULT ''")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS market_line_moves ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, pick_id INTEGER NOT NULL, "
        "match_id TEXT NOT NULL, league TEXT NOT NULL, entry_odds REAL NOT NULL, "
        "odds_5min REAL, odds_15min REAL, odds_30min REAL, measured_at_5 REAL, "
        "measured_at_15 REAL, measured_at_30 REAL, move_5min_pct REAL, "
        "move_15min_pct REAL, move_30min_pct REAL, source TEXT NOT NULL "
        "DEFAULT 'live', created_at REAL NOT NULL, UNIQUE(pick_id))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS subscriber_caps ("
        "league TEXT PRIMARY KEY, cap INTEGER NOT NULL, "
        "occupied INTEGER NOT NULL DEFAULT 0, updated_at REAL NOT NULL)"
    )
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_link_code "
                 "ON users(link_code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_tg_chat "
                 "ON users(telegram_chat_id)")
    # Append-only triggers
    # Trigger anti-retroactivo
    conn.execute("""CREATE TRIGGER IF NOT EXISTS picks_created_before_start
        BEFORE INSERT ON picks
        WHEN NEW.event_start IS NOT NULL AND NEW.created_at > NEW.event_start
        BEGIN
            SELECT RAISE(ABORT, 'picks: created_at posterior a event_start (retroactivo)');
        END;""")
    for table in ("picks", "pick_closings", "pick_results"):
        conn.execute(f"""CREATE TRIGGER IF NOT EXISTS {table}_no_update
            BEFORE UPDATE ON {table}
            BEGIN
                SELECT RAISE(ABORT, '{table} is append-only: UPDATE not allowed');
            END;""")
        conn.execute(f"""CREATE TRIGGER IF NOT EXISTS {table}_no_delete
            BEFORE DELETE ON {table}
            BEGIN
                SELECT RAISE(ABORT, '{table} is append-only: DELETE not allowed');
            END;""")
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


# ------------------------------------------------------- beta cerrada (cupo)
BETA_CAP_KEY = "beta_max_users"


class BetaCapReached(Exception):
    """El cupo duro de la beta cerrada está lleno (no se crea la cuenta)."""

    def __init__(self, used: int, cap: int):
        self.used = used
        self.cap = cap
        super().__init__(f"beta_full: {used}/{cap} cuentas de la beta")


def beta_cap(conn) -> int:
    """Cupo máximo de cuentas de la beta (0 = sin límite)."""
    row = conn.execute(
        "SELECT value FROM kv WHERE key = ?", (BETA_CAP_KEY,)).fetchone()
    if row is None:
        return 0
    try:
        return int(str(row["value"]).strip())
    except (TypeError, ValueError):
        return 0


def beta_status(conn) -> dict:
    """Estado del cupo: ``{cap, used, remaining, full}``."""
    cap = beta_cap(conn)
    used = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
    return {"cap": cap, "used": used,
            "remaining": None if cap <= 0 else max(0, cap - used),
            "full": bool(cap > 0 and used >= cap)}


def ensure_beta_cap(conn, cap: int | None = None) -> int:
    """Escribe el cupo en ``kv`` (idempotente; lo llama el arranque)."""
    value = config.BETA_MAX_USERS if cap is None else cap
    conn.execute(
        "INSERT INTO kv (key, value, updated_at) VALUES (?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
        "updated_at = excluded.updated_at",
        (BETA_CAP_KEY, str(value), time.time()))
    conn.commit()
    return value


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
    # Cap de beta cerrada: solo cuentas nuevas (segunda capa: el trigger
    # ``users_beta_cap`` en la BD, por si dos peticiones llegan a la vez).
    status = beta_status(conn)
    if status["full"]:
        raise BetaCapReached(status["used"], status["cap"])
    token = secrets.token_urlsafe(24)
    try:
        conn.execute(
            "INSERT INTO users (email, plan, token, created_at) VALUES (?,?,?,?)",
            (email, plan, token, time.time()))
        conn.commit()
    except INTEGRITY_ERRORS as exc:
        conn.rollback()
        if "beta_full" in str(exc):
            # El trigger de la BD cortó la inserción (carrera entre peticiones).
            raise BetaCapReached(status["used"], status["cap"]) from exc
        # Otra petición creó la cuenta al mismo tiempo: se devuelve la suya.
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


def ledger_anchor_set_ots(conn, day: str, *, ots_proof: str,
                          ots_calendar: str,
                          ots_submitted_at: float | None = None) -> dict | None:
    """Guarda el recibo externo OpenTimestamps del ancla diaria."""
    ts = float(ots_submitted_at or time.time())
    conn.execute(
        "UPDATE ledger_anchors SET ots_proof=?, ots_calendar=?, "
        "ots_submitted_at=? WHERE day=?",
        (str(ots_proof), str(ots_calendar), ts, str(day)))
    conn.commit()
    return ledger_anchor_on(conn, day)


def ledger_pick_by_id(conn, pick_id: int) -> dict | None:
    """Un pick del registro con su cierre, resultado y hashes de las 3 cadenas."""
    row = conn.execute(
        "SELECT p.*, "
        "c.closing_odds, c.closing_at, c.clv_pct, "
        "c.prev_hash AS closing_prev_hash, c.row_hash AS closing_row_hash, "
        "r.result, r.profit_units, r.settled_at, "
        "r.prev_hash AS result_prev_hash, r.row_hash AS result_row_hash "
        "FROM picks p "
        "LEFT JOIN pick_closings c ON c.pick_id = p.id "
        "LEFT JOIN pick_results r ON r.pick_id = p.id "
        "WHERE p.id = ?",
        (int(pick_id),)).fetchone()
    return dict(row) if row else None


def model_versions_list(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM model_versions ORDER BY released_at DESC").fetchall()
    return [dict(r) for r in rows]


# ----------------------------------------------- mercado: movimiento post-anuncio
def market_line_move_create(conn, pick_id: int, match_id: str, league: str,
                            entry_odds: float, source: str = "live") -> bool:
    """Registra la cuota de publicación para medir el impacto del anuncio."""
    try:
        conn.execute(
            "INSERT INTO market_line_moves "
            "(pick_id, match_id, league, entry_odds, source, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (int(pick_id), str(match_id), str(league), float(entry_odds),
             str(source), time.time()))
        conn.commit()
        return True
    except INTEGRITY_ERRORS:
        conn.rollback()
        return False


def market_line_move_update(conn, pick_id: int, *, window: int,
                            odds: float | None, measured_at: float | None = None) -> bool:
    """Guarda la cuota medida a los 5/15/30 min y calcula el movimiento %."""
    if odds is None:
        return False
    ts = float(measured_at or time.time())
    col_odds = {5: "odds_5min", 15: "odds_15min", 30: "odds_30min"}[window]
    col_time = {5: "measured_at_5", 15: "measured_at_15", 30: "measured_at_30"}[window]
    col_move = {5: "move_5min_pct", 15: "move_15min_pct", 30: "move_30min_pct"}[window]
    row = conn.execute(
        "SELECT entry_odds FROM market_line_moves WHERE pick_id=?",
        (int(pick_id),)).fetchone()
    if not row:
        return False
    entry = float(row["entry_odds"])
    move_pct = (float(odds) - entry) / entry * 100.0 if entry else 0.0
    conn.execute(
        f"UPDATE market_line_moves SET {col_odds}=?, {col_time}=?, "
        f"{col_move}=? WHERE pick_id=?",
        (float(odds), ts, round(move_pct, 4), int(pick_id)))
    conn.commit()
    return True


def market_line_move_get(conn, pick_id: int) -> dict | None:
    row = conn.execute(
        "SELECT * FROM market_line_moves WHERE pick_id=?",
        (int(pick_id),)).fetchone()
    return dict(row) if row else None


def market_line_moves_for_league(conn, league: str | None = None) -> list[dict]:
    if league:
        rows = conn.execute(
            "SELECT * FROM market_line_moves WHERE league=? ORDER BY id ASC",
            (str(league),)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM market_line_moves ORDER BY id ASC").fetchall()
    return [dict(r) for r in rows]


def market_impact_summary(conn) -> dict:
    """Métrica agregada: movimiento promedio de línea post-anuncio."""
    rows = market_line_moves_for_league(conn)
    out = {"picks": len(rows), "per_league": {}, "global": None}
    by_league: dict[str, list[dict]] = {}
    for r in rows:
        by_league.setdefault(str(r["league"]), []).append(r)

    def _agg(items: list[dict]) -> dict | None:
        moves = [r.get("move_30min_pct") for r in items
                 if r.get("move_30min_pct") is not None]
        m5 = [r.get("move_5min_pct") for r in items
              if r.get("move_5min_pct") is not None]
        m15 = [r.get("move_15min_pct") for r in items
               if r.get("move_15min_pct") is not None]
        if not moves:
            return None
        return {
            "picks": len(items),
            "measured": len(moves),
            "avg_move_5min_pct": round(sum(m5) / len(m5), 3) if m5 else None,
            "avg_move_15min_pct": round(sum(m15) / len(m15), 3) if m15 else None,
            "avg_move_30min_pct": round(sum(moves) / len(moves), 3),
            "max_move_30min_pct": round(max(moves), 3),
            "min_move_30min_pct": round(min(moves), 3),
        }

    for league, items in sorted(by_league.items()):
        out["per_league"][league] = _agg(items)
    out["global"] = _agg(rows)
    return out


# ----------------------------------------------- contadores de suscriptores
def subscriber_cap_set(conn, league: str, cap: int) -> dict:
    now = time.time()
    conn.execute(
        "INSERT INTO subscriber_caps (league, cap, occupied, updated_at) "
        "VALUES (?,?,0,?) "
        "ON CONFLICT(league) DO UPDATE SET cap=excluded.cap, "
        "updated_at=excluded.updated_at",
        (str(league), int(cap), now))
    conn.commit()
    return subscriber_cap_get(conn, league) or {}


def subscriber_cap_get(conn, league: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM subscriber_caps WHERE league=?", (str(league),)).fetchone()
    return dict(row) if row else None


def subscriber_cap_list(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM subscriber_caps ORDER BY league ASC").fetchall()
    return [dict(r) for r in rows]


def subscriber_cap_increment(conn, league: str, delta: int = 1) -> dict | None:
    row = subscriber_cap_get(conn, league)
    if not row:
        return None
    new_occ = max(0, int(row["occupied"]) + int(delta))
    conn.execute(
        "UPDATE subscriber_caps SET occupied=?, updated_at=? WHERE league=?",
        (new_occ, time.time(), str(league)))
    conn.commit()
    return subscriber_cap_get(conn, league)


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
        "channel_push": bool(d.get("channel_push")),
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
                      channel_push: bool = False,
                      enabled: bool = True) -> dict:
    email = _normalize_email(email)
    now = time.time()
    conn.execute(
        "INSERT INTO alert_rules "
        "(email, name, leagues, edge_min, odds_min, odds_max, markets, "
        "max_minutes_to_start, channel_email, channel_telegram, channel_push, "
        "enabled, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (email, name.strip(), _pack_list(leagues), float(edge_min),
         float(odds_min), float(odds_max), _pack_list(markets),
         int(max_minutes_to_start) if max_minutes_to_start is not None else None,
         1 if channel_email else 0, 1 if channel_telegram else 0,
         1 if channel_push else 0, 1 if enabled else 0, now, now))
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


# ------------------------------------------------ suscripciones Web Push
def push_subscribe(conn, email: str, *, endpoint: str,
                   p256dh: str = "", auth: str = "",
                   user_agent: str = "") -> dict:
    email = _normalize_email(email)
    endpoint = str(endpoint).strip()
    now = time.time()
    conn.execute(
        "INSERT INTO push_subscriptions "
        "(email, endpoint, p256dh, auth, user_agent, created_at) "
        "VALUES (?,?,?,?,?,?) "
        "ON CONFLICT(endpoint) DO UPDATE SET "
        "email = excluded.email, p256dh = excluded.p256dh, "
        "auth = excluded.auth, user_agent = excluded.user_agent",
        (email, endpoint, str(p256dh or ""), str(auth or ""),
         str(user_agent or "")[:200], now))
    conn.commit()
    row = conn.execute(
        "SELECT * FROM push_subscriptions WHERE endpoint=?",
        (endpoint,)).fetchone()
    return dict(row) if row else {}


def push_unsubscribe(conn, email: str, endpoint: str | None = None) -> int:
    email = _normalize_email(email)
    if endpoint:
        cur = conn.execute(
            "DELETE FROM push_subscriptions WHERE email=? AND endpoint=?",
            (email, str(endpoint).strip()))
    else:
        cur = conn.execute(
            "DELETE FROM push_subscriptions WHERE email=?", (email,))
    conn.commit()
    return cur.rowcount or 0


def push_subscriptions_for_user(conn, email: str) -> list[dict]:
    email = _normalize_email(email)
    rows = conn.execute(
        "SELECT * FROM push_subscriptions WHERE email=? ORDER BY id DESC",
        (email,)).fetchall()
    return [dict(r) for r in rows]
