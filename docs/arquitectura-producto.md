# ApuestaEdge — Arquitectura de producto (v2, $29/mes)

Documento de trabajo. Objetivo: pasar de "página de picks" a **sistema de autoverificación
transparente y auditable**, apoyado en la infraestructura ya existente (FastAPI + Postgres/Neon +
The Odds API + Stripe + Telegram), sin reescribir la plataforma.

Pregunta que debe responder cada pantalla: **¿cómo demuestra esto que los datos son reales, el
edge es real y las pérdidas no se ocultan?**

---

## 0. Punto de partida real (lo que hay hoy)

| Pieza | Estado |
|---|---|
| Motor de picks (Elo → probabilidad → de-vig → edge → Kelly 1/4) | ✅ `app/service.py`, `app/explain.py` |
| Cálculo de ROI / acierto / CLV / drawdown / p-valor binomial | ✅ `app/backtest.py`, `explain.performance_summary` |
| Picks en vivo | ✅ pero **se generan al vuelo, no se guardan** |
| Historial de resultados | ⚠️ tabla `history` sembrada con datos **simulados** (`scripts/generate_demo_history.py`) |
| Cuota de cierre / CLV automático | ❌ el CLV del historial es un número generado, no medido |
| Alertas | ⚠️ solo Telegram, sin reglas configurables; el delay Free no se aplica |
| Planes, Stripe, trial | ⚠️ base hecha; trial de 7 días sin tarjeta no existe todavía |
| i18n ES/EN, pago, auth | ✅ |

Consecuencia: **el activo que vende el producto (registro verificable) todavía no existe**. Es la
primera cosa que hay que construir, y es también la que hace imposible el "CLV de 12 meses" el día
1. Ver §6 (decisión editorial).

---

## 1. Mapa del sitio

```
/                     Inicio — la promesa en 1 pantalla
/picks                Registro completo (tabla + filtros + CSV)
/ligas                Dashboard por liga (CLV, ROI, p-valor)
/modelo               Auditoría del modelo (edge, Kelly, CLV, binomial, versiones)
/verificacion         Cómo comprobar que no manipulamos el registro (hash chain)
/alertas              Reglas de alerta (login) — Telegram / Email / Push
/precios               $29/mes, trial 7 días, Free
/legal/terminos       Términos, riesgo, +18, aviso México
/legal/privacidad     Privacidad y datos
/pick/{id}            (fase 2) Ficha pública e inmutable de un pick
```

Criterio de velocidad: **una sola app estática servida por FastAPI** con rutas de cliente sobre
`pathname` (fallback a `index.html`). Da URLs compartibles sin montar un framework. Las páginas
públicas (`/picks`, `/modelo`, `/verificacion`) se sirven también con datos embebidos para SEO en
fase 2.

---

## 2. Descripción funcional por página

### `/` — Inicio (above the fold)

- Titular: **"Publicamos cada pick, incluidas las pérdidas."**
- Subtítulo con fecha de inicio del registro: *"Registro abierto desde el 13 nov 2026. 0 picks
  cerrados todavía."* (ver §6)
- **3 métricas en vivo** (una sola llamada `/api/ledger/summary`):
  1. **CLV medio** — acumulado desde el inicio (no "12 meses" hasta que existan 12 meses)
  2. **Drawdown máximo** — en unidades
  3. **ROI acumulado** — con el nº de picks y el nº de pérdidas al lado, en rojo
- CTA primario: **"Ver registro completo de picks"** → `/picks`
- CTA secundario: **"Probar 7 días gratis"** (sin tarjeta)
- Bloque "Pick gratuito de hoy" (1/día, requiere email): cuota, edge, cuota de cierre si ya cerró.
- Franja de honestidad: *"No prometemos ganancias. Publicamos el resultado completo, gane o pierda."*

Métrica vacía ≠ métrica cero: si hay < 30 picks, se muestra "muestra insuficiente" en vez de un
porcentaje que parezca una promesa.

### `/picks` — Registro completo

Tabla server-side paginada (`/api/ledger/picks`), columnas:

`fecha/hora · liga · evento · mercado · selección · cuota · edge % · cuota de cierre · CLV · unidades · resultado`

- **Filtros**: liga, rango de fechas, rango de edge, mercado, resultado (ganadas / perdidas /
  todas). Persisten en la URL (`?liga=nba&edge_min=4`) para poder compartir una vista.
