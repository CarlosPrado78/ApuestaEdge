/* ApuestaEdge — panel de recomendaciones (sin dependencias externas). */
"use strict";

const state = {
  plan: "free",
  authenticated: false,
  email: "",
  billing: "stripe",
  sport: "",
  bankroll: 1000,
  plans: null,
};
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
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
let picksRequest = 0;
let subRequest = 0;

async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  const token = localStorage.getItem("ae_token");
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const r = await fetch(path, { ...opts, headers, credentials: "same-origin" });
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

/* ---------------------------------------------------------------- cuenta */
function applyAccount(me) {
  const authed = Boolean(me && me.authenticated);
  state.authenticated = authed;
  state.email = authed ? (me.email || "") : "";
  state.plan = authed ? (me.plan === "premium" ? "premium" : "free") : "free";
  state.billing = (me && me.billing) || state.billing;

  const badge = $("#account-plan");
  badge.textContent = state.plan === "premium" ? "Premium" : "Free";
  badge.classList.toggle("premium", state.plan === "premium");
  badge.classList.toggle("free", state.plan !== "premium");

  const emailEl = $("#account-email");
  emailEl.textContent = state.email;
  emailEl.hidden = !authed;
  $("#btn-login").hidden = authed;
  $("#btn-logout").hidden = !authed;

  if (authed) $("#email").value = state.email;

  renderPlanBanner();
  renderPlans();
  updateSubscribeButton();
}

function renderPlanBanner() {
  const box = $("#plan-banner");
  if (!box) return;
  box.hidden = false;
  if (!state.authenticated) {
    box.className = "plan-banner free";
    box.innerHTML = `
      <div>Estás viendo el <b>plan Free</b>: 10 picks/día con edge ≥ 6% y
        análisis resumido. <b>Premium</b> desbloquea 20 picks, edge ≥ 3% y el
        análisis completo.</div>
      <button class="btn primary" type="button" data-go="login">Entrar / crear cuenta</button>`;
    box.querySelector("[data-go=login]").addEventListener("click", openLogin);
    return;
  }
  if (state.plan === "premium") {
    box.className = "plan-banner premium";
    box.innerHTML = `
      <div>✓ <b>Premium activo</b> · 20 picks al día con edge ≥ 3%, stake Kelly,
        confianza y backtest completos.</div>
      <button class="btn ghost" type="button" data-go="sub">Ver mi suscripción</button>`;
  } else {
    box.className = "plan-banner free";
    box.innerHTML = `
      <div><b>Plan Free</b> · 10 picks/día con edge ≥ 6% y análisis resumido.
        Estás perdiendo los mejores valores (edge 3–6%) y el análisis completo.</div>
      <button class="btn primary" type="button" data-go="premium">Desbloquear Premium</button>`;
  }
  box.querySelector("[data-go]").addEventListener("click", (e) => {
    if (e.currentTarget.dataset.go === "sub") {
      $("#sub-panel").scrollIntoView({ behavior: "smooth", block: "center" });
    } else {
      $("#plan-select").value = "premium";
      $("#subscribe-form").scrollIntoView({ behavior: "smooth", block: "center" });
      $("#email").focus({ preventScroll: true });
    }
  });
}

function updateSubscribeButton() {
  const btn = $("#subscribe-btn");
  if (!btn) return;
  const sel = $("#plan-select");
  btn.textContent = sel && sel.value === "premium" ? "Continuar a pago" : "Crear cuenta";
}

function openLogin() {
  const dlg = $("#login-dialog");
  if (!$("#login-email").value && state.email) $("#login-email").value = state.email;
  $("#login-msg").textContent = "";
  if (typeof dlg.showModal === "function") dlg.showModal();
  else dlg.setAttribute("open", "");
  setTimeout(() => $("#login-email").focus(), 50);
}

function closeLogin() {
  const dlg = $("#login-dialog");
  if (typeof dlg.close === "function") dlg.close();
  else dlg.removeAttribute("open");
}

