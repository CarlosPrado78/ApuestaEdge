"use strict";
const I18N = {
  es: {
    nav_home: "Inicio", nav_ledger: "Registro", nav_leagues: "Ligas",
    nav_model: "Modelo", nav_verify: "Verificación", nav_alerts: "Alertas",
    nav_impact: "Impacto", nav_risk: "Riesgo", nav_team: "Equipo",
    nav_pricing: "Precios",
    eyebrow: "Riesgo de la estrategia",
    title: "Simulación Monte Carlo pública.",
    intro: "10.000 trayectorias con bankroll de 100 unidades y Kelly 1/4 sobre la distribución empírica de los picks cerrados del registro. Se recalcula automáticamente cuando hay nuevos picks asentados.",
    p10: "Percentil 10", p10_sub: "Peor caso razonable",
    p50: "Mediana", p50_sub: "Caso central",
    p90: "Percentil 90", p90_sub: "Mejor caso razonable",
    dd: "Drawdown mediano", dd_sub: "Peor caída típica",
    inputs_title: "Parámetros de la simulación",
    explain_title: "Qué significa cada percentil",
    e1: "Percentil 10: en 1 de cada 10 trayectorias el bankroll termina por debajo de este valor. Es el peor caso razonable, no el peor caso posible.",
    e2: "Mediana: la mitad de las trayectorias termina por encima y la mitad por debajo. Es el resultado más probable.",
    e3: "Percentil 90: en 9 de cada 10 trayectorias el bankroll termina por debajo de este valor. Es el mejor caso razonable.",
    e4: "Drawdown mediano: la peor caída típica desde un máximo local, medida en porcentaje del bankroll.",
    footer_disclaimer: "<strong>+18 · Uso responsable. No prometemos ganancias.</strong> Los pronósticos deportivos implican riesgo y los datos históricos no garantizan resultados futuros. Este sitio ofrece análisis estadístico independiente con fines informativos; no es un operador de juego, no acepta fondos ni custodia dinero (aviso aplicable en México y demás jurisdicciones).",
    footer_copyright: "ApuestaEdge © 2026 · Desarrollado y mantenido por Carlos Dakem · Auditoría pública en /verificacion",
  },
  en: {
    nav_home: "Home", nav_ledger: "Ledger", nav_leagues: "Leagues",
    nav_model: "Model", nav_verify: "Verification", nav_alerts: "Alerts",
    nav_impact: "Impact", nav_risk: "Risk", nav_team: "Team",
    nav_pricing: "Pricing",
    eyebrow: "Strategy risk",
    title: "Public Monte Carlo simulation.",
    intro: "10,000 trajectories with a 100-unit bankroll and 1/4 Kelly over the empirical distribution of settled picks in the ledger. Recomputed automatically when new picks settle.",
    p10: "Percentile 10", p10_sub: "Reasonable worst case",
    p50: "Median", p50_sub: "Central case",
    p90: "Percentile 90", p90_sub: "Reasonable best case",
    dd: "Median drawdown", dd_sub: "Typical worst drop",
    inputs_title: "Simulation parameters",
    explain_title: "What each percentile means",
    e1: "Percentile 10: in 1 of 10 trajectories the bankroll ends below this value. It is the reasonable worst case, not the worst possible case.",
    e2: "Median: half of trajectories end above and half below. It is the most likely outcome.",
    e3: "Percentile 90: in 9 of 10 trajectories the bankroll ends below this value. It is the reasonable best case.",
    e4: "Median drawdown: the typical worst drop from a local maximum, measured as a percentage of bankroll.",
    footer_disclaimer: "<strong>18+ · Responsible use. We do not promise profits.</strong> Sports forecasting involves risk and past data does not guarantee future results. This site provides independent statistical analysis for informational purposes only; it is not a gaming operator, does not accept wagers and does not custody funds (notice applicable in Mexico and other jurisdictions).",
    footer_copyright: "ApuestaEdge © 2026 · Built and maintained by Carlos Dakem · Public audit at /verificacion",
  },
};
const state = { lang: localStorage.getItem("ae_lang") || "es", data: null };
const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const t = (key) => (I18N[state.lang] && I18N[state.lang][key]) || I18N.es[key] || key;
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
async function load() {
  const resp = await fetch("/api/ledger/risk");
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  state.data = await resp.json();
  render();
}
function render() {
  const d = state.data;
  if (!d) return;
  const r = (d.results || {});
  $("#r-p10").textContent = Number(r.p10_final_bankroll || 0).toFixed(2);
  $("#r-p50").textContent = Number(r.median_final_bankroll || 0).toFixed(2);
  $("#r-p90").textContent = Number(r.p90_final_bankroll || 0).toFixed(2);
  $("#r-dd").textContent = `${Number(r.median_max_drawdown_pct || 0).toFixed(1)}%`;
  $("#risk-disclaimer").textContent = d.disclaimer || "";
  const inp = d.inputs || {};
  $("#risk-inputs").innerHTML = [
    ["Bankroll inicial", inp.bankroll_start],
    ["Picks simulados", inp.picks_simulated],
    ["Simulaciones", inp.simulations],
    ["Fracción Kelly", inp.kelly_fraction],
    ["Stake por pick (% bankroll)", inp.stake_pct_of_bankroll],
    ["Picks cerrados usados", inp.sample_picks],
    ["Datos reales", inp.real_data ? "Sí" : "No (distribución neutra)"],
  ].map(([k, v]) => `<div class="pick-dl-row"><dt>${esc(k)}</dt><dd>${esc(String(v))}</dd></div>`).join("");
}
function applyLang(lang) {
  state.lang = lang;
  localStorage.setItem("ae_lang", lang);
  document.documentElement.lang = lang;
  document.title = lang === "en" ? "Strategy risk · ApuestaEdge" : "Riesgo de la estrategia · ApuestaEdge";
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
}
async function init() {
  bind();
  applyLang(state.lang);
  try { await load(); } catch (e) { $("#risk-disclaimer").textContent = e.message; }
}
init();
