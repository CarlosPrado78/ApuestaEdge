/* Registro público de picks — tabla, filtros, resumen y CSV.
   Sin dependencias. Los datos vienen de /api/ledger/*; aquí solo se
   presentan: nunca se calcula un resultado ni se completa un hueco. */
"use strict";

/* ---------------------------------------------------------------- i18n */
const I18N = {
  es: {
    nav_home: "Inicio", nav_ledger: "Registro de picks",
    nav_leagues: "Ligas", nav_model: "Modelo",
    nav_verify: "Verificación", nav_pricing: "Precios",
    eyebrow: "Registro público · append-only",
    title: "Cada pick, incluido cada fallo.",
    intro: "Cada fila se escribe antes de que empiece el evento y no se puede editar ni borrar. Los resultados se asientan con el marcador real. Sin ejemplos, sin resultados inventados: si aún no hay picks cerrados, verás 0.",
    sum_roi: "ROI acumulado", sum_hit: "Acierto", sum_clv: "CLV medio",
    sum_picks: "Picks publicados", sum_losses: "Pérdidas publicadas",
    sub_roi: "beneficio por unidad", sub_insufficient: "muestra insuficiente (n = {n})",
    sub_hit: "sobre picks cerrados", sub_clv: "{n} picks con cuota de cierre",
    sub_closed: "{n} cerrados", sub_wins: "{n} ganadas",
    note_open_zero: "Registro abierto el 13 nov 2026 · 0 picks cerrados todavía. Publicamos cada evento antes de que empiece; los resultados aparecerán aquí con el marcador real.",
    note_small: "{total} picks publicados · {n} cerrados. Con menos de 30 picks cerrados no mostramos porcentajes: serían una promesa, no una medición.",
    note_ok: "Calculado sobre {n} picks cerrados. Los pendientes no cuentan.",
    table_title: "Registro de picks", loading: "Cargando registro…",
    export_csv: "Descargar CSV",
    f_league: "Liga", f_all: "Todas", f_from: "Desde", f_to: "Hasta",
    f_edge: "Edge mínimo", f_any: "Cualquiera", f_market: "Mercado",
    f_all_m: "Todos", m_h2h: "Ganador del evento", m_outright: "Outright",
    f_result: "Resultado", f_all_r: "Todas", r_won: "Ganadas", r_lost: "Perdidas",
    r_pending: "Pendientes", f_reset: "Limpiar filtros",
    integrity_loading: "Comprobando la cadena de hashes…",
    integrity_ok: "Cadena verificada: {n} filas · {chains} cadenas correctas.",
    integrity_bad: "⚠️ La cadena no cuadra: {reason}. No edites nada más y avísanos.",
    integrity_anchor: "Última publicación: {day} · cabeza {hash}",
    integrity_no_anchor: "Aún sin ancla diaria: se publica al cierre del primer día con picks.",
    table_caption: "Registro público de picks de ApuestaEdge",
    th_when: "Fecha / hora", th_league: "Liga", th_event: "Evento",
    th_market: "Mercado", th_selection: "Selección", th_odds: "Cuota",
    th_edge: "Edge", th_close: "Cierre", th_units: "Unidades",
    th_result: "Resultado", th_copy: "Copiar detalles del pick",
    table_note: "Cada fila se escribió antes del inicio del evento y no se puede editar. El CSV incluye los hashes para que cualquiera pueda recalcular la cadena.",
    load_more: "Cargar más",
    res_won: "GANADA", res_lost: "PERDIDA", res_push: "NULA",
    res_void: "ANULADA", res_pending: "PENDIENTE",
    copy_pick: "Copiar", copied: "Copiado", copy_failed: "No se pudo copiar",
    market_h2h: "Ganador del evento", market_outright: "Outright",
    published: "Publicado", closing_pending: "cierre pendiente", no_closing: "—",
    empty_open_title: "El registro está abierto desde el 13 nov 2026",
    empty_open_body: "Aún no hay picks publicados. Solo se publican eventos reales antes de su inicio; cuando haya uno con valor, aparecerá aquí y su resultado se asentará con el marcador oficial. Nada de ejemplos: 0 es 0.",
    empty_filtered_title: "Ningún pick coincide con estos filtros",
    empty_filtered_body: "Prueba con un rango de fechas más amplio o quita algún filtro. No ocultamos filas: simplemente no hay coincidencias.",
    count_showing: "Mostrando {shown} de {total} picks.",
    count_empty: "0 picks publicados todavía.",
    count_none: "0 coincidencias.",
    detail_more: "Más datos",
    profit: "Beneficio", row_hash: "Hash de la fila",
    footer_disclaimer: "<strong>+18 · Juego responsable.</strong> Los pronósticos deportivos implican riesgo. Los datos históricos no garantizan resultados futuros. Este sitio ofrece análisis estadístico con fines informativos; no es asesoramiento financiero ni garantía de resultados.",
    footer_copyright: "ApuestaEdge © 2026 · Cuotas y resultados de eventos reales",
  },
  en: {
    nav_home: "Home", nav_ledger: "Pick ledger",
    nav_leagues: "Leagues", nav_model: "Model",
    nav_verify: "Verification", nav_pricing: "Pricing",
    eyebrow: "Public ledger · append-only",
    title: "Every pick, including every miss.",
    intro: "Every row is written before the event starts and cannot be edited or deleted. Results settle from the real score. No samples, no invented outcomes: if there are no settled picks yet, you will see 0.",
    sum_roi: "Cumulative ROI", sum_hit: "Hit rate", sum_clv: "Average CLV",
    sum_picks: "Published picks", sum_losses: "Published losses",
    sub_roi: "profit per unit", sub_insufficient: "insufficient sample (n = {n})",
    sub_hit: "over settled picks", sub_clv: "{n} picks with closing odds",
    sub_closed: "{n} settled", sub_wins: "{n} won",
    note_open_zero: "Ledger opened 13 Nov 2026 · 0 settled picks yet. Every event is published before it starts; results will appear here from the real score.",
    note_small: "{total} picks published · {n} settled. With fewer than 30 settled picks we do not show percentages: they would be a promise, not a measurement.",
    note_ok: "Calculated over {n} settled picks. Pending picks do not count.",
    table_title: "Pick ledger", loading: "Loading ledger…",
    export_csv: "Download CSV",
    f_league: "League", f_all: "All", f_from: "From", f_to: "To",
    f_edge: "Minimum edge", f_any: "Any", f_market: "Market",
    f_all_m: "All", m_h2h: "Event winner", m_outright: "Outright",
    f_result: "Result", f_all_r: "All", r_won: "Won", r_lost: "Lost",
    r_pending: "Pending", f_reset: "Clear filters",
    integrity_loading: "Checking the hash chain…",
    integrity_ok: "Chain verified: {n} rows · {chains} chains intact.",
    integrity_bad: "⚠️ Chain mismatch: {reason}. Do not edit anything else and contact us.",
    integrity_anchor: "Latest publication: {day} · head {hash}",
    integrity_no_anchor: "No daily anchor yet: it is published at the end of the first day with picks.",
    table_caption: "ApuestaEdge public pick ledger",
    th_when: "Date / time", th_league: "League", th_event: "Event",
    th_market: "Market", th_selection: "Selection", th_odds: "Odds",
    th_edge: "Edge", th_close: "Close", th_units: "Units",
    th_result: "Result", th_copy: "Copy pick details",
    table_note: "Every row was written before the event started and cannot be edited. The CSV includes the hashes so anyone can recompute the chain.",
    load_more: "Load more",
    res_won: "WON", res_lost: "LOST", res_push: "PUSH",
    res_void: "VOID", res_pending: "PENDING",
    copy_pick: "Copy", copied: "Copied", copy_failed: "Copy failed",
    market_h2h: "Event winner", market_outright: "Outright",
    published: "Published", closing_pending: "closing pending", no_closing: "—",
    empty_open_title: "The ledger has been open since 13 Nov 2026",
    empty_open_body: "No picks published yet. Only real events are published before they start; when one has value it will appear here and settle from the official score. No samples: 0 means 0.",
    empty_filtered_title: "No picks match these filters",
    empty_filtered_body: "Try a wider date range or remove a filter. We do not hide rows: there are simply no matches.",
    count_showing: "Showing {shown} of {total} picks.",
    count_empty: "0 picks published yet.",
    count_none: "0 matches.",
    detail_more: "More details",
    profit: "Profit", row_hash: "Row hash",
    footer_disclaimer: "<strong>18+ · Responsible play.</strong> Sports forecasting involves risk. Past data does not guarantee future results. This site provides statistical analysis for information only; it is not financial advice or a guarantee of results.",
    footer_copyright: "ApuestaEdge © 2026 · Real event odds and results",
  },
};

