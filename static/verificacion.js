/* Verificación del registro público.
   Comprueba en el navegador el enlace entre filas, el hash de cada fila
   sobre su contenido canónico y el hash del ancla diaria. El verificador de
   Python reconstruye además el contenido canónico desde los campos crudos. */
"use strict";

const I18N = {
  es: {
    nav_home: "Inicio", nav_ledger: "Registro de picks",
    nav_leagues: "Ligas", nav_model: "Modelo",
    nav_verify: "Verificación", nav_alerts: "Alertas", nav_pricing: "Precios",
    eyebrow: "Verificación · registro append-only",
    title: "No tienes que creernos. Verifícalo.",
    intro: "Cada pick publicado queda encadenado al anterior con SHA-256. Si alguien edita, borra o reordena una fila, la cadena deja de cuadrar. Aquí ves el estado en vivo y puedes descargar el paquete completo para recalcularlo en tu máquina, sin depender de nosotros.",
    btn_verify: "Verificar ahora", btn_package: "Descargar paquete (JSON)",
    btn_script: "Descargar verificador (Python)",
    state_title: "Estado del registro", state_loading: "Comprobando las cadenas…",
    state_ok: "Cadena verificada en tu navegador: {rows} filas en {chains} cadenas. Cabezas y ancla cuadran.",
    state_bad: "La cadena no cuadra. No confíes en estos datos hasta que lo revisemos.",
    state_empty: "El registro está vacío todavía: 0 filas. Cuando se publique el primer pick, la cadena empezará aquí.",
    chain_picks: "Picks publicados",
    chain_picks_note: "Lo que se publicó antes de cada evento.",
    chain_closings: "Cierres y CLV",
    chain_closings_note: "Cuota de cierre congelada y CLV calculado.",
    chain_results: "Resultados",
    chain_results_note: "Asentado con el marcador real.",
    head_label: "Cabeza", empty_chain: "cadena vacía (aún sin filas)",
    anchor_loading: "Buscando el ancla diaria…",
    anchor_none: "Todavía no hay ancla diaria: se publica al cierre del primer día con picks. Mientras tanto, la cadena se puede verificar igual.",
    anchor_line: "Última publicación: {day} · cabeza {hash} · {rows} filas",
    anchor_prev: " · (ancla de un estado anterior: se compara con el paquete completo)",
    anchor_bad: "⚠️ El hash del ancla no coincide con sus propios datos.",
    browser_scope: "La comprobación del navegador verifica el enlace entre filas, el hash de cada fila sobre su contenido canónico y el hash del ancla. El verificador de Python reconstruye además ese contenido canónico desde los campos crudos, para que no dependas de lo que declare esta página.",
    browser_unsupported: "Este navegador no permite verificar en local (hace falta HTTPS y Web Crypto). Usa el verificador de Python: hace exactamente la misma comprobación sobre el paquete.",
    verifying: "Verificando en tu navegador…",
    verify_ok: "✓ Verificación local correcta: {rows} filas en 3 cadenas. Cabezas {picks}… · {closings}… · {results}…",
    verify_fail: "✗ La verificación local falló: {reason}",
    verify_fail_anchor: "✗ El hash del ancla no coincide con sus datos.",
    verify_fail_heads: "✗ El ancla más reciente dice tener las mismas filas pero otras cabezas: el registro se reescribió.",
    fail_link: "la fila {id} no enlaza con la anterior.",
    fail_hash: "el hash de la fila {id} no coincide con su contenido.",
    how_title: "Verificación independiente en tu máquina",
    how_sub: "Tres pasos, sin instalar nada más que Python. El script solo usa la biblioteca estándar y no llama a nuestra API: lee el paquete que descargaste.",
    step1_title: "Descarga el paquete",
    step1_body: "Contiene las filas crudas de las tres cadenas, la especificación del hash y todas las anclas publicadas.",
    step2_title: "Descarga el verificador",
    step2_body: "Un archivo de Python legible, sin dependencias. Puedes revisarlo antes de ejecutarlo.",
    step3_title: "Ejecútalo",
    step3_body: "Te dirá fila por fila si la cadena cuadra o dónde se rompió.",
    guarantees_title: "Qué garantiza",
    g1: "Que ninguna fila publicada se editó, borró ni reordenó después.",
    g2: "Que la cuota de cierre y el resultado se añadieron como filas nuevas, no reescribiendo el pick.",
    g3: "Que el ancla diaria resume las tres cabezas en un único hash comprobable.",
    limits_title: "Qué no garantiza",
    l1: "Que el modelo acierte: la transparencia no elimina la varianza.",
    l2: "Habría que comparar el ancla con una copia externa (red social, archivo, testigo) para detectar una reescritura completa y coordinada. El anclaje externo está en el roadmap.",
    l3: "Que un resultado sea justo: se asienta con el marcador oficial de la fuente de datos.",
    back_ledger: "← Volver al registro completo de picks",
    footer_disclaimer: "<strong>+18 · Uso responsable. No prometemos ganancias.</strong> Los pronósticos deportivos implican riesgo y los datos históricos no garantizan resultados futuros. Este sitio ofrece análisis estadístico independiente con fines informativos; no es un operador de juego, no acepta fondos ni custodia dinero (aviso aplicable en México y demás jurisdicciones).",
    footer_copyright: "ApuestaEdge © 2026 · Desarrollado y mantenido por Carlos Prado · Auditoría pública en /verificacion",
  },
  en: {
    nav_home: "Home", nav_ledger: "Pick ledger",
    nav_leagues: "Leagues", nav_model: "Model",
    nav_verify: "Verification", nav_alerts: "Alerts", nav_pricing: "Pricing",
    eyebrow: "Verification · append-only ledger",
    title: "You don't have to believe us. Verify it.",
    intro: "Every published pick is chained to the previous one with SHA-256. If anyone edits, deletes or reorders a row, the chain breaks. Here you see the live state and can download the full package to recompute it on your own machine, without trusting us.",
    btn_verify: "Verify now", btn_package: "Download package (JSON)",
    btn_script: "Download verifier (Python)",
    state_title: "Ledger state", state_loading: "Checking the chains…",
    state_ok: "Chain verified in your browser: {rows} rows across {chains} chains. Heads and anchor match.",
    state_bad: "The chain does not match. Do not trust this data until we review it.",
    state_empty: "The ledger is still empty: 0 rows. When the first pick is published, the chain starts here.",
    chain_picks: "Published picks",
    chain_picks_note: "What was published before each event.",
    chain_closings: "Closings and CLV",
    chain_closings_note: "Frozen closing odds and computed CLV.",
    chain_results: "Results",
    chain_results_note: "Settled from the real score.",
    head_label: "Head", empty_chain: "empty chain (no rows yet)",
    anchor_loading: "Looking for the daily anchor…",
    anchor_none: "No daily anchor yet: it is published at the end of the first day with picks. The chain can still be verified meanwhile.",
    anchor_line: "Latest publication: {day} · head {hash} · {rows} rows",
    anchor_prev: " · (anchor from an earlier state: compared with the full package)",
    anchor_bad: "⚠️ The anchor hash does not match its own data.",
    browser_scope: "The browser check verifies the link between rows, each row's hash over its canonical content and the anchor hash. The Python verifier also rebuilds that canonical content from the raw fields, so you don't depend on what this page claims.",
    browser_unsupported: "This browser cannot verify locally (HTTPS and Web Crypto required). Use the Python verifier: it runs the exact same check on the package.",
    verifying: "Verifying in your browser…",
    verify_ok: "✓ Local verification passed: {rows} rows across 3 chains. Heads {picks}… · {closings}… · {results}…",
    verify_fail: "✗ Local verification failed: {reason}",
    verify_fail_anchor: "✗ The anchor hash does not match its data.",
    verify_fail_heads: "✗ The latest anchor claims the same row counts but different heads: the ledger was rewritten.",
    fail_link: "row {id} does not link to the previous one.",
    fail_hash: "row {id}'s hash does not match its content.",
    how_title: "Independent verification on your machine",
    how_sub: "Three steps, nothing to install but Python. The script uses only the standard library and never calls our API: it reads the package you downloaded.",
    step1_title: "Download the package",
    step1_body: "It contains the raw rows of all three chains, the hash specification and every published anchor.",
    step2_title: "Download the verifier",
    step2_body: "A readable Python file with no dependencies. You can review it before running it.",
    step3_title: "Run it",
    step3_body: "It tells you row by row whether the chain matches or where it broke.",
    guarantees_title: "What it guarantees",
    g1: "That no published row was edited, deleted or reordered afterwards.",
    g2: "That closing odds and results were appended as new rows, not by rewriting the pick.",
    g3: "That the daily anchor summarizes the three heads in a single checkable hash.",
    limits_title: "What it does not guarantee",
    l1: "That the model is right: transparency does not remove variance.",
    l2: "You would need to compare the anchor with an external copy (social post, archive, witness) to detect a full coordinated rewrite. External timestamping is on the roadmap.",
    l3: "That a result is fair: it settles from the official score of the data source.",
    back_ledger: "← Back to the full pick ledger",
    footer_disclaimer: "<strong>18+ · Responsible use. We do not promise profits.</strong> Sports forecasting involves risk and past data does not guarantee future results. This site provides independent statistical analysis for informational purposes only; it is not a gaming operator, does not accept wagers and does not custody funds (notice applicable in Mexico and other jurisdictions).",
    footer_copyright: "ApuestaEdge © 2026 · Built and maintained by Carlos Prado · Public audit at /verificacion",
  },
};

