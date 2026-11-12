"""Configuración de ApuestaEdge (variables de entorno + valores por defecto)."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
# Datos incluidos en el repo (solo lectura): cuotas demo, ratings e historial.
ASSETS_DIR = BASE_DIR / "data"
# Estado escribible (SQLite). En Render/Docker/Fly apunta al volumen /data.
DATA_DIR = Path(os.environ.get("APUESTAEDGE_DATA_DIR", BASE_DIR / "data"))
DB_PATH = Path(os.environ.get("APUESTAEDGE_DB", DATA_DIR / "apuesta_edge.db"))


def asset_path(name: str) -> Path:
    """Asset de datos: prioriza DATA_DIR si ya está ahí (imágenes Docker),
    si no usa los archivos incluidos en el repo (Render python runtime)."""
    custom = DATA_DIR / name
    return custom if custom.exists() else ASSETS_DIR / name


SAMPLE_ODDS_PATH = asset_path("sample_odds.json")
HISTORY_PATH = asset_path("history.json")

# Clave de https://the-odds-api.com (plan gratuito: 500 créditos/mes).
# Sin clave la app funciona con el dataset de demostración incluido.
ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "").strip()

# Deportes soportados en la API externa (The Odds API).
ODDS_API_SPORTS = {
    "soccer": ["soccer_epl", "soccer_spain_la_liga", "soccer_mexico_ligamx",
               "soccer_italy_serie_a"],
    "basketball": ["basketball_nba"],
    "tennis": ["tennis_atp"],
    # Fútbol americano: NFL (temporada regular + playoffs) y NCAA FBS.
    "americanfootball": ["americanfootball_nfl", "americanfootball_ncaa_fbs"],
    # Boxeo y béisbol: mercados h2h con cobertura en vivo.
    "boxing": ["boxing_boxing"],
    "baseball": ["baseball_mlb"],
    # Outright (ganador de la carrera): The Odds API NO los cubre -> demo.
    "formula1": [],
    "motogp": [],
    "horseracing": [],
}

# Deportes outright: N participantes por evento (cuotas por participante).
OUTRIGHT_GROUPS = ("formula1", "motogp", "horseracing")

# Deportes sin proveedor de datos en vivo (solo dataset de demostración).
DEMO_ONLY_SPORTS = ("formula1", "motogp", "horseracing")

# Ocultos del radar temporalmente: sin fuente de datos real no se muestran
# (evita presentar eventos demo como si fueran cartelera real).
# Quitar de esta tupla cuando se conecte un proveedor en vivo para ellos.
HIDDEN_SPORTS = OUTRIGHT_GROUPS
ODDS_API_REGION = os.environ.get("ODDS_API_REGION", "eu")
ODDS_API_TIMEOUT = float(os.environ.get("ODDS_API_TIMEOUT", "12"))

# Parámetros de recomendación por plan.
PLANS = {
    "free": {
        "name": "Free",
        "price_usd": 0,
        "min_edge": 0.06,      # exige al menos +6% de edge
        "max_picks": 10,       # 10 recomendaciones diarias para enganchar
        "full_analysis": False,
        "features": [
            "10 selecciones diarias con edge ≥ 6%",
            "Probabilidad modelo vs mercado",
            "ROI público histórico",
        ],
    },
    "premium": {
        "name": "Premium",
        "price_usd": 29,
        "min_edge": 0.03,      # exige al menos +3% de edge
        "max_picks": 20,       # todas las selecciones con valor
        "full_analysis": True,
        "features": [
            "Todas las selecciones con edge ≥ 3%",
            "Stake Kelly fraccional y confianza estadística",
            "Explicación completa del modelo en cada pick",
            "Métricas CLV, drawdown y test binomial por liga",
            "Alertas cuando aparece valor nuevo",
        ],
    },
}

# Kelly fraccional y límites de riesgo (bankroll management).
KELLY_FRACTION = float(os.environ.get("KELLY_FRACTION", "0.25"))
MAX_STAKE_PCT = float(os.environ.get("MAX_STAKE_PCT", "3"))
DEFAULT_BANKROLL = float(os.environ.get("DEFAULT_BANKROLL", "1000"))

# Tamaño muestral efectivo de los ratings Elo (ver engine.ev).
EFFECTIVE_N = int(os.environ.get("EFFECTIVE_N", "60"))

# ------------------------------------------------------- alertas Telegram
# Bot creado con @BotFather: TELEGRAM_BOT_TOKEN y TELEGRAM_BOT_USERNAME.
# TELEGRAM_CHAT_ID: chat/canal de difusión (opcional; útil como admin/demo).
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME", "").strip()
TELEGRAM_BROADCAST_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
TELEGRAM_POLL_TIMEOUT = int(os.environ.get("TELEGRAM_POLL_TIMEOUT", "25"))
ALERT_INTERVAL_SECONDS = int(os.environ.get("ALERT_INTERVAL_SECONDS", "1800"))
ALERT_MIN_EDGE = float(os.environ.get("ALERT_MIN_EDGE", "0.04"))
ALERT_MAX_PICKS = {"free": 2, "premium": 6}
ALERT_TIMEOUT = float(os.environ.get("ALERT_TIMEOUT", "15"))


def telegram_enabled() -> bool:
    return bool(TELEGRAM_BOT_TOKEN)


# ------------------------------------------------------------ acceso (login)
# El acceso es con enlace de un solo uso enviado por correo (magic link):
# nadie puede entrar solo por saber el email de otra persona.
LOGIN_TOKEN_TTL_MINUTES = int(os.environ.get("LOGIN_TOKEN_TTL_MINUTES", "20"))
# Límite de enlaces por email y por IP (anti-abuso / spam de correos).
LOGIN_MAX_PER_EMAIL = int(os.environ.get("LOGIN_MAX_PER_EMAIL", "3"))
LOGIN_MAX_PER_IP = int(os.environ.get("LOGIN_MAX_PER_IP", "10"))
LOGIN_RATE_WINDOW_MINUTES = int(os.environ.get("LOGIN_RATE_WINDOW_MINUTES", "15"))


def public_base_url() -> str:
    """URL pública para los enlaces del correo (sin barra final).

    Nunca se usa la cabecera ``Origin``: la controla el cliente y permitiría
    robar el enlace. En producción define ``PUBLIC_BASE_URL``.
    """
    return os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")


def dev_login_enabled() -> bool:
    """``POST /api/auth/login`` (sin verificar el correo). Solo dev/tests."""
    return os.environ.get("AUTH_DEV_LOGIN", "").strip().lower() in {
        "1", "true", "yes", "on"}
