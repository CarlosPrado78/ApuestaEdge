"""API y servidor web de ApuestaEdge.

Ejecutar desde ``apuesta_edge``:

    uvicorn app.main:app --reload --port 8000

y abrir http://localhost:8000
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import secrets
import time
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import (auth, billing, config, db, explain, ledger, notifier, providers,
               service)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Arranque: historial demo + bot de Telegram (si hay token)."""
    conn = db.connect()
    try:
        if config.ALLOW_SAMPLE_DATA:
            # Solo en desarrollo/tests: nunca en producción.
            seeded = db.seed_history(conn)
            if seeded:
                print(f"[apuesta_edge] historial demo cargado: {seeded} picks")
        else:
            removed = db.clear_history(conn)
            if removed:
                print(f"[apuesta_edge] historial simulado eliminado: "
                      f"{removed} filas (el registro real manda)")
        db.seed_model_version(
            conn, config.MODEL_VERSION,
            "Modelo Elo + Poisson con de-vig Shin y Kelly fraccional 1/4.",
            changes="Versión inicial del registro público.")
    finally:
        conn.close()

    tasks: list[asyncio.Task] = []
    if config.telegram_enabled():
        # Comparte la caché de partidos con la web: el ciclo de alertas y los
        # comandos del bot no gastan créditos de la API por suscriptor.
        tg = notifier.TelegramNotifier(matches_provider=_get_matches)
        tasks.append(asyncio.create_task(tg.run()))
        tasks.append(asyncio.create_task(notifier.alert_loop(tg)))
        print(f"[apuesta_edge] alertas Telegram activas "
              f"(cada {config.ALERT_INTERVAL_SECONDS}s, "
              f"edge ≥ {config.ALERT_MIN_EDGE:.0%})")
    if config.ODDS_API_KEY:
        # Registro público: publica picks antes del evento, congela cierres,
        # asienta resultados y ancla la cadena una vez al día.
        tasks.append(asyncio.create_task(
            ledger.run_loop(matches_provider=_get_matches)))
        print(f"[apuesta_edge] registro activo "
              f"(cada {config.LEDGER_PUBLISH_INTERVAL}s, "
              f"edge ≥ {config.LEDGER_MIN_EDGE:.0%})")
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


app = FastAPI(
    title="ApuestaEdge",
    description="Recomendaciones de apuestas con valor esperado positivo "
                "basadas en modelos estadísticos (Elo, Poisson, Kelly, EV+).",
    version="1.0.0",
    lifespan=lifespan,
)

# Cache para no repetir llamadas a la API de cuotas (cada llamada cuesta
# créditos: ver config.MATCHES_CACHE_TTL).
_CACHE: dict = {"ts": 0.0, "matches": None, "source": None, "updated_at": 0.0}
CACHE_TTL = config.MATCHES_CACHE_TTL

# Último parte real guardado en la BD: sobrevive a cortes de cuota o de
# red sin caer en eventos de demostración.
_SNAPSHOT_KEY = "live_matches_snapshot"
_SNAPSHOT_MAX_AGE = 7 * 24 * 3600.0  # 7 días: más allá, caduca


