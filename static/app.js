/* ApuestaEdge — panel de recomendaciones (sin dependencias externas). */
"use strict";

const state = { plan: "free", sport: "", bankroll: 1000 };
const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

const pct = (x, d = 1) => `${(x * 100).toFixed(d)}%`;
const signed = (x, d = 1) => `${x >= 0 ? "+" : ""}${(x * 100).toFixed(d)}%`;
/* Para valores que la API ya devuelve en porcentaje (roi_pct, avg_clv_pct…). */
const spct = (x, d = 1) => `${x >= 0 ? "+" : ""}${Number(x).toFixed(d)}%`;
const num = (x, d = 2) => (Number.isFinite(x) ? x.toFixed(d) : "—");
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const icon = (s) => ({ soccer: "⚽", basketball: "🏀", tennis: "🎾",
                       americanfootball: "🏈", boxing: "🥊", baseball: "⚾",
                       formula1: "🏎️", motogp: "🏍️", horseracing: "🐎" }[s] || "🏅");
const SPORT_NAME = { soccer: "Fútbol", basketball: "Básquet", tennis: "Tenis",
                     americanfootball: "Fútbol americano", boxing: "Boxeo",
                     baseball: "Béisbol", formula1: "Fórmula 1",
                     motogp: "Motociclismo", horseracing: "Carreras de caballos" };