- **Resumen superior**: ROI, acierto, CLV medio, nº de picks, **nº de pérdidas en rojo**.
- **Exportar CSV** de la vista filtrada (mismo endpoint, `?format=csv`).
- **"Copiar detalles del pick"** por fila → texto plano listo para Telegram/Discord:
  `[13/11 21:30] NBA · Lakers vs Celtics · ML Lakers · cuota 1.94 · edge +4.2% · 1.0u · PENDIENTE`
- Móvil: tarjetas apiladas (no scroll horizontal) con los 4 datos clave y el resto en un
  desplegable.
- Nota al pie: *"Cada fila se escribió antes del inicio del evento y no se puede editar."*

### `/ligas` — Dashboard por liga

Tarjetas por liga (Premier, La Liga, Serie A, Bundesliga, NBA, LNBP/Liga MX, MLB, NFL, tenis,
boxeo). Cada una con: nº picks, acierto, CLV medio, ROI y **p-valor binomial**.

- Etiqueta **"Nuestra mejor liga"**: mayor CLV con p < 0.05 y n ≥ 30. Si no hay ninguna que cumpla,
  la etiqueta **no se muestra** (no se inventa un premio).
- Si n < 30 → "muestra insuficiente (n=12)" en lugar de p-valor.
- Nota fija: *"Los datos por liga son referencia, no garantía de resultados futuros."*

Reutiliza `bt.summarize` agrupando el ledger por `league`; el endpoint actual agrupa por `sport`,
así que hace falta el campo `league` en el ledger.

### `/modelo` — Auditoría del modelo

Cinco secciones, en lenguaje llano y con la fórmula visible:

1. **Cómo se calcula el edge**: probabilidad del modelo → probabilidad implícita de la casa
   (sin margen, Shin) → `edge = P_modelo − P_mercado`. Ejemplo numérico con un pick real.
2. **Kelly fraccional**: `f* = (p·b − q) / b`, se aplica **1/4 de Kelly**, tope 3% del bankroll,
   mínimo 0.5%. Por qué 1/4 (varianza y errores de estimación).
3. **CLV**: `CLV% = (cuota_apuesta / cuota_cierre − 1) × 100`. Fuente de la cuota de cierre y
   **hora exacta** de captura. Se muestra también el CLV en probabilidad sin margen.
4. **Test binomial**: qué es, por qué distingue suerte de habilidad, y por qué con n < 30 no se
   reporta.
5. **Límites honestos**: el mercado es eficiente; los edges grandes suelen ser información que el
   modelo no tiene. Enlaza a `/verificacion`.

- Declaración: **"La lógica central es auditable; los pesos específicos no son públicos."**
- **Historial de versiones** (tabla `model_versions`): versión, fecha, qué cambió, impacto medido
  en CLV/ROI desde el cambio. Se muestra también cuando el impacto fue **negativo**.

### `/verificacion` — Prueba de que el registro no se toca

La pieza que ningún competidor tiene y que cuesta poco:

- Explicación del **registro append-only** y de la **cadena de hashes**:
  `hash_fila = SHA256(hash_anterior + campos_del_pick)`.
- Se publica a diario el **hash cabeza** del registro (página + canal público). Cualquiera puede
  descargar el CSV y recalcular la cadena: si una fila se editó o borró, la cadena no cuadra.
- Estado en vivo: *"Última publicación: 13 nov 2026 · cabeza `a3f9…` · 128 filas verificadas"*.
- Botón **"Verificar ahora"**: recalcula la cadena en el navegador sobre el CSV descargado.
- Fase 2: anclaje externo (OpenTimestamps / publicación en un tercero) para que ni nosotros
  podamos reescribir el pasado.

### `/alertas` — Reglas (la diferenciación operativa)

Formulario por regla, guardado en base de datos (no "avísame por correo"):

- **Filtros**: liga(s), edge mínimo (ej. ≥ 5%), rango de cuota (1.50–2.50), mercado(s), tiempo
  máximo hasta el inicio (ej. ≤ 30 min).
- **Canales**: Email ✅, Telegram ✅ (si está vinculado), Web Push (fase 2).
- **Contenido de la alerta**: edge, cuota, hora de inicio, enlace directo a la casa **sin
  afiliado**, y si se usa afiliación, la declaración explícita.