def _save_live_snapshot(matches: list[dict]) -> None:
    try:
        db.kv_set(_SNAPSHOT_KEY, json.dumps(
            {"ts": time.time(), "matches": matches}, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001 - el respaldo es best-effort
        print(f"[apuesta_edge] no se pudo guardar el parte en vivo: {exc}")


def _load_live_snapshot() -> tuple[list[dict], str, float] | None:
    """Último parte real, sin eventos que ya hayan empezado."""
    try:
        row = db.kv_get(_SNAPSHOT_KEY)
        if not row:
            return None
        payload = json.loads(row[0])
        ts = float(payload.get("ts", 0.0))
        if not ts or time.time() - ts > _SNAPSHOT_MAX_AGE:
            return None
        cutoff = time.time() - 3600.0  # se descartan eventos ya iniciados
        fresh = [m for m in payload.get("matches", [])
                 if _commence_ts(m.get("commence_time", "")) > cutoff]
        if not fresh:
            return None
        return fresh, "live_cached", ts
    except Exception:  # noqa: BLE001 - respaldo best-effort
        return None


def _commence_ts(iso: str) -> float:
    try:
        return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError):
        return 0.0


def _get_matches() -> tuple[list[dict], str]:
    now = time.time()
    ttl = CACHE_TTL
    # Con la cuota casi agotada se refresca menos para no quedarse sin
    # créditos antes del día 1.
    quota = providers.LAST_DIAG.get("quota_remaining")
    if isinstance(quota, int) and 0 < quota < config.QUOTA_SOFT_FLOOR:
        ttl = max(ttl, 6 * 3600.0)
    if _CACHE["matches"] is None or now - _CACHE["ts"] > ttl:
        matches, source = providers.get_matches()
        updated_at = now
        if source == "error":
            # Sin datos en vivo: último parte real guardado, si existe.
            snapshot = _load_live_snapshot()
            if snapshot:
                matches, source, updated_at = snapshot
            elif config.ALLOW_SAMPLE_DATA:
                matches, source = providers.load_sample_matches(), "sample"
            else:
                # Nunca eventos inventados en producción: se indica
                # explícitamente que no hay datos en vivo.
                matches, source = [], "unavailable"
        elif source == "live":
            _save_live_snapshot(matches)
        # Deportes ocultos temporalmente (sin datos reales) fuera del radar.
        if config.HIDDEN_SPORTS:
            matches = [m for m in matches
                       if m.get("sport_group") not in config.HIDDEN_SPORTS]
        _CACHE.update(ts=now, matches=matches, source=source,
                      updated_at=updated_at)
    return _CACHE["matches"], _CACHE["source"]


def _resolve_plan(request: Request, requested: str) -> str:
    """Plan efectivo, con bloqueo del lado del servidor.

    - ``free`` siempre permitido.
    - ``premium``: requiere sesión con plan premium cuando Stripe está
      configurado (402 si no). Sin claves de Stripe corre en modo demo
      (todo desbloqueado, etiquetado como demo en la API).
    """
    if requested == "free":
        return "free"
    if auth.is_premium(request):
        return "premium"
    if billing.stripe_enabled():
        raise HTTPException(
            status_code=402,
            detail={"error": "premium_required",
                    "message": "El plan Premium requiere una suscripción activa.",
                    "upgrade": "/api/billing/checkout"})
    return "premium"  # modo demo (sin claves Stripe)


@app.get("/api/health")
def health() -> dict:
    matches, source = _get_matches()
    # Render expone el commit desplegado: permite verificar qué versión corre.
    commit = (os.environ.get("RENDER_GIT_COMMIT") or "")[:7]
    return {"status": "ok", "matches": len(matches), "source": source,
            "source_updated_at": _CACHE.get("updated_at") or None,
            "allow_sample": config.ALLOW_SAMPLE_DATA,
            "live_api_key": bool(config.ODDS_API_KEY),
            "odds_api": dict(providers.LAST_DIAG),
            "billing": "stripe" if billing.stripe_enabled() else "demo",
            "premium_locked": billing.stripe_enabled(),
            "database": "postgres" if db.using_postgres() else "sqlite",
            "commit": commit}


@app.get("/api/matches")
def matches(request: Request,
            sport: str | None = Query(None, description="soccer|basketball|tennis|americanfootball|boxing|baseball|hockey|formula1|motogp|horseracing"),
            lang: str = Query("es", pattern="^(es|en)$")) -> dict:
    all_matches, source = _get_matches()
    # El edge es el veredicto del modelo (contenido Premium). Se oculta a
    # quien no tenga sesión Premium para no regalarlo fuera de los picks.
    include_edge = auth.is_premium(request)
    data = service.matches_overview(all_matches, lang=lang,
                                    include_edge=include_edge)
    if sport:
        data = [m for m in data if m["sport"] == sport]
    return {"source": source, "count": len(data), "edge_visible": include_edge,
            "matches": data}


@app.get("/api/recommendations")
def recommendations(
    request: Request,
    plan: str | None = Query(None, pattern="^(free|premium)$"),
    sport: str | None = Query(None, description="soccer|basketball|tennis|americanfootball|boxing|baseball|hockey|formula1|motogp|horseracing"),
    min_edge: float | None = Query(None, ge=0.0, le=0.5),
    bankroll: float = Query(config.DEFAULT_BANKROLL, gt=0),
    lang: str = Query("es", pattern="^(es|en)$"),
) -> dict:
    # Sin ?plan explícito se usa el plan real de la cuenta (o free si es anónimo).
    if plan is None:
        plan = "premium" if auth.is_premium(request) else "free"
    plan = _resolve_plan(request, plan)   # 402 si premium sin suscripción
    matches, source = _get_matches()
    try:
        result = service.build_recommendations(
            plan=plan, sport=sport, min_edge=min_edge,
            bankroll=bankroll, matches=matches, source=source, lang=lang)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result["demo_mode"] = not billing.stripe_enabled()
    return result


@app.get("/api/performance")
def performance(sport: str | None = Query(None)) -> dict:
    if sport in config.HIDDEN_SPORTS:
        return {"sample": 0, "message": "Deporte no disponible temporalmente."}
    conn = db.connect()
    try:
        history = db.fetch_history(conn, sport)
        history = [h for h in history
                   if h["sport"] not in config.HIDDEN_SPORTS]
        if not history:
            return {"sample": 0, "message": "Sin historial todavía."}
        return explain.performance_summary(history, sport)
    finally:
        conn.close()


@app.get("/api/performance/by-sport")
def performance_by_sport() -> dict:
    conn = db.connect()
    try:
        history = db.fetch_history(conn)
        history = [h for h in history
                   if h["sport"] not in config.HIDDEN_SPORTS]
        sports = sorted({h["sport"] for h in history})
        return {"all": explain.performance_summary(history),
                "by_sport": {s: explain.performance_summary(
                    [h for h in history if h["sport"] == s], s) for s in sports}}
    finally:
        conn.close()


@app.get("/api/methodology")
def methodology() -> dict:
    return {
        "pipeline": [
            "Ratings Elo por deporte (ventaja de localía: 60 pts fútbol, 50 básquet, 40 fútbol americano, 25 béisbol; 0 en tenis, boxeo y carreras).",
            "Fútbol: tasas de goles Poisson derivadas del Elo -> matriz de marcadores -> 1X2, líneas y ambos marcan.",
            "Básquet, tenis, fútbol americano y béisbol: probabilidad logística de victoria del Elo (moneyline).",
            "Boxeo: Elo en terreno neutral (sin localía) ->2 boxeadores; F1, MotoGP y caballos: Elo de N participantes -> Bradley-Terry (ganador de la carrera).",
            "Desvigado de cada casa con método de potencias (Shin) y consenso entre casas.",
            "Edge = P(modelo) − P(mercado). Se filtra por edge mínimo del plan.",
            "Valor esperado EV = P(modelo) × cuota − 1; solo EV > 0 entra al radar.",
            "Confianza = P(modelo > mercado) con normal: sigma del modelo (n_efectivo=60) + dispersión entre casas.",
            "Stake = 0.25 × Kelly completo, tope 3% del bankroll, mínimo 0.5%.",
            "Cada pick queda registrado y se evalúa contra el resultado real (ROI, CLV, drawdown, test binomial).",
        ],
        "why_it_works": [
            "No acertamos más que el mercado: buscamos que la probabilidad estimada supere a la que el precio exige.",
            "Sin EV+ ninguna apuesta es estadísticamente defendible, aunque salga.",
            "El CLV mide si entramos mejor que el cierre; es el predictor más fiable de rentabilidad futura.",
            "El Kelly fraccional maximiza el crecimiento del bankroll limitando la varianza.",
            "La publicación del track record (ganado y perdido) permite auditar cada afirmación.",
        ],
        "honest_limits": [
            "Ningún sistema recomienda «sin fallas»: incluso con 55-60% de probabilidad real se pierde a menudo.",
            "Las probabilidades son estimaciones con incertidumbre; el bando del modelo no es un hecho.",
            "El mercado es muy eficiente: los edges grandes suelen ser información que el modelo no tiene (lesiones, motivación).",
            "Las rachas negativas son normales; el criterio es el ROI de cientos de apuestas, no el de una semana.",
            "Fórmula 1, MotoGP y carreras de caballos funcionan con datos de demostración: The Odds API no cubre esos deportes, hasta que se conecte otro proveedor no hay cuotas en vivo.",
            "Cuanto más pequeña la muestra de backtest de un deporte (combates, carreras), más preliminares son sus cifras.",
        ],
        "models": explain.MODEL_LABELS,
        "sports_labels": explain.SPORT_LABELS,
    }


@app.get("/api/plans")
def plans(lang: str = Query("es", pattern="^(es|en)$")) -> dict:
    localized = {}
    for key, plan in config.PLANS.items():
        item = dict(plan)
        if lang == "en":
            item["name"] = plan.get("name_en", plan["name"])
            item["features"] = plan.get("features_en", plan["features"])
        localized[key] = item
    return {"plans": localized,
            "billing": "stripe" if billing.stripe_enabled() else "demo",
            "premium_locked": billing.stripe_enabled()}


class SubscribeIn(BaseModel):
    email: str = Field(min_length=5, max_length=200)
    plan: str = Field(default="free", pattern="^(free|premium)$")


class LoginIn(BaseModel):
    email: str = Field(min_length=5, max_length=200)


def _valid_email(email: str) -> bool:
    return "@" in email and "." in email.split("@")[-1]


async def _checkout_or_demo(request: Request, email: str) -> dict:
    """Premium: pago con Stripe si está configurado, si no modo demo."""
    if billing.stripe_enabled():
        try:
            url = await billing.create_checkout(email, auth.origin_of(request))
        except Exception as exc:  # noqa: BLE001 - cualquier fallo de red
            raise HTTPException(
                status_code=502,
                detail=f"No se pudo iniciar el pago con Stripe: {exc}") from exc
        return {"activated": False, "mode": "stripe", "checkout_url": url,
                "message": "Te redirigimos a Stripe para completar el pago."}
    # Modo demo (sin claves): se activa al instante.
    conn = db.connect()
    try:
        db.set_user_plan(conn, email, "premium")
    finally:
        conn.close()
    return {"activated": True, "mode": "demo", "plan": "premium",
            "message": "¡Premium activado en modo demo! "
                       "(Configura STRIPE_SECRET_KEY para cobrar de verdad)."}


@app.post("/api/subscribe")
async def subscribe(payload: SubscribeIn, request: Request) -> dict:
    """Alta de suscriptor: Free informativo; Premium crea sesión de Stripe.

    Para pagar hace falta haber iniciado sesión (email + contraseña).
    """
    if not _valid_email(payload.email):
        raise HTTPException(status_code=400, detail="Correo inválido.")
    email = payload.email.strip().lower()

    if payload.plan != "premium":
        conn = db.connect()
        try:
            result = db.add_subscriber(conn, email, "free")
            db.create_user(conn, email)
        finally:
            conn.close()
        return {**result, "plan": "free", "email": email,
                "activated": True, "demo": not billing.stripe_enabled(),
                "message": "Cuenta Free creada. Inicia sesión para entrar."}

    # Premium: hace falta sesión autenticada.
    user = auth.user_from_request(request)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Inicia sesión (o crea tu cuenta) antes de suscribirte.")
    email = user["email"]

    conn = db.connect()
    try:
        result = db.add_subscriber(conn, email, "premium")
    finally:
        conn.close()

    upgrade = await _checkout_or_demo(request, email)
    result.update(upgrade)
    conn = db.connect()
    try:
        user = db.get_user_by_email(conn, email) or user
    finally:
        conn.close()
    if upgrade.get("mode") == "stripe":
        result["message"] += " Tu cuenta pasará a Premium al confirmarse el pago."
    result["plan"] = user.get("plan", "free")
    result["email"] = email
    result["demo"] = not billing.stripe_enabled()
    return result


async def _recover_premium(user: dict) -> dict:
    """Reengancha la suscripción activa de Stripe para ese correo.

    Red de seguridad: si la BD se recreó (Render Free), el usuario cambió de
    dispositivo o pagó en otro servidor, al entrar recupera el Premium que ya
    tiene pagado sin tocar SQL a mano.
    """
    if not billing.stripe_enabled():
        return user
    if user.get("plan") == "premium" or user.get("stripe_subscription_id"):
        return user
    try:
        found = await billing.find_active_subscription(user["email"])
    except Exception:  # noqa: BLE001 - Stripe caído: se entra como Free
        return user
    if not found:
        return user
    sub = found["subscription"]
    conn = db.connect()
    try:
        db.save_stripe_ids(
            conn, user["email"], customer_id=found.get("customer_id"),
            subscription_id=str(sub.get("id") or "") or None)
        db.set_subscription_state(
            conn, user["id"], plan="premium",
            period_end=billing.subscription_period_end(sub),
            cancel_at_period_end=bool(sub.get("cancel_at_period_end")))
        return db.get_user_by_email(conn, user["email"]) or user
    finally:
        conn.close()


def _set_session_cookie(response, request: Request, token: str) -> None:
    """Cookie de sesión (HttpOnly: el JS no puede leerla ni filtrarla)."""
    secure = (request.headers.get("x-forwarded-proto", request.url.scheme)
              == "https")
    response.set_cookie(
        auth.COOKIE_NAME, token, max_age=60 * 60 * 24 * 180, path="/",
        httponly=True, samesite="lax", secure=secure)


class RegisterIn(BaseModel):
    email: str = Field(min_length=5, max_length=200)
    password: str = Field(min_length=1, max_length=200)


class LoginIn(BaseModel):
    email: str = Field(min_length=5, max_length=200)
    password: str = Field(min_length=1, max_length=200)


@app.post("/api/auth/register")
async def register(payload: RegisterIn, request: Request) -> dict:
    """Crea una cuenta con email + contraseña.

    Si el email ya tiene cuenta, se rechaza (no se revela si existía antes).
    """
    email = payload.email.strip().lower()
    if not _valid_email(email):
        raise HTTPException(status_code=400, detail="Correo inválido.")
    if len(payload.password) < config.PASSWORD_MIN_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"La contraseña debe tener al menos "
                   f"{config.PASSWORD_MIN_LENGTH} caracteres.")

    conn = db.connect()
    try:
        existing = db.get_user_by_email(conn, email)
        if existing and db.has_password(conn, email):
            raise HTTPException(
                status_code=409,
                detail="Ya existe una cuenta con ese correo. Inicia sesión.")
        user = db.create_user(conn, email)
        db.set_user_password(conn, email, auth.hash_password(payload.password))
        user = db.get_user_by_email(conn, email) or user
    finally:
        conn.close()

    user = await _recover_premium(user)
    response = JSONResponse({
        "ok": True, "email": user.get("email"), "plan": user.get("plan"),
        "token": user.get("token", ""),
        "demo": not billing.stripe_enabled()})
    _set_session_cookie(response, request, user.get("token", ""))
    return response