/* ---------------------------------------------------------------- estado */
const state = {
  lang: localStorage.getItem("ae_lang") || "es",
  league: "", from: "", to: "", edge: "", market: "", result: "",
  offset: 0, limit: 25, total: 0, rows: [],
  summary: null, verify: null, loadedOnce: false,
};

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const ENOUGH = 30;

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
const num = (x, d = 2) => (Number.isFinite(Number(x)) ? Number(x).toFixed(d) : "—");
const signed = (x, d = 2) => `${Number(x) >= 0 ? "+" : ""}${Number(x).toFixed(d)}%`;
const signClass = (x) => (Number(x) >= 0 ? "pos" : "neg");
const locale = () => (state.lang === "en" ? "en-US" : "es-MX");

function fmtTs(ts, opts) {
  if (!ts) return "—";
  try {
    return new Date(Number(ts) * 1000).toLocaleString(locale(), opts || {
      day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
    });
  } catch { return "—"; }
}
const shortTs = (ts) => fmtTs(ts, {
  day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
});

async function api(path) {
  const resp = await fetch(path, { headers: { Accept: "application/json" } });
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try { const body = await resp.json(); detail = body.detail || detail; } catch { /* sin cuerpo */ }
    throw new Error(String(detail));
  }
  return resp.json();
}

