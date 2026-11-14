/* ---------------------------------------------------------------- i18n */
const I18N = {
  es: {
    login: "Iniciar sesión", logout: "Salir", nav_picks: "Picks de hoy",
    nav_perf: "Rendimiento", nav_why: "Por qué funciona", nav_pricing: "Precios",
    nav_ledger: "Registro completo", nav_leagues: "Ligas",
    nav_model: "Modelo", nav_verify: "Verificación",
    hero_eyebrow: "Registro público desde el 13 nov 2026",
    hero_title: "Publicamos <em>cada</em> pick, incluidas las pérdidas.",
    hero_lead: "Cada pick se publica antes del evento, se asienta con el marcador real y queda en un registro que no se puede editar. Sin resultados inventados: si todavía no hay picks cerrados, verás 0.",
    hero_cta_picks: "Ver registro completo de picks", hero_cta_why: "Probar 7 días gratis",
    hero_roi: "ROI acumulado", hero_clv: "CLV medio", hero_dd: "Drawdown máximo",
    hero_losses: "Pérdidas publicadas", hero_bets: "Picks publicados",
    hero_honesty: "No prometemos ganancias. Publicamos el resultado completo, gane o pierda.",
    hero_insufficient: "muestra insuficiente (n = {n})",
    sub_closed: "{n} cerrados", sub_wins: "{n} ganadas",
    ledger_open_zero: "Registro abierto el 13 nov 2026 · 0 picks cerrados todavía. Publicamos cada evento antes de que empiece; los resultados aparecerán aquí con el marcador real.",
    ledger_small: "{total} picks publicados · {n} cerrados. Con menos de 30 picks cerrados no mostramos porcentajes: serían una promesa, no una medición.",
    ledger_ok: "Calculado sobre {n} picks cerrados. Los pendientes no cuentan.",
    settled_word: "cerrados", equity_empty: "Aún no hay picks cerrados: la curva aparecerá con el primer resultado.",
    picks_title: "Recomendaciones de hoy", chip_all: "Todos",
    bankroll: "Bankroll", login_title: "Entrar en ApuestaEdge",
    login_help: "Accede con tu email y contraseña.",
    login_toggle: "¿No tienes cuenta? Crear una",
    login_toggle_back: "¿Ya tienes cuenta? Entrar",
    btn_login_submit: "Entrar", btn_register_submit: "Crear cuenta",
    cancel: "Cancelar",
    plan_free: "Free", plan_premium: "Premium",
    free_banner: "Estás viendo el plan Free: 5 picks/día con edge ≥ 6% y análisis resumido. Premium desbloquea 20 picks, edge ≥ 3% y el análisis completo.",
    free_banner_btn: "Entrar / crear cuenta",
    premium_banner: "✓ Premium activo · 20 picks al día con edge ≥ 3%, stake Kelly, confianza y backtest completos.",
    free_user_banner: "Plan Free · 5 picks/día con edge ≥ 6% y análisis resumido. Estás perdiendo los mejores valores (edge 3–6%) y el análisis completo.",
    unlock_premium: "Desbloquear Premium",
    view_subscription: "Ver mi suscripción",
    upgrading: "Continuar a pago", creating: "Crear cuenta",
    sending_link: "Enviando…",
    wrong_creds: "Correo o contraseña incorrectos.",
    short_pw: "La contraseña debe tener al menos 8 caracteres.",
    already_exists: "Ya existe una cuenta con ese correo. Inicia sesión.",
    account_created: "Cuenta creada.",
    picks_loading: "Calculando valor esperado…",
    wrong_creds: "Correo o contraseña incorrectos.",
    short_pw: "La contraseña debe tener al menos 8 caracteres.",
    already_exists: "Ya existe una cuenta con ese correo. Inicia sesión.",
    invalid_email: "Correo inválido.",
    login_before_subscribe: "Inicia sesión (o crea tu cuenta) antes de suscribirte.",
    redirect_stripe: "Te redirigimos a Stripe para completar el pago.",
    free_created: "Cuenta Free creada. Inicia sesión para entrar.",
    premium_on_confirm: " Tu cuenta pasará a Premium al confirmarse el pago.",
    signed_out: "Sesión cerrada.",
    no_subscription_to_manage: "Esta cuenta aún no tiene una suscripción de Stripe que gestionar.",
    stripe_not_confirmed: "Stripe aún no ha confirmado el pago.",
    invalid_session: "Sesión inválida.",
    done_ok: "✅ Listo.",
    before_kickoff: "antes del pitido inicial",
    audited_label: "Picks auditados",
    won_word: "ganados",
    avg_odds_label: "Cuota media",
    avg_odds_sub: "precio medio de entrada",
    roi_sub: "beneficio por unidad apostada",
    pf_sub: "ganancias ÷ pérdidas",
    drawdown_label: "Drawdown máx.",
    drawdown_sub: "peor caída acumulada",
    signif_yes: "ventaja significativa (95%)",
    signif_no: "ventaja aún no significativa",
    no_data: "Sin datos",
    included_premium: "Incluido en Premium",
    go_premium: "Hazte Premium",
    start_premium: "Empezar Premium",
    premium_content: "Contenido Premium",
    premium_label: "Premium",
    odds_word: "cuota",
    hide_analysis: "Ocultar análisis",
    load_error: "No se pudieron cargar los picks:",
    risks_title: "Riesgos que debes conocer",
    forever: "/ siempre",
    per_month: "/ mes",
    free_price: "Gratis",
    most_popular: "MÁS POPULAR",
    login_help_register: "Email y contraseña (mín. 8 caracteres).",
    signed_in_premium: "✓ Sesión iniciada como Premium.",
    premium_activated_short: "✓ Premium activado. Ya tienes el análisis completo.",
    premium_activated_long: "✓ <b>Premium activado</b>. Ya ves 20 picks con edge ≥ 3% y análisis completo.",
    stripe_processing: "Stripe todavía está procesando el pago. Esperando confirmación…",
    verify_failed: "No pudimos verificar el pago automáticamente:",
    retrying: "Reintentando…",
    payment_maybe: "El pago puede haberse completado, pero Premium aún no aparece. ",
    payment_maybe_tail: "Pulsa <b>«Actualizar estado»</b> en tu suscripción; si persiste, escríbenos.",
    payment_registered: "Pago registrado. Si el portal no aparece, pulsa «Actualizar estado»; el webhook de Stripe puede tardar unos segundos.",
    demo_mode_short: "Modo <b>demo</b> · plan",
    no_charges: "(sin cobros reales).",
    cancels_on: "se cancela el",
    renews_on: "renueva el",
    sub_free_note: "📦 Plan <b>Free</b> · Premium desbloquea 20 picks y todo el análisis.",
    plan_word: "plan",
    equity_close: "Cierre actual",
    units_word: "unidades",
    equity_stakes: "sobre stakes de 0.5–2.5% del bankroll.",
    tg_linked: "Vinculado",
    tg_receive: "recibirás picks",
    tg_min_edge: "con edge",
    tg_every: "cada",
    tg_no_repeat: "(sin repetir ninguno).",
    tg_link_one_click: "Vincula tu cuenta con un clic:",
    tg_open_bot: "abrir",
    tg_in_telegram: "en Telegram",
    tg_or_send: "o envía",
    tg_inside_bot: "dentro del bot",
    tg_login_first: "Inicia sesión arriba para obtener tu enlace de vinculación con Telegram.",
    tg_load_error: "No se pudo cargar el estado de Telegram.",
    plan_label: "Plan", min_edge_label: "edge mínimo",
    matches_analyzed: "partidos analizados", with_value: "con valor",
    edge_label: "Edge", ev_label: "Valor esperado", confidence_label: "Confianza",
    why_trust: "Ver análisis",
    no_picks_short: "Sin picks con valor ahora mismo.",
    no_picks_detail: "Esperar a que el mercado ofrezca ventaja es parte del método: no entrar también es una decisión estadística.",
    free_delay_empty: "El plan Free recibe cada pick 2 h después de publicarse en el registro. Ahora mismo no hay ninguno liberado: vuelve más tarde o consulta el registro público.",
    delayed_note: "Desbloquea 20 picks con edge ≥ 3%, stake Kelly, confianza y backtest completos en Premium.",
    locked_odds_full: "🔒 cuota y casa en Premium",
    unlock_analysis: "Desbloquear análisis →",
    kelly_full: "Kelly completo",
    kelly_used: "usamos",
    stake_suggested: "Stake sugerido",
    best_odds_among: "Mejor cuota entre",
    houses: "casas",
    model_label: "Modelo",
    backtest_label: "Backtest",
    picks_word: "picks",
    roi_label: "ROI",
    hit_rate_label: "Acierto",
    breakeven_label: "breakeven",
    demo_mode: "Modo demostración: partidos y cuotas de ejemplo.",
    live_odds: "✅ Cuotas en vivo, actualizadas cada pocas horas.",
    live_cached: "⏳ Datos en vivo del último parte guardado; la API no responde ahora mismo.",
    no_live_data: "⚠️ Sin datos en vivo ahora mismo. No mostramos eventos inventados: vuelve en unos minutos.",
    matches_on_radar: "partidos en el radar",
    hit_rate_table: "Acierto",
    breakeven_table: "breakeven",
    clv_avg: "CLV medio",
    entry_vs_close: "entrada vs cierre",
    plan_free_label: "Plan Free",
    plan_title_free: "Plan Free", plan_title_premium: "Plan Premium",
    free_word: "Free",
    start_free: "Empezar gratis",
    create_account_title: "Crear cuenta en ApuestaEdge",
    create_account_title: "Crear cuenta en ApuestaEdge",
    premium_active: "✅ Premium activo",
    loading: "Cargando…",
    picks_sub: "Filtradas por valor esperado positivo y confianza estadística.",
    perf_title: "Rendimiento auditable",
    perf_sub: "Historial completo de picks (ganados y perdidos). Publicamos lo bueno y lo malo: sin track record verificable no hay confianza posible.",
    perf_equity: "Curva de equity (unidades acumuladas)",
    perf_by_league: "Por liga",
    th_league: "Liga", th_picks: "Picks", th_hit: "Acierto",
    perf_footnote: "p < 0.05 → la ventaja es estadísticamente significativa al 95%. Con menos de 30 picks cerrados por liga no se reporta p-valor.",
    perf_link: "Ver el registro completo, pick por pick, con filtros y CSV →",
    why_title: "¿Por qué ApuestaEdge?",
    why_sub: "Lo que recibes, en concreto — sin humo:",
    benefit1_title: "🎯 Solo entradas con ventaja",
    benefit1_desc: "Nada entra al radar sin valor esperado positivo: si la cuota no supera lo que el mercado exige, no te lo enseñamos. Cero corazonadas.",
    benefit2_title: "💸 El «cuánto», calculado por ti",
    benefit2_desc: "Cada recomendación trae su stake sugerido (calculado automáticamente con tope del 3% de tu bankroll): disciplina automática, sin adivinar cantidades.",
    benefit3_title: "⚡ Picks listos cada pocas horas",
    benefit3_desc: "Ahorras horas de análisis: el radar procesa todos los mercados solo y te muestra lo que interesa, con filtros por deporte en un clic.",
    benefit4_title: "📱 Alertas al instante en Telegram",
    benefit4_desc: "En cuanto aparece una entrada nueva con valor recibes la notificación en tu móvil, con cuota, stake y el porqué. Sin recargar nada.",
    benefit5_title: "🏅 7 deportes, un solo radar",
    benefit5_desc: "Fútbol, básquet, tenis, fútbol americano, boxeo, béisbol y hockey en la misma plataforma, con cuotas reales de cada partido.",
    benefit6_title: "📈 Track record público y auditable",
    benefit6_desc: "Publicamos ROI, CLV, drawdown y test estadístico de cada deporte — lo bueno y lo malo. Sin resultados verificables no hay confianza.",
    steps_title: "Empieza en 3 pasos",
    step1_bold: "Crea tu cuenta gratis",
    step1_text: "(sin tarjeta) y mira las 5 recomendaciones del día.",
    step2_bold: "Define tu bankroll",
    step2_text: "arriba de la lista de picks: cada tarjeta calcula su stake exacto sobre tu capital.",
    step3_bold: "Activa las alertas de Telegram",
    step3_text: "y recibe cada valor nuevo al instante; cuando quieras más, Premium desbloquea el análisis completo.",
    plans_title: "Planes",
    plans_sub: "Empieza gratis. Premium desbloquea todos los valores, el stake exacto y el análisis completo.",
    creating: "Crear cuenta",
    already_have_account: "¿Ya tienes cuenta? Usa Iniciar sesión arriba a la derecha.",
    telegram_title: "📣 Alertas por Telegram",
    checking: "Comprobando estado…",
    subscription_title: "💳 Tu suscripción",
    update_status: "Actualizar estado",
    manage_subscription: "Gestionar suscripción",
    footer_disclaimer: "+18 · Juego responsable. Apostar conlleva riesgo de perder dinero. Este sitio ofrece análisis estadístico con fines informativos; no es asesoramiento financiero ni garantía de resultados. Ningún modelo acierta siempre: jugamos para tener ventaja a largo plazo, no certezas por partido.",
    footer_copyright: "ApuestaEdge © 2026 · Cuotas y resultados de eventos reales",
    email_placeholder: "tu@correo.com",
    pw_placeholder: "Contraseña (mín. 8 caracteres)",
    loading_data: "Cargando datos…",
    premium_active: "✅ Premium activo",
    loading: "Cargando…",
    no_picks: "Sin picks con valor ahora mismo. Esperar a que el mercado ofrezca ventaja es parte del método: no entrar también es una decisión estadística.",
    delayed_badge: "⏱ Premium vio este pick hace 2 h",
    locked_note: "Stake Kelly, cuándo entrar, confianza y backtest completos en el plan Premium.",
    locked_odds: "🔒 cuota y casa en Premium",
    locked_conf: "🔒",
    premium_tag: "PREMIUM",
  },
  en: {
    login: "Sign in", logout: "Sign out", nav_picks: "Today's picks",
    nav_perf: "Performance", nav_why: "Why it works", nav_pricing: "Pricing",
    nav_ledger: "Full ledger", nav_leagues: "Leagues",
    nav_model: "Model", nav_verify: "Verification",
    hero_eyebrow: "Public ledger since 13 Nov 2026",
    hero_title: "We publish <em>every</em> pick, including the losses.",
    hero_lead: "Every pick is published before the event, settles from the real score and stays in a ledger that cannot be edited. No invented results: if there are no settled picks yet, you will see 0.",
    hero_cta_picks: "View the full pick ledger", hero_cta_why: "Try 7 days free",
    hero_roi: "Cumulative ROI", hero_clv: "Average CLV", hero_dd: "Max drawdown",
    hero_losses: "Published losses", hero_bets: "Published picks",
    hero_honesty: "We don't promise profits. We publish the full result, win or lose.",
    hero_insufficient: "insufficient sample (n = {n})",
    sub_closed: "{n} settled", sub_wins: "{n} won",
    ledger_open_zero: "Ledger opened 13 Nov 2026 · 0 settled picks yet. Every event is published before it starts; results will appear here from the real score.",
    ledger_small: "{total} picks published · {n} settled. With fewer than 30 settled picks we do not show percentages: they would be a promise, not a measurement.",
    ledger_ok: "Calculated over {n} settled picks. Pending picks do not count.",
    settled_word: "settled", equity_empty: "No settled picks yet: the curve will appear with the first result.",
    picks_title: "Today's recommendations", chip_all: "All",
    bankroll: "Bankroll", login_title: "Sign in to ApuestaEdge",
    login_help: "Sign in with your email and password.",
    login_toggle: "No account? Create one",
    login_toggle_back: "Already have an account? Sign in",
    btn_login_submit: "Sign in", btn_register_submit: "Create account",
    cancel: "Cancel",
    plan_free: "Free", plan_premium: "Premium",
    free_banner: "You're on the Free plan: 5 picks/day with edge ≥ 6% and summary analysis. Premium unlocks 20 picks, edge ≥ 3% and full analysis.",
    free_banner_btn: "Sign in / create account",
    premium_banner: "✓ Premium active · 20 picks/day with edge ≥ 3%, Kelly stake, confidence and full backtest.",
    free_user_banner: "Free plan · 5 picks/day with edge ≥ 6% and summary analysis. You're missing the best values (edge 3–6%) and full analysis.",
    unlock_premium: "Unlock Premium",
    view_subscription: "View my subscription",
    upgrading: "Continue to payment", creating: "Create account",
    sending_link: "Sending…",
    wrong_creds: "Wrong email or password.",
    short_pw: "Password must be at least 8 characters.",
    already_exists: "An account with this email already exists. Sign in.",
    account_created: "Account created.",
    picks_loading: "Calculating expected value…",
    wrong_creds: "Wrong email or password.",
    short_pw: "Password must be at least 8 characters.",
    already_exists: "An account with this email already exists. Sign in.",
    invalid_email: "Invalid email.",
    login_before_subscribe: "Sign in (or create your account) before subscribing.",
    redirect_stripe: "Redirecting you to Stripe to complete the payment.",
    free_created: "Free account created. Sign in to continue.",
    premium_on_confirm: " Your account will move to Premium once the payment is confirmed.",
    signed_out: "Signed out.",
    no_subscription_to_manage: "This account doesn't have a Stripe subscription to manage yet.",
    stripe_not_confirmed: "Stripe hasn't confirmed the payment yet.",
    invalid_session: "Invalid session.",
    done_ok: "✅ Done.",
    before_kickoff: "before kick-off",
    audited_label: "Audited picks",
    won_word: "won",
    avg_odds_label: "Average odds",
    avg_odds_sub: "average entry price",
    roi_sub: "profit per unit staked",
    pf_sub: "gains ÷ losses",
    drawdown_label: "Max drawdown",
    drawdown_sub: "worst cumulative drop",
    signif_yes: "edge significant (95%)",
    signif_no: "edge not yet significant",
    no_data: "No data",
    included_premium: "Included in Premium",
    go_premium: "Upgrade to Premium",
    start_premium: "Start Premium",
    premium_content: "Premium content",
    premium_label: "Premium",
    odds_word: "odds",
    hide_analysis: "Hide analysis",
    load_error: "Could not load picks:",
    risks_title: "Risks you should know",
    forever: "/ forever",
    per_month: "/ month",
    free_price: "Free",
    most_popular: "MOST POPULAR",
    login_help_register: "Email and password (min. 8 characters).",
    signed_in_premium: "✓ Signed in as Premium.",
    premium_activated_short: "✓ Premium activated. You now have the full analysis.",
    premium_activated_long: "✓ <b>Premium activated</b>. You now see 20 picks with edge ≥ 3% and the full analysis.",
    stripe_processing: "Stripe is still processing the payment. Waiting for confirmation…",
    verify_failed: "We couldn't verify the payment automatically:",
    retrying: "Retrying…",
    payment_maybe: "The payment may have completed, but Premium doesn't show yet. ",
    payment_maybe_tail: "Click <b>“Update status”</b> in your subscription; if it persists, contact us.",
    payment_registered: "Payment recorded. If the portal doesn't appear, click “Update status”; Stripe's webhook may take a few seconds.",
    demo_mode_short: "<b>Demo</b> mode · plan",
    no_charges: "(no real charges).",
    cancels_on: "cancels on",
    renews_on: "renews on",
    sub_free_note: "📦 <b>Free</b> plan · Premium unlocks 20 picks and the full analysis.",
    plan_word: "plan",
    equity_close: "Current close",
    units_word: "units",
    equity_stakes: "on stakes of 0.5–2.5% of bankroll.",
    tg_linked: "Linked",
    tg_receive: "you'll receive picks",
    tg_min_edge: "with edge",
    tg_every: "every",
    tg_no_repeat: "(no repeats).",
    tg_link_one_click: "Link your account in one click:",
    tg_open_bot: "open",
    tg_in_telegram: "in Telegram",
    tg_or_send: "or send",
    tg_inside_bot: "inside the bot",
    tg_login_first: "Sign in above to get your Telegram link code.",
    tg_load_error: "Could not load Telegram status.",
    plan_label: "Plan", min_edge_label: "min edge",
    matches_analyzed: "matches analyzed", with_value: "with value",
    edge_label: "Edge", ev_label: "Expected value", confidence_label: "Confidence",
    why_trust: "View analysis",
    no_picks_short: "No value picks right now.",
    no_picks_detail: "Waiting for the market to offer an edge is part of the method: sitting one out is also a statistical decision.",
    free_delay_empty: "The Free plan receives every pick 2 h after it is published to the ledger. None has been released yet: check back later or browse the public ledger.",
    delayed_note: "Unlock 20 picks with edge ≥ 3%, Kelly stake, confidence and full backtest in Premium.",
    locked_odds_full: "🔒 odds and bookmaker in Premium",
    unlock_analysis: "Unlock analysis →",
    kelly_full: "Full Kelly",
    kelly_used: "we use",
    stake_suggested: "Suggested stake",
    best_odds_among: "Best odds among",
    houses: "bookmakers",
    model_label: "Model",
    backtest_label: "Backtest",
    picks_word: "picks",
    roi_label: "ROI",
    hit_rate_label: "Hit rate",
    breakeven_label: "breakeven",
    demo_mode: "Demo mode: sample matches and odds.",
    live_odds: "✅ Live odds, refreshed every few hours.",
    live_cached: "⏳ Live data from the last saved snapshot; the API is not responding right now.",
    no_live_data: "⚠️ No live data right now. We don't show invented events: check back in a few minutes.",
    matches_on_radar: "matches on the radar",
    hit_rate_table: "Hit rate",
    breakeven_table: "breakeven",
    clv_avg: "Avg CLV",
    entry_vs_close: "entry vs close",
    plan_free_label: "Free plan",
    plan_title_free: "Free plan", plan_title_premium: "Premium plan",
    free_word: "Free",
    start_free: "Start free",
    create_account_title: "Create account on ApuestaEdge",
    create_account_title: "Create account on ApuestaEdge",
    premium_active: "✅ Premium active",
    loading: "Loading…",
    picks_sub: "Filtered by positive expected value and statistical confidence.",
    perf_title: "Auditable performance",
    perf_sub: "Full pick history (wins and losses). We publish the good and the bad: without a verifiable track record there is no trust.",
    perf_equity: "Equity curve (cumulative units)",
    perf_by_league: "By league",
    th_league: "League", th_picks: "Picks", th_hit: "Hit rate",
    perf_footnote: "p < 0.05 → the edge is statistically significant at 95%. With fewer than 30 settled picks per league, no p-value is reported.",
    perf_link: "See the full ledger, pick by pick, with filters and CSV →",
    why_title: "Why ApuestaEdge?",
    why_sub: "What you get, concretely — no hype:",
    benefit1_title: "🎯 Only entries with an edge",
    benefit1_desc: "Nothing enters the radar without positive expected value: if the odds don't beat what the market demands, we don't show it. No gut feelings.",
    benefit2_title: "💸 The «how much», calculated for you",
    benefit2_desc: "Each recommendation includes a suggested stake (automatically calculated with a 3% bankroll cap): automatic discipline, no guessing amounts.",
    benefit3_title: "⚡ Picks ready every few hours",
    benefit3_desc: "Save hours of analysis: the radar processes all markets on its own and shows you what matters, with one-click sport filters.",
    benefit4_title: "📱 Instant Telegram alerts",
    benefit4_desc: "As soon as a new value entry appears you get a notification on your phone, with odds, stake and the why. No refreshing needed.",
    benefit5_title: "🏅 7 sports, one radar",
    benefit5_desc: "Soccer, basketball, tennis, American football, boxing, baseball and hockey on one platform, with real odds for every match.",
    benefit6_title: "📈 Public and auditable track record",
    benefit6_desc: "We publish ROI, CLV, drawdown and statistical test per sport — the good and the bad. Without verifiable results there is no trust.",
    steps_title: "Start in 3 steps",
    step1_bold: "Create your free account",
    step1_text: "(no card) and see the 5 daily recommendations.",
    step2_bold: "Set your bankroll",
    step2_text: "above the picks list: each card calculates its exact stake on your capital.",
    step3_bold: "Enable Telegram alerts",
    step3_text: "and receive every new value instantly; when you want more, Premium unlocks full analysis.",
    plans_title: "Plans",
    plans_sub: "Start free. Premium unlocks all values, exact stake and full analysis.",
    creating: "Create account",
    already_have_account: "Already have an account? Use Sign in at the top right.",
    telegram_title: "📣 Telegram alerts",
    checking: "Checking status…",
    subscription_title: "💳 Your subscription",
    update_status: "Update status",
    manage_subscription: "Manage subscription",
    footer_disclaimer: "+18 · Responsible gambling. Betting carries risk of losing money. This site offers statistical analysis for informational purposes; it is not financial advice or a guarantee of results. No model is always right: we play for long-term edge, not per-match certainty.",
    footer_copyright: "ApuestaEdge © 2026 · Real event odds and results",
    email_placeholder: "you@email.com",
    pw_placeholder: "Password (min. 8 characters)",
    loading_data: "Loading data…",
    premium_active: "✅ Premium active",
    loading: "Loading…",
    no_picks: "No value picks right now. Waiting for the market to offer an edge is part of the method: not betting is also a statistical decision.",
    delayed_badge: "⏱ Premium saw this pick 2h ago",
    locked_note: "Kelly stake, entry timing, confidence and full backtest are in the Premium plan.",
    locked_odds: "🔒 odds and bookmaker in Premium",
    locked_conf: "🔒",
    premium_tag: "PREMIUM",
  }
};