- **Pausar / reanudar** con un interruptor, sin soporte. Historial de envíos visible.
- Límites anti-abuso: máx. N reglas por plan, dedupe `(regla, pick, canal)`, y el **delay de 2 h
  del plan Free aplicado también a las alertas**.
- Coste: reutilizar el caché de partidos; nunca regenerar recomendaciones por suscriptor.

### `/precios` — Suscripción

- **$29/mes**, sin contrato anual, cancelación en cualquier momento (portal de Stripe).
- **Trial 7 días** con todo incluido, **sin tarjeta**; al terminar, degrada a Free sin cobrar.
- **Free**: 1 pick/día por email + histórico de 7 días.
- Sin cuentas atrás, sin "quedan X lugares", sin descuentos de presión.
- Comparativa honesta de qué incluye cada plan, sin promesas de rentabilidad.

### `/legal/*` + pie global

Descargo en **todas** las páginas: *"Los pronósticos deportivos implican riesgo. Los datos
históricos no garantizan resultados futuros. Solo para mayores de 18 años. Juega con moderación."*
Aviso específico para México (servicio de pronósticos, no casa de apuestas; no se aceptan apuestas
ni se custodia dinero). Identidad real del desarrollador/equipo, correo de contacto y fecha de
última revisión legal.

---

## 3. Modelo de datos (lo nuevo)

Tres tablas nuevas y una regla de oro: **nada se actualiza, todo se añade**.

```sql
-- 1) El pick, inmutable desde que se publica
picks (
  id BIGSERIAL PK,
  created_at, event_start, sport, league, event, market, selection,
  bet_odds, model_prob, market_prob, edge, stake_units,
  model_version, source,             -- 'live' | 'unavailable' (nunca 'demo')
  prev_hash, row_hash                -- cadena de hashes
)
-- 2) El cierre y el resultado, también append-only
pick_results (
  id PK, pick_id FK, closing_odds, closing_at, clv_pct,
  result TEXT,                       -- won | lost | push | void
  settled_at, prev_hash, row_hash,
  UNIQUE(pick_id)
)
-- 3) Versiones del modelo
model_versions (version PK, released_at, summary, changes_json, measured_impact)
```

- `picks` **no tiene** `UPDATE` ni `DELETE`: el usuario de la app solo recibe `INSERT`/`SELECT`
  sobre ella (revocación a nivel de Postgres). Una corrección se publica como fila nueva en
  `pick_results`/`pick_corrections`, nunca sobrescribiendo.
- Las migraciones actuales (`_USER_COLUMNS`, etc.) siguen el mismo patrón ya usado.
- `history` queda **solo para backtest**, etiquetada como tal y separada del ledger. El seed
  simulado se elimina de producción (ver §6).

### Captura automática de la cuota de cierre

Job cada 5 min (no un cálculo manual):

1. Selecciona picks `pending` cuyo `event_start` cae en los próximos 20 min.
2. Pide el snapshot de cuotas **solo de esos deportes** (1 crédito por deporte y ejecución).
3. Congela la última cuota vista antes del inicio como `closing_odds`, calcula y **añade** la fila
   en `pick_results`.
4. Al terminar el evento, un job de resultados escribe `result` (o marca `void` si se canceló).

Presupuesto de créditos (20K/mes ≈ 666/día): polling normal + cierre acotado por deporte queda
holgadamente dentro; lo que **no** se hace es pedir cuotas de todos los deportes cada 5 min.

---

## 4. Flujo de interacción

**Visitante → confianza**
`/` (titular + 3 métricas + nº de pérdidas) → `/picks` (filtra "perdidas") → ve pérdidas reales con
fecha y cuota → `/verificacion` (descarga CSV, recalcula hash) → `/modelo` (entiende el edge) →
`/precios`.

**Registro → valor**
`/` → "Pick gratuito de hoy" → email → recibe 1 pick/día → a los 7 días pierde el histórico →
`/precios` → trial 7 días sin tarjeta → configura 1 regla en `/alertas` → recibe alertas en
Telegram/email → al día 8, si no convierte, vuelve a Free sin cobro.

**Suscripción**
`/precios` → Stripe Checkout → webhook firmado → `plan=premium` → `/alertas` completo + ledger sin
límite de 7 días → portal de Stripe para cancelar (efectivo a fin de periodo, sin preguntas).