/* --------------------------------------------------------------- filtros */
function queryParams() {
  const p = new URLSearchParams();
  if (state.league) p.set("league", state.league);
  if (state.from) p.set("date_from", state.from);
  if (state.to) p.set("date_to", state.to);
  if (state.edge) p.set("edge_min", state.edge);
  if (state.market) p.set("market", state.market);
  if (state.result) p.set("result", state.result);
  return p;
}

const hasFilters = () => Boolean(
  state.league || state.from || state.to || state.edge || state.market || state.result);

function syncUrl() {
  const qs = queryParams().toString();
  history.replaceState(null, "", `/picks${qs ? `?${qs}` : ""}`);
  const csv = queryParams();
  csv.set("format", "csv");
  csv.set("limit", "5000");
  $("#export-csv").href = `/api/ledger/picks?${csv.toString()}`;
}

function readUrl() {
  const p = new URLSearchParams(location.search);
  state.league = p.get("league") || "";
  state.from = p.get("date_from") || "";
  state.to = p.get("date_to") || "";
  state.edge = p.get("edge_min") || "";
  state.market = p.get("market") || "";
  state.result = p.get("result") || "";
}

/* -------------------------------------------------------------- resumen */
function renderSummary(s) {
  s = s || state.summary;
  if (!s) return;
  const roiOk = s.sample >= ENOUGH;
  const clvOk = s.clv_sample >= ENOUGH;

  const set = (sel, text, cls) => {
    const el = $(sel);
    if (!el) return;
    el.textContent = text;
    el.classList.remove("pos", "neg");
    if (cls) el.classList.add(cls);
  };
  set("#s-roi", roiOk ? signed(s.roi_pct) : "—", roiOk ? signClass(s.roi_pct) : "");
  set("#s-hit", roiOk ? `${num(s.hit_rate_pct, 1)}%` : "—", "");
  set("#s-clv", clvOk ? signed(s.avg_clv_pct) : "—", clvOk ? signClass(s.avg_clv_pct) : "");
  set("#s-picks", String(s.picks_total || 0), "");
  set("#s-losses", String(s.losses || 0), "neg");

  $("#s-roi-sub").textContent = roiOk ? t("sub_roi") : fill("sub_insufficient", { n: s.sample || 0 });
  $("#s-hit-sub").textContent = roiOk ? t("sub_hit") : fill("sub_insufficient", { n: s.sample || 0 });
  $("#s-clv-sub").textContent = clvOk
    ? fill("sub_clv", { n: s.clv_sample })
    : fill("sub_insufficient", { n: s.clv_sample || 0 });
  $("#s-picks-sub").textContent = fill("sub_closed", { n: s.sample || 0 });
  $("#s-losses-sub").textContent = fill("sub_wins", { n: s.wins || 0 });
  renderNote(s);
}