let currentLang = localStorage.getItem("ae_lang") || "es";

function t(key) {
  return (I18N[currentLang] && I18N[currentLang][key]) || (I18N.es[key] || key);
}

function applyLang(lang) {
  currentLang = lang;
  localStorage.setItem("ae_lang", lang);
  document.documentElement.lang = lang;
  // Update all data-i18n elements
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    const val = t(key);
    if (val && val !== key) el.textContent = val;
  });
  // Update hero title (contains HTML)
  const heroTitle = document.querySelector("h1");
  if (heroTitle && t("hero_title") !== "hero_title") heroTitle.innerHTML = t("hero_title");
  // Update sport chips
  document.querySelectorAll("[data-i18n-sport]").forEach((el) => {
    const sport = el.getAttribute("data-i18n-sport");
    const icon = el.textContent.trim().split(" ")[0];
    el.textContent = icon + " " + SPORT_NAME(sport);
  });
  // Update language toggle button
  const btn = document.getElementById("lang-toggle");
  if (btn) btn.textContent = lang === "es" ? "EN" : "ES";
  // Update sport chips (they have emoji + text, handle separately)
  // Re-render picks if loaded
  if (typeof renderPlanBanner === "function") renderPlanBanner();
  // Re-render dynamic sections in the new language.
  if (typeof loadPicks === "function" && state && state.plan) loadPicks();
  if (typeof loadPlans === "function" && state && state.plans) loadPlans();
  // El registro público no depende de los planes: se repinta siempre.
  if (typeof loadPerformance === "function") { loadPerformance(); loadStats(); }
  if (typeof loadTelegram === "function" && state && state.plans) loadTelegram();
  if (typeof loadSubscription === "function" && state && state.plans) loadSubscription();
  // Update login dialog text based on mode
  updateLoginDialogText();
}