**Verificación (loop de confianza)**
Cada día: job publica hash cabeza → aparece en `/verificacion` y en el canal público → cualquiera
compara con su CSV. Cada cambio de modelo: fila nueva en `model_versions` y nota en `/modelo`.

---

## 5. Checklist de MVP

### Imprescindible para cobrar (P0)

| # | Entregable | Por qué |
|---|---|---|
| 1 | Tabla `picks` + `pick_results` append-only, con hash chain | Es el producto |
| 2 | Eliminar el historial simulado de producción; seed solo para tests | Riesgo reputacional/legal |
| 3 | Job de cierre: cuota de cierre + CLV + resultado automáticos | Sin esto el CLV es ficción |
| 4 | `/picks`: tabla, 5 filtros, resumen con pérdidas en rojo, CSV, copiar pick | La prueba |
| 5 | `/` con 3 métricas reales del ledger + contador de pérdidas | La promesa |
| 6 | `/modelo` (edge, Kelly 1/4, CLV, binomial, "pesos no públicos") + versiones | Credibilidad |
| 7 | `/verificacion` con hash cabeza diario y verificador en navegador | Diferenciador barato |
| 8 | Stripe $29 + trial 7 días sin tarjeta + Free 1 pick/día + histórico 7 días | Ingreso |
| 9 | Alertas con reglas (liga, edge, cuota, mercado, tiempo) en Email + Telegram, pausar/reanudar | Diferenciación |
| 10 | Bugfixes: edge filtrado en `/api/matches`, auth en `broadcast-test`, delay Free en alertas, caché en `send_digest`, `/mis_picks` con registro | Seguridad y coherencia |
| 11 | Legal: descargo global, aviso MX, identidad real, "no prometemos ganancias" | Cumplimiento |
| 12 | UI: dark/gris, verde/rojo/azul, tabla legible en móvil | Percepción de seriedad |

### Después del lanzamiento (P1, semanas 2–4)

- Web Push (service worker + VAPID) como tercer canal.
- `/ligas` con p-valor y "mejor liga" (n ≥ 30, si no, sin etiqueta).
- `/pick/{id}` permalink público e inmutable (compartir en grupos = crecimiento).
- Anclaje externo del hash (OpenTimestamps) y enlace a seguimiento independiente.
- Historial de impacto por versión del modelo medido automáticamente.
- Email transaccional con dominio propio (SPF/DKIM) y baja en 1 clic.
- SEO: páginas públicas renderizadas en servidor, `sitemap.xml`, datos estructurados.

### Explícitamente fuera del MVP

- Foro/comunidad, app móvil, webhooks públicos, API de pago, comparador de casas, cash-out,
  cualquier forma de "garantía" o "bankroll gestionado".
- Backtest presentado como track record. **Nunca** se mezcla.

---

## 6. La decisión editorial que hay que tomar antes de programar

El brief pide "CLV promedio de 12 meses" y un registro completo. Hoy hay **0 picks reales** y un
historial simulado. Solo hay dos caminos honestos:

**A. Lanzar el registro desde cero, en público (recomendado).**
`/` dice: *"Registro abierto el 13 nov 2026 · 0 picks cerrados"*. Cada pick se publica **antes**
del evento. En 30 días hay ~100 picks: suficiente para que el producto empiece a hablar por sí
solo. El backtest se muestra aparte y **etiquetado como backtest**, nunca como resultados.

**B. Esperar 6–12 meses** a tener historial antes de cobrar. Mata la velocidad de lanzamiento.

Recomiendo A: la transparencia no es tener un historial largo, es **no fingir que lo tienes**. Un
contador que empieza en 0 y sube en público es más creíble que un ROI de 12 meses sin origen
auditable — y es exactamente el relato que ningún competidor puede copiar rápido.

---

## 7. Lo que solo puede hacer el propietario

1. **Pagar el plan 20K** de The Odds API (checkout abierto) → sin datos reales no hay ledger.
2. **Crear el bot de Telegram** con @BotFather (`/newbot`) y entregar `TELEGRAM_BOT_TOKEN` +
   `TELEGRAM_BOT_USERNAME` en Render.
3. **Decidir el nombre real y el correo de contacto** que aparecerán en `/legal` y en el pie.
4. **Revisar el aviso legal de México** con alguien con criterio jurídico local (yo dejo el texto
   base y las banderas de riesgo, no sustituyo asesoría legal).