function renderNote(s) {
  s = s || state.summary;
  const el = $("#ledger-note");
  if (!el) return;
  if (!s || !s.picks_total) {
    el.textContent = t("note_open_zero");
  } else if (s.sample < ENOUGH) {
    el.textContent = fill("note_small", { total: s.picks_total, n: s.sample });
  } else {
    const when = s.last_settled_at ? ` · ${fmtTs(s.last_settled_at)}` : "";
    el.textContent = fill("note_ok", { n: s.sample }) + when;
  }
}

/* ------------------------------------------------------------ integridad */
function renderIntegrity(v) {
  v = v || state.verify;
  const text = $("#integrity-text");
  const dot = $("#integrity-dot");
  if (!text || !dot) return;
  if (!v) { text.textContent = t("integrity_loading"); return; }
  const picks = (v.chains && v.chains.picks) || {};
  const chainsOk = Object.values(v.chains || {}).filter((c) => c.ok).length;
  dot.classList.toggle("ok", Boolean(v.ok));
  dot.classList.toggle("bad", !v.ok);
  let html;
  if (v.ok) {
    html = esc(fill("integrity_ok", { n: picks.rows || 0, chains: chainsOk }));
    const anchor = v.anchor;
    if (anchor) {
      html += " · " + esc(fill("integrity_anchor", {
        day: fmtTs(new Date(`${anchor.day}T12:00:00Z`).getTime() / 1000,
                   { day: "2-digit", month: "short", year: "numeric" }),
        hash: String(anchor.head_hash || "").slice(0, 12),
      }));
    } else {
      html += " · " + esc(t("integrity_no_anchor"));
    }
  } else {
    const broken = Object.values(v.chains || {}).find((c) => !c.ok) || {};
    html = esc(fill("integrity_bad", { reason: broken.reason || "hash" }));
  }
  text.innerHTML = html;
}

/* ---------------------------------------------------------------- tabla */
function resultBadge(r) {
  return `<span class="res ${esc(r.result)}">${esc(t(`res_${r.result}`))}</span>`;
}

function marketLabel(r) {
  return r.market === "outright" ? t("market_outright") : t("market_h2h");
}

function clvCell(r) {
  if (r.clv_pct === null || r.clv_pct === undefined) return '<span class="muted">—</span>';
  return `<span class="${signClass(r.clv_pct)}">${signed(r.clv_pct, 2)}</span>`;
}

function profitCell(r) {
  if (r.profit_units === null || r.profit_units === undefined) return "";
  const val = Number(r.profit_units);
  return `<small class="${signClass(val)}">${val >= 0 ? "+" : ""}${num(val, 2)} u</small>`;
}

function desktopRow(r) {
  const label = (key) => esc(t(key));
  return `
  <tr>
    <td data-label="${label("th_when")}" title="${esc(t("published"))} ${esc(fmtTs(r.created_at))}">
      ${esc(fmtTs(r.event_start))}
    </td>
    <td data-label="${label("th_league")}">${esc(r.league)}</td>
    <td data-label="${label("th_event")}" class="cell-event">${esc(r.event)}</td>
    <td data-label="${label("th_market")}">${esc(marketLabel(r))}</td>
    <td data-label="${label("th_selection")}">${esc(r.selection_label)}</td>
    <td data-label="${label("th_odds")}"><b>${num(r.bet_odds)}</b></td>
    <td data-label="${label("th_edge")}"><span class="pos">${signed(r.edge_pct, 1)}</span></td>
    <td data-label="${label("th_close")}">${r.closing_odds === null || r.closing_odds === undefined ? '<span class="muted">—</span>' : num(r.closing_odds)}</td>
    <td data-label="CLV">${clvCell(r)}</td>
    <td data-label="${label("th_units")}">${num(r.stake_units, 2)} u</td>
    <td data-label="${label("th_result")}">${resultBadge(r)} ${profitCell(r)}</td>
    <td class="cell-copy"><button class="copy-btn" type="button" data-copy="${r.id}" title="${esc(t("copy_pick"))}" aria-label="${esc(t("copy_pick"))}">⧉</button></td>
  </tr>`;
}