function updateLoginDialogText() {
  const title = document.getElementById("login-title");
  const help = document.getElementById("login-help");
  const toggle = document.getElementById("login-toggle");
  const submit = document.getElementById("login-submit");
  if (!title) return;
  if (loginMode === "register") {
    title.textContent = t("create_account_title");
    help.textContent = t("login_help_register");
    if (submit) submit.textContent = t("btn_register_submit");
    if (toggle) toggle.textContent = t("login_toggle_back");
  } else {
    title.textContent = t("login_title");
    help.textContent = t("login_help");
    if (submit) submit.textContent = t("btn_login_submit");
    if (toggle) toggle.textContent = t("login_toggle");
  }
}

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
                       hockey: "🏒",
                       formula1: "🏎️", motogp: "🏍️", horseracing: "🐎" }[s] || "🏅");
const SPORT_NAME_ES = { soccer: "Fútbol", basketball: "Básquet", tennis: "Tenis",
                     americanfootball: "Fútbol americano", boxing: "Boxeo",
                     baseball: "Béisbol", hockey: "Hockey",
                     formula1: "Fórmula 1",
                     motogp: "Motociclismo", horseracing: "Carreras de caballos" };
const SPORT_NAME_EN = { soccer: "Soccer", basketball: "Basketball", tennis: "Tennis",
                     americanfootball: "American Football", boxing: "Boxing",
                     baseball: "Baseball", hockey: "Hockey",
                     formula1: "Formula 1",
                     motogp: "MotoGP", horseracing: "Horse Racing" };