const when = (iso) => {
  try {
    return new Date(iso).toLocaleString("es-MX",
      { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
  } catch { return iso || "por confirmar"; }
};

async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  const token = localStorage.getItem("ae_token");
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const r = await fetch(path, { ...opts, headers });
  if (!r.ok) {
    let body = {};
    try { body = await r.json(); } catch { /* sin cuerpo */ }
    const detail = body?.detail;
    const msg = (detail && detail.message) || (typeof detail === "string" ? detail : `HTTP ${r.status}`);
    const err = new Error(msg);
    err.status = r.status;
    err.detail = detail;
    throw err;
  }
  return r.json();
}

/* ------------------------------------------------------------------ picks */
async function loadPicks() {
  const box = $("#picks-list");
  box.innerHTML = '<p class="muted">Calculando valor esperado…</p>';
  const q = new URLSearchParams({ plan: state.plan, bankroll: state.bankroll });
  if (state.sport) q.set("sport", state.sport);
  try {
    const data = await api(`/api/recommendations?${q}`);
    if (!data.picks.length) {
      box.innerHTML = '<p class="muted">Sin picks con valor ahora mismo. ' +
        'Esperar a que el mercado ofrezca ventaja es parte del método: ' +
        'no apostar también es una decisión estadística.</p>';
      return;
    }
    $("#picks-sub").textContent =
      `Top ${data.count} · edge mínimo ${pct(data.min_edge, 0)} · ` +
      `${data.models_scanned} partidos analizados · ${data.value_candidates} con valor`;
    box.innerHTML = data.picks.map(card).join("");
    $$(".why-btn").forEach((b) => b.addEventListener("click", () => {
      b.closest(".pick").classList.toggle("open");
      b.textContent = b.closest(".pick").classList.contains("open")
        ? "Ocultar análisis" : "¿Por qué confiar?";
    }));
  } catch (e) {
    if (e.status === 402) {
      box.innerHTML = `
        <div class="pick locked">
          <div class="pick-top"><div class="match">
            <span class="league">🔒 Contenido Premium</span>
            <span class="teams">${e.message}</span>
            <span class="time">Desbloquea el análisis completo: Kelly, confianza, backtest y todos los valores con edge ≥ 3%.</span>
          </div>
          <a class="btn primary" href="#precios" style="align-self:center">Ver planes</a></div>
        </div>`;
      return;
    }
    box.innerHTML = `<p class="muted">No se pudieron cargar los picks: ${esc(e.message)}</p>`;
  }
}

function card(p) {
  const locked = p.tier === "free";
  const k = p.kelly || {};
  return `
  <article class="pick">
    <div class="pick-top">
      <div class="match">
        <span class="league">${icon(p.sport)} ${esc(p.league || p.sport_key)}</span>
        <span class="teams">${esc(p.event || `${p.home_team} vs ${p.away_team}`)}</span>
        <span class="time">🕐 ${esc(when(p.commence_time))} UTC · antes del pitido inicial</span>
      </div>
      <div class="sel">${esc(p.selection_label)}<small>cuota ${num(p.odds)} · ${esc(p.bookmaker)}</small></div>
      <div class="val"><label>Edge</label><b class="pos">${signed(p.edge)}</b>
        <span class="badge edge">modelo ${pct(p.model_prob)}</span></div>
      <div class="val"><label>Valor esperado</label><b class="pos">${signed(p.ev)}</b>
        <span class="badge ev">mercado ${pct(p.market_prob)}</span></div>
      <div class="val"><label>Confianza</label><b>${pct(p.confidence, 0)}</b>
        <span class="conf"><i style="width:${Math.round(p.confidence * 100)}%"></i></span></div>
      <button class="why-btn" type="button">¿Por qué confiar?</button>
    </div>
    <div class="pick-body">
      <div class="why-summary">${esc(p.explanation.summary)}</div>
      <ol class="steps">
        ${p.explanation.steps.map((s) => `
          <li><b>${esc(s.title)}</b><p>${esc(s.detail)}</p></li>`).join("")}
      </ol>
      ${locked ? `
      <div class="locked">🔒 Stake Kelly, confianza y backtest completos están en Premium.
        <a href="#precios">Desbloquear análisis →</a></div>` : `
      <div class="mini">
        <span>Kelly completo: <b>${num(k.kelly_full_pct)}%</b> → usamos
          <b>${num(k.kelly_fraction_used, 2)}×</b> con tope 3%</span>
        <span>Stake sugerido: <b>${num(k.stake_pct)}%</b> = <b>${num(k.stake_units)} u.</b></span>
        <span>Mejor cuota entre <b>${p.books_count}</b> casas</span>
        ${p.model_detail ? `<span>Modelo: <b>${esc(p.model_detail)}</b></span>` : ""}
      </div>
      ${p.backtest ? `<div class="mini">
        <span>Backtest ${p.backtest.bets} picks: ROI <b>${spct(p.backtest.roi_pct)}</b></span>
        <span>Acierto <b>${num(p.backtest.hit_rate_pct, 1)}%</b> vs breakeven
          <b>${num(p.backtest.breakeven_hit_pct, 1)}%</b></span>
        <span>CLV <b>${spct(p.backtest.avg_clv_pct)}</b></span>
        <span>Drawdown <b>${num(p.backtest.max_drawdown_units)} u.</b></span>
        <span>p = <b>${num(p.backtest.binomial_p_value, 3)}</b></span>
      </div>` : ""}`}
      <div class="risks"><h4>Riesgos que debes conocer</h4>
        <ul>${p.explanation.risks.map((r) => `<li>${esc(r)}</li>`).join("")}</ul></div>
    </div>
  </article>`;
}

/* ------------------------------------------------------------ rendimiento */
async function loadStats() {
  try {
    const [perf, health] = await Promise.all([
      api("/api/performance"), api("/api/health")]);
    if (perf.bets) {
      $("#hs-roi").textContent = spct(perf.roi_pct);
      $("#hs-hit").textContent = num(perf.hit_rate_pct, 1) + "%";
      $("#hs-clv").textContent = spct(perf.avg_clv_pct);
      $("#hs-p").textContent = num(perf.binomial_p_value, 3);
      $("#hs-bets").textContent = String(perf.bets);
    }
    $("#source-note").textContent =
      (health.source === "live"
        ? "✅ Cuotas en vivo (The Odds API) actualizadas cada pocos minutos."
        : "ℹ️ Modo demostración: partidos y cuotas de ejemplo. Añade ODDS_API_KEY al entorno para datos en vivo.") +
      ` · ${health.matches} partidos en el radar.`;
  } catch { /* silencioso: el hero sigue siendo legible */ }
}

async function loadPerformance() {
  try {
    const [all, by] = await Promise.all([
      api("/api/performance"), api("/api/performance/by-sport")]);
    if (all.bets) {
      $("#metrics").innerHTML = [
        ["ROI / yield", spct(all.roi_pct), "beneficio por unidad apostada"],
        ["Acierto", num(all.hit_rate_pct, 1) + "%", `breakeven ${num(all.breakeven_hit_pct, 1)}%`],
        ["Profit factor", num(all.profit_factor), "ganancias ÷ pérdidas"],
        ["CLV medio", spct(all.avg_clv_pct), "entrada vs cierre"],
        ["Drawdown máx.", num(all.max_drawdown_units) + " u.", "peor caída acumulada"],
        ["Test binomial", "p = " + num(all.binomial_p_value, 3),
          all.binomial_p_value < 0.05 ? "ventaja significativa (95%)" : "ventaja aún no significativa"],
        ["Pick auditados", String(all.bets), `${all.wins} ganados`],
        ["Cuota media", num(all.avg_odds), "precio medio de entrada"],
      ].map(([l, v, s]) => `<div class="metric"><b>${v}</b><label>${l}</label><small>${s}</small></div>`).join("");
      drawEquity(all.equity_curve || []);
    }
    const rows = Object.entries(by.by_sport || {}).map(([sport, s]) => `
      <tr><td>${icon(sport)} ${esc(SPORT_NAME[sport] || sport)}</td><td>${s.bets}</td>
      <td>${num(s.hit_rate_pct, 1)}%</td>
      <td class="${s.roi_pct >= 0 ? "pos" : ""}">${spct(s.roi_pct)}</td>
      <td>${spct(s.avg_clv_pct)}</td><td>${num(s.binomial_p_value, 3)}</td></tr>`).join("");
    $("#sport-table tbody").innerHTML = rows || '<tr><td colspan="6">Sin datos</td></tr>';
  } catch { /* la sección queda con su mensaje de carga */ }
}

function drawEquity(curve) {
  if (!curve.length) return;
  const w = 560, h = 170, pad = 12;
  const min = Math.min(0, ...curve), max = Math.max(0, ...curve);
  const span = max - min || 1;
  const x = (i) => pad + (i / Math.max(curve.length - 1, 1)) * (w - 2 * pad);
  const y = (v) => h - pad - ((v - min) / span) * (h - 2 * pad);
  const pts = curve.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const zero = y(0).toFixed(1);
  const last = curve[curve.length - 1];
  $("#equity").innerHTML = `
    <svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" role="img" aria-label="Curva de equity">
      <line x1="${pad}" y1="${zero}" x2="${w - pad}" y2="${zero}"
            stroke="#3a4a6d" stroke-dasharray="4 4"/>
      <polyline points="${pts}" fill="none" stroke="#38e07b" stroke-width="2.5"
                stroke-linejoin="round" stroke-linecap="round"/>
    </svg>
    <p class="footnote">Cierre actual: <b class="pos">${last >= 0 ? "+" : ""}${num(last)} unidades</b>
      sobre stakes de 0.5–2.5% del bankroll.</p>`;
}

/* ---------------------------------------------------------------- planes */
async function loadPlans() {
  try {
    const { plans } = await api("/api/plans");
    $("#plans").innerHTML = Object.entries(plans).map(([key, p]) => `
      <div class="plan ${key === "premium" ? "featured" : ""}">
        ${key === "premium" ? '<span class="tag">MÁS POPULAR</span>' : ""}
        <h3>${esc(p.name)}</h3>
        <div class="price">${p.price_usd === 0 ? "Gratis" : "$" + p.price_usd + ""}
          <small>${p.price_usd === 0 ? "/ siempre" : "/ mes"}</small></div>
        <ul>${p.features.map((f) => `<li>${esc(f)}</li>`).join("")}</ul>
        <button class="btn ${key === "premium" ? "primary" : "ghost"} plan-cta"
                data-plan="${key}">${key === "premium" ? "Empezar Premium" : "Plan Free"}</button>
      </div>`).join("");
    $$(".plan-cta").forEach((b) => b.addEventListener("click", () => {
      setPlan(b.dataset.plan);
      $("#plan-select").value = b.dataset.plan;
      $("#email").focus({ preventScroll: false });
      $("#subscribe-form").scrollIntoView({ behavior: "smooth", block: "center" });
    }));
  } catch { /* ignora */ }
}

function setPlan(plan) {
  state.plan = plan;
  $$(".plan-btn").forEach((b) => b.classList.toggle("active", b.dataset.plan === plan));
  $("#btn-premium").textContent = plan === "premium" ? "Premium ✓" : "Premium";
  loadPicks();
}

/* ---------------------------------------------------------------- events */
$$(".plan-btn").forEach((b) => b.addEventListener("click", () => setPlan(b.dataset.plan)));
$$(".chip").forEach((c) => c.addEventListener("click", () => {
  $$(".chip").forEach((x) => x.classList.remove("active"));
  c.classList.add("active");
  state.sport = c.dataset.sport;
  loadPicks();
}));
$("#bankroll").addEventListener("change", (e) => {
  const v = Number(e.target.value);
  state.bankroll = Number.isFinite(v) && v > 0 ? v : 1000;
  loadPicks();
});
$("#subscribe-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msg = $("#sub-msg");
  msg.textContent = "Enviando…";
  try {
    const r = await api("/api/subscribe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: $("#email").value, plan: $("#plan-select").value }),
    });
    if (r.token) localStorage.setItem("ae_token", r.token);
    if (r.checkout_url) {                      // pago real con Stripe
      msg.textContent = "Redirigiendo a Stripe…";
      setTimeout(() => { window.location.href = r.checkout_url; }, 500);
      return;
    }
    msg.textContent = r.message || "✅ Listo.";
    e.target.reset();
    if (r.plan === "premium" || r.activated) setPlan($("#plan-select").value);
  } catch (err) { msg.textContent = `⚠️ ${err.message}`; }
});