function mobileCard(r) {
  return `
  <article class="lc">
    <div class="lc-top">
      <span class="lc-league">${esc(r.league)}</span>
      ${resultBadge(r)}
    </div>
    <p class="lc-event">${esc(r.event)}</p>
    <p class="lc-sel">${esc(r.selection_label)}</p>
    <div class="lc-grid">
      <div><label>${esc(t("th_odds"))}</label><b>${num(r.bet_odds)}</b></div>
      <div><label>${esc(t("th_edge"))}</label><b class="pos">${signed(r.edge_pct, 1)}</b></div>
      <div><label>CLV</label><b>${clvCell(r)}</b></div>
      <div><label>${esc(t("th_units"))}</label><b>${num(r.stake_units, 2)} u</b></div>
    </div>
    <p class="lc-when muted">${esc(fmtTs(r.event_start))}</p>
    <details class="lc-more">
      <summary>${esc(t("detail_more"))}</summary>
      <dl>
        <dt>${esc(t("th_market"))}</dt><dd>${esc(marketLabel(r))}</dd>
        <dt>${esc(t("th_close"))}</dt><dd>${r.closing_odds === null || r.closing_odds === undefined ? esc(t("closing_pending")) : num(r.closing_odds)}</dd>
        <dt>${esc(t("profit"))}</dt><dd>${profitCell(r) || "—"}</dd>
        <dt>${esc(t("published"))}</dt><dd>${esc(fmtTs(r.created_at))}</dd>
        <dt>${esc(t("row_hash"))}</dt><dd class="hash">${esc(String(r.row_hash || "").slice(0, 16))}…</dd>
      </dl>
    </details>
    <button class="btn ghost small copy-btn" type="button" data-copy="${r.id}">${esc(t("copy_pick"))}</button>
  </article>`;
}

function renderRows() {
  const rows = state.rows;
  const tbody = $("#ledger-body");
  const cards = $("#ledger-cards");
  tbody.innerHTML = rows.map(desktopRow).join("");
  cards.innerHTML = rows.map(mobileCard).join("");

  $("#ledger-table-wrap").hidden = rows.length === 0;
  $("#ledger-cards").hidden = rows.length === 0;
  renderEmpty();
  $("#load-more").hidden = rows.length >= state.total;
}

function renderEmpty() {
  const panel = $("#ledger-empty");
  if (state.rows.length) { panel.hidden = true; return; }
  const filtered = hasFilters();
  panel.hidden = false;
  $("#empty-title").textContent = filtered ? t("empty_filtered_title") : t("empty_open_title");
  $("#empty-body").textContent = filtered ? t("empty_filtered_body") : t("empty_open_body");
  $("#empty-reset").hidden = !filtered;
}

function renderCount(total) {
  const el = $("#ledger-count");
  if (!el) return;
  if (!total) {
    el.textContent = hasFilters() ? t("count_none") : t("count_empty");
  } else {
    el.textContent = fill("count_showing", { shown: state.rows.length, total });
  }
}

async function loadPicks({ append = false } = {}) {
  if (!append) { state.offset = 0; state.rows = []; }
  const params = queryParams();
  params.set("limit", String(state.limit));
  params.set("offset", String(state.offset));
  try {
    const data = await api(`/api/ledger/picks?${params.toString()}`);
    state.total = data.total;
    state.rows = append ? state.rows.concat(data.picks) : data.picks;
    state.loadedOnce = true;
    renderRows();
    renderCount(data.total);
  } catch (e) {
    state.rows = [];
    $("#ledger-table-wrap").hidden = true;
    $("#ledger-cards").hidden = true;
    const panel = $("#ledger-empty");
    panel.hidden = false;
    $("#empty-title").textContent = t("table_title");
    $("#empty-body").textContent = e.message;
    $("#empty-reset").hidden = true;
    $("#ledger-count").textContent = "—";
  }
}

/* -------------------------------------------------------------- portapapeles */
async function writeClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const area = document.createElement("textarea");
    area.value = text;
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch { ok = false; }
    area.remove();
    return ok;
  }
}

function pickText(r) {
  const parts = [
    `[${shortTs(r.event_start)}]`,
    r.league,
    r.event,
    r.selection_label,
    `${t("th_odds")} ${num(r.bet_odds)}`,
    `edge ${signed(r.edge_pct, 1)}`,
    r.closing_odds === null || r.closing_odds === undefined
      ? t("closing_pending")
      : `${t("th_close").toLowerCase()} ${num(r.closing_odds)} (CLV ${signed(r.clv_pct, 1)})`,
    `${num(r.stake_units, 2)}u`,
    t(`res_${r.result}`),
    `#${r.id}`,
    `hash ${String(r.row_hash || "").slice(0, 12)}`,
  ];
  return parts.join(" · ");
}