@app.post("/api/auth/login")
async def login(payload: LoginIn, request: Request) -> dict:
    """Acceso con email + contraseña."""
    email = payload.email.strip().lower()
    if not _valid_email(email):
        raise HTTPException(status_code=400, detail="Correo inválido.")

    conn = db.connect()
    try:
        user = db.get_user_by_email(conn, email)
        stored_hash = db.get_password_hash(conn, email) if user else None
    finally:
        conn.close()

    if not user or not auth.verify_password(payload.password, stored_hash):
        raise HTTPException(status_code=401,
                            detail="Correo o contraseña incorrectos.")

    user = await _recover_premium(user)
    # Releer por si _recover_premium actualizó el plan.
    conn = db.connect()
    try:
        user = db.get_user_by_email(conn, user["email"]) or user
    finally:
        conn.close()

    response = JSONResponse({
        "ok": True, "email": user.get("email"), "plan": user.get("plan"),
        "token": user.get("token", ""),
        "demo": not billing.stripe_enabled()})
    _set_session_cookie(response, request, user.get("token", ""))
    return response


@app.get("/api/auth/me")
def me(request: Request) -> dict:
    user = auth.user_from_request(request)
    if not user:
        return {"authenticated": False, "plan": "free",
                "billing": "stripe" if billing.stripe_enabled() else "demo",
                "demo": not billing.stripe_enabled()}
    return {"authenticated": True, "email": user["email"], "plan": user["plan"],
            "billing": "stripe" if billing.stripe_enabled() else "demo",
            "has_stripe_customer": bool(user.get("stripe_customer_id")),
            "demo": not billing.stripe_enabled()}


