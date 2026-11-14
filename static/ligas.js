/* Dashboard por liga: métricas del registro público con muestra explícita.
   Regla editorial: con menos de 30 picks cerrados no se muestran porcentajes
   que parezcan una promesa; se dice «muestra insuficiente (n = X)». */
"use strict";

const I18N = {
  es: {
    nav_home: "Inicio", nav_ledger: "Registro",
    nav_leagues: "Ligas", nav_model: "Modelo", nav_verify: "Verificación", nav_alerts: "Alertas",
    nav_pricing: "Precios",
    eyebrow: "Rendimiento por liga",
    title: "Cada liga con su muestra. Sin cherry-picking.",
    intro: "Estas cifras salen del registro público, solo con picks ya cerrados y asentados con el marcador real. Una liga con pocos picks no se disfraza de buena racha: se marca como muestra insuficiente. La etiqueta de mejor liga exige al menos 30 picks cerrados y p < 0.05.",
    sum_leagues: "Ligas con picks", sum_picks: "Picks publicados",
    sum_closed: "Picks cerrados", sum_best: "Mejor liga (n≥30 y p<0.05)",
    loading: "Cargando ligas…",
    note_total: "{total} picks publicados · {closed} cerrados. Solo los cerrados cuentan para los porcentajes.",
    note_none: "Todavía no hay picks cerrados: las métricas aparecerán cuando el primer evento termine. No mostramos ejemplos ni cifras de demostración.",
    grid_title: "Todas las ligas",
    grid_sub: "Ordenadas por número de picks cerrados. El p-valor es el test binomial de una cola contra el breakeven de la cuota media.",
    open_ledger: "Ver registro completo",
    empty_title: "Todavía no hay picks cerrados por liga",
    empty_body: "El registro está abierto y solo publica eventos reales antes de su inicio. Cuando haya resultados, cada liga aparecerá aquí con su muestra exacta. Nada de ejemplos: 0 es 0.",
    insufficient: "muestra insuficiente (n = {n})",
    card_closed: "{sample} de {picks} cerrados",
    card_pending: "{n} pendientes",
    label_hit: "Acierto", label_roi: "ROI", label_clv: "CLV medio",
    label_p: "p-valor", label_wl: "Ganadas / perdidas",
    best_badge: "Mejor liga · n≥30 y p<0.05",
    sig_badge: "Significativa · p<0.05",
    no_sig: "Sin significancia estadística",
    p_na: "Sin datos",
    note: "Una liga con p < 0.05 es evidencia estadística, no una garantía: el resultado futuro sigue siendo incierto y el tamaño de muestra importa. Publicamos también las ligas con pérdidas.",
    footer_disclaimer: "<strong>+18 · Uso responsable. No prometemos ganancias.</strong> Los pronósticos deportivos implican riesgo y los datos históricos no garantizan resultados futuros. Este sitio ofrece análisis estadístico independiente con fines informativos; no es un operador de juego, no acepta fondos ni custodia dinero (aviso aplicable en México y demás jurisdicciones).",
    footer_copyright: "ApuestaEdge © 2026 · Desarrollado y mantenido por Carlos Prado · Auditoría pública en /verificacion",
  },
  en: {
    nav_home: "Home", nav_ledger: "Ledger",
    nav_leagues: "Leagues", nav_model: "Model", nav_verify: "Verification", nav_alerts: "Alerts",
    nav_pricing: "Pricing",
    eyebrow: "Performance by league",
    title: "Every league with its sample. No cherry-picking.",
    intro: "These figures come from the public ledger, only from settled picks resolved with the real score. A league with few picks is not dressed up as a hot streak: it is flagged as an insufficient sample. The best-league label requires at least 30 settled picks and p < 0.05.",
    sum_leagues: "Leagues with picks", sum_picks: "Published picks",
    sum_closed: "Settled picks", sum_best: "Best league (n≥30 and p<0.05)",
    loading: "Loading leagues…",
    note_total: "{total} picks published · {closed} settled. Only settled picks count towards the percentages.",
    note_none: "No settled picks yet: metrics will appear when the first event ends. We show no examples or demo figures.",
    grid_title: "All leagues",
    grid_sub: "Sorted by number of settled picks. The p-value is a one-sided binomial test against the break-even of the average odds.",
    open_ledger: "View the full ledger",
    empty_title: "No settled picks by league yet",
    empty_body: "The ledger is open and only publishes real events before they start. Once there are results, every league will appear here with its exact sample. No examples: 0 is 0.",
    insufficient: "insufficient sample (n = {n})",
    card_closed: "{sample} of {picks} settled",
    card_pending: "{n} pending",
    label_hit: "Hit rate", label_roi: "ROI", label_clv: "Avg CLV",
    label_p: "p-value", label_wl: "Won / lost",
    best_badge: "Best league · n≥30 and p<0.05",
    sig_badge: "Significant · p<0.05",
    no_sig: "No statistical significance",
    p_na: "No data",
    note: "A league with p < 0.05 is statistical evidence, not a guarantee: future results remain uncertain and sample size matters. We publish losing leagues too.",
    footer_disclaimer: "<strong>18+ · Responsible use. We do not promise profits.</strong> Sports forecasting involves risk and past data does not guarantee future results. This site provides independent statistical analysis for informational purposes only; it is not a gaming operator, does not accept wagers and does not custody funds (notice applicable in Mexico and other jurisdictions).",
    footer_copyright: "ApuestaEdge © 2026 · Built and maintained by Carlos Prado · Public audit at /verificacion",
  },
};