async function refreshAccount() {
  if (!localStorage.getItem("ae_token")) { applyAccount(null); return null; }
  try {
    const me = await api("/api/auth/me");
    if (me && me.authenticated) { applyAccount(me); return me; }
  } catch (err) {
    if (!err.status || err.status === 401) localStorage.removeItem("ae_token");
  }
  applyAccount(null);
  return null;
}

async function afterAccountChange() {
  await Promise.all([loadPicks(), loadSubscription(), loadTelegram()]);
}

async function login(email) {
  const r = await api("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (r.token) localStorage.setItem("ae_token", r.token);
  applyAccount({ authenticated: true, email: r.email, plan: r.plan,
                 billing: r.demo ? "demo" : "stripe" });
  await afterAccountChange();
  return r;
}

async function logout() {
  try { await api("/api/auth/logout", { method: "POST" }); } catch { /* da igual */ }
  localStorage.removeItem("ae_token");
  applyAccount(null);
  await afterAccountChange();
}

/* ------------------------------------------------------------------ picks */
async function loadPicks() {
  const box = $("#picks-list");
  const requestId = ++picksRequest;
  box.innerHTML = '<p class="muted">Calculando valor esperado…</p>';
  const q = new URLSearchParams({ plan: state.plan, bankroll: state.bankroll });
  if (state.sport) q.set("sport", state.sport);
  try {
    const data = await api(`/api/recommendations?${q}`);
    if (requestId !== picksRequest) return;   // respuesta vieja: se descarta
    const label = data.plan === "premium" ? "Premium" : "Free";
    if (!data.picks.length) {
      $("#picks-sub").innerHTML =
        `Plan <b>${label}</b> · edge mínimo ${pct(data.min_edge, 0)} · ` +
        `${data.models_scanned} partidos analizados · ${data.value_candidates} con valor`;
      box.innerHTML = '<p class="muted">Sin picks con valor ahora mismo. ' +
        'Esperar a que el mercado ofrezca ventaja es parte del método: ' +
        'no apostar también es una decisión estadística.</p>';
      return;
    }
    $("#picks-sub").innerHTML =
      `Plan <b>${label}</b> · Top ${data.count} · edge mínimo ${pct(data.min_edge, 0)} · ` +
      `${data.models_scanned} partidos analizados · ${data.value_candidates} con valor`;
    box.innerHTML = data.picks.map(card).join("");
    $$(".why-btn").forEach((b) => b.addEventListener("click", () => {
      b.closest(".pick").classList.toggle("open");
      b.textContent = b.closest(".pick").classList.contains("open")
        ? "Ocultar análisis" : "¿Por qué confiar?";
    }));
  } catch (e) {
    if (requestId !== picksRequest) return;
    if (e.status === 402) {
      const needsLogin = !state.authenticated;
      box.innerHTML = `
        <div class="pick locked">
          <div class="pick-top"><div class="match">
            <span class="league">🔒 Contenido Premium</span>
            <span class="teams">${esc(e.message)}</span>
            <span class="time">Desbloquea 20 picks con edge ≥ 3%, stake Kelly,
              confianza, backtest y análisis completo.</span>
          </div>
          <button class="btn primary" type="button" style="align-self:center"
                  data-go="${needsLogin ? "login" : "premium"}">
            ${needsLogin ? "Entrar / crear cuenta" : "Ver planes"}</button></div>
        </div>`;
      const btn = box.querySelector("[data-go]");
      btn.addEventListener("click", () => {
        if (btn.dataset.go === "login") openLogin();
        else $("#precios").scrollIntoView({ behavior: "smooth" });
      });
      return;
    }
    box.innerHTML = `<p class="muted">No se pudieron cargar los picks: ${esc(e.message)}</p>`;
  }
}

function card(p) {
  const locked = p.tier === "free";
  const k = p.kelly || {};
  const tierTag = locked ? "" : '<span class="premium-tag">PREMIUM</span>';
  return `
  <article class="pick">
    <div class="pick-top">
      <div class="match">
        <span class="league">${icon(p.sport)} ${esc(p.league || p.sport_key)}${tierTag}</span>
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
      <div class="locked">🔒 ${esc(p.explanation.locked_note || "Stake Kelly, confianza y backtest completos están en Premium.")}
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
    state.plans = plans;
    renderPlans();
  } catch { /* ignora */ }
}

function ctaFor(key) {
  if (state.authenticated && state.plan === key) {
    return { label: "Tu plan actual", disabled: true };
  }
  if (state.authenticated && state.plan === "premium" && key === "free") {
    return { label: "Incluido en Premium", disabled: true };
  }
  if (key === "premium") {
    return { label: state.authenticated ? "Hazte Premium" : "Empezar Premium",
             disabled: false };
  }
  return { label: state.authenticated ? "Plan Free" : "Empezar gratis",
           disabled: false };
}

function renderPlans() {
  if (!state.plans) return;
  $("#plans").innerHTML = Object.entries(state.plans).map(([key, p]) => {
    const cta = ctaFor(key);
    return `
      <div class="plan ${key === "premium" ? "featured" : ""}">
        ${key === "premium" ? '<span class="tag">MÁS POPULAR</span>' : ""}
        <h3>${esc(p.name)}</h3>
        <div class="price">${p.price_usd === 0 ? "Gratis" : "$" + p.price_usd + ""}
          <small>${p.price_usd === 0 ? "/ siempre" : "/ mes"}</small></div>
        <ul>${p.features.map((f) => `<li>${esc(f)}</li>`).join("")}</ul>
        <button class="btn ${key === "premium" ? "primary" : "ghost"} plan-cta
                ${cta.disabled ? "plan-current" : ""}" data-plan="${key}"
                ${cta.disabled ? "disabled" : ""}>${cta.label}</button>
      </div>`;
  }).join("");
  $$(".plan-cta:not([disabled])").forEach((b) => b.addEventListener("click", () => {
    $("#plan-select").value = b.dataset.plan;
    updateSubscribeButton();
    $("#subscribe-form").scrollIntoView({ behavior: "smooth", block: "center" });
    if (!state.authenticated) $("#email").focus({ preventScroll: true });
  }));
}

/* ---------------------------------------------------------------- events */
$("#btn-login").addEventListener("click", openLogin);
$("#btn-logout").addEventListener("click", logout);
$("#login-cancel").addEventListener("click", closeLogin);
$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msg = $("#login-msg");
  const email = ($("#login-email").value || "").trim();
  if (!email) return;
  msg.textContent = "Entrando…";
  try {
    const r = await login(email);
    closeLogin();
    msg.textContent = "";
    if (r.plan === "premium") {
      showActivation("✓ Sesión iniciada como Premium.", "ok", 3500);
    }
  } catch (err) {
    msg.textContent = `⚠️ ${err.message}`;
  }
});
$("#login-dialog").addEventListener("click", (e) => {
  if (e.target === $("#login-dialog")) closeLogin();
});

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
$("#plan-select").addEventListener("change", updateSubscribeButton);
$("#subscribe-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msg = $("#sub-msg");
  const plan = $("#plan-select").value;
  const email = ($("#email").value || state.email || "").trim();
  msg.textContent = "Enviando…";
  try {
    const r = await api("/api/subscribe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, plan }),
    });
    if (r.token) localStorage.setItem("ae_token", r.token);
    if (r.checkout_url) {                      // pago real con Stripe
      msg.textContent = "Redirigiendo a Stripe…";
      setTimeout(() => { window.location.href = r.checkout_url; }, 400);
      return;
    }
    msg.textContent = r.message || "✅ Listo.";
    await refreshAccount();
    await afterAccountChange();
    if (r.plan === "premium" || r.activated) {
      showActivation("✓ Premium activado. Ya tienes el análisis completo.", "ok", 4500);
    }
  } catch (err) { msg.textContent = `⚠️ ${err.message}`; }
});

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
    box.innerHTML = "Inicia sesión arriba para obtener tu enlace de vinculación con Telegram.";
  } catch {
    box.textContent = "No se pudo cargar el estado de Telegram.";
  }
}

/* ------------------------------------------------------- suscripción */
async function loadSubscription() {
  const panel = $("#sub-panel");
  if (!panel) return;
  const requestId = ++subRequest;
  const sync = $("#btn-sync");
  const btn = $("#btn-portal");
  if (!state.authenticated) { panel.hidden = true; return; }
  sync.hidden = false;
  sync.onclick = async () => {
    sync.disabled = true;
    sync.textContent = "Actualizando…";
    await refreshAccount();
    await Promise.all([loadSubscription(), loadPicks()]);
    sync.disabled = false;
    sync.textContent = "Actualizar estado";
  };
  try {
    const s = await api("/api/billing/subscription");
    if (requestId !== subRequest) return;    // respuesta vieja: se descarta
    panel.hidden = false;
    const box = $("#sub-state");
    if (s.billing === "demo") {
      box.innerHTML = `Modo <b>demo</b> · plan <b>${esc(s.plan)}</b> ` +
        "(sin cobros reales).";
      btn.hidden = true;
      return;
    }
    if (s.plan === "premium") {
      let txt = "✅ <b>Premium activo</b>";
      if (s.current_period_end) {
        const fecha = new Date(s.current_period_end).toLocaleDateString("es-MX");
        txt += s.cancel_at_period_end
          ? ` · se cancela el <b>${fecha}</b>`
          : ` · renueva el <b>${fecha}</b>`;
      }
      box.innerHTML = txt;
    } else {
      box.innerHTML = "📦 Plan <b>Free</b> · Premium desbloquea 20 picks y todo el análisis.";
    }
    btn.hidden = !s.can_manage;
    if (!s.can_manage && s.plan === "premium") {
      box.innerHTML += '<br><small class="muted">Pago registrado. Si el portal no aparece, ' +
        'pulsa «Actualizar estado»; el webhook de Stripe puede tardar unos segundos.</small>';
    }
    btn.onclick = async () => {
      btn.disabled = true;
      try {
        const r = await api("/api/billing/portal", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: state.email }),
        });
        if (r.portal_url) window.location.href = r.portal_url;
      } catch (err) {
        box.innerHTML = `⚠️ ${esc(err.message)}`;
      } finally { btn.disabled = false; }
    };
  } catch { if (requestId === subRequest) panel.hidden = true; }
}

/* ------------------------------------------------ volver desde Stripe */
function showActivation(html, kind = "", timeout = 0) {
  const box = $("#activation");
  box.hidden = false;
  box.className = `activation ${kind}`;
  box.innerHTML = html;
  if (timeout) setTimeout(() => { box.hidden = true; }, timeout);
}
function hideActivation() { $("#activation").hidden = true; }

async function handleStripeReturn() {
  const params = new URLSearchParams(location.search);
  if (params.get("suscripcion") !== "ok") return;
  const sessionId = params.get("session_id");
  showActivation("⏳ Confirmando tu pago con Stripe…");
  let activated = state.plan === "premium";

  if (sessionId) {
    try {
      const r = await api("/api/billing/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      if (r.token) localStorage.setItem("ae_token", r.token);
      activated = r.plan === "premium";
      if (!activated) {
        showActivation("Stripe todavía está procesando el pago. Esperando confirmación…");
      }
    } catch (err) {
      showActivation(`No pudimos verificar el pago automáticamente: ${esc(err.message)}. Reintentando…`, "error");
    }
  }

  for (let i = 0; i < 15 && !activated; i++) {
    await sleep(2500);
    const me = await refreshAccount();
    if (me && me.plan === "premium") { activated = true; break; }
  }

  if (activated) {
    await refreshAccount();
    showActivation("✓ <b>Premium activado</b>. Ya ves 20 picks con edge ≥ 3% y análisis completo.", "ok", 8000);
  } else {
    showActivation("El pago puede haberse completado, pero Premium aún no aparece. " +
      "Pulsa <b>«Actualizar estado»</b> en tu suscripción; si persiste, escríbenos.", "error");
  }
  history.replaceState(null, "", location.pathname + "#picks");
  await Promise.all([loadPicks(), loadSubscription()]);
}

/* --------------------------------------------------------------- boot */
async function init() {
  await loadPlans();
  await refreshAccount();
  await Promise.all([
    loadPicks(), loadStats(), loadPerformance(), loadTelegram(), loadSubscription()]);
  await handleStripeReturn();
}

init();
