# ApuestaEdge ⚡

> Web app que analiza partidos con **modelos estadísticos reales** y recomienda
> **a quién, qué, cuándo y cuánto apostar**, explicando en cada caso *por qué*
> la recomendación es estadísticamente sólida — y con su rendimiento auditable.

Pensada para **generar ingresos**: planes Free/Premium (suscripciones), con la
arquitectura preparada para conectar Stripe/Paddle y, opcionalmente, programas
de afiliados de casas de apuestas con licencia.

---

## ⚠️ Aclaración honesta (léela)

Ningún sistema puede recomendar “sin fallas”: el deporte tiene varianza y el
mercado es muy eficiente. Lo que **sí** hace este proyecto es lo que usan los
apostadores profesionales:

1. **Solo recomienda apuestas con valor esperado positivo (EV+)**: la
   probabilidad estimada por el modelo supera a la que exige la cuota.
2. **Explica el porqué con números** (modelo, mercado desvigado, edge,
   confianza estadística, Kelly, backtest con test binomial).
3. **Publica aciertos y fallos**: ROI, CLV, drawdown y significancia estadística
   se muestran en el panel; sin track record verificable no hay confianza.

Incluso con 55% de probabilidad real, ~45 de cada 100 apuestas pierden. El
objetivo matemático es crecer a largo plazo, no acertar siempre. La página
incluye aviso de juego responsable (+18) y explícitamente dice lo que el modelo
**no** puede garantizar.

---

## Qué hace

