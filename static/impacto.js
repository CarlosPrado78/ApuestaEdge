"use strict";
const I18N = {
  es: {
    nav_home: "Inicio", nav_ledger: "Registro", nav_leagues: "Ligas",
    nav_model: "Modelo", nav_verify: "Verificación", nav_alerts: "Alertas",
    nav_impact: "Impacto", nav_risk: "Riesgo", nav_team: "Equipo",
    nav_pricing: "Precios",
    eyebrow: "Atributo irreplicable",
    title: "Prueba de que el edge no se erosiona con tu suscripción.",
    intro: "Cada pick publicado se mide: cuota en el momento de publicación y cuota 5, 15 y 30 minutos después. El movimiento de línea atribuible al anuncio se publica por liga y global. Si el anuncio moviera la línea, el edge real se erosionaría y tú lo verías antes de pagar.",
    sum_picks: "Picks medidos", sum_5min: "Movimiento a 5 min",
    sum_15min: "Movimiento a 15 min", sum_30min: "Movimiento a 30 min",
    sub_5: "vs. línea de entrada", sub_15: "vs. línea de entrada",
    table_title: "Movimiento por liga",
    table_sub: "Solo se publica movimiento cuando hay al menos un pick medido a los 30 minutos. Un movimiento cercano a 0% significa que el anuncio no erosiona el edge.",
    col_league: "Liga", col_picks: "Picks", col_measured: "Medidos (30 min)",
    col_5: "Mov. 5 min", col_15: "Mov. 15 min", col_30: "Mov. 30 min",
    empty: "Todavía no hay picks medidos. El movimiento se calcula automáticamente a los 5, 15 y 30 minutos de cada publicación.",
    how_title: "Cómo se mide",
    h1: "Cuota en el momento de publicación",
    h1b: "Se registra la mejor cuota disponible al publicar el pick (entrada).",
    h2: "Cuota a los 5, 15 y 30 minutos",
    h2b: "El ciclo del servidor consulta de nuevo la cuota de la misma selección a esos intervalos.",
    h3: "Movimiento %",
    h3b: "Movimiento = (cuota_post − cuota_entrada) / cuota_entrada × 100. Negativo = la línea se movió en nuestra contra (edge erosionado).",
    h4: "Agregado por liga y global",
    h4b: "Se publica el promedio, mínimo y máximo por liga y global. Sin cherry-picking: se incluyen también los movimientos adversos.",
    footer_disclaimer: "<strong>+18 · Uso responsable. No prometemos ganancias.</strong> Los pronósticos deportivos implican riesgo y los datos históricos no garantizan resultados futuros. Este sitio ofrece análisis estadístico independiente con fines informativos; no es un operador de juego, no acepta fondos ni custodia dinero (aviso aplicable en México y demás jurisdicciones).",
    footer_copyright: "ApuestaEdge © 2026 · Desarrollado y mantenido por Carlos Dakem · Auditoría pública en /verificacion",
  },
  en: {
    nav_home: "Home", nav_ledger: "Ledger", nav_leagues: "Leagues",
    nav_model: "Model", nav_verify: "Verification", nav_alerts: "Alerts",
    nav_impact: "Impact", nav_risk: "Risk", nav_team: "Team",
    nav_pricing: "Pricing",
    eyebrow: "Irreducible attribute",
    title: "Proof that the edge does not erode with your subscription.",
    intro: "Every published pick is measured: odds at publication and odds 5, 15 and 30 minutes later. The line movement attributable to the announcement is published per league and globally. If the announcement moved the line, the real edge would erode and you would see it before paying.",
    sum_picks: "Picks measured", sum_5min: "Movement at 5 min",
    sum_15min: "Movement at 15 min", sum_30min: "Movement at 30 min",
    sub_5: "vs. entry line", sub_15: "vs. entry line",
    table_title: "Movement by league",
    table_sub: "Movement is only published when at least one pick has been measured at 30 minutes. A movement near 0% means the announcement does not erode the edge.",
    col_league: "League", col_picks: "Picks", col_measured: "Measured (30 min)",
    col_5: "Move 5 min", col_15: "Move 15 min", col_30: "Move 30 min",
    empty: "No picks measured yet. Movement is computed automatically 5, 15 and 30 minutes after each publication.",
    how_title: "How it is measured",
    h1: "Odds at publication time",
    h1b: "The best available odds at publish time are recorded as entry.",
    h2: "Odds at 5, 15 and 30 minutes",
    h2b: "The server cycle re-checks the same selection's odds at those intervals.",
    h3: "Movement %",
    h3b: "Movement = (post_odds − entry_odds) / entry_odds × 100. Negative = line moved against us (edge eroded).",
    h4: "Aggregated per league and globally",
    h4b: "Average, minimum and maximum are published per league and globally. No cherry-picking: adverse movements are included.",
    footer_disclaimer: "<strong>18+ · Responsible use. We do not promise profits.</strong> Sports forecasting involves risk and past data does not guarantee future results. This site provides independent statistical analysis for informational purposes only; it is not a gaming operator, does not accept wagers and does not custody funds (notice applicable in Mexico and other jurisdictions).",
    footer_copyright: "ApuestaEdge © 2026 · Built and maintained by Carlos Dakem · Public audit at /verificacion",
  },
};
const state = { lang: localStorage.getItem("ae_lang") || "es", data: null };
const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const t = (key) => (I18N[state.lang] && I18N[state.lang][key]) || I18N.es[key] || key;
const fill = (key, vars) => { let out = t(key); Object.entries(vars || {}).forEach(([k, v]) => { out = out.split(`{${k}}`).join(String(v)); }); return out; };
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmtMove = (x) => (x == null ? "—" : `${x > 0 ? "+" : ""}${Number(x).toFixed(2)}%`);

