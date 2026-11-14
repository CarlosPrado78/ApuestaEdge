"use strict";
const I18N = {
  es: {
    nav_home: "Inicio", nav_ledger: "Registro", nav_leagues: "Ligas",
    nav_model: "Modelo", nav_verify: "Verificación", nav_alerts: "Alertas",
    nav_impact: "Impacto", nav_risk: "Riesgo", nav_team: "Equipo",
    nav_pricing: "Precios",
    eyebrow: "Quién está detrás",
    title: "Una persona, con nombre real y trazabilidad verificable.",
    intro: "ApuestaEdge lo construye una sola persona. No es una agencia ni un equipo anónimo: es un desarrollador con nombre, repositorio público y un motivo concreto. Si algo falla, sabes a quién preguntar.",
    who_title: "Identidad",
    who_role: "Desarrollador y responsable del modelo",
    who_bio: "Construye ApuestaEdge porque está cansado de pronósticos sin prueba. El código, el registro y la metodología son públicos y auditables. Un solo responsable, un solo punto de contacto, sin intermediarios.",
    verify_link: "Verificar el registro",
    why_title: "Por qué existe este proyecto",
    w1: "Los pronósticos deportivos están llenos de resultados inventados y capturas de pantalla. Aquí cada pick se publica antes del evento y se asienta con el marcador real.",
    w2: "Nadie puede borrar una pérdida ni editar una cuota: el registro es append-only con cadena de hashes SHA-256 anclada a OpenTimestamps.",
    w3: "El plan Premium no se lanza hasta tener 200 picks cerrados con CLV calculado y hash anclado. Mientras tanto, lista de espera honesta.",
    w4: "Una sola persona, responsable de todo: si el modelo falla, lo verás en el changelog público.",
    community_title: "Comunidad y retroalimentación",
    community_body: "Discute picks, reporta errores y propone mejoras en el grupo público de Telegram. Cada pick tiene su enlace \\"Discutir este pick\\".",
    community_cta: "Unirse a la comunidad (Telegram)",
    back_ledger: "← Volver al registro",
    footer_disclaimer: "<strong>+18 · Uso responsable. No prometemos ganancias.</strong> Los pronósticos deportivos implican riesgo y los datos históricos no garantizan resultados futuros. Este sitio ofrece análisis estadístico independiente con fines informativos; no es un operador de juego, no acepta fondos ni custodia dinero (aviso aplicable en México y demás jurisdicciones).",
    footer_copyright: "ApuestaEdge © 2026 · Desarrollado y mantenido por Carlos Prado · Auditoría pública en /verificacion",
  },
  en: {
    nav_home: "Home", nav_ledger: "Ledger", nav_leagues: "Leagues",
    nav_model: "Model", nav_verify: "Verification", nav_alerts: "Alerts",
    nav_impact: "Impact", nav_risk: "Risk", nav_team: "Team",
    nav_pricing: "Pricing",
    eyebrow: "Who is behind it",
    title: "One person, with a real name and verifiable traceability.",
    intro: "ApuestaEdge is built by one person. Not an agency or an anonymous team: a developer with a name, a public repository and a concrete motive. If something fails, you know who to ask.",
    who_title: "Identity",
    who_role: "Developer and model owner",
    who_bio: "Builds ApuestaEdge because he is tired of forecasts without proof. The code, the ledger and the methodology are public and auditable. One responsible person, one point of contact, no intermediaries.",
    verify_link: "Verify the ledger",
    why_title: "Why this project exists",
    w1: "Sports forecasting is full of invented results and screenshots. Here every pick is published before the event and settled with the real score.",
    w2: "No one can delete a loss or edit odds: the ledger is append-only with a SHA-256 hash chain anchored to OpenTimestamps.",
    w3: "The Premium plan does not launch until there are 200 settled picks with CLV computed and hash anchored. Until then, an honest waitlist.",
    w4: "One person, responsible for everything: if the model fails, you will see it in the public changelog.",
    community_title: "Community and feedback",
    community_body: "Discuss picks, report errors and propose improvements in the public Telegram group. Every pick has its \\"Discuss this pick\\" link.",
    community_cta: "Join the community (Telegram)",
    back_ledger: "← Back to ledger",
    footer_disclaimer: "<strong>18+ · Responsible use. We do not promise profits.</strong> Sports forecasting involves risk and past data does not guarantee future results. This site provides independent statistical analysis for informational purposes only; it is not a gaming operator, does not accept wagers and does not custody funds (notice applicable in Mexico and other jurisdictions).",
    footer_copyright: "ApuestaEdge © 2026 · Built and maintained by Carlos Prado · Public audit at /verificacion",
  },
};
const state = { lang: localStorage.getItem("ae_lang") || "es" };
const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const t = (key) => (I18N[state.lang] && I18N[state.lang][key]) || I18N.es[key] || key;
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
function applyLang(lang) {
  state.lang = lang;
  localStorage.setItem("ae_lang", lang);
  document.documentElement.lang = lang;
  document.title = lang === "en" ? "Who is behind it · ApuestaEdge" : "Quién está detrás · ApuestaEdge";
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
}
function bind() {
  $("#lang-toggle").addEventListener("click", () => {
    applyLang(state.lang === "es" ? "en" : "es");
  });
}
function init() { bind(); applyLang(state.lang); }
init();
