"""Alertas por Telegram: bot, vinculación de cuentas y envío de picks.

Componentes:

- ``format_pick``        mensaje HTML de un pick (con sus números).
- ``process_update``     comandos del bot (pura, fácil de testear).
- ``TelegramNotifier``   polling largo de ``getUpdates`` + envío.
- ``alert_loop``         scheduler: manda cada pick con valor **una sola vez**
                         (dedupe en la tabla ``alerts``) a cada suscriptor.

Variables (``app/config.py``):

    TELEGRAM_BOT_TOKEN     token de @BotFather (obligatorio para activar)
    TELEGRAM_BOT_USERNAME  username del bot (para el deep link)
    TELEGRAM_CHAT_ID       chat de difusión opcional (admin / demo)
    ALERT_INTERVAL_SECONDS cadencia del resumen (1800 = 30 min)
    ALERT_MIN_EDGE         edge mínimo para alertar (0.04 = 4%)

Sin ``TELEGRAM_BOT_TOKEN`` el módulo está inerte: la app sigue igual.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import html
import logging
import smtplib
import time
from contextlib import suppress
from email.message import EmailMessage
from typing import Any

import httpx

from . import config, db, service

log = logging.getLogger("apuesta_edge.telegram")
API_BASE = "https://api.telegram.org"

# Enlaces directos a las casas (sin códigos de afiliado ni parámetros de
# seguimiento). Si una casa no está en el mapa, no se inventa URL.
BOOKMAKER_URLS: dict[str, str] = {
    "pinnacle": "https://www.pinnacle.com",
    "bet365": "https://www.bet365.com",
    "betfair": "https://www.betfair.com",
    "betfair_ex_eu": "https://www.betfair.com/exchange",
    "williamhill": "https://sports.williamhill.com",
    "888sport": "https://www.888sport.com",
    "unibet": "https://www.unibet.com",
    "bwin": "https://sports.bwin.com",
    "1xbet": "https://1xbet.com",
    "marathonbet": "https://www.marathonbet.com",
    "codere": "https://www.codere.mx",
    "caliente": "https://www.caliente.mx",
    "betmgm": "https://sports.betmgm.com",
    "draftkings": "https://sportsbook.draftkings.com",
    "fanduel": "https://sportsbook.fanduel.com",
}


def bookmaker_url(bookmaker: str | None) -> str | None:
    if not bookmaker:
        return None
    key = str(bookmaker).strip().lower().replace(" ", "")
    return BOOKMAKER_URLS.get(key)

HELP_TEXT = (
    "🤖 <b>ApuestaEdge</b>\n"
    "Te aviso cuando aparezca una apuesta con valor esperado positivo.\n\n"
    "Comandos:\n"
    "/start &lt;codigo&gt; — vincular tu cuenta Premium/Free\n"
    "/mis_picks — ver los picks con valor de ahora\n"
    "/status — tu plan y estado de vinculación\n"
    "/stop — dejar de recibir alertas")


def api_url(method: str) -> str:
    return f"{API_BASE}/bot{config.TELEGRAM_BOT_TOKEN}/{method}"


# --------------------------------------------------------------- formato
def format_pick(pick: dict[str, Any], plan: str = "premium",
                bankroll: float | None = None) -> str:
    """Mensaje HTML de un pick (escapa todos los datos externos)."""
    e = html.escape
    sport_icon = {"soccer": "⚽", "basketball": "🏀", "tennis": "🎾",
                  "americanfootball": "🏈", "boxing": "🥊", "baseball": "⚾",
                  "formula1": "🏎️", "motogp": "🏍️", "horseracing": "🐎"}.get(
        pick.get("sport", ""), "🏅")
    kelly = pick.get("kelly") or {}
    when = e(str(pick.get("commence_time") or "horario por confirmar"))
    lines = [
        f"{sport_icon} <b>{e(pick.get('league', ''))}</b>",
        f"<b>{e(pick.get('home_team', ''))}</b> vs <b>{e(pick.get('away_team', ''))}</b>",
        "",
        f"👉 <b>{e(pick.get('selection_label', ''))}</b> a "
        f"<b>{pick['odds']:.2f}</b> ({e(pick.get('bookmaker', ''))})",
        f"📈 Edge <b>{pick['edge'] * 100:+.1f}%</b> · "
        f"EV <b>{pick['ev'] * 100:+.1f}%</b> · "
        f"Confianza <b>{pick['confidence'] * 100:.0f}%</b>",
        f"🧠 Modelo {pick['model_prob'] * 100:.1f}% vs "
        f"mercado {pick['market_prob'] * 100:.1f}%",
        f"🕐 Entra antes de {when} UTC",
    ]
    if plan == "premium" and kelly.get("stake_pct"):
        bankroll = bankroll or config.DEFAULT_BANKROLL
        lines.insert(5, f"💰 Stake Kelly: <b>{kelly['stake_pct']:.2f}%</b> "
                        f"({kelly['stake_units']:.2f} u. de {bankroll:.0f})")
    summary = (pick.get("explanation") or {}).get("summary")
    if summary and plan == "premium":
        lines += ["", f"ℹ️ {e(summary)}"]
    direct_url = bookmaker_url(pick.get("bookmaker"))
    if direct_url:
        lines += ["", f'🔗 <a href="{e(direct_url)}">'
                      f'{e(str(pick.get("bookmaker", "")))}</a> '
                      "(enlace directo, sin afiliado)"]
    else:
        lines += ["", "🔗 Enlace sin afiliación comercial"]
    if plan != "premium":
        lines += ["", "🔒 Desbloquea el stake, la confianza y el análisis "
                      "completo en Premium."]
    return "\n".join(lines)


def format_digest(picks: list[dict], plan: str,
                  bankroll: float | None = None) -> str:
    """Varios picks en un solo mensaje (evita el límite de ráfagas)."""
    header = f"🎯 <b>{len(picks)} picks con valor ahora mismo</b>\n"
    body = "\n\n".join(format_pick(p, plan, bankroll) for p in picks)
    return header + "\n" + body


# ------------------------------------------------------------- comandos
def process_update(update: dict, conn=None,
                   matches_provider=None) -> list[tuple[str, str]]:
    """Traduce un update de Telegram en respuestas [(chat_id, texto)].

    Pura respecto a la red: los envíos los hace ``TelegramNotifier``.
    ``matches_provider`` permite reutilizar la caché de partidos del
    servidor en lugar de gastar créditos de la API en cada comando.
    """
    message = update.get("message") or {}
    chat_id = str((message.get("chat") or {}).get("id", ""))
    text = str(message.get("text") or "").strip()
    if not chat_id or not text:
        return []

    own = conn is not None
    if conn is None:
        conn = db.connect()
    try:
        if text.startswith("/start"):
            parts = text.split(maxsplit=1)
            code = parts[1].strip() if len(parts) > 1 else ""
            if code:
                user = db.link_telegram(conn, code, chat_id)
                if user:
                    plan_txt = "<b>Premium</b>" if user.get("plan") == "premium" \
                        else "<b>Free</b>"
                    return [(chat_id,
                             f"✅ <b>¡Cuenta vinculada!</b> ({plan_txt} · "
                             f"{html.escape(str(user.get('email', '')))})\n"
                             f"Recibirás las alertas de valor de tu plan.\n\n"
                             "Comandos: /mis_picks · /status · /stop")]
                return [(chat_id, "❌ Código inválido. Pídelo en la web "
                                  "(sección Precios) y usa: "
                                  "/start &lt;codigo&gt;")]
            return [(chat_id, HELP_TEXT)]

        if text.startswith("/stop"):
            removed = db.unlink_telegram(conn, chat_id)
            return [(chat_id, "🔕 Alertas desactivadas. "
                              f"Vuelve con /start &lt;codigo&gt;."
                              if removed else
                              "Este chat no estaba vinculado.")]

        user = db.user_by_chat(conn, chat_id)
        plan = (user or {}).get("plan", "free")
        not_linked = ("⚠️ Este chat no está vinculado. Usa "
                      "/start &lt;codigo&gt; (lo encuentras en la web).")

        if text.startswith("/status"):
            if user:
                return [(chat_id,
                         f"👤 {html.escape(str(user.get('email', '')))}\n"
                         f"📦 Plan: <b>{str(plan).capitalize()}</b>\n"
                         "🔔 Alertas: activas")]
            return [(chat_id, not_linked)]

        if text.startswith("/mis_picks"):
            # Los picks son de una cuenta: sin vincular no hay a quién
            # aplicar plan, límites ni retraso del plan Free.
            if not user:
                return [(chat_id, not_linked)]
            matches = source = None
            if matches_provider is not None:
                matches, source = matches_provider()
            result = service.build_recommendations(
                plan=plan, conn=conn, matches=matches, source=source)
            picks = [p for p in result["picks"]
                     if p["edge"] >= config.ALERT_MIN_EDGE]
            if not picks:
                return [(chat_id,
                         "⏳ Ahora mismo no hay apuestas con valor ≥ "
                         f"{config.ALERT_MIN_EDGE * 100:.0f}%. "
                         "Esperar también es parte del método 😉")]
            limit = config.ALERT_MAX_PICKS.get(plan, 2)
            return [(chat_id, format_digest(picks[:limit], plan))]

        return [(chat_id, HELP_TEXT)]
    finally:
        if not own:
            conn.close()


# ----------------------------------------------------------------- envío
async def send_message(chat_id: str, text: str,
                       client: httpx.AsyncClient | None = None) -> tuple[bool, str]:
    """Envía un mensaje. Devuelve ``(ok, error)`` sin lanzar excepciones."""
    if not config.telegram_enabled():
        return False, "TELEGRAM_BOT_TOKEN no configurado"
    close = client is None
    client = client or httpx.AsyncClient(timeout=config.ALERT_TIMEOUT)
    try:
        resp = await client.post(api_url("sendMessage"), json={
            "chat_id": chat_id, "text": text, "parse_mode": "HTML",
            "disable_web_page_preview": True})
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        if resp.status_code == 200 and data.get("ok"):
            return True, ""
        return False, str(data.get("description") or f"HTTP {resp.status_code}")
    except httpx.HTTPError as exc:
        return False, str(exc)
    finally:
        if close:
            await client.aclose()


def _should_unlink(error: str) -> bool:
    lowered = error.lower()
    return any(s in lowered for s in
               ("bot was blocked", "chat not found", "user is deactivated",
                "bot can't initiate"))


# --------------------------------------------------------- reglas configurables
def pick_event_start_ts(pick: dict[str, Any]) -> float | None:
    """Convierte ``commence_time`` ISO UTC o ``event_start`` a epoch."""
    if pick.get("event_start") is not None:
        try:
            return float(pick["event_start"])
        except (TypeError, ValueError):
            return None
    raw = str(pick.get("commence_time") or "").strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        return dt.datetime.fromisoformat(raw).timestamp()
    except ValueError:
        return None


def pick_matches_rule(pick: dict[str, Any], rule: dict[str, Any], *,
                      now: float | None = None) -> bool:
    """Evalúa si un pick cumple todos los filtros de una regla."""
    if not rule.get("enabled", True):
        return False
    plan = str(rule.get("plan") or "free")
    plan_min_edge = float(config.PLANS.get(plan, config.PLANS["free"])["min_edge"])
    edge_min = max(float(rule.get("edge_min", 0.03)), plan_min_edge)
    if float(pick.get("edge") or 0.0) < edge_min:
        return False

    odds = float(pick.get("odds") or pick.get("bet_odds") or 0.0)
    if odds < float(rule.get("odds_min", 1.01)) or odds > float(rule.get("odds_max", 100.0)):
        return False

    leagues = [x.strip() for x in (rule.get("leagues") or []) if str(x).strip()]
    if leagues and str(pick.get("league") or "") not in leagues:
        return False

    markets = [x.strip() for x in (rule.get("markets") or []) if str(x).strip()]
    pick_market = str(pick.get("market") or "h2h")
    if markets and pick_market not in markets:
        return False

    max_mins = rule.get("max_minutes_to_start")
    if max_mins is not None:
        start_ts = pick_event_start_ts(pick)
        if start_ts is None:
            return False
        ref_now = time.time() if now is None else float(now)
        delta_seconds = start_ts - ref_now
        if delta_seconds <= 0 or delta_seconds > float(max_mins) * 60.0:
            return False

    return True


def format_email_pick(pick: dict[str, Any], rule: dict[str, Any],
                      plan: str = "premium") -> tuple[str, str]:
    """Devuelve ``(asunto, cuerpo_texto)`` sin enlaces de afiliado."""
    event = f"{pick.get('home_team', '')} vs {pick.get('away_team', '')}".strip(" vs")
    if not event:
        event = str(pick.get("event") or "")
    edge_pct = float(pick.get("edge") or 0.0) * 100.0
    odds = float(pick.get("odds") or pick.get("bet_odds") or 0.0)
    subject = (f"[ApuestaEdge · {rule.get('name', 'Regla')}] "
               f"{pick.get('league', '')}: {pick.get('selection_label', '')} "
               f"@ {odds:.2f} ({edge_pct:+.1f}%)")
    direct_url = bookmaker_url(pick.get("bookmaker"))
    link_line = (f"Casa: {pick.get('bookmaker', '')} — {direct_url} "
                 "(enlace directo, sin código de afiliado)"
                 if direct_url else
                 f"Casa: {pick.get('bookmaker', '')} (sin enlace de afiliado)")
    lines = [
        f"Regla activa: {rule.get('name', 'Alerta')}",
        f"Liga: {pick.get('league', '')}",
        f"Evento: {event}",
        f"Selección: {pick.get('selection_label', '')}",
        f"Cuota: {odds:.2f} · Edge: {edge_pct:+.2f}%",
        f"Prob. modelo: {float(pick.get('model_prob') or 0.0) * 100:.1f}% vs "
        f"mercado: {float(pick.get('market_prob') or 0.0) * 100:.1f}%",
        f"Inicio: {pick.get('commence_time') or 'por confirmar'} UTC",
        link_line,
    ]
    kelly = pick.get("kelly") or {}
    if plan == "premium" and kelly.get("stake_pct"):
        lines.append(f"Stake Kelly 1/4: {kelly['stake_pct']:.2f}% "
                     f"({kelly.get('stake_units', 0.0):.2f} u.)")
    lines += [
        "",
        "Gestiona o pausa tus reglas en /alertas.",
        "+18 · Los pronósticos implican riesgo y los datos pasados no "
        "garantizan resultados futuros.",
    ]
    return subject, "\n".join(lines)


def send_email_alert(to_email: str, pick: dict[str, Any],
                     rule: dict[str, Any], plan: str = "free") -> tuple[bool, str, str]:
    """Envía alerta por SMTP si está configurado; si no, la registra en bandeja."""
    subject, body = format_email_pick(pick, rule, plan=plan)
    if not config.email_enabled():
        return True, "recorded", "Registrada en tu historial de alertas web"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.SMTP_FROM
    msg["To"] = to_email
    msg.set_content(body)
    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10) as smtp:
            if config.SMTP_USER and config.SMTP_PASSWORD:
                smtp.starttls()
                smtp.login(config.SMTP_USER, config.SMTP_PASSWORD)
            smtp.send_message(msg)
        return True, "sent", "Enviada por correo SMTP"
    except Exception as exc:  # noqa: BLE001
        return False, "failed", str(exc)


async def dispatch_alert_rules(
    conn, *, matches=None, source: str | None = None,
    client: httpx.AsyncClient | None = None,
    now: float | None = None,
) -> dict[str, int]:
    """Evalúa las reglas activas y entrega por Email y Telegram sin duplicar.

    Reutiliza el parte de partidos y respeta el retraso de 2 h del plan Free
    porque pide las recomendaciones de ``free`` y ``premium`` a ``service``.
    """
    rules = db.alert_rules_active(conn)
    if not rules:
        return {"rules": 0, "sent": 0, "email": 0, "telegram": 0}

    by_plan: dict[str, list[dict]] = {}
    for plan in {str(r.get("plan") or "free") for r in rules}:
        res = service.build_recommendations(
            plan=plan, conn=conn, matches=matches, source=source)
        by_plan[plan] = list(res.get("picks") or [])

    sent_total = email_sent = tg_sent = 0
    for rule in rules:
        plan = str(rule.get("plan") or "free")
        picks = by_plan.get(plan, [])
        limit = config.ALERT_MAX_PICKS.get(plan, 1)
        matched = [p for p in picks if pick_matches_rule(p, rule, now=now)][:limit]
        for pick in matched:
            event_name = (f"{pick.get('home_team', '')} vs "
                          f"{pick.get('away_team', '')}").strip(" vs")
            start_ts = pick_event_start_ts(pick)
            match_id = str(pick.get("match_id") or "")
            selection = str(pick.get("selection") or "")

            if rule.get("channel_email"):
                if not db.alert_delivery_exists(
                        conn, rule["id"], "email", match_id, selection):
                    ok, status, detail = send_email_alert(
                        rule["email"], pick, rule, plan=plan)
                    if ok:
                        db.alert_delivery_record(
                            conn, rule_id=rule["id"], email=rule["email"],
                            channel="email", match_id=match_id,
                            selection=selection,
                            league=str(pick.get("league") or ""),
                            event=event_name,
                            selection_label=str(pick.get("selection_label") or ""),
                            bookmaker=str(pick.get("bookmaker") or ""),
                            odds=float(pick.get("odds") or 0.0),
                            edge=float(pick.get("edge") or 0.0),
                            event_start=start_ts, status=status, detail=detail)
                        sent_total += 1
                        email_sent += 1

            if rule.get("channel_telegram") and rule.get("telegram_chat_id"):
                if not db.alert_delivery_exists(
                        conn, rule["id"], "telegram", match_id, selection):
                    chat_id = str(rule["telegram_chat_id"])
                    ok, err = await send_message(
                        chat_id, format_pick(pick, plan), client)
                    if ok:
                        db.alert_delivery_record(
                            conn, rule_id=rule["id"], email=rule["email"],
                            channel="telegram", match_id=match_id,
                            selection=selection,
                            league=str(pick.get("league") or ""),
                            event=event_name,
                            selection_label=str(pick.get("selection_label") or ""),
                            bookmaker=str(pick.get("bookmaker") or ""),
                            odds=float(pick.get("odds") or 0.0),
                            edge=float(pick.get("edge") or 0.0),
                            event_start=start_ts, status="sent",
                            detail="Enviada por Telegram")
                        db.alert_mark_sent(
                            conn, chat_id, match_id, selection,
                            float(pick.get("edge") or 0.0))
                        sent_total += 1
                        tg_sent += 1
                    elif _should_unlink(err):
                        db.unlink_telegram(conn, chat_id)

    return {"rules": len(rules), "sent": sent_total,
            "email": email_sent, "telegram": tg_sent}


class TelegramNotifier:
    """Polling de ``getUpdates`` + resumen periódico de picks con valor.

    ``matches_provider`` es la función del servidor que devuelve
    ``(partidos, fuente)`` con su caché y su respaldo. Se usa UNA vez por
    ciclo y por comando: antes cada suscriptor disparaba sus propias
    llamadas a The Odds API y se quemaban créditos innecesarios.
    """

    def __init__(self, matches_provider=None) -> None:
        self.offset = 0
        self.matches_provider = matches_provider

    # ------------------------------------------------------------ bot
    async def handle_updates(self, updates: list[dict],
                             client: httpx.AsyncClient) -> None:
        for update in updates:
            self.offset = max(self.offset, int(update.get("update_id", 0)) + 1)
            try:
                for chat_id, text in process_update(
                        update, matches_provider=self.matches_provider):
                    ok, err = await send_message(chat_id, text, client)
                    if not ok:
                        log.warning("Telegram alerta no enviada: %s", err)
            except Exception:  # noqa: BLE001 - un update malo no rompe el loop
                log.exception("Error procesando update %s", update.get("update_id"))

    async def poll_once(self, client: httpx.AsyncClient) -> None:
        resp = await client.get(api_url("getUpdates"), params={
            "offset": self.offset, "timeout": config.TELEGRAM_POLL_TIMEOUT,
            "allowed_updates": '["message"]'}, timeout=config.TELEGRAM_POLL_TIMEOUT + 10)
        if resp.status_code != 200:
            raise RuntimeError(f"getUpdates HTTP {resp.status_code}")
        data = resp.json()
        if data.get("ok"):
            await self.handle_updates(data.get("result", []), client)

    async def run(self) -> None:
        """Bucle de polling (se cancela con la lifespan de la app)."""
        async with httpx.AsyncClient(timeout=config.TELEGRAM_POLL_TIMEOUT + 15) as client:
            while True:
                try:
                    await self.poll_once(client)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001 - reconecta y sigue
                    log.warning("Fallo de polling Telegram: %s", exc)
                    await asyncio.sleep(5)

    # --------------------------------------------------------- resumen
    async def send_digest(self, client: httpx.AsyncClient | None = None) -> int:
        """Envía los picks con valor a cada suscriptor vinculado.

        Dedupe por (chat, partido, selección): nunca repite un pick.
        Devuelve el número de mensajes enviados.
        """
        if not config.telegram_enabled():
            return 0
        close = client is None
        client = client or httpx.AsyncClient(timeout=config.ALERT_TIMEOUT)
        sent = 0
        # Un solo parte de partidos por ciclo, compartido por todos los
        # suscriptores (cada llamada a la API cuesta créditos).
        matches = source = None
        if self.matches_provider is not None:
            try:
                matches, source = self.matches_provider()
            except Exception:  # noqa: BLE001 - sin datos no se alerta
                log.exception("No se pudo obtener el parte de partidos")
                matches, source = [], "unavailable"
        try:
            conn = db.connect()
            try:
                recipients = [(u["telegram_chat_id"], u["plan"])
                              for u in db.users_with_telegram(conn)]
                if not recipients and config.TELEGRAM_BROADCAST_CHAT:
                    recipients = [(config.TELEGRAM_BROADCAST_CHAT, "premium")]
                for chat_id, plan in recipients:
                    result = service.build_recommendations(
                        plan=plan, conn=conn, matches=matches, source=source)
                    picks = [p for p in result["picks"]
                             if p["edge"] >= config.ALERT_MIN_EDGE]
                    limit = config.ALERT_MAX_PICKS.get(plan, 2)
                    for pick in picks[:limit]:
                        if db.alert_already_sent(conn, chat_id,
                                                 pick["match_id"],
                                                 pick["selection"]):
                            continue  # ya enviado: no molestar
                        ok, err = await send_message(
                            chat_id, format_pick(pick, plan), client)
                        if ok:
                            # Se marca SOLO tras el envío: si falla la red,
                            # el próximo ciclo lo reintenta en lugar de
                            # perder el aviso para siempre.
                            db.alert_mark_sent(conn, chat_id, pick["match_id"],
                                               pick["selection"], pick["edge"])
                            sent += 1
                        else:
                            log.warning("No se pudo alertar a %s: %s", chat_id, err)
                            if _should_unlink(err):
                                db.unlink_telegram(conn, chat_id)
                                break  # chat muerto: al siguiente ciclo
                rules_res = await dispatch_alert_rules(
                    conn, matches=matches, source=source, client=client)
                sent += int(rules_res.get("sent") or 0)
            finally:
                conn.close()
        finally:
            if close:
                await client.aclose()
        return sent


async def alert_loop(notifier: TelegramNotifier,
                     interval: int | None = None) -> None:
    """Scheduler: primer aviso a los 20 s y después cada ``interval`` s."""
    interval = interval or config.ALERT_INTERVAL_SECONDS
    await asyncio.sleep(20)
    while True:
        try:
            n = await notifier.send_digest()
            if n:
                log.info("[telegram] %s picks enviados", n)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            log.exception("Error en el ciclo de alertas")
        await asyncio.sleep(interval)