@app.post("/api/auth/logout")
def logout() -> JSONResponse:
    """Cierra sesión: el cliente borra el token y aquí se limpia la cookie."""
    response = JSONResponse({"ok": True, "message": "Sesión cerrada."})
    response.delete_cookie(auth.COOKIE_NAME, path="/")
    return response


@app.post("/api/billing/checkout")
async def checkout(request: Request) -> dict:
    """Inicia el pago Premium (solo con claves de Stripe)."""
    if not billing.stripe_enabled():
        raise HTTPException(status_code=400, detail={
            "error": "stripe_not_configured",
            "message": "Sin STRIPE_SECRET_KEY la app corre en modo demo: "
                       "el Premium se activa directo desde /api/subscribe."})
    body = await request.json()
    email = str(body.get("email", "")).strip().lower()
    if not _valid_email(email):
        raise HTTPException(status_code=400, detail="Correo inválido.")
    conn = db.connect()
    try:
        db.create_user(conn, email)
        db.add_subscriber(conn, email, "premium")
    finally:
        conn.close()
    url = await billing.create_checkout(email, auth.origin_of(request))
    return {"checkout_url": url, "mode": "stripe"}


class ConfirmIn(BaseModel):
    session_id: str = Field(min_length=5, max_length=200)


@app.post("/api/billing/confirm")
async def billing_confirm(payload: ConfirmIn, request: Request) -> dict:
    """Confirma el pago al volver de Stripe (sin depender del webhook).

    El ``session_id`` de Checkout es impredecible y solo lo conoce el
    comprador, así que sirve como prueba para activar su cuenta. Devuelve un
    token de sesión para que el navegador quede autenticado incluso si perdió
    el token al cambiar de dispositivo.
    """
    if not billing.stripe_enabled():
        raise HTTPException(status_code=400, detail={
            "error": "stripe_not_configured",
            "message": "Stripe no está configurado (modo demo)."})
    try:
        session = await billing.retrieve_checkout_session(payload.session_id)
    except Exception as exc:  # noqa: BLE001 - error de red o ID inválido
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo verificar el pago con Stripe: {exc}") from exc

    paid = (session.get("payment_status") in ("paid", "no_payment_required")
            or session.get("status") == "complete")
    if not paid:
        return {"ok": False, "activated": False,
                "status": session.get("status"),
                "message": "Stripe aún no ha confirmado el pago."}

    email = billing.email_from_session(session)
    if not email:
        raise HTTPException(status_code=400, detail={
            "error": "no_email",
            "message": "La sesión de pago no trae un correo válido."})

    customer_id = str(session.get("customer") or "") or None
    subscription_id = str(session.get("subscription") or "") or None
    sub: dict | None = None
    if subscription_id:
        try:
            sub = await billing.retrieve_subscription(subscription_id)
        except Exception:  # noqa: BLE001 - la sesión ya prueba el pago
            sub = None

    status = str((sub or {}).get("status") or "active")
    active = status in billing.ACTIVE_SUB_STATUSES
    period_end = billing.subscription_period_end(sub or {})
    cancel_at_end = bool((sub or {}).get("cancel_at_period_end"))

    conn = db.connect()
    try:
        user = db.get_user_by_email(conn, email) or db.create_user(conn, email)
        if customer_id or subscription_id:
            db.save_stripe_ids(conn, email, customer_id=customer_id,
                               subscription_id=subscription_id)
        db.set_subscription_state(
            conn, user["id"], plan="premium" if active else "free",
            period_end=period_end, cancel_at_period_end=cancel_at_end)
        user = db.get_user_by_email(conn, email) or user
    finally:
        conn.close()

    return {"ok": True, "received": True, "activated": active,
            "email": user.get("email", email),
            "plan": user.get("plan", "free"),
            "token": user.get("token", ""),
            "status": status}


