/* Permalink público e inmutable de un pick (/pick/{id}). */
"use strict";

const I18N = {
  es: {
    nav_home: "Inicio", nav_ledger: "Registro de picks",
    nav_leagues: "Ligas", nav_model: "Modelo",
    nav_verify: "Verificación", nav_alerts: "Alertas",
    nav_pricing: "Precios",
    eyebrow: "Registro inmutable · Pick",
    published_before: "Publicado antes del inicio y encadenado con SHA-256.",
    btn_verify: "Verificar hash SHA-256 en este navegador",
    btn_copy_link: "Copiar enlace permanente",
    btn_copy_details: "Copiar detalles del pick",
    back_ledger: "← Volver al registro",
    lbl_odds: "Cuota de entrada",
    lbl_edge: "Edge del modelo",
    lbl_closing: "Cuota de cierre / CLV",
    lbl_result: "Resultado",
    card_details: "Datos registrados antes del inicio",
    card_hashes: "Prueba criptográfica (SHA-256)",
    hash_explainer: "Cada etapa (publicación, cierre de cuota y resultado) escribe una fila independiente enlazada con el hash anterior.",
    row_hash_label: "Hash de publicación:",
    dt_league: "Liga", dt_event: "Evento", dt_market: "Mercado",
    dt_selection: "Selección", dt_book: "Casa (sin afiliado)",
    dt_stake: "Stake Kelly 1/4", dt_published: "Publicado (UTC)",
    dt_kickoff: "Inicio del evento (UTC)", dt_settled: "Asentado (UTC)",
    dt_model_ver: "Versión del modelo",
    probs_sub: "Modelo {m}% vs mercado {k}%",
    closing_pending: "Pendiente de cierre",
    clv_sub: "CLV {clv}",
    res_won: "Ganada", res_lost: "Perdida", res_push: "Nula (push)",
    res_void: "Anulada", res_pending: "Pendiente",
    profit_units: "{u} u.",
    chain_pick: "1. Publicación del pick",
    chain_closing: "2. Cierre de cuota (CLV)",
    chain_result: "3. Resultado asentado",
    verify_ok: "✓ Verificado en tu navegador: los hashes SHA-256 de este pick coinciden exactamente con sus cadenas canónicas.",
    verify_bad: "✗ Alerta: el hash recalculado no coincide con el registrado.",
    verify_nocrypto: "Web Crypto no está disponible en este contexto; usa verify_ledger.py en /verificacion.",
    copied_link: "Enlace copiado",
    copied_details: "Detalles copiados",
    direct_no_aff: "enlace directo, sin afiliado",
    footer_disclaimer: "<strong>+18 · Uso responsable. No prometemos ganancias.</strong> Los pronósticos deportivos implican riesgo y los datos históricos no garantizan resultados futuros. Este sitio ofrece análisis estadístico independiente con fines informativos; no es un operador de juego, no acepta fondos ni custodia dinero (aviso aplicable en México y demás jurisdicciones).",
    footer_copyright: "ApuestaEdge © 2026 · Desarrollado y mantenido por Carlos Prado · Auditoría pública en /verificacion",
  },
  en: {
    nav_home: "Home", nav_ledger: "Pick ledger",
    nav_leagues: "Leagues", nav_model: "Model",
    nav_verify: "Verification", nav_alerts: "Alerts",
    nav_pricing: "Pricing",
    eyebrow: "Immutable ledger · Pick",
    published_before: "Published before kickoff and chained with SHA-256.",
    btn_verify: "Verify SHA-256 hash in this browser",
    btn_copy_link: "Copy permanent link",
    btn_copy_details: "Copy pick details",
    back_ledger: "← Back to ledger",
    lbl_odds: "Entry odds",
    lbl_edge: "Model edge",
    lbl_closing: "Closing odds / CLV",
    lbl_result: "Outcome",
    card_details: "Data recorded before kickoff",
    card_hashes: "Cryptographic proof (SHA-256)",
    hash_explainer: "Each stage (pick publication, closing odds and settled result) writes an independent row linked to the previous hash.",
    row_hash_label: "Publication hash:",
    dt_league: "League", dt_event: "Event", dt_market: "Market",
    dt_selection: "Selection", dt_book: "Bookmaker (no affiliate)",
    dt_stake: "1/4 Kelly stake", dt_published: "Published (UTC)",
    dt_kickoff: "Event start (UTC)", dt_settled: "Settled (UTC)",
    dt_model_ver: "Model version",
    probs_sub: "Model {m}% vs market {k}%",
    closing_pending: "Closing pending",
    clv_sub: "CLV {clv}",
    res_won: "Won", res_lost: "Lost", res_push: "Push",
    res_void: "Void", res_pending: "Pending",
    profit_units: "{u} u.",
    chain_pick: "1. Pick publication",
    chain_closing: "2. Closing odds (CLV)",
    chain_result: "3. Settled outcome",
    verify_ok: "✓ Verified in your browser: the SHA-256 hashes of this pick match its canonical strings.",
    verify_bad: "✗ Warning: recomputed hash does not match the recorded hash.",
    verify_nocrypto: "Web Crypto is unavailable in this context; use verify_ledger.py on /verificacion.",
    copied_link: "Link copied",
    copied_details: "Details copied",
    direct_no_aff: "direct link, no affiliate",
    footer_disclaimer: "<strong>18+ · Responsible use. We do not promise profits.</strong> Sports forecasting involves risk and past data does not guarantee future results. This site provides independent statistical analysis for informational purposes only; it is not a gaming operator, does not accept wagers and does not custody funds (notice applicable in Mexico and other jurisdictions).",
    footer_copyright: "ApuestaEdge © 2026 · Built and maintained by Carlos Prado · Public audit at /verificacion",
  },
};