- **Radar de partidos**: **7 deportes con datos reales** — fútbol (EPL, LaLiga,
  Serie A, Bundesliga, Ligue 1, Liga MX), básquet (NBA), tenis (ATP/WTA en
  temporada), **fútbol americano (NFL/NCAA)**, **boxeo**, **béisbol (MLB)** y
  **hockey (NHL)**, con cuotas en vivo de [The Odds API](https://the-odds-api.com).
  Con `ODDS_API_KEY` configurada solo se muestran eventos reales: nunca se
  mezclan partidos de demostración con datos en vivo.
- **Modelos**: Elo por deporte con ventaja de localía; en fútbol, tasas de goles
  Poisson **calibradas** al score esperado del Elo → matriz de marcadores → 1X2.
  En básquet, tenis, fútbol americano y béisbol: moneyline logístico del Elo
  (localía: 60/50/20/40/25 pts según deporte; 0 en boxeo, terreno neutral).
  Los grupos outright (F1/MotoGP/caballos, **Bradley-Terry**) siguen soportados
  por el motor en desarrollo, pero **no aparecen en el radar de producción**:
  The Odds API no los cubre y no se muestran eventos sin fuente real.
- **Desvigado de las cuotas**: método de potencias (Shin) + consenso entre casas.
- **Frontend orientado a conversión**: «Recomendaciones de hoy» (5 picks curados en Free,
  todos los valores en Premium), rendimiento auditable, sección de beneficios y
  planes. El detalle metodológico (pipeline, límites, por qué funciona) **no se
  muestra en la página**: vive en este README y en `GET /api/methodology`.
- **Filtro de valor**: `edge = P(modelo) − P(mercado)`, `EV = P(modelo)×cuota − 1`,
  solo entra `EV > 0` con edge ≥ umbral del plan (6% Free, 3% Premium).
- **Confianza estadística**: `P(modelo > mercado)` con aproximación normal
  usando la incertidumbre del modelo (n efectivo = 60 partidos) y la dispersión
  entre casas.
- **Dimensionamiento**: `0.25 × Kelly completo`, tope duro de 3% del bankroll,
  mínimo 0.5%.
- **Explicación por pick**: 6 pasos (modelo → mercado → valor → Kelly → cuándo
  entrar → evidencia) + riesgos. En Free se desbloquean 3 pasos; el resto es el
  gancho de Premium.
- **Rendimiento auditable**: ROI, acierto vs breakeven, profit factor, CLV,
  drawdown y **test binomial** por deporte, con curva de equity.
- **Registro público de picks (`/picks`)**: cada pick se publica **antes** del
  evento en una tabla append-only con cadena de hashes SHA-256, se asienta con
  el marcador real y no se puede editar ni borrar. Tabla con filtros, resumen
  (ROI, acierto, CLV, pérdidas) y export CSV. Con menos de 30 picks cerrados se
  muestra «muestra insuficiente (n=X)» en lugar de porcentajes que parezcan una
  promesa. Detalle técnico abajo.
- **Rendimiento por liga (`/ligas`)**: cada liga con su muestra exacta,
  acierto, ROI, CLV y p-valor binomial. La etiqueta de «mejor liga» solo
  aparece con n ≥ 30 picks cerrados y p < 0.05; el resto se marca como
  muestra insuficiente o sin significancia.
- **Auditoría del modelo (`/modelo`)**: edge, Kelly fraccional 1/4, fórmula
  del CLV y test binomial explicados con sus límites. Los pesos internos no
  se publican; cada cambio queda en el historial de versiones que se anota en
  cada pick.
- **Verificación (`/verificacion`)**: estado de las tres cadenas, ancla diaria,
  comprobación en el navegador con Web Crypto y un verificador independiente
  de Python (solo biblioteca estándar) que recalcula la cadena desde el
  paquete JSON, sin confiar en el servidor.

## Instalación

Requiere Python 3.10+.

```bash
cd "Proyecto predeterminado"
python3 -m venv .venv
source .venv/bin/activate
pip install -r apuesta_edge/requirements.txt
```

## Uso

```bash
cd apuesta_edge
uvicorn app.main:app --reload --port 8000
```

Abre <http://localhost:8000>.

### Cuotas en vivo (opcional)

Sin configuración funciona con el dataset de demostración
(`data/sample_odds.json`). Para datos reales:

```bash
export ODDS_API_KEY='tu_clave'        # plan 20K: 20.000 créditos/mes ($30)
uvicorn app.main:app --port 8000
```

Con `ODDS_API_KEY` configurada la página **solo muestra eventos reales**:
nunca se mezcla el dataset de demo con datos en vivo. Si la API falla
(cuota agotada, red caída) se sirve el último parte real guardado en la
base (máx. 7 días, sin eventos ya iniciados) y, si no lo hay, la página
indica "sin datos" con el radar vacío en lugar de inventar partidos.

Presupuesto de créditos: cada refresco cuesta (deportes × regiones)
créditos, así que la caché dura 2 h por defecto
(`MATCHES_CACHE_TTL=7200`) → ~11K de 20K créditos/mes. Si la API reporta
menos de `ODDS_QUOTA_SOFT_FLOOR` créditos restantes, el refresco se
extiende a 6 h para no agotar la cuota antes del día 1.

El panel indica en el encabezado si está en modo **demo**, **en vivo** o
**sin datos**.

### Variables de entorno

| Variable | Default | Qué controla |
|---|---|---|
| `ODDS_API_KEY` | vacía | Clave de The Odds API (sin clave = demo) |
| `ODDS_API_REGION` | `us,eu` | Región de las casas de apuestas |
| `ODDS_API_TIMEOUT` | `12` | Timeout (s) por llamada a The Odds API |
| `ODDS_QUOTA_SOFT_FLOOR` | `2000` | Si quedan menos créditos, alarga la caché |
| `MATCHES_CACHE_TTL` | `7200` con clave / `120` sin clave | Caducidad (s) de la caché de partidos |
| `ALLOW_SAMPLE_DATA` | `1` sin clave / `0` con clave | ¿Se permite caer al dataset de demo? |
| `KELLY_FRACTION` | `0.25` | Fracción del Kelly usada |
| `MAX_STAKE_PCT` | `3` | Tope de stake (% del bankroll) |
| `DEFAULT_BANKROLL` | `1000` | Banca por defecto del panel |
| `EFFECTIVE_N` | `60` | Tamaño muestral efectivo de los ratings |
| `APUESTAEDGE_DB` | `data/apuesta_edge.db` | Ruta de la base SQLite |
| `DATABASE_URL` | vacía | PostgreSQL (Neon/Supabase/Render): persistencia real |
| `PASSWORD_MIN_LENGTH` | `8` | Longitud mínima de la contraseña |
| `ADMIN_TOKEN` | vacía | Bearer para `broadcast-test` y ancla manual (sin él: 403) |
| `MODEL_VERSION` | `elo-1.0` | Versión del modelo que se anota en cada pick |
| `LEDGER_MIN_EDGE` | `0.03` | Edge mínimo para publicar en el registro |
| `LEDGER_PUBLISH_INTERVAL` | `900` | Segundos entre ciclos del registro |
| `LEDGER_CLOSE_WINDOW` | `900` | Ventana antes del inicio para congelar la cuota de cierre |
| `LEDGER_SETTLE_WINDOW` | `259200` | Días hacia atrás para buscar marcadores (3 días) |

### Registro público (ledger)

- Tres cadenas independientes (`picks`, `pick_closings`, `pick_results`) con
  `prev_hash`/`row_hash` SHA-256; se anclan juntas una vez al día en
  `ledger_anchors`. Cualquier edición o borrado rompe la verificación.
- Solo publica con datos reales (`source == "live"`): en demo el registro queda
  vacío a propósito. Sin `ODDS_API_KEY` tampoco corre el ciclo de fondo.
- `capture_closings` congela la cuota de cierre y calcula el CLV automático;
  `settle` asienta el resultado con el marcador real (outrights quedan
  pendientes).
- El plan **Free ve cada pick 2 h después** de su publicación: la liberación se
  calcula contra `picks.created_at` (no hay caché en memoria). En demo se
  muestra la muestra sin retraso.
- El CSV incluye `prev_hash` y `row_hash` para inspección; incluye BOM para
  Excel.

## API

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/health` | Estado y fuente de datos (demo / vivo) |
| GET | `/api/matches?sport=` | Partidos + probabilidades modelo y mercado |
| GET | `/api/recommendations?plan=&sport=&min_edge=&bankroll=` | Picks rankeados con explicación |
| GET | `/api/performance?sport=` | ROI, CLV, drawdown, p-value (historial; la home usa el ledger) |
| GET | `/api/performance/by-sport` | Métricas por deporte |
| GET | `/api/ledger/summary` | Resumen del registro público (ROI, CLV, drawdown, pérdidas) |
| GET | `/api/ledger/picks` | Registro filtrable (`league`, fechas, `edge_min`, `market`, `result`); `format=csv` |
| GET | `/api/ledger/leagues` | Métricas por liga + p-valor y «mejor liga» solo con n≥30 |
| GET | `/api/ledger/verify` | Recalcula las tres cadenas de hashes |
| GET | `/api/ledger/versions` | Versión del modelo e historial |
| GET | `/api/methodology` | Pipeline y límites (API: la web no muestra ya esa sección) |
| GET | `/api/plans` | Planes, features y modo de cobro |
| POST | `/api/subscribe` | Registro `{email, password}` → token de sesión |
| POST | `/api/auth/login` | `{email, password}` → token (PBKDF2) |
| GET | `/api/auth/me` | Sesión y plan del token actual |
| POST | `/api/billing/checkout` | Inicia el pago Premium (Stripe) |
| POST | `/api/billing/confirm` | Verifica la sesión de Stripe al volver del pago y activa Premium |
| POST | `/api/billing/webhook` | Ciclo de vida: activa, renueva y **da de baja** Premium |
| GET | `/api/billing/subscription` | Estado de tu suscripción (fin de periodo, cancelación) |
| POST | `/api/billing/portal` | Portal del cliente Stripe (cancelar, cambiar tarjeta) |
| GET | `/api/telegram` | Estado de alertas + código de vinculación |
| POST | `/api/telegram/reset-alerts` | Reenviar picks ya notificados |
| POST | `/api/telegram/broadcast-test` | Mensaje de prueba al chat admin (requiere `ADMIN_TOKEN`) |

Documentación interactiva: <http://localhost:8000/docs>

### Alertas por Telegram

Cada suscriptor puede vincular su cuenta y recibir los picks con valor en su
Telegram. El bot manda **solo picks nuevos** (dedupe en la tabla `alerts`),
con el edge mínimo `ALERT_MIN_EDGE` y respetando el plan (Free: 2 picks;
Premium: hasta 6 con stake, confianza y resumen del análisis).

```bash
# 1) Crea el bot con @BotFather y copia el token
export TELEGRAM_BOT_TOKEN='123456:ABC...'      # obligatorio
export TELEGRAM_BOT_USERNAME='apuesta_edge_bot'  # para el deep link t.me/...?start=CODIGO
export TELEGRAM_CHAT_ID='-1001234567890'        # opcional: chat admin/difusión
export ALERT_INTERVAL_SECONDS=1800              # cadencia (30 min)
export ALERT_MIN_EDGE=0.04                      # edge mínimo para alertar
uvicorn app.main:app --port 8000
```

Flujo del usuario:

1. Se registra en la web → en la sección Precios aparece su enlace
   `https://t.me/<bot>?start=<codigo>` (o escribe `/start <codigo>` en el bot).
2. El bot confirma la vinculación (`/status`, `/stop`).
3. Recibe cada pick con valor por privado; `/mis_picks` muestra los del momento.

Comandos del bot: `/start <codigo>`, `/mis_picks`, `/status`, `/stop`.

Sin `TELEGRAM_BOT_TOKEN` el sistema está inerte y el panel de Telegram se
oculta (no se anuncia algo que no existe). `/mis_picks` exige un chat
vinculado: sin vínculo no hay a quién aplicar plan, límite ni retraso Free.

### Plan y bloqueo (importante para monetizar)

El plan **no** vive en un query param: se resuelve con la sesión del usuario
(`Authorization: Bearer <token>` o cookie `ae_token`).

- **Sin claves de Stripe (modo demo)**: `plan=premium` funciona para probar el
  flujo completo y queda marcado `"demo_mode": true` en la respuesta.
- **Con `STRIPE_SECRET_KEY` (producción)**: pedir premium sin suscripción
  devuelve **HTTP 402** y el panel muestra el CTA de upgrade. El plan solo se
  activa cuando el **webhook de Stripe** (`checkout.session.completed`)
  confirma el pago, verificando la firma `Stripe-Signature`.

Ciclo de vida completo manejado por el webhook (nada queda "colgado"):

| Evento de Stripe | Efecto en la app |
|---|---|
| `checkout.session.completed` | Activa Premium y guarda `customer`/`subscription` |
| `customer.subscription.updated` (`active`/`trialing`) | Renueva; registra fin de periodo y si hay cancelación programada |
| `customer.subscription.updated` (cancelación programada) | Premium hasta `current_period_end`, luego baja |
| `customer.subscription.deleted` | Vuelve a **Free** (el 402 vuelve a aplicar) |

El usuario gestiona su suscripción desde el panel **"💳 Tu suscripción"**
(web): ve la fecha de renovación/cancelación y abre el **portal de Stripe**
(`POST /api/billing/portal`) para cancelar o cambiar la tarjeta.

```bash
export STRIPE_SECRET_KEY='sk_test_...'
export STRIPE_WEBHOOK_SECRET='whsec_...'   # en desarrollo: stripe listen --forward-to localhost:8000/api/billing/webhook
uvicorn app.main:app --port 8000
```

Paso a paso para cobrar de verdad:

1. Crea un producto *Premium mensual* en Stripe (o deja el `price_data`
   inline del código, $29/mes) y copia las claves de prueba al entorno.
2. Levanta el webhook con `stripe listen --forward-to localhost:8000/api/billing/webhook`.
3. Regístrate con el formulario de la web → te redirige a Checkout.
4. Tras el pago exitoso, el webhook marca `plan=premium` y el panel desbloquea
   todos los picks con edge ≥ 3% + Kelly + backtest.
5. Para producción: dominio, `success_url` con https y claves live.

## Cómo se calcula cada recomendación

1. Elo (ventaja local: 60 pts fútbol, 50 básquet, 20 tenis).
2. Fútbol: Elo → score esperado `P(victoria) + 0.5·P(empate)` → reparto de
   goles calibrado → Poisson → matriz de marcadores → 1X2, ambos marcan, líneas.
3. Básquet/tenis: probabilidad logística del Elo (moneyline).
4. Desvigado por casa (método de potencias) y consenso entre casas.
5. `edge = P(modelo) − P(mercado)`; `EV = P(modelo) × cuota − 1`.
6. Confianza `= Φ((P_modelo − P_mercado) / σ_total)`, con
   `σ_total² = σ_modelo² + σ_entre_casas²`.
7. Stake `= min(0.25 × Kelly, 3%)` del bankroll.
8. El pick se guarda y se contrasta con el resultado real (ROI, CLV, p-value).

## Despliegue permanente (online 24/7)

El repositorio incluye todo lo necesario para publicarlo sin tocar código:
`Dockerfile`, `render.yaml` (Blueprint de Render), `Procfile` y `.gitignore`
(la BD local no se sube; cada despliegue crea la suya y el seed de demo se
carga solo).

### Ruta A — Render (recomendada, sin instalar nada)

1. **Sube el proyecto a GitHub** — ✅ hecho: [github.com/CarlosPrado78/ApuestaEdge](https://github.com/CarlosPrado78/ApuestaEdge)
   (público, rama `main`, 6 commits). Cada cambio futuro se despliega con:

   ```bash
   git add -A && git commit -m "Descripción" && git push
   # Render redespliega solo al detectar el push
   ```

2. **Conecta Render**: en <https://render.com> → *New* → *Blueprint* →
   conecta tu cuenta de GitHub → instala la app de Render solo para el repo
   `CarlosPrado78/ApuestaEdge` → *Connect*.
   Render detecta `render.yaml` solo (Blueprint) y configura build, disco de
   1 GB en `/data` y health check `/api/health`.

3. **Pulsa *Deploy***. ✅ hecho — la app está en vivo en
   **<https://apuestaedge.onrender.com>** (plan Free de Render, build ~40 s,
   visible desde cualquier computadora o celular del mundo).

4. **Variables de entorno** (dashboard → *Environment*), cuando quieras activar
   producción real:

   | Variable | Para qué |
   |---|---|
   | `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` | Cobros reales (bloqueo 402) |
   | `ODDS_API_KEY` | Cuotas en vivo (The Odds API, plan 20K $30/mes) |
   | `TELEGRAM_BOT_TOKEN` / `TELEGRAM_BOT_USERNAME` | Alertas al Telegram |

5. **Webhook de Stripe**: apunta a
   `https://TU-DOMINIO/api/billing/webhook` (eventos `checkout.session.completed`,
   `customer.subscription.created`, `customer.subscription.updated`,
   `customer.subscription.deleted`). El pago también se confirma al volver del
   checkout (`/api/billing/confirm`), así que un webhook lento no deja al
   cliente en Free.

> ⚠️ **Persistencia en Render**: el plan Free no tiene disco persistente. Está
> comprobado que, usando SQLite, **las cuentas y los planes se borran en cada
> despliegue**. Para que los pagos sobrevivan hay que usar PostgreSQL: define
> `DATABASE_URL` (Neon, Supabase o Render Postgres) y la app guarda todo ahí.
>
> **Neon (gratis, recomendado)**
> 1. Crea una cuenta en <https://neon.tech> → *New Project* → copia la
>    *Connection string* (`postgresql://...?sslmode=require`).
> 2. Render → tu servicio → *Environment* → *Add Environment Variable*:
>    `DATABASE_URL` = la cadena copiada (marca *sync: false*).
> 3. Render redespliega solo. Comprueba `GET /api/health`: debe responder
>    `"database": "postgres"`.
>
> La app crea las tablas y las migra sola la primera vez; no hay que ejecutar
> SQL a mano. Sin `DATABASE_URL` sigue usando SQLite local (desarrollo/tests).
>
> Plan gratis de Render: el servicio se duerme tras 15 min sin tráfico y
> tarda ~30 s en despertar (basta con recargar). Para 24/7 sin dormir,
> el plan Starter cuesta $7/mes. Alternativas: Fly.io, Railway, PythonAnywhere.

### Ruta B — Docker en tu propio servidor (VPS)

```bash
docker build -t apuestaedge .
docker run -d -p 80:8000 \
  -v apuestaedge-data:/data \
  -e STRIPE_SECRET_KEY=sk_live_... \
  apuestaedge
```

### Ruta C — solo red local (ya funcionando en este equipo)

```bash
cd apuesta_edge
../.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8123
```

Abre `http://<IP-de-esta-mac>:8123` desde cualquier equipo de la misma Wi-Fi.

### Acceso con email + contraseña

El login es con **email y contraseña** (sin dependencias externas de correo):

- `POST /api/auth/register` `{email, password}` → crea la cuenta (mín. 8 caracteres).
- `POST /api/auth/login` `{email, password}` → inicia sesión.
- La contraseña se guarda con PBKDF2-SHA256 + sal aleatoria.
- Al entrar se reengancha automáticamente el Premium ya pagado en Stripe (si la
  BD se recreó o el usuario cambió de dispositivo).

No hace falta configurar ningún proveedor de correo ni dominio personalizado.

## Monetización

- **Suscripciones (base)**: `app/config.py → PLANS` define Free y Premium.
  El flujo de cobro ya está implementado (ver *Plan y bloqueo* arriba):
  registro → Stripe Checkout → webhook → plan Premium activo en servidor.
  Para producción solo faltan las claves live y el dominio con https.
- **Afiliados (opcional)**: añade enlaces de casas con licencia a los picks;
  es la vía de ingreso complementaria más habitual en este nicho.
- **API/Datos**: los mismos endpoints pueden servir un plan B2B.

## Estructura

```
apuesta_edge/
  app/
    main.py          # FastAPI: endpoints + panel estático + gating de plan
    auth.py          # sesiones por token (Bearer/cookie) y plan del usuario
    billing.py       # Stripe Checkout + webhook (firma) + modo demo
    notifier.py      # bot Telegram: comandos, formato de picks y alertas
    config.py        # planes, Kelly, claves de entorno
    providers.py     # The Odds API + dataset demo + ratings Elo
    service.py       # pipeline: modelo → mercado → edge → Kelly → pick
    explain.py       # explicación en español de cada recomendación
    db.py            # SQLite/PostgreSQL: ledger, usuarios/sesiones y suscriptores
    ledger.py        # registro append-only: cadenas de hashes, CLV, asentado, ancla
    engine/
      devig.py       # desvigado (potencias / proporcional) y CLV
      elo.py         # ratings Elo + ventaja de localía
      poisson.py     # goles Poisson calibrados al Elo
      kelly.py       # Kelly fraccional y tope de riesgo
      ev.py          # valor esperado y confianza (bayesiana/normal)
      backtest.py    # ROI, drawdown, profit factor, test binomial
  static/            # web: index.html + app.js, picks.html + ledger.js, estilos
  docs/              # arquitectura de producto y decisiones editoriales
  data/              # ratings, cuotas demo, historial, SQLite
  scripts/generate_demo_history.py
  tests/             # 155 tests (motor, servicio, API, ledger, auth, cobros, alertas y 9 deportes)
```

## Tests

```bash
cd apuesta_edge && python -m pytest
```

Cubren el motor estadístico (proporciones, calibración de Poisson/Elo, Kelly,
EV, binomial), el pipeline (solo EV>0, tope de stake, gating Free/Premium) y la
API completa y el registro público (cadenas de hashes, manipulación
detectada, CLV, asentado, CSV y retraso del plan Free).

## Roadmap

- Dixon-Coles para ajustar marcadores 0-0/1-1 y Poisson bivariado.
- Elo con regresión de temporada y ratings por superficie/deporte.
- Mercados adicionales: líneas de goles, handicaps asiáticos, totales.
- Proveedor de datos en vivo para Fórmula 1, MotoGP y caballos (hoy demo).
- Registro real + Stripe + alertas (email/Telegram) cuando aparece valor.
- Backtest walk-forward sobre temporadas completas.

---

## Juego responsable

ApuestaEdge es una herramienta de análisis estadístico con fines informativos.
No es asesoramiento financiero ni garantía de resultados. Tienes que ser mayor
de edad (+18) en tu jurisdicción. Apostar conlleva riesgo de pérdida: respeta
el stake sugerido, nunca persigas pérdidas y juega solo dinero que puedas
permitirte perder.