@app.post("/api/billing/webhook")
async def stripe_webhook(request: Request) -> dict:
    """Webhook de Stripe: activa y **desactiva** el Premium.

    Eventos gestionados:
    - ``checkout.session.completed``      → activa Premium + guarda IDs.
    - ``customer.subscription.updated``   → renueva/baja según ``status``.
    - ``customer.subscription.deleted``   → vuelve a Free (cancelación).
    """
    secret = billing.webhook_secret()
    if not secret:
        raise HTTPException(status_code=400, detail="STRIPE_WEBHOOK_SECRET no configurado.")
    payload = await request.body()
    header = request.headers.get(billing.SIGNATURE_HEADER, "")
    if not billing.verify_signature(payload, header, secret):
        raise HTTPException(status_code=400, detail="Firma inválida.")
    try:
        event = billing.parse_event(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Payload inválido.") from exc

    etype = event.get("type", "")
    if etype not in ("checkout.session.completed",
                     "customer.subscription.created",
                     "customer.subscription.updated",
                     "customer.subscription.deleted"):
        return {"received": True, "action": "ignored"}

    sub = billing.subscription_from_event(event)
    if not sub:
        return {"received": True, "action": "no_subscription"}

    conn = db.connect()
    try:
        # Localiza al usuario: por email (metadata) o por los IDs guardados.
        user = None
        if sub["email"]:
            user = db.get_user_by_email(conn, sub["email"])
        if user is None:
            user = db.user_by_stripe_ids(
                conn, customer_id=sub["customer_id"] or None,
                subscription_id=sub["subscription_id"] or None)
        if user is None:
            return {"received": True, "action": "unknown_user"}

        if etype == "checkout.session.completed":
            db.save_stripe_ids(conn, user["email"],
                               customer_id=sub["customer_id"] or None,
                               subscription_id=sub["subscription_id"] or None)
            db.set_subscription_state(
                conn, user["id"], plan="premium",
                period_end=sub["period_end"],
                cancel_at_period_end=sub["cancel_at_period_end"])
            action = "activated"
        elif sub["status"] in billing.ACTIVE_SUB_STATUSES:
            # Renovación o cambio de configuración: sigue en Premium.
            db.save_stripe_ids(conn, user["email"],
                               customer_id=sub["customer_id"] or None,
                               subscription_id=sub["subscription_id"] or None)
            db.set_subscription_state(
                conn, user["id"], plan="premium",
                period_end=sub["period_end"],
                cancel_at_period_end=sub["cancel_at_period_end"])
            action = "renewed" if not sub["cancel_at_period_end"] \
                else "cancel_scheduled"
        else:
            # canceled / unpaid / incomplete_expired → Free.
            db.set_subscription_state(conn, user["id"], plan="free",
                                      period_end=None,
                                      cancel_at_period_end=False)
            action = "deactivated"
        return {"received": True, "action": action, "email": user["email"],
                "activated": action in ("activated", "renewed",
                                        "cancel_scheduled")}
    finally:
        conn.close()


@app.get("/api/billing/subscription")
async def subscription_status(request: Request) -> dict:
    """Estado de la suscripción del usuario (para gestionarla en la web)."""
    user = auth.user_from_request(request)
    if not user:
        return {"authenticated": False, "billing": "demo" if not billing.stripe_enabled() else "stripe"}
    conn = db.connect()
    try:
        row = db.get_user_by_email(conn, user["email"]) or {}
    finally:
        conn.close()
    period_end = row.get("sub_current_period_end")
    cancel_at_end = bool(row.get("sub_cancel_at_period_end"))
    plan = row.get("plan", "free")

    # Autorreparación: si falta la fecha de renovación (p. ej. una compra
    # anterior a este cambio), se consulta Stripe una sola vez y se guarda.
    if (billing.stripe_enabled() and period_end is None
            and row.get("stripe_subscription_id")):
        try:
            live = await billing.retrieve_subscription(row["stripe_subscription_id"])
        except Exception:  # noqa: BLE001 - si Stripe falla, se responde lo guardado
            live = None
        if live:
            period_end = billing.subscription_period_end(live)
            cancel_at_end = bool(live.get("cancel_at_period_end"))
            status = str(live.get("status") or "")
            plan = "premium" if status in billing.ACTIVE_SUB_STATUSES else "free"
            conn = db.connect()
            try:
                db.set_subscription_state(
                    conn, row["id"], plan=plan, period_end=period_end,
                    cancel_at_period_end=cancel_at_end)
            finally:
                conn.close()

    return {
        "authenticated": True,
        "billing": "demo" if not billing.stripe_enabled() else "stripe",
        "plan": plan,
        "has_stripe_customer": bool(row.get("stripe_customer_id")),
        "cancel_at_period_end": cancel_at_end,
        "current_period_end": (dt.datetime.fromtimestamp(
            period_end, dt.timezone.utc).isoformat() if period_end else None),
        "can_manage": billing.stripe_enabled() and bool(row.get("stripe_customer_id")),
    }


class PortalIn(BaseModel):
    email: str = Field(min_length=5, max_length=200)


@app.post("/api/billing/portal")
async def billing_portal(payload: PortalIn, request: Request) -> dict:
    """Sesión del Cliente de Stripe: cancelar, cambiar tarjeta, facturas."""
    if not billing.stripe_enabled():
        raise HTTPException(status_code=400, detail="Stripe no configurado (modo demo).")
    user = auth.user_from_request(request)
    if not user or user.get("email", "").lower() != payload.email.strip().lower():
        raise HTTPException(status_code=401, detail="Sesión inválida.")
    conn = db.connect()
    try:
        row = db.get_user_by_email(conn, user["email"]) or {}
        customer_id = row.get("stripe_customer_id")
    finally:
        conn.close()
    if not customer_id:
        raise HTTPException(status_code=404, detail={
            "error": "no_customer",
            "message": "Esta cuenta aún no tiene una suscripción de Stripe que gestionar."})
    try:
        url = await billing.create_portal_session(customer_id, auth.origin_of(request))
    except Exception as exc:  # noqa: BLE001 - fallo de red de Stripe
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo abrir el portal de Stripe: {exc}") from exc
    return {"portal_url": url}


# ------------------------------------------------------------ alertas Telegram
def _telegram_status(request: Request) -> dict:
    user = auth.user_from_request(request)
    out: dict = {
        "configured": config.telegram_enabled(),
        "bot_username": config.TELEGRAM_BOT_USERNAME,
        "authenticated": bool(user),
        "linked": False,
        "chat_id": None,
        "link_code": None,
        "deep_link": None,
        "plan": (user or {}).get("plan", "free"),
        "min_edge": round(config.ALERT_MIN_EDGE, 4),
        "interval_seconds": config.ALERT_INTERVAL_SECONDS,
        "broadcast_chat": bool(config.TELEGRAM_BROADCAST_CHAT),
    }
    if user:
        conn = db.connect()
        try:
            row = db.get_user_by_email(conn, user["email"]) or {}
            out["linked"] = bool(row.get("telegram_chat_id"))
            out["chat_id"] = row.get("telegram_chat_id")
            if not out["linked"]:
                code = db.ensure_link_code(conn, user["email"])
                out["link_code"] = code
                if config.TELEGRAM_BOT_USERNAME:
                    out["deep_link"] = (f"https://t.me/{config.TELEGRAM_BOT_USERNAME}"
                                        f"?start={code}")
        finally:
            conn.close()
    return out


@app.get("/api/telegram")
def telegram_status(request: Request) -> dict:
    return _telegram_status(request)


class TelegramResetIn(BaseModel):
    email: str = Field(min_length=5, max_length=200)


@app.post("/api/telegram/reset-alerts")
def telegram_reset(payload: TelegramResetIn, request: Request) -> dict:
    """Vuelve a permitir el envío de los picks ya notificados."""
    user = auth.user_from_request(request)
    if not user or user.get("email", "").lower() != payload.email.strip().lower():
        raise HTTPException(status_code=401, detail="Sesión inválida.")
    conn = db.connect()
    try:
        row = db.get_user_by_email(conn, user["email"]) or {}
        if not row.get("telegram_chat_id"):
            raise HTTPException(status_code=400, detail="Chat no vinculado.")
        cleared = db.alerts_reset(conn, row["telegram_chat_id"])
    finally:
        conn.close()
    return {"ok": True, "cleared": cleared}


def require_admin(request: Request) -> None:
    """Autoriza acciones internas con ``Authorization: Bearer $ADMIN_TOKEN``.

    Sin ADMIN_TOKEN configurado la ruta no existe para nadie (403): un
    endpoint de administración jamás debe quedar abierto por omisión.
    """
    token = config.ADMIN_TOKEN
    if not token:
        raise HTTPException(
            status_code=403,
            detail="Acción de administración deshabilitada (falta ADMIN_TOKEN).")
    header = request.headers.get("authorization", "")
    scheme, _, value = header.partition(" ")
    if scheme.lower() != "bearer" or not secrets.compare_digest(
            value.strip(), token):
        raise HTTPException(status_code=401, detail="No autorizado.")


@app.post("/api/telegram/broadcast-test")
async def telegram_broadcast_test(request: Request) -> dict:
    """Mensaje de prueba al chat de difusión (solo admin con ADMIN_TOKEN)."""
    require_admin(request)
    if not config.telegram_enabled():
        raise HTTPException(status_code=400, detail="TELEGRAM_BOT_TOKEN no configurado.")
    if not config.TELEGRAM_BROADCAST_CHAT:
        raise HTTPException(status_code=400, detail="TELEGRAM_CHAT_ID no configurado.")
    ok, err = await notifier.send_message(
        config.TELEGRAM_BROADCAST_CHAT,
        "✅ <b>ApuestaEdge</b>: alertas configuradas correctamente. "
        "Los picks con valor llegarán aquí automáticamente.")
    if not ok:
        raise HTTPException(status_code=502, detail=f"Telegram: {err}")
    return {"ok": True, "chat_id": config.TELEGRAM_BROADCAST_CHAT}


# ------------------------------------------------------------ registro (ledger)
def _day_ts(value: str | None, *, end: bool = False) -> float | None:
    """``YYYY-MM-DD`` -> epoch UTC (fin de día incluido si ``end``)."""
    if not value:
        return None
    try:
        day = dt.datetime.strptime(value, "%Y-%m-%d").replace(
            tzinfo=dt.timezone.utc)
    except ValueError as exc:
        raise HTTPException(status_code=422,
                            detail="Fecha inválida: usa YYYY-MM-DD.") from exc
    if end:
        return (day + dt.timedelta(days=1)).timestamp() - 1.0
    return day.timestamp()


def _pick_public(row: dict) -> dict:
    """Fila de la BD -> JSON público (sin perder hashes ni precisión)."""
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "event_start": row["event_start"],
        "sport": row["sport"],
        "sport_key": row.get("sport_key"),
        "league": row["league"],
        "event": row["event"],
        "market": row["market"],
        "selection": row["selection"],
        "selection_label": row["selection_label"],
        "bookmaker": row["bookmaker"],
        "bet_odds": round(float(row["bet_odds"]), 4),
        "edge": round(float(row["edge"]), 5),
        "edge_pct": round(float(row["edge"]) * 100.0, 2),
        "model_prob": round(float(row["model_prob"]), 4),
        "market_prob": round(float(row["market_prob"]), 4),
        "closing_odds": (round(float(row["closing_odds"]), 4)
                         if row.get("closing_odds") is not None else None),
        "clv_pct": (round(float(row["clv_pct"]), 3)
                    if row.get("clv_pct") is not None else None),
        "stake_units": round(float(row["stake_units"]), 3),
        "result": row.get("result") or "pending",
        "profit_units": (round(float(row["profit_units"]), 3)
                         if row.get("profit_units") is not None else None),
        "settled_at": row.get("settled_at"),
        "prev_hash": row["prev_hash"],
        "row_hash": row["row_hash"],
    }


