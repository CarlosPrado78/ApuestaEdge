"""Persistencia ligera en SQLite: historial de picks + suscriptores."""

from __future__ import annotations

import json
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any

from . import config

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
"""

# Columnas añadidas con el tiempo (migración ligera para BD ya creadas).
# Nota: SQLite no permite añadir columnas UNIQUE por ALTER; la unicidad del
# código de vinculación se garantiza con un índice único creado abajo.
_USER_COLUMNS = ("telegram_chat_id TEXT", "link_code TEXT",
                 "stripe_subscription_id TEXT",
                 "sub_current_period_end REAL",
                 "sub_cancel_at_period_end INTEGER DEFAULT 0")

_SEED_SQL = """INSERT INTO history
    (ts, sport, match, selection, odds, edge, stake_pct, won, profit, clv_pct)
    VALUES (?,?,?,?,?,?,?,?,?,?)"""


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path or config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


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


def add_subscriber(conn: sqlite3.Connection, email: str, plan: str) -> dict:
    try:
        conn.execute("INSERT INTO subscribers (email, plan, ts) VALUES (?,?,?)",
                     (email.strip().lower(), plan, time.time()))
        conn.commit()
        return {"ok": True, "email": email.strip().lower(), "plan": plan}
    except sqlite3.IntegrityError:
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
    """Crea (o recupera) el usuario y garantiza que tenga token."""
    email = _normalize_email(email)
    existing = get_user_by_email(conn, email)
    if existing:
        return existing
    token = secrets.token_urlsafe(24)
    conn.execute(
        "INSERT INTO users (email, plan, token, created_at) VALUES (?,?,?,?)",
        (email, plan, token, time.time()))
    conn.commit()
    return get_user_by_email(conn, email) or {}


def set_user_plan(conn: sqlite3.Connection, email: str, plan: str) -> None:
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
        except sqlite3.IntegrityError:
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
    except sqlite3.IntegrityError:
        return False


def alerts_reset(conn: sqlite3.Connection, chat_id: str | None = None) -> int:
    """Borra el historial de alertas (para reenviar / mantenimiento)."""
    if chat_id is None:
        cur = conn.execute("DELETE FROM alerts")
    else:
        cur = conn.execute("DELETE FROM alerts WHERE chat_id=?", (str(chat_id),))
    conn.commit()
    return cur.rowcount