/* Restaura la sesión (plan premium real) al cargar. */
async function restoreSession() {
  if (!localStorage.getItem("ae_token")) return;
  try {
    const me = await api("/api/auth/me");
    if (me.authenticated && me.plan === "premium" && state.plan !== "premium") {
      setPlan("premium");
    }
  } catch { /* sesión inválida: se ignora */ }
}

/* ------------------------------------------------------- alertas Telegram */
async function loadTelegram() {
  const box = $("#tg-body");
  if (!box) return;
  try {
    const t = await api("/api/telegram");
    if (!t.configured) {
      box.innerHTML = "Próximamente aquí: crea un bot con <b>@BotFather</b> y define " +
        `<code>TELEGRAM_BOT_TOKEN</code> en el servidor para recibir cada pick con valor ` +
        "en tu Telegram.";
      return;
    }
    if (t.linked) {
      box.innerHTML = `✅ <b>Vinculado</b> · plan <b>${esc(t.plan)}</b> · recibirás picks ` +
        `con edge ≥ ${pct(t.min_edge, 0)} cada ${Math.round(t.interval_seconds / 60)} min ` +
        "(sin repetir ninguno).";
      return;
    }
    if (t.authenticated && t.deep_link) {
      box.innerHTML = `🔗 Vincula tu cuenta con un clic: ` +
        `<a href="${esc(t.deep_link)}" target="_blank" rel="noopener">abrir @${esc(t.bot_username)} en Telegram</a> ` +
        `o envía <code>/start ${esc(t.link_code)}</code> dentro del bot.`;
      return;
    }
    box.innerHTML = "Crea tu cuenta en el formulario de arriba para obtener tu " +
      "enlace de vinculación con Telegram.";
  } catch {
    box.textContent = "No se pudo cargar el estado de Telegram.";
  }
}