async function copyFrom(btn) {
  const r = state.rows.find((row) => String(row.id) === String(btn.dataset.copy));
  if (!r) return;
  const ok = await writeClipboard(pickText(r));
  const original = btn.dataset.label || btn.textContent;
  btn.dataset.label = original;
  btn.textContent = ok ? `✓ ${t("copied")}` : t("copy_failed");
  btn.classList.toggle("ok", ok);
  setTimeout(() => {
    btn.textContent = original;
    btn.classList.remove("ok");
  }, 1600);
}

/* ---------------------------------------------------------------- carga */
async function loadSummary() {
  try {
    state.summary = await api("/api/ledger/summary");
    renderSummary(state.summary);
  } catch { /* la tabla sigue siendo la fuente principal */ }
}

async function loadVerify() {
  try {
    state.verify = await api("/api/ledger/verify");
    renderIntegrity(state.verify);
  } catch {
    $("#integrity-text").textContent = "—";
  }
}

async function loadLeagues() {
  try {
    const data = await api("/api/ledger/leagues");
    const select = $("#f-league");
    const names = Object.keys(data.leagues || {}).sort((a, b) => a.localeCompare(b));
    select.innerHTML = `<option value="">${esc(t("f_all"))}</option>` +
      names.map((name) => `<option value="${esc(name)}">${esc(name)}</option>`).join("");
    select.value = state.league;
    if (select.value !== state.league) {
      const opt = document.createElement("option");
      opt.value = state.league;
      opt.textContent = state.league;
      select.appendChild(opt);
      select.value = state.league;
    }
  } catch { /* el filtro de liga queda sin opciones */ }
}

function applyInputs() {
  $("#f-league").value = state.league;
  $("#f-from").value = state.from;
  $("#f-to").value = state.to;
  $("#f-edge").value = state.edge;
  $("#f-market").value = state.market;
  $("#f-result").value = state.result;
  if ($("#f-edge").value !== state.edge) {
    const opt = document.createElement("option");
    opt.value = state.edge;
    opt.textContent = `≥ ${(Number(state.edge) * 100).toFixed(0)}%`;
    $("#f-edge").appendChild(opt);
    $("#f-edge").value = state.edge;
  }
}

function readInputs() {
  state.league = $("#f-league").value;
  state.from = $("#f-from").value;
  state.to = $("#f-to").value;
  state.edge = $("#f-edge").value;
  state.market = $("#f-market").value;
  state.result = $("#f-result").value;
}

async function refresh() {
  readInputs();
  syncUrl();
  await loadPicks({ append: false });
}

/* ---------------------------------------------------------------- idioma */
function applyLang(lang, { reload = true } = {}) {
  state.lang = lang;
  localStorage.setItem("ae_lang", lang);
  document.documentElement.lang = lang;
  document.title = state.lang === "en"
    ? "Full pick ledger · ApuestaEdge"
    : "Registro completo de picks · ApuestaEdge";

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

  renderSummary(state.summary);
  renderIntegrity(state.verify);
  renderRows();
  renderCount(state.total);
  if (reload) loadLeagues();
}

/* ---------------------------------------------------------------- init */
function bind() {
  ["f-league", "f-from", "f-to", "f-edge", "f-market", "f-result"].forEach((id) => {
    $(`#${id}`).addEventListener("change", refresh);
  });
  $("#f-reset").addEventListener("click", resetFilters);
  $("#empty-reset").addEventListener("click", resetFilters);
  $("#load-more").addEventListener("click", async () => {
    state.offset = state.rows.length;
    await loadPicks({ append: true });
  });
  document.addEventListener("click", (event) => {
    const btn = event.target.closest("[data-copy]");
    if (btn) copyFrom(btn);
  });
  $("#lang-toggle").addEventListener("click", () => {
    applyLang(state.lang === "es" ? "en" : "es");
    loadPicks({ append: false });
  });
}

function resetFilters() {
  state.league = ""; state.from = ""; state.to = "";
  state.edge = ""; state.market = ""; state.result = "";
  applyInputs();
  refresh();
}

async function init() {
  readUrl();
  applyInputs();
  bind();
  syncUrl();
  applyLang(state.lang, { reload: false });
  await Promise.all([loadSummary(), loadVerify(), loadLeagues()]);
  await loadPicks({ append: false });
}

init();
