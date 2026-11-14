/* Reglas configurables de alertas: liga, edge mínimo, rango de cuota,
   mercado y tiempo hasta el inicio. Pausar / reanudar en un clic. */
"use strict";

const I18N = {
  es: {
    nav_home: "Inicio", nav_ledger: "Registro de picks",
    nav_leagues: "Ligas", nav_model: "Modelo",
    nav_verify: "Verificación", nav_alerts: "Alertas",
    nav_pricing: "Precios",
    eyebrow: "Alertas operativas",
    title: "Tus reglas, tus filtros, sin ruido.",
    intro: "Define exactamente qué quieres recibir: liga, edge mínimo, rango de cuota, mercado y margen de tiempo antes del inicio. Cada coincidencia se envía una sola vez por Email o Telegram, con enlace directo a la casa sin código de afiliado, y puedes pausar o reanudar cualquier regla con un clic.",
    sum_active: "Reglas activas", sum_plan: "Plan y cadencia",
    sum_channels: "Canales", sum_sent: "Envíos registrados",
    sum_dedupe: "Sin duplicados por regla y canal",
    loading: "Cargando…",
    affiliate_note: "Transparencia comercial: los enlaces a casas incluidos en las alertas son directos y no llevan códigos de afiliado ni comisiones por clic.",
    auth_title: "Inicia sesión o crea tu cuenta gratuita para guardar reglas",
    auth_sub: "En el plan Free puedes activar 1 regla (edge ≥ 6%, con el retraso de 2 horas respecto al registro en vivo). Premium desbloquea hasta 10 reglas en tiempo real desde edge ≥ 3%.",
    auth_login: "Entrar", auth_register: "Crear cuenta gratis",
    form_title: "Nueva regla de alerta",
    form_sub: "Solo se avisa cuando un pick supera todos los filtros a la vez.",
    f_name: "Nombre de la regla", f_edge: "Edge mínimo (%)",
    f_odds_min: "Cuota mínima", f_odds_max: "Cuota máxima",
    f_market: "Mercado", f_time: "Tiempo hasta el inicio",
    m_all: "Todos los mercados", m_h2h: "Ganador / 1X2 (h2h)",
    m_outright: "Ganador de torneo (outright)",
    t_any: "Cualquier margen antes del inicio",
    t_30: "≤ 30 minutos", t_60: "≤ 1 hora", t_180: "≤ 3 horas",
    t_360: "≤ 6 horas", t_1440: "≤ 24 horas",
    f_leagues: "Ligas (vacío = todas las ligas)",
    f_channels: "Canales de entrega",
    ch_email: "Email (e historial web)",
    ch_telegram: "Telegram instantáneo",
    tg_hint: "Para recibir en Telegram, vincula tu cuenta con el código de la portada.",
    tg_linked_ok: "Telegram vinculado y listo para entregar tus reglas.",
    btn_save: "Guardar regla",
    rules_title: "Mis reglas configuradas",
    rules_sub: "Pausa o reanuda cuando quieras sin borrar la configuración.",
    btn_evaluate: "Comprobar ahora",
    rules_empty: "Todavía no tienes reglas guardadas.",
    history_title: "Historial de alertas enviadas",
    history_sub: "Cada envío queda anotado con la regla que lo disparó, el canal, la cuota de entrada y el enlace directo sin afiliado.",
    deliveries_empty: "Todavía no se ha disparado ninguna alerta para tu cuenta.",
    col_date: "Fecha", col_channel: "Canal", col_league: "Liga / Evento",
    col_pick: "Selección", col_odds: "Cuota", col_edge: "Edge",
    col_book: "Casa (sin afiliado)",
    limit_sub: "{used} de {max} reglas en tu plan",
    delay_free: "Retraso Free de 2 h · edge mín. 6%",
    delay_premium: "Tiempo real · edge mín. 3%",
    ch_sub_guest: "Inicia sesión para activar tus canales",
    ch_sub_ready: "Email activo · Telegram {tg}",
    tg_yes: "vinculado", tg_no: "sin vincular",
    badge_active: "Activa", badge_paused: "Pausada",
    btn_pause: "Pausar", btn_resume: "Reanudar", btn_delete: "Eliminar",
    all_leagues: "Todas las ligas",
    any_time: "Sin límite de tiempo",
    up_to_min: "≤ {m} min al inicio",
    rule_saved: "Regla guardada.",
    eval_done: "Comprobación lista ({n} envíos nuevos).",
    direct_no_aff: "enlace directo · sin afiliado",
    footer_disclaimer: "<strong>+18 · Uso responsable. No prometemos ganancias.</strong> Los pronósticos deportivos implican riesgo y los datos históricos no garantizan resultados futuros. Este sitio ofrece análisis estadístico independiente con fines informativos; no es un operador de juego, no acepta fondos ni custodia dinero (aviso aplicable en México y demás jurisdicciones).",
    footer_copyright: "ApuestaEdge © 2026 · Desarrollado y mantenido por Carlos Prado · Auditoría pública en /verificacion",
  },
  en: {
    nav_home: "Home", nav_ledger: "Pick ledger",
    nav_leagues: "Leagues", nav_model: "Model",
    nav_verify: "Verification", nav_alerts: "Alerts",
    nav_pricing: "Pricing",
    eyebrow: "Operational alerts",
    title: "Your rules, your filters, zero noise.",
    intro: "Define exactly what you want to receive: league, minimum edge, odds range, market and time window before kickoff. Each match is sent once via Email or Telegram, with a direct non-affiliate bookmaker link, and you can pause or resume any rule with one click.",
    sum_active: "Active rules", sum_plan: "Plan & cadence",
    sum_channels: "Channels", sum_sent: "Recorded deliveries",
    sum_dedupe: "No duplicates per rule and channel",
    loading: "Loading…",
    affiliate_note: "Commercial transparency: bookmaker links included in alerts are direct and carry no affiliate codes or click commissions.",
    auth_title: "Sign in or create your free account to save rules",
    auth_sub: "On the Free plan you can enable 1 rule (edge ≥ 6%, with the 2-hour delay relative to the live ledger). Premium unlocks up to 10 real-time rules starting at edge ≥ 3%.",
    auth_login: "Sign in", auth_register: "Create free account",
    form_title: "New alert rule",
    form_sub: "You only get notified when a pick clears every filter at once.",
    f_name: "Rule name", f_edge: "Minimum edge (%)",
    f_odds_min: "Minimum odds", f_odds_max: "Maximum odds",
    f_market: "Market", f_time: "Time until start",
    m_all: "All markets", m_h2h: "Match winner / 1X2 (h2h)",
    m_outright: "Tournament winner (outright)",
    t_any: "Any time before kickoff",
    t_30: "≤ 30 minutes", t_60: "≤ 1 hour", t_180: "≤ 3 hours",
    t_360: "≤ 6 hours", t_1440: "≤ 24 hours",
    f_leagues: "Leagues (empty = all leagues)",
    f_channels: "Delivery channels",
    ch_email: "Email (& web history)",
    ch_telegram: "Instant Telegram",
    tg_hint: "To receive on Telegram, link your account using the code on the home page.",
    tg_linked_ok: "Telegram linked and ready to deliver your rules.",
    btn_save: "Save rule",
    rules_title: "My configured rules",
    rules_sub: "Pause or resume anytime without losing your setup.",
    btn_evaluate: "Check now",
    rules_empty: "You have no saved rules yet.",
    history_title: "Sent alerts history",
    history_sub: "Every delivery is logged with the rule that triggered it, channel, entry odds and direct non-affiliate link.",
    deliveries_empty: "No alerts have been triggered for your account yet.",
    col_date: "Date", col_channel: "Channel", col_league: "League / Event",
    col_pick: "Selection", col_odds: "Odds", col_edge: "Edge",
    col_book: "Bookmaker (no affiliate)",
    limit_sub: "{used} of {max} rules on your plan",
    delay_free: "2h Free delay · min edge 6%",
    delay_premium: "Real-time · min edge 3%",
    ch_sub_guest: "Sign in to activate your channels",
    ch_sub_ready: "Email active · Telegram {tg}",
    tg_yes: "linked", tg_no: "not linked",
    badge_active: "Active", badge_paused: "Paused",
    btn_pause: "Pause", btn_resume: "Resume", btn_delete: "Delete",
    all_leagues: "All leagues",
    any_time: "No time cap",
    up_to_min: "≤ {m} min to start",
    rule_saved: "Rule saved.",
    eval_done: "Check complete ({n} new deliveries).",
    direct_no_aff: "direct link · no affiliate",
    footer_disclaimer: "<strong>18+ · Responsible use. We do not promise profits.</strong> Sports forecasting involves risk and past data does not guarantee future results. This site provides independent statistical analysis for informational purposes only; it is not a gaming operator, does not accept wagers and does not custody funds (notice applicable in Mexico and other jurisdictions).",
    footer_copyright: "ApuestaEdge © 2026 · Built and maintained by Carlos Prado · Public audit at /verificacion",
  },
};