/* ------------------------------------------------------- suscripción */
async function loadSubscription() {
  const panel = $("#sub-panel");
  if (!panel) return;
  try {
    const s = await api("/api/billing/subscription");
    if (!s.authenticated) { panel.hidden = true; return; }
    panel.hidden = false;
    const state = $("#sub-state");
    const btn = $("#btn-portal");
    if (s.billing === "demo") {
      state.innerHTML = `Modo <b>demo</b> · plan <b>${esc(s.plan)}</b> ` +
        "(sin cobros reales).";
      btn.hidden = true;
      return;
    }
    if (s.plan === "premium") {
      let txt = "✅ <b>Premium activo</b>";
      if (s.current_period_end) {
        const fecha = new Date(s.current_period_end).toLocaleDateString("es-ES");
        txt += s.cancel_at_period_end
          ? ` · se cancela el <b>${fecha}</b>`
          : ` · renueva el <b>${fecha}</b>`;
      }
      state.innerHTML = txt;
    } else {
      state.innerHTML = "📦 Plan <b>Free</b> · Premium desbloquea todo el análisis.";
    }
    btn.hidden = !s.can_manage;
    btn.onclick = async () => {
      const email = ($("#email").value || "").trim();
      try {
        const r = await api("/api/billing/portal", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email }),
        });
        if (r.portal_url) window.location.href = r.portal_url;
      } catch (err) {
        state.innerHTML = `⚠️ ${esc(err.message)} ` +
          "(necesitas iniciar sesión con el correo de la compra).";
      }
    };
  } catch { panel.hidden = true; }
}

/* --------------------------------------------------------------- boot */
loadStats();
loadPicks();
loadPerformance();
loadPlans();
loadTelegram();
loadSubscription();
restoreSession();
