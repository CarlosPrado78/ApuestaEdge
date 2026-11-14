/* Auditoría del modelo: lógica pública, pesos privados, versiones reales. */
"use strict";

const I18N = {
  es: {
    nav_home: "Inicio", nav_ledger: "Registro de picks",
    nav_leagues: "Ligas", nav_model: "Modelo", nav_verify: "Verificación", nav_alerts: "Alertas",
    nav_pricing: "Precios",
    eyebrow: "Auditoría del modelo",
    title: "La lógica es pública. Los pesos, no.",
    intro: "Puedes revisar cómo se calcula cada pick, qué se publica y qué se descarta. No publicamos los pesos internos del modelo para que no se puedan copiar ni optimizar contra ellos, pero cada cambio de versión queda registrado y cada pick queda en el registro público antes de empezar.",
    open_ledger: "Ver registro completo", open_verify: "Comprobar el registro",
    pipeline_title: "Cómo se decide un pick",
    pipeline_sub: "Cuatro pasos, en este orden. Si algún paso no se cumple, no hay pick. No se publica «porque hay que publicar».",
    p1_title: "Probabilidad del modelo",
    p1_body: "El modelo estima la probabilidad de cada resultado a partir del rendimiento previo de los equipos, el contexto del partido y la localía. Esa probabilidad es la entrada, no el resultado final.",
    p2_title: "Probabilidad del mercado",
    p2_body: "Se elimina el margen de las cuotas (de-vig) para convertir el precio en una probabilidad comparable. Sin ese ajuste, el margen de la casa se confundiría con una ventaja.",
    p3_title: "Edge y filtro de publicación",
    p3_body: "El edge es la diferencia entre ambas probabilidades. Solo se publica si supera un mínimo (3% por defecto) y si la cuota elegida es la mejor disponible entre las casas consultadas.",
    p4_title: "Tamaño de la posición",
    p4_body: "El stake sale del criterio de Kelly fraccional, no de una intuición. Se usa un cuarto del Kelly completo y un tope duro del 3% del bankroll por pick.",
    kelly_title: "Kelly fraccional 1/4",
    kelly_body: "El Kelly completo maximiza el crecimiento a largo plazo pero produce caídas muy violentas. Usamos un cuarto de esa fracción y un tope duro por pick.",
    kelly_note: "Si el stake resultante es menor al 0.5% del bankroll, el pick se descarta: no merece el riesgo operativo.",
    clv_title: "CLV automático",
    clv_body: "El Closing Line Value compara la cuota a la que entramos con la cuota de cierre, congelada automáticamente antes de que empiece el evento. Mide si conseguimos mejor precio que el mercado final, con independencia de si el pick se gana o se pierde.",
    clv_note: "Ejemplo: entrar a 2.20 y cerrar a 2.00 da +10% de CLV. Un CLV medio positivo sostenido es mejor señal que una racha de aciertos.",
    binom_title: "Test binomial",
    binom_body: "El p-valor responde a una pregunta concreta: si el modelo solo acertara al ritmo que exige la cuota media, ¿sería raro observar estos aciertos? Se calcula a una cola.",
    binom_note: "Solo llamamos «significativa» a una muestra con n ≥ 30 y p < 0.05. Con menos datos, la etiqueta honesta es «muestra insuficiente».",
    withhold_title: "Qué no publicamos y por qué",
    w1: "Los pesos y transformaciones internas del modelo: son la parte replicable y no queremos que se optimice el mercado contra ellos.",
    w2: "Los picks descartados por no superar el filtro: publicar todo lo que se estudió permitiría elegir a posteriori. Lo que sí se publica es cada pick aceptado, antes del evento.",
    w3: "Datos personales o de cuentas: el registro es público y anónimo.",
    limits_title: "Límites que asumimos",
    l1: "El mercado es eficiente la mayor parte del tiempo: la mayoría de eventos no generan edge y no se publica nada.",
    l2: "Una muestra pequeña puede parecer buena o mala por pura varianza. Por eso no mostramos porcentajes con menos de 30 picks cerrados.",
    l3: "El CLV depende de la cuota de cierre de las casas consultadas; si esa referencia falla, la fila de cierre queda pendiente y se indica.",
    l4: "Nada de esto garantiza resultados futuros. Publicamos las pérdidas con el mismo detalle que las ganancias.",
    versions_title: "Historial de versiones",
    versions_sub: "Cada pick guarda la versión del modelo con la que se publicó. Un cambio de lógica se registra aquí antes de aplicarse.",
    versions_loading: "Cargando versiones…",
    versions_empty: "Todavía no hay versiones registradas. La versión inicial se anota con el primer pick publicado.",
    versions_error: "No se pudo cargar el historial: {error}",
    current_badge: "En uso",
    version_unknown: "versión sin registrar",
    version_changes: "Cambios",
    version_summary: "Resumen",
    note: "Esta página describe la lógica, no promete resultados. El registro público y la página de verificación son la prueba de lo que realmente se publicó.",
    footer_disclaimer: "<strong>+18 · Uso responsable. No prometemos ganancias.</strong> Los pronósticos deportivos implican riesgo y los datos históricos no garantizan resultados futuros. Este sitio ofrece análisis estadístico independiente con fines informativos; no es un operador de juego, no acepta fondos ni custodia dinero (aviso aplicable en México y demás jurisdicciones).",
    footer_copyright: "ApuestaEdge © 2026 · Desarrollado y mantenido por Carlos Prado · Auditoría pública en /verificacion",
  },
  en: {
    nav_home: "Home", nav_ledger: "Pick ledger",
    nav_leagues: "Leagues", nav_model: "Model", nav_verify: "Verification", nav_alerts: "Alerts",
    nav_pricing: "Pricing",
    eyebrow: "Model audit",
    title: "The logic is public. The weights are not.",
    intro: "You can review how every pick is computed, what gets published and what gets discarded. We do not publish the model's internal weights so they cannot be copied or optimized against, but every version change is logged and every pick is in the public ledger before the event starts.",
    open_ledger: "View the full ledger", open_verify: "Verify the ledger",
    pipeline_title: "How a pick is decided",
    pipeline_sub: "Four steps, in this order. If any step fails, there is no pick. We do not publish 'because we have to publish'.",
    p1_title: "Model probability",
    p1_body: "The model estimates the probability of each outcome from the teams' prior performance, match context and home advantage. That probability is the input, not the final result.",
    p2_title: "Market probability",
    p2_body: "The bookmaker margin is removed from the odds (de-vig) to turn the price into a comparable probability. Without that adjustment, the house margin would be mistaken for an edge.",
    p3_title: "Edge and publishing filter",
    p3_body: "Edge is the difference between both probabilities. A pick is only published if it exceeds a minimum (3% by default) and the chosen odds are the best available among the books consulted.",
    p4_title: "Position size",
    p4_body: "Stake comes from fractional Kelly, not a hunch. We use one quarter of full Kelly and a hard cap of 3% of bankroll per pick.",
    kelly_title: "Fractional Kelly 1/4",
    kelly_body: "Full Kelly maximizes long-term growth but produces violent drawdowns. We use one quarter of that fraction and a hard cap per pick.",
    kelly_note: "If the resulting stake is below 0.5% of bankroll, the pick is discarded: it is not worth the operational risk.",
    clv_title: "Automatic CLV",
    clv_body: "Closing Line Value compares the odds we entered at with the closing odds, frozen automatically before the event starts. It measures whether we got a better price than the final market, regardless of whether the pick won or lost.",
    clv_note: "Example: entering at 2.20 and closing at 2.00 gives +10% CLV. A sustained positive average CLV is a better signal than a winning streak.",
    binom_title: "Binomial test",
    binom_body: "The p-value answers one specific question: if the model only hit at the rate required by the average odds, how unusual would these wins be? It is computed one-sided.",
    binom_note: "We only call a sample 'significant' with n ≥ 30 and p < 0.05. With less data, the honest label is 'insufficient sample'.",
    withhold_title: "What we do not publish and why",
    w1: "The model's internal weights and transformations: they are the replicable part and we do not want the market optimized against them.",
    w2: "Picks discarded for failing the filter: publishing everything studied would allow hindsight selection. What we do publish is every accepted pick, before the event.",
    w3: "Personal or account data: the ledger is public and anonymous.",
    limits_title: "Limits we accept",
    l1: "The market is efficient most of the time: most events produce no edge and nothing is published.",
    l2: "A small sample can look good or bad purely from variance. That is why we do not show percentages with fewer than 30 settled picks.",
    l3: "CLV depends on the closing odds of the books consulted; if that reference fails, the closing row stays pending and is flagged.",
    l4: "None of this guarantees future results. We publish losses in the same detail as wins.",
    versions_title: "Version history",
    versions_sub: "Every pick records the model version it was published with. A logic change is logged here before it is applied.",
    versions_loading: "Loading versions…",
    versions_empty: "No versions logged yet. The initial version is recorded with the first published pick.",
    versions_error: "Could not load the history: {error}",
    current_badge: "In use",
    version_unknown: "unlogged version",
    version_changes: "Changes",
    version_summary: "Summary",
    note: "This page describes the logic, it does not promise results. The public ledger and the verification page are the proof of what was actually published.",
    footer_disclaimer: "<strong>18+ · Responsible use. We do not promise profits.</strong> Sports forecasting involves risk and past data does not guarantee future results. This site provides independent statistical analysis for informational purposes only; it is not a gaming operator, does not accept wagers and does not custody funds (notice applicable in Mexico and other jurisdictions).",
    footer_copyright: "ApuestaEdge © 2026 · Built and maintained by Carlos Prado · Public audit at /verificacion",
  },
};

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