const MIN_SAMPLE = 30;
const state = { lang: localStorage.getItem("ae_lang") || "es", data: null };

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
const pct = (x, d = 1) => `${x > 0 ? "+" : ""}${Number(x).toFixed(d)}%`;
const signed = (x, d = 1) => `${x > 0 ? "+" : ""}${Number(x).toFixed(d)}`;
const num = (x, d = 2) => (Number.isFinite(Number(x)) ? Number(x).toFixed(d) : "—");

function insufficient(n) {
  return fill("insufficient", { n });
}

function pLabel(p) {
  if (!Number.isFinite(Number(p))) return t("p_na");
  const value = Number(p);
  if (value < 0.001) return "< 0.001";
  return value.toFixed(3);
}

function renderSummary() {
  const leagues = Object.entries((state.data && state.data.leagues) || {});
  const closed = leagues.reduce((sum, [, l]) => sum + Number(l.sample || 0), 0);
  const picks = leagues.reduce((sum, [, l]) => sum + Number(l.picks || 0), 0);
  const best = leagues
    .filter(([, l]) => l.significant)
    .sort((a, b) => Number(a[1].binomial_p_value) - Number(b[1].binomial_p_value))[0];

  $("#s-leagues").textContent = String(leagues.length);
  $("#s-picks").textContent = String(picks);
  $("#s-closed").textContent = String(closed);
  $("#s-best").textContent = best ? best[0] : "—";

  const note = $("#league-note");
  if (!leagues.length) {
    note.textContent = t("note_none");
  } else {
    note.textContent = fill("note_total", { total: picks, closed });
    if (!best) note.textContent += " · " + t("no_sig") + ".";
  }
}

function metric(label, value, tone) {
  const cls = tone === "loss" ? "loss" : tone === "gain" ? "gain" : "";
  return `<div class="league-metric"><span class="label">${esc(label)}</span>` +
         `<span class="value ${cls}">${esc(value)}</span></div>`;
}

function cardHtml(name, league) {
  const sample = Number(league.sample || 0);
  const picks = Number(league.picks || 0);
  const pending = Math.max(0, picks - sample);
  const closedNote = fill("card_closed", { sample, picks }) +
    (pending ? ` · ${fill("card_pending", { n: pending })}` : "");
  const enough = sample >= MIN_SAMPLE;

  const hit = enough ? pct(league.hit_rate_pct) : insufficient(sample);
  const roi = enough ? pct(league.roi_pct) : insufficient(sample);
  const clv = Number(league.clv_sample || 0) >= MIN_SAMPLE
    ? pct(league.avg_clv_pct) : insufficient(Number(league.clv_sample || 0));
  const p = sample ? pLabel(league.binomial_p_value) : t("p_na");

  const roiTone = enough ? (Number(league.roi_pct) < 0 ? "loss" : "gain") : "";
  const clvTone = Number(league.clv_sample || 0) >= MIN_SAMPLE
    ? (Number(league.avg_clv_pct) < 0 ? "loss" : "gain") : "";
  const wl = `${Number(league.wins || 0)} / ${Number(league.losses || 0)}`;

  let badge = "";
  if (league.significant) {
    badge = `<span class="league-badge best">${esc(t("best_badge"))}</span>`;
  } else if (enough) {
    badge = `<span class="league-badge muted">${esc(t("no_sig"))}</span>`;
  } else {
    badge = `<span class="league-badge warn">${esc(insufficient(sample))}</span>`;
  }

  return `<article class="league-card">
    <div class="league-top">
      <h3>${esc(name)}</h3>
      ${badge}
    </div>
    <p class="league-sample">${esc(closedNote)}</p>
    <div class="league-metrics">
      ${metric(t("label_hit"), hit)}
      ${metric(t("label_roi"), roi, roiTone)}
      ${metric(t("label_clv"), clv, clvTone)}
      ${metric(t("label_p"), p)}
    </div>
    <p class="league-wl">${esc(t("label_wl"))}: ${esc(wl)}</p>
  </article>`;
}

function render() {
  renderSummary();
  const grid = $("#league-grid");
  const empty = $("#league-empty");
  const leagues = Object.entries((state.data && state.data.leagues) || {});

  if (!leagues.length) {
    grid.innerHTML = "";
    grid.hidden = true;
    empty.hidden = false;
    return;
  }
  empty.hidden = true;
  grid.hidden = false;
  leagues.sort((a, b) => {
    const diff = Number(b[1].sample || 0) - Number(a[1].sample || 0);
    return diff !== 0 ? diff : a[0].localeCompare(b[0]);
  });
  grid.innerHTML = leagues.map(([name, league]) => cardHtml(name, league)).join("");
}

function applyLang(lang) {
  state.lang = lang;
  localStorage.setItem("ae_lang", lang);
  document.documentElement.lang = lang;
  document.title = lang === "en"
    ? "Performance by league · ApuestaEdge"
    : "Rendimiento por liga · ApuestaEdge";
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

async function load() {
  try {
    const resp = await fetch("/api/ledger/leagues", {
      headers: { Accept: "application/json" },
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    state.data = await resp.json();
    render();
  } catch (e) {
    $("#league-grid").innerHTML =
      `<p class="muted">${esc(e.message)}</p>`;
    $("#league-note").textContent = "—";
  }
}

function bind() {
  $("#lang-toggle").addEventListener("click", () => {
    applyLang(state.lang === "es" ? "en" : "es");
  });
}

async function init() {
  bind();
  applyLang(state.lang);
  await load();
}

init();
