"""Configuración de ApuestaEdge (variables de entorno + valores por defecto)."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("APUESTAEDGE_DATA_DIR", BASE_DIR / "data"))
DB_PATH = Path(os.environ.get("APUESTAEDGE_DB", DATA_DIR / "apuesta_edge.db"))
SAMPLE_ODDS_PATH = DATA_DIR / "sample_odds.json"
HISTORY_PATH = DATA_DIR / "history.json"

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
ODDS_API_REGION = os.environ.get("ODDS_API_REGION", "eu")
ODDS_API_TIMEOUT = float(os.environ.get("ODDS_API_TIMEOUT", "12"))

# Parámetros de recomendación por plan.
PLANS = {
    "free": {
        "name": "Free",
        "price_usd": 0,
        "min_edge": 0.06,      # exige al menos +6% de edge
        "max_picks": 3,
        "full_analysis": False,
        "features": [
            "3 selecciones diarias con edge ≥ 6%",
            "Probabilidad modelo vs mercado",
            "ROI público histórico",
        ],
    },
    "premium": {
        "name": "Premium",
        "price_usd": 29,
        "min_edge": 0.03,      # exige al menos +3% de edge
        "max_picks": 12,
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