const state = {
  lang: localStorage.getItem("ae_lang") || "es",
  data: null,
};

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const t = (key) => (I18N[state.lang] && I18N[state.lang][key]) || I18N.es[key] || key;
const fill = (key, vars) => {
  let out = t(key);
  Object.entries(vars || {}).forEach(([k, v]) => {
    out = out.split(`{${k}}`).join(String(v));
  });
  return out;
};
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function authHeaders() {
  const token = localStorage.getItem("ae_token");
  const h = { Accept: "application/json", "Content-Type": "application/json" };
  if (token) h.Authorization = `Bearer ${token}`;
  return h;
}

function fmtDate(epoch) {
  const v = Number(epoch);
  if (!Number.isFinite(v) || v <= 0) return "—";
  return new Date(v * 1000).toLocaleString(
    state.lang === "en" ? "en-GB" : "es-ES",
    { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function renderLeagues(leagues) {
  const box = $("#r-leagues");
  if (!box) return;
  const selected = new Set(
    Array.from(box.querySelectorAll("input:checked")).map((i) => i.value));
  box.innerHTML = (leagues || []).map((lg) => `
    <label class="chip-check">
      <input type="checkbox" value="${esc(lg)}" ${selected.has(lg) ? "checked" : ""}>
      <span>${esc(lg)}</span>
    </label>
  `).join("");
}

function renderSummary() {
  const d = state.data;
  if (!d) return;
  const rules = d.rules || [];
  const activeCount = rules.filter((r) => r.enabled).length;
  $("#a-active").textContent = `${activeCount} / ${d.max_rules || 1}`;
  $("#a-limit-sub").textContent = fill("limit_sub", {
    used: rules.length, max: d.max_rules || 1,
  });
  const planName = (d.plan || "free") === "premium" ? "Premium" : "Free";
  $("#a-plan").textContent = planName;
  $("#a-delay-sub").textContent = (d.plan === "premium")
    ? t("delay_premium") : t("delay_free");
  $("#a-deliveries").textContent = String((d.deliveries || []).length);

  const ch = d.channels || {};
  $("#a-channels-sub").textContent = d.authenticated
    ? fill("ch_sub_ready", { tg: ch.telegram_linked ? t("tg_yes") : t("tg_no") })
    : t("ch_sub_guest");

  $("#alerts-auth-box").hidden = Boolean(d.authenticated);
  const tgHint = $("#telegram-hint");
  if (tgHint) {
    tgHint.textContent = ch.telegram_linked ? t("tg_linked_ok") : t("tg_hint");
  }
}

function renderRules() {
  const box = $("#rules-list");
  const rules = (state.data && state.data.rules) || [];
  if (!rules.length) {
    box.innerHTML = `<p class="muted">${esc(t("rules_empty"))}</p>`;
    return;
  }
  box.innerHTML = rules.map((r) => {
    const badgeCls = r.enabled ? "best" : "muted";
    const badgeTxt = r.enabled ? t("badge_active") : t("badge_paused");
    const leaguesTxt = (r.leagues && r.leagues.length)
      ? r.leagues.join(", ") : t("all_leagues");
    const marketsTxt = (r.markets && r.markets.length)
      ? r.markets.join(", ") : t("m_all");
    const timeTxt = r.max_minutes_to_start
      ? fill("up_to_min", { m: r.max_minutes_to_start }) : t("any_time");
    const channels = [
      r.channel_email ? "Email" : null,
      r.channel_telegram ? "Telegram" : null,
    ].filter(Boolean).join(" + ");

    return `<article class="rule-card" data-rule-id="${r.id}">
      <div class="rule-card-head">
        <div>
          <h4>${esc(r.name)}</h4>
          <p class="rule-meta">${esc(leaguesTxt)}</p>
        </div>
        <span class="league-badge ${badgeCls}">${esc(badgeTxt)}</span>
      </div>
      <div class="rule-tags">
        <span class="chip">Edge ≥ ${(Number(r.edge_min) * 100).toFixed(1)}%</span>
        <span class="chip">${Number(r.odds_min).toFixed(2)} – ${Number(r.odds_max).toFixed(2)}</span>
        <span class="chip">${esc(marketsTxt)}</span>
        <span class="chip">${esc(timeTxt)}</span>
        <span class="chip">${esc(channels)}</span>
      </div>
      <div class="rule-actions">
        <button class="btn small ghost" type="button" data-action="toggle" data-id="${r.id}" data-enabled="${r.enabled ? "1" : "0"}">
          ${esc(r.enabled ? t("btn_pause") : t("btn_resume"))}
        </button>
        <button class="btn small ghost" type="button" data-action="delete" data-id="${r.id}">
          ${esc(t("btn_delete"))}
        </button>
      </div>
    </article>`;
  }).join("");
}

function renderDeliveries() {
  const deliveries = (state.data && state.data.deliveries) || [];
  const empty = $("#deliveries-empty");
  const wrap = $("#deliveries-table-wrap");
  const tbody = $("#deliveries-body");
  if (!deliveries.length) {
    empty.hidden = false;
    wrap.hidden = true;
    tbody.innerHTML = "";
    return;
  }
  empty.hidden = true;
  wrap.hidden = false;
  tbody.innerHTML = deliveries.map((d) => {
    const edgePct = `+${(Number(d.edge || 0) * 100).toFixed(1)}%`;
    const book = esc(d.bookmaker || "—");
    const bookCell = d.bookmaker_url
      ? `<a href="${esc(d.bookmaker_url)}" target="_blank" rel="noopener noreferrer">${book} ↗</a> <span class="muted">(${esc(t("direct_no_aff"))})</span>`
      : `${book} <span class="muted">(${esc(t("direct_no_aff"))})</span>`;
    return `<tr>
      <td>${esc(fmtDate(d.sent_at))}</td>
      <td><span class="chip">${esc(d.channel)}</span></td>
      <td><strong>${esc(d.league)}</strong><br><span class="muted">${esc(d.event)}</span></td>
      <td>${esc(d.selection_label)}</td>
      <td>${Number(d.odds || 0).toFixed(2)}</td>
      <td class="pos">${esc(edgePct)}</td>
      <td>${bookCell}</td>
    </tr>`;
  }).join("");
}

function render() {
  if (!state.data) return;
  renderLeagues(state.data.leagues || []);
  renderSummary();
  renderRules();
  renderDeliveries();
}

async function load() {
  const resp = await fetch("/api/alerts/rules", { headers: authHeaders() });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  state.data = await resp.json();
  render();
}

async function handleAuth(mode) {
  const email = $("#auth-email").value.trim();
  const password = $("#auth-password").value;
  const fb = $("#auth-feedback");
  fb.hidden = false;
  fb.textContent = t("loading");
  try {
    const endpoint = mode === "register" ? "/api/auth/register" : "/api/auth/login";
    const resp = await fetch(endpoint, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ email, password }),
    });
    const body = await resp.json();
    if (!resp.ok) throw new Error(body.detail || `HTTP ${resp.status}`);
    if (body.token) localStorage.setItem("ae_token", body.token);
    fb.hidden = true;
    await load();
  } catch (e) {
    fb.textContent = e.message;
  }
}