const state = {
  lang: localStorage.getItem("ae_lang") || "es",
  pick: window.__PICK_DATA__ || null,
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

function fmtUtc(epoch) {
  const v = Number(epoch);
  if (!Number.isFinite(v) || v <= 0) return "—";
  return new Date(v * 1000).toISOString().replace("T", " ").slice(0, 16) + " UTC";
}

function resultLabel(res) {
  return t(`res_${res || "pending"}`);
}

function render() {
  const p = state.pick;
  if (!p) return;
  $("#p-odds").textContent = Number(p.bet_odds).toFixed(2);
  $("#p-book").textContent = p.bookmaker || "—";
  $("#p-edge").textContent = `+${Number(p.edge_pct).toFixed(1)}%`;
  $("#p-probs").textContent = fill("probs_sub", {
    m: (Number(p.model_prob) * 100).toFixed(1),
    k: (Number(p.market_prob) * 100).toFixed(1),
  });

  if (p.closing_odds != null) {
    $("#p-closing").textContent = Number(p.closing_odds).toFixed(2);
    const clv = Number(p.clv_pct || 0);
    $("#p-clv-sub").textContent = fill("clv_sub", {
      clv: `${clv > 0 ? "+" : ""}${clv.toFixed(2)}%`,
    });
  } else {
    $("#p-closing").textContent = "—";
    $("#p-clv-sub").textContent = t("closing_pending");
  }

  const resEl = $("#p-result");
  resEl.textContent = resultLabel(p.result);
  resEl.classList.remove("pos", "neg");
  if (p.result === "won") resEl.classList.add("pos");
  if (p.result === "lost") resEl.classList.add("neg");

  if (p.profit_units != null) {
    const u = Number(p.profit_units);
    $("#p-profit").textContent = fill("profit_units", {
      u: `${u > 0 ? "+" : ""}${u.toFixed(2)}`,
    });
  } else {
    $("#p-profit").textContent = `${Number(p.stake_units).toFixed(2)} u.`;
  }

  const bookHtml = p.bookmaker_url
    ? `<a href="${esc(p.bookmaker_url)}" target="_blank" rel="noopener noreferrer">${esc(p.bookmaker)} ↗</a> <span class="muted">(${esc(t("direct_no_aff"))})</span>`
    : `${esc(p.bookmaker)} <span class="muted">(${esc(t("direct_no_aff"))})</span>`;

  const rows = [
    [t("dt_league"), esc(p.league)],
    [t("dt_event"), esc(p.event)],
    [t("dt_market"), esc(p.market)],
    [t("dt_selection"), esc(p.selection_label)],
    [t("dt_book"), bookHtml],
    [t("dt_stake"), `${Number(p.stake_units).toFixed(2)} u.`],
    [t("dt_published"), esc(fmtUtc(p.created_at))],
    [t("dt_kickoff"), esc(fmtUtc(p.event_start))],
    [t("dt_settled"), esc(fmtUtc(p.settled_at))],
    [t("dt_model_ver"), `<code>${esc(p.model_version)}</code>`],
  ];
  $("#p-details").innerHTML = rows.map(([k, v]) =>
    `<div class="pick-dl-row"><dt>${esc(k)}</dt><dd>${v}</dd></div>`
  ).join("");

  const stages = [
    {
      title: t("chain_pick"),
      prev: p.prev_hash || "(genesis)",
      row: p.row_hash,
      canon: p.pick_canonical,
    },
  ];
  if (p.closing_row_hash) {
    stages.push({
      title: t("chain_closing"),
      prev: p.closing_prev_hash || "(genesis)",
      row: p.closing_row_hash,
      canon: p.closing_canonical,
    });
  }
  if (p.result_row_hash) {
    stages.push({
      title: t("chain_result"),
      prev: p.result_prev_hash || "(genesis)",
      row: p.result_row_hash,
      canon: p.result_canonical,
    });
  }
  $("#p-hashes").innerHTML = stages.map((s) => `
    <div class="hash-stage">
      <strong>${esc(s.title)}</strong>
      <div class="chain-head">prev: <code>${esc(s.prev)}</code></div>
      <div class="chain-head">row: <code>${esc(s.row)}</code></div>
      <pre class="code-block"><code>${esc(s.canon || "")}</code></pre>
    </div>
  `).join("");
}

async function sha256Hex(text) {
  const bytes = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function verifyPickHashes() {
  const box = $("#pick-verify-box");
  box.hidden = false;
  box.className = "verify-result";
  if (!window.crypto || !window.crypto.subtle) {
    box.textContent = t("verify_nocrypto");
    return;
  }
  const p = state.pick;
  const checks = [
    [p.prev_hash || "", p.pick_canonical, p.row_hash],
  ];
  if (p.closing_row_hash && p.closing_canonical) {
    checks.push([p.closing_prev_hash || "", p.closing_canonical, p.closing_row_hash]);
  }
  if (p.result_row_hash && p.result_canonical) {
    checks.push([p.result_prev_hash || "", p.result_canonical, p.result_row_hash]);
  }
  for (const [prev, canon, expected] of checks) {
    const computed = await sha256Hex(String(prev) + String(canon));
    if (computed !== expected) {
      box.classList.add("bad");
      box.textContent = t("verify_bad");
      return;
    }
  }
  box.classList.add("ok");
  box.textContent = t("verify_ok");
}

function applyLang(lang) {
  state.lang = lang;
  localStorage.setItem("ae_lang", lang);
  document.documentElement.lang = lang;
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
  render();
}

function bind() {
  $("#lang-toggle").addEventListener("click", () => {
    applyLang(state.lang === "es" ? "en" : "es");
  });
  $("#btn-verify-pick").addEventListener("click", verifyPickHashes);
  $("#btn-copy-link").addEventListener("click", async () => {
    const url = window.location.href;
    if (navigator.clipboard) await navigator.clipboard.writeText(url);
    $("#btn-copy-link").textContent = t("copied_link");
  });
  $("#btn-copy-pick").addEventListener("click", async () => {
    const p = state.pick;
    const summary = [
      `ApuestaEdge Pick #${p.id}`,
      `${p.league} · ${p.event}`,
      `${p.selection_label} @ ${Number(p.bet_odds).toFixed(2)} (${p.bookmaker})`,
      `Edge +${Number(p.edge_pct).toFixed(1)}% · Stake ${Number(p.stake_units).toFixed(2)}u`,
      `SHA-256: ${p.row_hash}`,
      window.location.href,
    ].join("\n");
    if (navigator.clipboard) await navigator.clipboard.writeText(summary);
    $("#btn-copy-pick").textContent = t("copied_details");
  });
}

function init() {
  bind();
  applyLang(state.lang);
}

init();