async function load() {
  const resp = await fetch("/api/ledger/market-impact");
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  state.data = await resp.json();
  render();
}

function render() {
  const d = state.data;
  if (!d) return;
  const mi = d.market_impact || {};
  const g = mi.global;
  $("#i-picks").textContent = String(mi.picks || 0);
  $("#i-measured").textContent = g ? `${g.measured} medidos (30 min)` : "—";
  $("#i-5").textContent = fmtMove(g && g.avg_move_5min_pct);
  $("#i-15").textContent = fmtMove(g && g.avg_move_15min_pct);
  $("#i-30").textContent = fmtMove(g && g.avg_move_30min_pct);
  $("#i-source").textContent = `Fuente de cierre: ${d.closing_line_source}`;
  $("#impact-source").textContent = `Fuente de línea de cierre declarada: ${d.closing_line_source}. CLV = (cuota_entrada / cuota_cierre − 1) × 100.`;

  const body = $("#impact-body");
  const empty = $("#impact-empty");
  const rows = Object.entries(mi.per_league || {});
  if (!rows.length) {
    empty.hidden = false;
    body.innerHTML = "";
    return;
  }
  empty.hidden = true;
  body.innerHTML = rows.map(([league, agg]) => `
    <tr>
      <td>${esc(league)}</td>
      <td>${agg ? agg.picks : 0}</td>
      <td>${agg ? agg.measured : 0}</td>
      <td>${fmtMove(agg && agg.avg_move_5min_pct)}</td>
      <td>${fmtMove(agg && agg.avg_move_15min_pct)}</td>
      <td>${fmtMove(agg && agg.avg_move_30min_pct)}</td>
    </tr>
  `).join("");
}

function applyLang(lang) {
  state.lang = lang;
  localStorage.setItem("ae_lang", lang);
  document.documentElement.lang = lang;
  document.title = lang === "en" ? "Market impact · ApuestaEdge" : "Impacto de mercado · ApuestaEdge";
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
  try { await load(); } catch (e) { $("#impact-source").textContent = e.message; }
}
init();