const TABLES = ["picks", "pick_closings", "pick_results"];
const ANCHOR_KEYS = ["picks_head", "picks_count", "closings_head",
                     "closings_count", "results_head", "results_count"];

const state = {
  lang: localStorage.getItem("ae_lang") || "es",
  pkg: null,
  running: false,
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
const short = (hash) => String(hash || "").slice(0, 16);

async function sha256Hex(text) {
  const data = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0")).join("");
}

function canVerify() {
  return Boolean(window.crypto && window.crypto.subtle && window.TextEncoder);
}

/* ------------------------------------------------------------ estado */
function renderCards() {
  const pkg = state.pkg;
  const server = (pkg && pkg.server_check && pkg.server_check.chains) || {};
  TABLES.forEach((table) => {
    const card = document.querySelector(`.chain-card[data-chain="${table}"]`);
    if (!card) return;
    const rows = (pkg && pkg.tables && pkg.tables[table]) || [];
    const info = server[table] || {};
    card.querySelector("[data-rows]").textContent =
      rows.length ? String(rows.length) : t("empty_chain");
    card.querySelector("[data-head]").textContent =
      rows.length && info.head ? `${short(info.head)}…` : "—";
    const dot = card.querySelector("[data-dot]");
    dot.classList.remove("ok", "bad");
    if (rows.length) dot.classList.add(info.ok === false ? "bad" : "ok");
  });
}

function renderAnchor() {
  const panel = $("#anchor-panel");
  const dot = $("#anchor-dot");
  const text = $("#anchor-text");
  const anchors = (state.pkg && state.pkg.anchors) || [];
  dot.classList.remove("ok", "bad");
  if (!anchors.length) {
    text.textContent = t("anchor_none");
    dot.classList.add("ok");
    return;
  }
  const anchor = anchors[0];
  const otsLabel = state.lang === "en"
    ? "Download .ots proof (OpenTimestamps)"
    : "Descargar prueba .ots (OpenTimestamps)";
  text.innerHTML = esc(fill("anchor_line", {
    day: anchor.day, hash: short(anchor.head_hash) + "…",
    rows: Number(anchor.picks_count || 0),
  })) + ` · <a href="/api/ledger/anchors/${encodeURIComponent(anchor.day)}.ots">${esc(otsLabel)} ↗</a>`;
  dot.classList.add("ok");
  panel.hidden = false;
}

async function verifyChain(rows) {
  let prev = "";
  for (let i = 0; i < rows.length; i += 1) {
    const row = rows[i];
    if (String(row.prev_hash || "") !== prev) {
      return { ok: false, reason: fill("fail_link", { id: row.id ?? i + 1 }) };
    }
    const expected = await sha256Hex(prev + String(row.canonical || ""));
    if (expected !== row.row_hash) {
      return { ok: false, reason: fill("fail_hash", { id: row.id ?? i + 1 }) };
    }
    prev = row.row_hash;
  }
  return { ok: true, rows: rows.length, head: prev };
}

async function verifyAnchorHash(anchor) {
  const material = ANCHOR_KEYS.map((k) => String(anchor[k])).join("|");
  return (await sha256Hex(material)) === anchor.head_hash;
}

function showResult(ok, message) {
  const box = $("#verify-result");
  box.hidden = false;
  box.classList.remove("ok", "bad");
  box.classList.add(ok ? "ok" : "bad");
  box.textContent = message;
}

async function runVerification() {
  if (!state.pkg || state.running) return;
  const sub = $("#state-sub");
  if (!canVerify()) {
    sub.textContent = t("browser_unsupported");
    return;
  }
  state.running = true;
  sub.textContent = t("verifying");
  const results = {};
  let total = 0;
  let failure = null;
  for (const table of TABLES) {
    const rows = (state.pkg.tables && state.pkg.tables[table]) || [];
    const res = await verifyChain(rows);
    results[table] = res;
    total += res.rows;
    if (!res.ok && !failure) failure = res.reason;
  }

  const anchors = state.pkg.anchors || [];
  let anchorOk = true;
  let headsMismatch = false;
  if (anchors.length) {
    const anchor = anchors[0];
    anchorOk = await verifyAnchorHash(anchor);
    const counts = {
      picks_count: results.picks.rows,
      closings_count: results.pick_closings.rows,
      results_count: results.pick_results.rows,
    };
    const sameCounts = Object.entries(counts)
      .every(([key, value]) => Number(anchor[key] || 0) === value);
    if (sameCounts) {
      headsMismatch = !(String(anchor.picks_head) === results.picks.head &&
        String(anchor.closings_head) === results.pick_closings.head &&
        String(anchor.results_head) === results.pick_results.head);
    }
    if (!anchorOk) {
      $("#anchor-dot").classList.remove("ok");
      $("#anchor-dot").classList.add("bad");
    }
  }

  const ok = !failure && anchorOk && !headsMismatch;
  TABLES.forEach((table) => {
    const dot = document.querySelector(
      `.chain-card[data-chain="${table}"] [data-dot]`);
    if (!dot) return;
    dot.classList.remove("ok", "bad");
    if (results[table].rows) dot.classList.add(results[table].ok ? "ok" : "bad");
  });

  if (ok) {
    if (total === 0) {
      sub.textContent = t("state_empty");
    } else {
      const chains = TABLES.filter((table) => results[table].rows).length;
      sub.textContent = fill("state_ok", { rows: total, chains });
    }
    showResult(true, fill("verify_ok", {
      rows: total,
      picks: short(results.picks.head),
      closings: short(results.pick_closings.head),
      results: short(results.pick_results.head),
    }));
  } else {
    sub.textContent = t("state_bad");
    const reason = failure || (!anchorOk ? t("verify_fail_anchor") : t("verify_fail_heads"));
    showResult(false, fill("verify_fail", { reason }));
  }
  state.running = false;
}

/* ------------------------------------------------------------ idioma */
function applyLang(lang) {
  state.lang = lang;
  localStorage.setItem("ae_lang", lang);
  document.documentElement.lang = lang;
  document.title = lang === "en"
    ? "Ledger verification · ApuestaEdge"
    : "Verificación del registro · ApuestaEdge";
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
  renderCards();
  renderAnchor();
  if (state.pkg) runVerification();
}

/* ------------------------------------------------------------ init */
async function loadPackage() {
  try {
    const resp = await fetch("/api/ledger/export", {
      headers: { Accept: "application/json" },
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    state.pkg = await resp.json();
    renderCards();
    renderAnchor();
    await runVerification();
  } catch (e) {
    $("#state-sub").textContent = `— ${e.message}`;
  }
}

function bind() {
  $("#lang-toggle").addEventListener("click", () => {
    applyLang(state.lang === "es" ? "en" : "es");
  });
  $("#verify-now").addEventListener("click", runVerification);
}

async function init() {
  bind();
  applyLang(state.lang);
  await loadPackage();
}

init();