async function handleCreateRule(ev) {
  ev.preventDefault();
  const fb = $("#r-feedback");
  fb.textContent = t("loading");
  const leagues = Array.from(
    document.querySelectorAll("#r-leagues input:checked")).map((i) => i.value);
  const market = $("#r-market").value;
  const maxMinsRaw = $("#r-time").value;
  const payload = {
    name: $("#r-name").value.trim(),
    edge_min: Number($("#r-edge").value) / 100.0,
    odds_min: Number($("#r-odds-min").value),
    odds_max: Number($("#r-odds-max").value),
    leagues,
    markets: market ? [market] : [],
    max_minutes_to_start: maxMinsRaw ? Number(maxMinsRaw) : null,
    channel_email: $("#r-ch-email").checked,
    channel_telegram: $("#r-ch-telegram").checked,
  };
  try {
    const resp = await fetch("/api/alerts/rules", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(payload),
    });
    const body = await resp.json();
    if (!resp.ok) throw new Error(body.detail || `HTTP ${resp.status}`);
    $("#r-name").value = "";
    fb.textContent = t("rule_saved");
    await load();
  } catch (e) {
    fb.textContent = e.message;
  }
}

async function handleRuleAction(ev) {
  const btn = ev.target.closest("button[data-action]");
  if (!btn) return;
  const id = Number(btn.getAttribute("data-id"));
  const action = btn.getAttribute("data-action");
  if (action === "toggle") {
    const enabled = btn.getAttribute("data-enabled") !== "1";
    await fetch(`/api/alerts/rules/${id}`, {
      method: "PATCH",
      headers: authHeaders(),
      body: JSON.stringify({ enabled }),
    });
    await load();
  } else if (action === "delete") {
    await fetch(`/api/alerts/rules/${id}`, {
      method: "DELETE",
      headers: authHeaders(),
    });
    await load();
  }
}