const SPORT_NAME = (s) => (currentLang === "en" ? SPORT_NAME_EN : SPORT_NAME_ES)[s] || s;
const when = (iso) => {
  try {
    return new Date(iso).toLocaleString(currentLang === "en" ? "en-US" : "es-MX",
      { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
  } catch { return iso || "por confirmar"; }
};
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const PENDING_KEY = "ae_pending_session";
let picksRequest = 0;
let subRequest = 0;

async function confirmPendingSession() {
  const sessionId = localStorage.getItem(PENDING_KEY);
  if (!sessionId) return false;
  try {
    const r = await api("/api/billing/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    if (r.token) localStorage.setItem("ae_token", r.token);
    if (r.plan === "premium") {
      localStorage.removeItem(PENDING_KEY);
      await refreshAccount();
      return true;
    }
  } catch { /* se reintenta más tarde */ }
  return false;
}

const SERVER_MSG_KEYS = {
  "Correo o contraseña incorrectos.": "wrong_creds",
  "La contraseña debe tener al menos 8 caracteres.": "short_pw",
  "Ya existe una cuenta con ese correo. Inicia sesión.": "already_exists",
  "Correo inválido.": "invalid_email",
  "Inicia sesión (o crea tu cuenta) antes de suscribirte.": "login_before_subscribe",
  "Te redirigimos a Stripe para completar el pago.": "redirect_stripe",
  "Cuenta Free creada. Inicia sesión para entrar.": "free_created",
  " Tu cuenta pasará a Premium al confirmarse el pago.": "premium_on_confirm",
  "Sesión cerrada.": "signed_out",
  "Esta cuenta aún no tiene una suscripción de Stripe que gestionar.": "no_subscription_to_manage",
  "Stripe aún no ha confirmado el pago.": "stripe_not_confirmed",
  "Sesión inválida.": "invalid_session",
  "✅ Listo.": "done_ok",
};
const serverMsg = (s) => (SERVER_MSG_KEYS[s] ? t(SERVER_MSG_KEYS[s]) : s);

async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  const token = localStorage.getItem("ae_token");
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const r = await fetch(path, { ...opts, headers, credentials: "same-origin" });
  if (!r.ok) {
    let body = {};
    try { body = await r.json(); } catch { /* sin cuerpo */ }
    const detail = body?.detail;
    const msg = serverMsg((detail && detail.message) || (typeof detail === "string" ? detail : `HTTP ${r.status}`));
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
      <div>${t("free_banner")}</div>
      <button class="btn primary" type="button" data-go="login">${t("free_banner_btn")}</button>`;
    box.querySelector("[data-go=login]").addEventListener("click", openLogin);
    return;
  }
  if (state.plan === "premium") {
    box.className = "plan-banner premium";
    box.innerHTML = `
      <div>✓ ${t("premium_banner")}</div>
      <button class="btn ghost" type="button" data-go="sub">${t("view_subscription")}</button>`;
  } else {
    box.className = "plan-banner free";
    box.innerHTML = `
      <div>${t("free_user_banner")}</div>
      <button class="btn primary" type="button" data-go="premium">${t("unlock_premium")}</button>`;
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
  btn.textContent = sel && sel.value === "premium" ? t("upgrading") : t("creating");
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
  try {
    const me = await api("/api/auth/me");
    if (me && me.authenticated) { applyAccount(me); return me; }
  } catch (err) {
    if (err.status === 401) localStorage.removeItem("ae_token");
  }
  applyAccount(null);
  return null;
}

async function afterAccountChange() {
  await Promise.all([loadPicks(), loadSubscription(), loadTelegram()]);
}

let loginMode = "login"; // "login" | "register"

async function doLogin(email, password) {
  const r = await api("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (r.token) localStorage.setItem("ae_token", r.token);
  applyAccount({ authenticated: true, email: r.email, plan: r.plan,
                  billing: r.demo ? "demo" : "stripe" });
  await afterAccountChange();
  return r;
}

async function doRegister(email, password) {
  const r = await api("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
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
  localStorage.removeItem(PENDING_KEY);
  applyAccount(null);
  await afterAccountChange();
}

/* ------------------------------------------------------------------ picks */
async function loadPicks() {
  const box = $("#picks-list");
  const requestId = ++picksRequest;
  box.innerHTML = '<p class="muted">' + t('picks_loading') + '</p>';
  const q = new URLSearchParams({ plan: state.plan, bankroll: state.bankroll, lang: currentLang });
  if (state.sport) q.set("sport", state.sport);
  try {
    const data = await api(`/api/recommendations?${q}`);
    if (requestId !== picksRequest) return;   // respuesta vieja: se descarta
    const label = data.plan === "premium" ? t("plan_title_premium") : t("plan_title_free");
    if (!data.picks.length) {
      $("#picks-sub").innerHTML =
        `<b>${label}</b> · ${t("min_edge_label")} ${pct(data.min_edge, 0)} · ` +
        `${data.models_scanned} ${t("matches_analyzed")} · ${data.value_candidates} ${t("with_value")}`;
      box.innerHTML = data.release_delay_seconds
        ? '<p class="muted">' + t('free_delay_empty') +
          ' <a href="/picks">' + t('nav_ledger') + ' →</a></p>'
        : '<p class="muted">' + t('no_picks_short') + ' ' +
          t('no_picks_detail') + '</p>';
      return;
    }
    $("#picks-sub").innerHTML =
      `<b>${label}</b> · Top ${data.count} · ${t("min_edge_label")} ${pct(data.min_edge, 0)} · ` +
      `${data.models_scanned} ${t("matches_analyzed")} · ${data.value_candidates} ${t("with_value")}`;
    box.innerHTML = data.picks.map(card).join("");
    $$(".why-btn").forEach((b) => b.addEventListener("click", () => {
      b.closest(".pick").classList.toggle("open");
      b.textContent = b.closest(".pick").classList.contains("open")
        ? t("hide_analysis") : t("why_trust");
    }));
  } catch (e) {
    if (requestId !== picksRequest) return;
    if (e.status === 402) {
      const needsLogin = !state.authenticated;
      box.innerHTML = `
        <div class="pick locked">
          <div class="pick-top"><div class="match">
            <span class="league">${t("premium_content")}</span>
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
    box.innerHTML = `<p class="muted">${t("load_error")} ${esc(e.message)}</p>`;
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
        <span class="time">🕐 ${esc(when(p.commence_time))} UTC · ${t("before_kickoff")}</span>
      </div>
      <div class="sel">${esc(p.selection_label)}<small>${p.odds ? `${t("odds_word")} ${num(p.odds)} · ${esc(p.bookmaker)}` : t('locked_odds_full')}</small></div>
      <div class="val"><label>${t("edge_label")}</label><b class="pos">${signed(p.edge)}</b>
        ${p.model_prob ? `<span class="badge edge">${t("model_label").toLowerCase()} ${pct(p.model_prob)}</span>` : ""}</div>
      <div class="val"><label>${t("ev_label")}</label><b class="pos">${signed(p.ev)}</b></div>
      <div class="val"><label>${t("confidence_label")}</label><b>${p.confidence ? pct(p.confidence, 0) : '🔒'}</b>
        ${p.confidence ? `<span class="conf"><i style="width:${Math.round(p.confidence * 100)}%"></i></span>` : `<span class="muted small">${t("premium_label")}</span>`}</div>
      ${p.delayed ? `<div class="delayed-badge">${t("delayed_badge")}</div>` : ""}
      <button class="why-btn" type="button">${t("why_trust")}</button>
    </div>
    <div class="pick-body">
      <div class="why-summary">${esc(p.explanation.summary)}</div>
      <ol class="steps">
        ${p.explanation.steps.map((s) => `
          <li><b>${esc(s.title)}</b><p>${esc(s.detail)}</p></li>`).join("")}
      </ol>
      ${locked ? `
      <div class="locked">🔒 ${esc(p.explanation.locked_note || t("locked_note"))}
        <a href="#precios">${t("unlock_analysis")}</a></div>` : `
      <div class="mini">
        <span>${t("kelly_full")}: <b>${num(k.kelly_full_pct)}%</b> → ${t("kelly_used")}
          <b>${num(k.kelly_fraction_used, 2)}×</b> con tope 3%</span>
        <span>${t("stake_suggested")}: <b>${num(k.stake_pct)}%</b> = <b>${num(k.stake_units)} u.</b></span>
        <span>${t("best_odds_among")} <b>${p.books_count}</b> ${t("houses")}</span>
        ${p.model_detail ? `<span>${t("model_label")}: <b>${esc(p.model_detail)}</b></span>` : ""}
      </div>
      ${p.backtest ? `<div class="mini">
        <span>${t("backtest_label")} ${p.backtest.bets} ${t("picks_word")}: ${t("roi_label")} <b>${spct(p.backtest.roi_pct)}</b></span>
        <span>${t("hit_rate_label")} <b>${num(p.backtest.hit_rate_pct, 1)}%</b> vs ${t("breakeven_label")}
          <b>${num(p.backtest.breakeven_hit_pct, 1)}%</b></span>
        <span>CLV <b>${spct(p.backtest.avg_clv_pct)}</b></span>
        <span>${t("drawdown_label")} <b>${num(p.backtest.max_drawdown_units)} u.</b></span>
        <span>p = <b>${num(p.backtest.binomial_p_value, 3)}</b></span>
      </div>` : ""}`}
      <div class="risks"><h4>${t("risks_title")}</h4>
        <ul>${p.explanation.risks.map((r) => `<li>${esc(r)}</li>`).join("")}</ul></div>
    </div>
  </article>`;
}

/* ------------------------------------------------------------ rendimiento */
function fill(template, vars) {
  let out = String(template);
  Object.entries(vars || {}).forEach(([k, v]) => {
    out = out.split(`{${k}}`).join(String(v));
  });
  return out;
}

function renderHero(s) {
  const set = (sel, text, cls) => {
    const el = $(sel);
    if (!el) return;
    el.textContent = text;
    el.classList.remove("pos", "neg");
    if (cls) el.classList.add(cls);
  };
  const roiOk = s.sample >= 30;
  const clvOk = s.clv_sample >= 30;
  set("#hs-roi", roiOk ? spct(s.roi_pct) : "—",
      roiOk ? (s.roi_pct >= 0 ? "pos" : "neg") : "");
  set("#hs-clv", clvOk ? spct(s.avg_clv_pct) : "—",
      clvOk ? (s.avg_clv_pct >= 0 ? "pos" : "neg") : "");
  set("#hs-dd", s.sample ? `${num(s.max_drawdown_units)} u.` : "—", "");
  set("#hs-losses", String(s.losses || 0), "neg");
  set("#hs-bets", String(s.picks_total || 0), "");
  const sub = (sel, text) => { const el = $(sel); if (el) el.textContent = text; };
  sub("#hs-roi-sub", roiOk ? t("roi_sub") : fill(t("hero_insufficient"), { n: s.sample }));
  sub("#hs-clv-sub", clvOk ? t("entry_vs_close")
      : fill(t("hero_insufficient"), { n: s.clv_sample || 0 }));
  sub("#hs-dd-sub", s.sample ? t("drawdown_sub") : t("no_data"));
  sub("#hs-losses-sub", fill(t("sub_wins"), { n: s.wins || 0 }));
  sub("#hs-bets-sub", fill(t("sub_closed"), { n: s.sample || 0 }));
}

async function loadStats() {
  try {
    const [s, health] = await Promise.all([
      api("/api/ledger/summary"), api("/api/health")]);
    renderHero(s);
    const src = health.source;
    const note = src === "live" ? t("live_odds")
      : src === "live_cached" ? t("live_cached")
      : src === "unavailable" ? t("no_live_data")
      : t("demo_mode");
    let ledger;
    if (!s.picks_total) ledger = t("ledger_open_zero");
    else if (s.sample < 30) ledger = fill(t("ledger_small"), {
      total: s.picks_total, n: s.sample,
    });
    else ledger = fill(t("ledger_ok"), { n: s.sample });
    $("#source-note").textContent =
      `${ledger} · ${note} · ${health.matches} ${t("matches_on_radar")}`;
  } catch { /* silencioso: el hero sigue siendo legible */ }
}

async function loadPerformance() {
  try {
    const [s, by] = await Promise.all([
      api("/api/ledger/summary"), api("/api/ledger/leagues")]);
    const roiOk = s.sample >= 30;
    const clvOk = s.clv_sample >= 30;
    const insufficient = fill(t("hero_insufficient"), { n: s.sample });
    const smallClv = fill(t("hero_insufficient"), { n: s.clv_sample || 0 });
    $("#metrics").innerHTML = [
      ["ROI / yield", roiOk ? spct(s.roi_pct) : "—",
        roiOk ? t("roi_sub") : insufficient],
      [t("hit_rate_table"), roiOk ? num(s.hit_rate_pct, 1) + "%" : "—",
        `${t("breakeven_table")} ${roiOk ? num(s.breakeven_hit_pct, 1) + "%" : "—"}`],
      [t("clv_avg"), clvOk ? spct(s.avg_clv_pct) : "—",
        clvOk ? t("entry_vs_close") : smallClv],
      [t("drawdown_label"), s.sample ? num(s.max_drawdown_units) + " u." : "—",
        t("drawdown_sub")],
      [t("hero_losses"), String(s.losses || 0),
        fill(t("sub_wins"), { n: s.wins || 0 })],
      [t("hero_bets"), String(s.picks_total || 0),
        fill(t("sub_closed"), { n: s.sample || 0 })],
      ["Test binomial", roiOk ? "p = " + num(s.binomial_p_value, 3) : "—",
        roiOk ? (s.binomial_p_value < 0.05 ? t("signif_yes") : t("signif_no")) : t("no_data")],
      [t("avg_odds_label"), s.sample ? num(s.avg_odds) : "—", t("avg_odds_sub")],
    ].map(([label, value, note]) =>
      `<div class="metric"><b>${value}</b><label>${label}</label><small>${note}</small></div>`).join("");
    drawEquity(s.equity_curve || []);

    const leagues = Object.entries(by.leagues || {});
    const significant = leagues.filter(([, row]) => row.significant);
    const best = significant.length
      ? significant.reduce((a, b) => (b[1].avg_clv_pct > a[1].avg_clv_pct ? b : a))[0]
      : null;
    const rows = leagues.map(([league, row]) => {
      const ok = row.sample >= 30;
      const star = league === best ? ' <span class="badge edge" title="mejor liga">★</span>' : "";
      return `<tr><td>${esc(league)}${star}</td><td>${row.picks}</td>
        <td>${ok ? num(row.hit_rate_pct, 1) + "%" : "—"}</td>
        <td class="${ok ? (row.roi_pct >= 0 ? "pos" : "neg") : ""}">${ok ? spct(row.roi_pct) : "—"}</td>
        <td class="${ok ? (row.avg_clv_pct >= 0 ? "pos" : "neg") : ""}">${ok ? spct(row.avg_clv_pct) : "—"}</td>
        <td>${ok ? num(row.binomial_p_value, 3) : "—"}</td></tr>`;
    }).join("");
    $("#sport-table tbody").innerHTML = rows ||
      `<tr><td colspan="6">${t("equity_empty")}</td></tr>`;
  } catch { /* la sección queda con su mensaje de carga */ }
}

function drawEquity(curve) {
  if (!curve || !curve.length) {
    $("#equity").innerHTML = `<p class="muted">${t("equity_empty")}</p>`;
    return;
  }
  const w = 560, h = 170, pad = 12;
  const min = Math.min(0, ...curve), max = Math.max(0, ...curve);
  const span = max - min || 1;
  const x = (i) => pad + (i / Math.max(curve.length - 1, 1)) * (w - 2 * pad);
  const y = (v) => h - pad - ((v - min) / span) * (h - 2 * pad);
  const pts = curve.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const zero = y(0).toFixed(1);
  const last = curve[curve.length - 1];
  $("#equity").innerHTML = `
    <svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" role="img" aria-label="Equity curve">
      <line x1="${pad}" y1="${zero}" x2="${w - pad}" y2="${zero}"
            stroke="#3a4a6d" stroke-dasharray="4 4"/>
      <polyline points="${pts}" fill="none" stroke="#38e07b" stroke-width="2.5"
                stroke-linejoin="round" stroke-linecap="round"/>
    </svg>
    <p class="footnote">${t("equity_close")}: <b class="${last >= 0 ? "pos" : "neg"}">${last >= 0 ? "+" : ""}${num(last)} ${t("units_word")}</b>
      ${t("equity_stakes")}</p>`;
}

/* ---------------------------------------------------------------- planes */
async function loadPlans() {
  try {
    const { plans } = await api(`/api/plans?lang=${currentLang}`);
    state.plans = plans;
    renderPlans();
  } catch { /* ignora */ }
}

function ctaFor(key) {
  if (state.authenticated && state.plan === key) {
    return { label: "Tu plan actual", disabled: true };
  }
  if (state.authenticated && state.plan === "premium" && key === "free") {
    return { label: t("included_premium"), disabled: true };
  }
  if (key === "premium") {
    return { label: state.authenticated ? t("go_premium") : t("start_premium"),
             disabled: false };
  }
  return { label: state.authenticated ? t("plan_free_label") : t("start_free"),
           disabled: false };
}

function renderPlans() {
  if (!state.plans) return;
  $("#plans").innerHTML = Object.entries(state.plans).map(([key, p]) => {
    const cta = ctaFor(key);
    return `
      <div class="plan ${key === "premium" ? "featured" : ""}">
        ${key === "premium" ? `<span class="tag">${t("most_popular")}</span>` : ""}
        <h3>${esc(p.name)}</h3>
        <div class="price">${p.price_usd === 0 ? t("free_price") : "$" + p.price_usd}
          <small>${p.price_usd === 0 ? t("forever") : t("per_month")}</small></div>
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
$("#lang-toggle").addEventListener("click", () => applyLang(currentLang === "es" ? "en" : "es"));
$("#btn-login").addEventListener("click", openLogin);
$("#btn-logout").addEventListener("click", logout);
$("#login-cancel").addEventListener("click", closeLogin);
$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msg = $("#login-msg");
  const email = ($("#login-email").value || "").trim();
  const password = $("#login-password").value || "";
  if (!email || !password) return;
  msg.textContent = loginMode === "register" ? "Creando cuenta…" : "Entrando…";
  try {
    const r = loginMode === "register"
      ? await doRegister(email, password)
      : await doLogin(email, password);
    closeLogin();
    msg.textContent = "";
    if (r.plan === "premium") {
      showActivation(t("signed_in_premium"), "ok", 3500);
    }
  } catch (err) {
    msg.textContent = `⚠️ ${err.message}`;
  }
});

$("#login-toggle").addEventListener("click", (e) => {
  e.preventDefault();
  loginMode = loginMode === "login" ? "register" : "login";
  const title = $("#login-title");
  const help = $("#login-help");
  const submit = $("#login-submit");
  const toggle = $("#login-toggle");
  if (loginMode === "register") {
    title.textContent = t("create_account_title");
    help.textContent = t("login_help_register");
    submit.textContent = t("btn_register_submit");
    toggle.textContent = t("login_toggle_back");
  } else {
    title.textContent = t("login_title");
    help.textContent = t("login_help");
    submit.textContent = "Entrar";
    toggle.textContent = t("login_toggle");
  }
  $("#login-msg").textContent = "";
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
    msg.textContent = serverMsg(r.message) || t("done_ok");
    await refreshAccount();
    await afterAccountChange();
    if (r.plan === "premium" || r.activated) {
      showActivation(t("premium_activated_short"), "ok", 4500);
    }
  } catch (err) { msg.textContent = `⚠️ ${err.message}`; }
});

/* ------------------------------------------------------- alertas Telegram */
async function loadTelegram() {
  const box = $("#tg-body");
  if (!box) return;
  const panel = $("#tg-panel");
  try {
    const tg = await api("/api/telegram");
    if (!tg.configured) {
      // Sin bot configurado no se anuncia la función: un beneficio que no
      // existe no se muestra como "próximamente".
      if (panel) panel.hidden = true;
      const benefit = $("#benefit-telegram");
      if (benefit) benefit.hidden = true;
      return;
    }
    if (panel) panel.hidden = false;
    const benefit = $("#benefit-telegram");
    if (benefit) benefit.hidden = false;
    if (tg.linked) {
      box.innerHTML = `✅ <b>${t("tg_linked")}</b> · ${t("plan_word")} <b>${esc(tg.plan)}</b> · ${t("tg_receive")} ` +
        `${t("tg_min_edge")} ≥ ${pct(tg.min_edge, 0)} ${t("tg_every")} ${Math.round(tg.interval_seconds / 60)} min ` +
        `${t("tg_no_repeat")}`;
      return;
    }
    if (tg.authenticated && tg.deep_link) {
      box.innerHTML = `🔗 ${t("tg_link_one_click")} ` +
        `<a href="${esc(tg.deep_link)}" target="_blank" rel="noopener">${t("tg_open_bot")} @${esc(tg.bot_username)} ${t("tg_in_telegram")}</a> ` +
        `${t("tg_or_send")} <code>/start ${esc(tg.link_code)}</code> ${t("tg_inside_bot")}.`;
      return;
    }
    box.innerHTML = t("tg_login_first");
  } catch {
    box.textContent = t("tg_load_error");
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
    await confirmPendingSession();
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
      box.innerHTML = `${t("demo_mode_short")} <b>${esc(s.plan)}</b> ` +
        t("no_charges");
      btn.hidden = true;
      return;
    }
    if (s.plan === "premium") {
      let txt = "✅ <b>" + t("premium_active") + "</b>";
      if (s.current_period_end) {
        const fecha = new Date(s.current_period_end).toLocaleDateString(currentLang === "en" ? "en-US" : "es-MX");
        txt += s.cancel_at_period_end
          ? ` · ${t("cancels_on")} <b>${fecha}</b>`
          : ` · ${t("renews_on")} <b>${fecha}</b>`;
      }
      box.innerHTML = txt;
    } else {
      box.innerHTML = t("sub_free_note");
    }
    btn.hidden = !s.can_manage;
    if (!s.can_manage && s.plan === "premium") {
      box.innerHTML += '<br><small class="muted">' + t("payment_registered") + '</small>';
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
  if (sessionId) localStorage.setItem(PENDING_KEY, sessionId);
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
      if (activated) localStorage.removeItem(PENDING_KEY);
      if (!activated) {
        showActivation(t("stripe_processing"));
      }
    } catch (err) {
      showActivation(`${t("verify_failed")} ${esc(err.message)}. ${t("retrying")}`, "error");
    }
  }

  for (let i = 0; i < 15 && !activated; i++) {
    await sleep(2500);
    const me = await refreshAccount();
    if (me && me.plan === "premium") { activated = true; break; }
  }

  if (activated) {
    localStorage.removeItem(PENDING_KEY);
    await refreshAccount();
    showActivation(t("premium_activated_long"), "ok", 8000);
  } else {
    showActivation(t("payment_maybe") +
      t("payment_maybe_tail"), "error");
  }
  history.replaceState(null, "", location.pathname + "#picks");
  await Promise.all([loadPicks(), loadSubscription()]);
}

/* --------------------------------------------------------------- boot */
async function init() {
  applyLang(currentLang);
  await loadPlans();
  await refreshAccount();
  if (localStorage.getItem(PENDING_KEY) &&
      !new URLSearchParams(location.search).get("suscripcion")) {
    await confirmPendingSession();
  }
  await Promise.all([
    loadPicks(), loadStats(), loadPerformance(), loadTelegram(), loadSubscription()]);
  await handleStripeReturn();
}

init();