LEDGER_CSV_COLUMNS = (
    "id", "created_at", "event_start", "sport", "league", "event", "market",
    "selection", "selection_label", "bookmaker", "bet_odds", "edge_pct",
    "closing_odds", "clv_pct", "stake_units", "result", "profit_units",
    "prev_hash", "row_hash",
)


@app.get("/api/ledger/summary")
def ledger_summary() -> dict:
    """Métricas públicas: solo picks asentados; los pendientes van aparte."""
    conn = db.connect()
    try:
        out = ledger.summary(conn)
        out["anchor"] = db.ledger_anchor_latest(conn)
        out["model_version"] = config.MODEL_VERSION
        out["min_edge"] = config.LEDGER_MIN_EDGE
        return out
    finally:
        conn.close()


@app.get("/api/ledger/picks")
def ledger_picks(
    request: Request,
    league: str | None = None,
    sport: str | None = None,
    edge_min: float | None = Query(None, ge=0.0, le=0.5),
    edge_max: float | None = Query(None, ge=0.0, le=0.5),
    market: str | None = Query(None, pattern="^(h2h|outright)$"),
    result: str | None = Query(None, pattern="^(won|lost|push|void|pending)$"),
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(50, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    format: str = Query("json", pattern="^(json|csv)$"),
):
    """Registro filtrable (JSON o CSV).

    El plan Free y los visitantes ven los últimos 7 días; Premium ve el
    archivo completo. La verificación y el paquete de hashes siguen siendo
    públicos para cualquiera: el límite es de navegación, no de auditoría.
    """
    premium = auth.is_premium(request)
    history_days = (None if premium
                    else config.PLANS["free"]["history_days"])
    cutoff = (time.time() - history_days * 86400
              if history_days else None)

    from_ts = _day_ts(date_from)
    if cutoff is not None:
        from_ts = cutoff if from_ts is None else max(from_ts, cutoff)
    conn = db.connect()
    try:
        rows, total = db.ledger_pick_rows(
            conn, league=league, sport=sport, edge_min=edge_min,
            edge_max=edge_max, market=market, result=result,
            date_from=from_ts, date_to=_day_ts(date_to, end=True),
            limit=limit, offset=offset)
        data = [_pick_public(r) for r in rows]
        if format == "csv":
            import csv as _csv
            import io as _io
            from fastapi.responses import Response
            buf = _io.StringIO()
            writer = _csv.DictWriter(buf, fieldnames=LEDGER_CSV_COLUMNS,
                                     extrasaction="ignore")
            writer.writeheader()
            for row in data:
                out = dict(row)
                for key in ("created_at", "event_start", "settled_at"):
                    if out.get(key):
                        out[key] = dt.datetime.fromtimestamp(
                            float(out[key]), dt.timezone.utc).isoformat()
                writer.writerow(out)
            filename = "apuestaedge-picks.csv"
            return Response(
                content="\ufeff" + buf.getvalue(),
                media_type="text/csv; charset=utf-8",
                headers={"Content-Disposition":
                         f'attachment; filename="{filename}"',
                         "X-History-Days": str(history_days or 0),
                         "X-History-Limited": str(bool(history_days)).lower()})
        return {"total": total, "count": len(data), "picks": data,
                "history_days": history_days,
                "history_limited": bool(history_days)}
    finally:
        conn.close()


@app.get("/api/ledger/verify")
def ledger_verify() -> dict:
    """Recalcula las cadenas de hashes: cualquiera puede comprobar el CSV."""
    conn = db.connect()
    try:
        report = ledger.verify(conn)
        report["anchor"] = db.ledger_anchor_latest(conn)
        return report
    finally:
        conn.close()


@app.get("/api/ledger/export")
def ledger_export() -> dict:
    """Paquete JSON con las filas crudas y las anclas para verificar offline."""
    conn = db.connect()
    try:
        return ledger.export_package(conn)
    finally:
        conn.close()


@app.get("/api/ledger/leagues")
def ledger_leagues() -> dict:
    conn = db.connect()
    try:
        data = ledger.by_league(conn)
        total_picks = data.pop("_total_picks")
        return {"total_picks": total_picks, "leagues": data}
    finally:
        conn.close()


@app.get("/api/ledger/versions")
def ledger_versions() -> dict:
    conn = db.connect()
    try:
        return {"current": config.MODEL_VERSION,
                "versions": db.model_versions_list(conn)}
    finally:
        conn.close()


@app.post("/api/ledger/anchor")
def ledger_publish_anchor(request: Request) -> dict:
    """Fuerza la publicación del ancla de hoy (solo admin)."""
    require_admin(request)
    conn = db.connect()
    try:
        day = time.strftime("%Y-%m-%d", time.gmtime())
        saved = ledger.anchor(conn, day=day)
        return {"ok": True, "anchor": saved}
    finally:
        conn.close()


# --------------------------------------------------------------- páginas
# URLs limpias para las páginas públicas: StaticFiles sirve /picks.html,
# pero el enlace que se comparte es /picks.
@app.get("/picks", include_in_schema=False)
def picks_page() -> FileResponse:
    """Registro completo de picks (tabla, filtros y CSV)."""
    return FileResponse(config.BASE_DIR / "static" / "picks.html",
                        media_type="text/html")


@app.get("/verificacion", include_in_schema=False)
def verification_page() -> FileResponse:
    """Cómo comprobar que el registro no se ha tocado."""
    return FileResponse(config.BASE_DIR / "static" / "verificacion.html",
                        media_type="text/html")


@app.get("/ligas", include_in_schema=False)
def leagues_page() -> FileResponse:
    """Rendimiento por liga con muestra explícita y p-valor."""
    return FileResponse(config.BASE_DIR / "static" / "ligas.html",
                        media_type="text/html")


@app.get("/modelo", include_in_schema=False)
def model_page() -> FileResponse:
    """Auditoría del modelo y historial de versiones."""
    return FileResponse(config.BASE_DIR / "static" / "modelo.html",
                        media_type="text/html")


@app.get("/verificacion/verify_ledger.py", include_in_schema=False)
def verification_script() -> FileResponse:
    """Verificador independiente (solo biblioteca estándar de Python)."""
    return FileResponse(config.BASE_DIR / "static" / "verify_ledger.py",
                        media_type="text/x-python",
                        filename="verify_ledger.py")


# Estático al final: las rutas /api/* tienen prioridad.
app.mount("/", StaticFiles(directory=str(config.BASE_DIR / "static"),
                           html=True), name="static")