function fmtDate(epoch) {
  const value = Number(epoch);
  if (!Number.isFinite(value) || value <= 0) return "—";
  return new Date(value * 1000).toLocaleDateString(
    state.lang === "en" ? "en-GB" : "es-ES",
    { year: "numeric", month: "short", day: "numeric" });
}

function renderVersions() {
  const panel = $("#versions-panel");
  const versions = (state.data && state.data.versions) || [];
  const current = state.data && state.data.current;
  if (!versions.length) {
    panel.innerHTML = `<p class="muted">${esc(t("versions_empty"))}</p>`;
    return;
  }
  panel.innerHTML = versions.map((v) => {
    const inUse = v.version === current;
    const imp = v.measured_impact || {};
    const sample = Number(imp.sample || 0);
    const picks = Number(imp.picks || 0);
    let impactHtml = "";
    if (v.measured_impact) {
      const sampleTxt = state.lang === "en"
        ? `${picks} published · ${sample} settled`
        : `${picks} publicados · ${sample} cerrados`;
      const metricTxt = sample >= 30
        ? `ROI ${Number(imp.roi_pct).toFixed(1)}% · CLV ${Number(imp.avg_clv_pct).toFixed(2)}%`
        : (state.lang === "en"
            ? `insufficient sample (n = ${sample})`
            : `muestra insuficiente (n = ${sample})`);
      impactHtml = `<p class="version-changes"><b>${esc(state.lang === "en" ? "Measured impact" : "Impacto medido")}:</b> ${esc(sampleTxt)} · ${esc(metricTxt)}</p>`;
    }
    return `<article class="version-row">
      <div class="version-head">
        <h3>${esc(v.version)}</h3>
        ${inUse ? `<span class="version-badge">${esc(t("current_badge"))}</span>` : ""}
        <span class="version-date">${esc(fmtDate(v.released_at))}</span>
      </div>
      <p class="muted">${esc(v.summary || "")}</p>
      ${v.changes ? `<p class="version-changes"><b>${esc(t("version_changes"))}:</b> ${esc(v.changes)}</p>` : ""}
      ${impactHtml}
    </article>`;
  }).join("");
}

function applyLang(lang) {
  state.lang = lang;
  localStorage.setItem("ae_lang", lang);
  document.documentElement.lang = lang;
  document.title = lang === "en"
    ? "Model and methodology · ApuestaEdge"
    : "Modelo y metodología · ApuestaEdge";
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
  renderVersions();
}

async function load() {
  try {
    const resp = await fetch("/api/ledger/versions", {
      headers: { Accept: "application/json" },
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    state.data = await resp.json();
    renderVersions();
  } catch (e) {
    $("#versions-panel").innerHTML =
      `<p class="muted">${esc(fill("versions_error", { error: e.message }))}</p>`;
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