async function handleEvaluate() {
  const fb = $("#r-feedback");
  fb.textContent = t("loading");
  try {
    const resp = await fetch("/api/alerts/evaluate", {
      method: "POST",
      headers: authHeaders(),
    });
    const body = await resp.json();
    if (!resp.ok) throw new Error(body.detail || `HTTP ${resp.status}`);
    const sent = (body.dispatched && body.dispatched.sent) || 0;
    fb.textContent = fill("eval_done", { n: sent });
    await load();
  } catch (e) {
    fb.textContent = e.message;
  }
}

function applyLang(lang) {
  state.lang = lang;
  localStorage.setItem("ae_lang", lang);
  document.documentElement.lang = lang;
  document.title = lang === "en"
    ? "Configurable alerts · ApuestaEdge"
    : "Alertas configurables · ApuestaEdge";
  $$("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    const val = t(key);
    if (val && val !== key) {
      if (val.includes("<")) el.innerHTML = val;
      else el.textContent = val;
    }
  });
  const btn = $("#lang-toggle");
  if (btn) btn.textContent = lang === "es" ? "EN" : "ES";
  if (state.data) render();
}

function bind() {
  $("#lang-toggle").addEventListener("click", () => {
    applyLang(state.lang === "es" ? "en" : "es");
  });
  $("#alert-auth-form").addEventListener("submit", (ev) => {
    ev.preventDefault();
    handleAuth("login");
  });
  $("#auth-register-btn").addEventListener("click", () => {
    handleAuth("register");
  });
  $("#rule-form").addEventListener("submit", handleCreateRule);
  $("#rules-list").addEventListener("click", handleRuleAction);
  $("#btn-evaluate").addEventListener("click", handleEvaluate);
}

async function init() {
  bind();
  applyLang(state.lang);
  try {
    await load();
  } catch (e) {
    $("#r-feedback").textContent = e.message;
  }
}

init();
