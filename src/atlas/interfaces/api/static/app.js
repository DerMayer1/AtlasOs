const state = {
  apiKey: sessionStorage.getItem("atlas_api_key") || "",
  connectionMode: sessionStorage.getItem("atlas_connection_mode") || "api-key",
  currentJobId: sessionStorage.getItem("atlas_current_job") || null,
  currentResult: null,
  macroJobId: sessionStorage.getItem("atlas_macro_job") || null,
  macroData: null,
  companies: [
    {
      name: "Alpha Industrials",
      sector: "industrials",
      ebitda: 120,
      multiple: 8,
      carrying_value: 900,
      ebitda_volatility: 0.3,
      multiple_floor: 4.4,
      multiple_ceiling: 10,
      macro_sensitivity: 1,
      sector_sensitivity: 1,
      multiple_volatility: 0.18,
      debt: 420,
      cash: 90,
      debt_due_1y: 80,
      interest_rate: 0.08,
    },
    {
      name: "Beta Logistics",
      sector: "logistics",
      ebitda: 60,
      multiple: 6.5,
      carrying_value: 450,
      ebitda_volatility: 0.38,
      multiple_floor: 3.6,
      multiple_ceiling: 8.1,
      macro_sensitivity: 1.15,
      sector_sensitivity: 1.2,
      multiple_volatility: 0.22,
      debt: 310,
      cash: 35,
      debt_due_1y: 95,
      interest_rate: 0.09,
    },
    {
      name: "Gamma Health",
      sector: "healthcare",
      ebitda: 200,
      multiple: 11,
      carrying_value: 2400,
      ebitda_volatility: 0.22,
      multiple_floor: 7,
      multiple_ceiling: 13.5,
      macro_sensitivity: 0.75,
      sector_sensitivity: 0.8,
      multiple_volatility: 0.14,
      debt: 650,
      cash: 180,
      debt_due_1y: 70,
      interest_rate: 0.065,
    },
  ],
};

const elements = {
  body: document.body,
  form: document.querySelector("#portfolio-form"),
  companyRows: document.querySelector("#company-rows"),
  portfolioName: document.querySelector("#portfolio-name"),
  nSims: document.querySelector("#n-sims"),
  seed: document.querySelector("#seed"),
  addCompany: document.querySelector("#add-company"),
  clearForm: document.querySelector("#clear-form"),
  runAnalysis: document.querySelector("#run-analysis"),
  refreshAnalysis: document.querySelector("#refresh-analysis"),
  emptyState: document.querySelector("#empty-state"),
  results: document.querySelector("#results"),
  notice: document.querySelector("#notice"),
  systemMessage: document.querySelector("#system-message"),
  keyDialog: document.querySelector("#key-dialog"),
  keyForm: document.querySelector("#key-form"),
  apiKeyInput: document.querySelector("#api-key"),
  configureKey: document.querySelector("#configure-key"),
  cancelKey: document.querySelector("#cancel-key"),
  connectionDot: document.querySelector("#connection-dot"),
  connectionLabel: document.querySelector("#connection-label"),
  connectionDetail: document.querySelector("#connection-detail"),
  copyCitation: document.querySelector("#copy-citation"),
  refreshHistory: document.querySelector("#refresh-history"),
  historyList: document.querySelector("#history-list"),
  navItems: document.querySelectorAll("[data-page]"),
  pageTitle: document.querySelector("#page-title"),
  pageSubtitle: document.querySelector("#page-subtitle"),
  impairmentPage: document.querySelector("#impairment"),
  macroPage: document.querySelector("#macro-monitor"),
  runMacroMonitor: document.querySelector("#run-macro-monitor"),
  macroEmptyState: document.querySelector("#macro-empty-state"),
  macroResults: document.querySelector("#macro-results"),
  macroHistoryList: document.querySelector("#macro-history-list"),
  refreshMacroHistory: document.querySelector("#refresh-macro-history"),
  macroIndicatorSelect: document.querySelector("#macro-indicator-select"),
};

const PAGE_COPY = {
  impairment: {
    title: "Impairment analysis",
    subtitle: "Deterministic macro-financial portfolio stress analysis.",
  },
  "macro-monitor": {
    title: "Macro Monitor",
    subtitle: "Current regimes, stress signals and transparent reference scenarios.",
  },
};

const INDICATOR_LABELS = {
  fed_funds: "Fed funds",
  baa_aaa_spread: "BAA–AAA spread",
  t10y2y: "10Y–2Y curve",
  cpi_yoy: "CPI YoY",
  unemployment: "Unemployment",
  vix: "VIX",
};

function escapeText(value) {
  return String(value ?? "");
}

function renderCompanies() {
  elements.companyRows.replaceChildren();
  state.companies.forEach((company, index) => {
    const entry = document.createElement("article");
    entry.className = "company-entry";
    const row = document.createElement("div");
    row.className = "company-row";
    row.dataset.index = String(index);

    const fields = [
      ["name", "text", company.name, "Company name"],
      ["ebitda", "number", company.ebitda, "EBITDA"],
      ["multiple", "number", company.multiple, "Multiple"],
      ["carrying_value", "number", company.carrying_value, "Carrying value"],
    ];

    fields.forEach(([key, type, value, label]) => {
      const input = document.createElement("input");
      input.type = type;
      input.value = escapeText(value);
      input.setAttribute("aria-label", `${label} for company ${index + 1}`);
      if (type === "number") {
        input.min = "0.01";
        input.step = "0.01";
      }
      input.addEventListener("input", () => {
        state.companies[index][key] =
          type === "number" ? Number(input.value) : input.value;
      });
      row.append(input);
    });

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "remove-company";
    remove.setAttribute("aria-label", `Remove ${company.name || `company ${index + 1}`}`);
    remove.textContent = "×";
    remove.addEventListener("click", () => {
      if (state.companies.length === 1) {
        showNotice("A portfolio must contain at least one company.", "error");
        return;
      }
      state.companies.splice(index, 1);
      renderCompanies();
    });
    row.append(remove);

    const advanced = document.createElement("details");
    advanced.className = "company-profile";
    const summary = document.createElement("summary");
    summary.textContent = "Financial risk profile";
    advanced.append(summary);

    const grid = document.createElement("div");
    grid.className = "company-profile-grid";
    const advancedFields = [
      ["sector", "text", "Sector", "e.g. industrials", null],
      ["ebitda_volatility", "number", "EBITDA volatility", "0.30", "0.01"],
      ["multiple_floor", "number", "Multiple floor", "4.0", "0.1"],
      ["multiple_ceiling", "number", "Multiple ceiling", "10.0", "0.1"],
      ["macro_sensitivity", "number", "Macro sensitivity", "1.0", "0.05"],
      ["sector_sensitivity", "number", "Sector sensitivity", "1.0", "0.05"],
      ["multiple_volatility", "number", "Multiple volatility", "0.18", "0.01"],
      ["debt", "number", "Gross debt", "0", "0.01"],
      ["cash", "number", "Cash", "0", "0.01"],
      ["debt_due_1y", "number", "Debt due in 1 year", "0", "0.01"],
      ["interest_rate", "number", "Interest rate", "0.08", "0.005"],
    ];
    advancedFields.forEach(([key, type, labelText, placeholder, step]) => {
      const label = document.createElement("label");
      label.className = "field";
      const caption = document.createElement("span");
      caption.textContent = labelText;
      const input = document.createElement("input");
      input.type = type;
      input.value = escapeText(company[key] ?? "");
      input.placeholder = placeholder;
      if (type === "number") {
        input.min = "0";
        input.step = step;
      }
      input.addEventListener("input", () => {
        state.companies[index][key] =
          type === "number" ? Number(input.value) : input.value;
      });
      label.append(caption, input);
      grid.append(label);
    });
    advanced.append(grid);
    entry.append(row, advanced);
    elements.companyRows.append(entry);
  });
}

function setConnectionState() {
  const connected = Boolean(state.apiKey);
  elements.connectionDot.classList.toggle("is-connected", connected);
  elements.connectionLabel.textContent = connected
    ? state.connectionMode === "local-demo"
      ? "Local demo ready"
      : "API key configured"
    : "API key required";
  elements.connectionDetail.textContent = connected
    ? state.connectionMode === "local-demo"
      ? "Synthetic snapshot · persisted runs"
      : `${location.origin}`
    : "Same-origin API";
  elements.configureKey.textContent = connected ? "Change" : "Configure";
  elements.systemMessage.textContent = connected
    ? "Ready to create a portfolio and run one analysis."
    : "Waiting for API configuration.";
}

function showNotice(message, kind = "") {
  elements.notice.textContent = message;
  elements.notice.className = `notice${kind ? ` is-${kind}` : ""}`;
}

function hideNotice() {
  elements.notice.className = "notice is-hidden";
  elements.notice.textContent = "";
}

function showPage(page) {
  const target = PAGE_COPY[page] ? page : "impairment";
  elements.impairmentPage.classList.toggle("is-hidden", target !== "impairment");
  elements.macroPage.classList.toggle("is-hidden", target !== "macro-monitor");
  elements.navItems.forEach((item) => {
    item.classList.toggle("is-active", item.dataset.page === target);
  });
  elements.pageTitle.textContent = PAGE_COPY[target].title;
  elements.pageSubtitle.textContent = PAGE_COPY[target].subtitle;
  document.title = `Atlas | ${PAGE_COPY[target].title}`;
}

function setLoading(loading, label = "Run analysis") {
  elements.body.classList.toggle("is-loading", loading);
  elements.runAnalysis.disabled = loading;
  elements.runAnalysis.lastChild.textContent = loading ? " Running…" : ` ${label}`;
}

function setMacroLoading(loading) {
  elements.runMacroMonitor.disabled = loading;
  elements.runMacroMonitor.lastChild.textContent = loading
    ? " Running…"
    : " Run monitor";
}

async function api(path, options = {}) {
  if (!state.apiKey) {
    openKeyDialog();
    throw new Error("Configure an API key before running an analysis.");
  }
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": state.apiKey,
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      // Keep the HTTP status when the response is not JSON.
    }
    throw new Error(message);
  }
  return response;
}

function validatePortfolio() {
  const invalid = state.companies.find(
    (company) =>
      !company.name.trim() ||
      company.ebitda <= 0 ||
      company.multiple <= 0 ||
      company.carrying_value <= 0,
  );
  if (invalid) {
    throw new Error("Every company needs a name and positive financial values.");
  }
}

async function runAnalysis(event) {
  event.preventDefault();
  hideNotice();
  try {
    validatePortfolio();
    setLoading(true);
    elements.systemMessage.textContent = "Creating portfolio…";

    const portfolioResponse = await api("/portfolios", {
      method: "POST",
      body: JSON.stringify({
        name: elements.portfolioName.value.trim(),
        companies: state.companies,
      }),
    });
    const portfolio = await portfolioResponse.json();

    elements.systemMessage.textContent = "Executing deterministic impairment engine…";
    const analysisResponse = await api("/analyses", {
      method: "POST",
      body: JSON.stringify({
        engine: "impairment",
        portfolio_id: portfolio.portfolio_id,
        params: {
          n_sims: Number(elements.nSims.value),
          seed: Number(elements.seed.value),
        },
      }),
    });
    const analysis = await analysisResponse.json();
    state.currentJobId = analysis.job_id;
    sessionStorage.setItem("atlas_current_job", state.currentJobId);
    await refreshAnalysis();
  } catch (error) {
    showNotice(error.message, "error");
    elements.systemMessage.textContent = "Analysis did not complete.";
  } finally {
    setLoading(false);
  }
}

async function runMacroMonitor() {
  hideNotice();
  try {
    setMacroLoading(true);
    elements.systemMessage.textContent = "Executing deterministic Macro Monitor…";
    const response = await api("/analyses", {
      method: "POST",
      body: JSON.stringify({ engine: "macro_monitor" }),
    });
    const analysis = await response.json();
    state.macroJobId = analysis.job_id;
    state.currentJobId = analysis.job_id;
    sessionStorage.setItem("atlas_macro_job", state.macroJobId);
    sessionStorage.setItem("atlas_current_job", state.currentJobId);
    await refreshAnalysis();
  } catch (error) {
    showNotice(error.message, "error");
    elements.systemMessage.textContent = "Macro Monitor did not complete.";
  } finally {
    setMacroLoading(false);
  }
}

async function refreshAnalysis() {
  if (!state.currentJobId) {
    return;
  }
  hideNotice();
  try {
    const response = await api(`/analyses/${state.currentJobId}`);
    const analysis = await response.json();
    if (analysis.status === "succeeded") {
      state.currentResult = analysis.result;
      if (analysis.engine === "macro_monitor") {
        state.macroJobId = analysis.job_id;
        sessionStorage.setItem("atlas_macro_job", state.macroJobId);
        await renderMacroResult(analysis);
        showPage("macro-monitor");
      } else {
        renderResult(analysis);
        showPage("impairment");
      }
      elements.refreshAnalysis.classList.add("is-hidden");
      elements.systemMessage.textContent =
        analysis.engine === "macro_monitor"
          ? "Macro state completed. Signals and scenarios are ready."
          : "Analysis completed. Evidence is ready.";
      showNotice(
        analysis.engine === "macro_monitor"
          ? "Macro Monitor completed successfully."
          : "Analysis completed successfully.",
        "success",
      );
      await loadHistory();
      return;
    }
    if (analysis.status === "failed") {
      throw new Error(analysis.error || "The analysis failed.");
    }
    elements.refreshAnalysis.classList.remove("is-hidden");
    elements.systemMessage.textContent = `Analysis is ${analysis.status}. Refresh when ready.`;
    showNotice(
      "The analysis is queued. Atlas does not poll automatically; use Refresh status.",
    );
    await loadHistory();
  } catch (error) {
    showNotice(error.message, "error");
    elements.systemMessage.textContent = "Could not refresh analysis status.";
  }
}

async function loadHistory({ quiet = false } = {}) {
  if (!state.apiKey) {
    renderHistory([]);
    return false;
  }
  try {
    const response = await api("/analyses?limit=10");
    const body = await response.json();
    renderHistory(body.analyses);
    return true;
  } catch (error) {
    if (!quiet) {
      elements.historyList.replaceChildren();
      const message = document.createElement("p");
      message.className = "history-empty";
      message.textContent = `Unable to load analysis history: ${error.message}`;
      elements.historyList.append(message);
    }
    return false;
  }
}

function renderHistory(analyses) {
  renderHistoryList(
    elements.historyList,
    analyses.filter((analysis) => analysis.engine === "impairment"),
    "impairment",
  );
  renderHistoryList(
    elements.macroHistoryList,
    analyses.filter((analysis) => analysis.engine === "macro_monitor"),
    "macro-monitor",
  );
}

function renderHistoryList(target, analyses, page) {
  target.replaceChildren();
  if (!analyses.length) {
    const empty = document.createElement("p");
    empty.className = "history-empty";
    empty.textContent = state.apiKey
      ? page === "macro-monitor"
        ? "No persisted macro runs yet."
        : "No persisted impairment analyses yet."
      : "Connect to Atlas to load persisted analyses.";
    target.append(empty);
    return;
  }

  analyses.forEach((analysis) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "history-item";
    item.addEventListener("click", async () => {
      state.currentJobId = analysis.job_id;
      sessionStorage.setItem("atlas_current_job", state.currentJobId);
      await refreshAnalysis();
      document.querySelector(`#${page}`).scrollIntoView({ behavior: "smooth" });
    });

    const main = document.createElement("span");
    main.className = "history-main";
    const name = document.createElement("strong");
    name.textContent =
      page === "macro-monitor"
        ? `${capitalize(analysis.macro_regime || "Macro")} state`
        : analysis.portfolio_name || analysis.job_id;
    const metadata = document.createElement("span");
    metadata.textContent = `${analysis.job_id} · ${analysis.status}`;
    main.append(name, metadata);

    const outcome = document.createElement("span");
    outcome.className =
      page === "macro-monitor" || analysis.portfolio_mean_p_impairment == null
        ? "history-risk history-status"
        : "history-risk";
    outcome.textContent =
      page === "macro-monitor"
        ? analysis.stress_index == null
          ? analysis.status
          : `Stress ${Number(analysis.stress_index).toFixed(2)}`
        : analysis.portfolio_mean_p_impairment == null
        ? analysis.status
        : percent(analysis.portfolio_mean_p_impairment);

    const date = document.createElement("span");
    date.className = "history-date";
    date.textContent = new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(analysis.created_at));

    item.append(main, outcome, date);
    target.append(item);
  });
}

function capitalize(value) {
  const text = String(value || "");
  return text ? text[0].toUpperCase() + text.slice(1) : "";
}

function percent(value) {
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function money(value) {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 1,
  }).format(Number(value));
}

function optionalMoney(value) {
  return value == null ? "—" : money(value);
}

function renderResult(analysis) {
  const result = analysis.result;
  elements.emptyState.classList.add("is-hidden");
  elements.results.classList.remove("is-hidden");

  document.querySelector("#portfolio-risk").textContent = percent(
    result.metrics.portfolio_mean_p_impairment,
  );
  document.querySelector("#portfolio-count").textContent =
    `${Math.round(result.metrics.n_companies)} companies · ${result.engine_version}`;
  document.querySelector("#analysis-id").textContent = analysis.job_id;
  document.querySelector("#snapshot-id").textContent = analysis.snapshot_id;
  document.querySelector("#model-version").textContent = result.model_version;
  document.querySelector("#analysis-status").textContent = analysis.status;
  document.querySelector("#expected-loss").textContent = optionalMoney(
    result.metrics.portfolio_expected_impairment_loss,
  );
  document.querySelector("#loss-p95").textContent = optionalMoney(
    result.metrics.portfolio_loss_p95,
  );

  renderRegimes(result.metrics);
  loadCompanyScores(analysis.job_id);
  if (result.artifacts.some((artifact) => artifact.name === "portfolio_scenarios.csv")) {
    loadPortfolioScenarios(analysis.job_id);
  } else {
    const rows = document.querySelector("#scenario-rows");
    rows.replaceChildren();
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 5;
    cell.textContent = "Scenario distributions are available from Engine 1.0 onward.";
    row.append(cell);
    rows.append(row);
  }
  renderArtifacts(result.artifacts, analysis.job_id);

  const citation =
    `[${analysis.job_id}/metrics.json:portfolio_mean_p_impairment]`;
  document.querySelector("#portfolio-citation").textContent = citation;
}

function renderRegimes(metrics) {
  const regimes = [
    ["expansion", metrics.p_regime_expansion],
    ["tightening", metrics.p_regime_tightening],
    ["crisis", metrics.p_regime_crisis],
  ];
  const list = document.querySelector("#regime-list");
  list.replaceChildren();
  regimes.forEach(([name, value]) => {
    const row = document.createElement("div");
    row.className = "regime-row";
    row.dataset.regime = name;

    const label = document.createElement("span");
    label.textContent = name[0].toUpperCase() + name.slice(1);
    const track = document.createElement("div");
    track.className = "regime-track";
    const fill = document.createElement("div");
    fill.className = "regime-fill";
    fill.style.width = `${Math.max(1, Number(value) * 100)}%`;
    track.append(fill);
    const amount = document.createElement("span");
    amount.className = "regime-value";
    amount.textContent = percent(value);
    row.append(label, track, amount);
    list.append(row);
  });
}

async function fetchArtifact(jobId, name, type = "text") {
  const response = await api(`/artifacts/${jobId}/${encodeURIComponent(name)}`, {
    headers: { Accept: type === "json" ? "application/json" : "text/csv" },
  });
  return type === "json" ? response.json() : response.text();
}

async function renderMacroResult(analysis) {
  const jobId = analysis.job_id;
  const [macroState, indicatorsCsv, regimesCsv, historyCsv, scenariosCsv] =
    await Promise.all([
      fetchArtifact(jobId, "macro_state.json", "json"),
      fetchArtifact(jobId, "indicator_snapshot.csv"),
      fetchArtifact(jobId, "regime_history.csv"),
      fetchArtifact(jobId, "macro_history.csv"),
      fetchArtifact(jobId, "scenario_assumptions.csv"),
    ]);

  state.macroData = {
    state: macroState,
    indicators: parseCsv(indicatorsCsv),
    regimes: parseCsv(regimesCsv),
    history: parseCsv(historyCsv),
    scenarios: parseCsv(scenariosCsv),
  };

  elements.macroEmptyState.classList.add("is-hidden");
  elements.macroResults.classList.remove("is-hidden");
  document.querySelector("#macro-current-regime").textContent = capitalize(
    macroState.regime.current,
  );
  document.querySelector("#macro-current-regime").dataset.regime =
    macroState.regime.current;
  document.querySelector("#macro-as-of").textContent = `As of ${formatPeriod(
    macroState.as_of,
  )}`;
  document.querySelector("#macro-confidence").textContent = percent(
    macroState.regime.confidence,
  );
  document.querySelector("#macro-stress").textContent =
    Number(macroState.stress.composite).toFixed(2);
  document.querySelector("#macro-stress-level").textContent = capitalize(
    macroState.stress.level,
  );
  document.querySelector("#macro-alert-count").textContent = String(
    macroState.alerts.length,
  );
  document.querySelector("#macro-stress-breadth").textContent =
    `${percent(macroState.stress.breadth)} of indicators elevated`;

  renderMacroRegimeComparison(macroState.regime);
  renderMacroAlerts(macroState.alerts);
  renderMacroIndicatorTable(state.macroData.indicators);
  renderMacroRegimeChart(state.macroData.regimes);
  configureIndicatorChart(state.macroData.history);
  renderMacroScenarios(state.macroData.scenarios);
}

function renderMacroRegimeComparison(regime) {
  const list = document.querySelector("#macro-regime-list");
  list.replaceChildren();
  ["expansion", "tightening", "crisis"].forEach((name) => {
    const current = Number(regime.probabilities[name]);
    const next = Number(regime.next_month_probabilities[name]);
    const row = document.createElement("article");
    row.className = "regime-comparison-row";
    row.dataset.regime = name;

    const heading = document.createElement("div");
    const label = document.createElement("strong");
    label.textContent = capitalize(name);
    const values = document.createElement("span");
    values.textContent = `${percent(current)} now · ${percent(next)} next month`;
    heading.append(label, values);

    const track = document.createElement("div");
    track.className = "dual-track";
    const currentBar = document.createElement("span");
    currentBar.className = "dual-track-current";
    currentBar.style.width = `${Math.max(1, current * 100)}%`;
    const nextMarker = document.createElement("i");
    nextMarker.style.left = `${Math.min(99, Math.max(1, next * 100))}%`;
    nextMarker.setAttribute("aria-hidden", "true");
    track.append(currentBar, nextMarker);
    row.append(heading, track);
    list.append(row);
  });
}

function renderMacroAlerts(alerts) {
  const list = document.querySelector("#macro-alert-list");
  list.replaceChildren();
  if (!alerts.length) {
    const empty = document.createElement("p");
    empty.className = "macro-no-alerts";
    empty.textContent = "No indicator crossed the configured alert thresholds.";
    list.append(empty);
    return;
  }
  alerts.forEach((alert) => {
    const item = document.createElement("article");
    item.className = `macro-alert is-${alert.severity}`;
    const marker = document.createElement("span");
    marker.className = "alert-marker";
    const body = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = INDICATOR_LABELS[alert.indicator] || alert.indicator;
    const reason = document.createElement("span");
    reason.textContent = `${capitalize(alert.reason)} · score ${Number(
      alert.score,
    ).toFixed(2)}`;
    body.append(title, reason);
    const severity = document.createElement("em");
    severity.textContent = capitalize(alert.severity);
    item.append(marker, body, severity);
    list.append(item);
  });
}

function renderMacroIndicatorTable(indicators) {
  const body = document.querySelector("#macro-indicator-rows");
  body.replaceChildren();
  indicators.forEach((indicator) => {
    const row = document.createElement("tr");
    const stress = Number(indicator.stress_score);
    const values = [
      INDICATOR_LABELS[indicator.indicator] || indicator.indicator,
      Number(indicator.current_value).toFixed(2),
      signed(indicator.change_short),
      stress.toFixed(2),
      percent(indicator.adverse_percentile),
    ];
    values.forEach((value, index) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      if (index === 3) {
        cell.className =
          stress >= 1.5
            ? "signal-value is-critical"
            : stress >= 0.75
              ? "signal-value is-elevated"
              : stress <= -0.75
                ? "signal-value is-supportive"
                : "signal-value";
      }
      row.append(cell);
    });
    body.append(row);
  });
}

function renderMacroRegimeChart(rows) {
  const latest = rows.slice(-60);
  renderLineChart(
    document.querySelector("#macro-regime-chart"),
    latest,
    [
      { key: "expansion", color: "#2f7d42" },
      { key: "tightening", color: "#8a6b2e" },
      { key: "crisis", color: "#b83a32" },
    ],
    { min: 0, max: 1, format: (value) => `${Math.round(value * 100)}%` },
  );
}

function configureIndicatorChart(rows) {
  const keys = Object.keys(rows[0] || {}).filter((key) => key !== "period");
  const previous = elements.macroIndicatorSelect.value;
  elements.macroIndicatorSelect.replaceChildren();
  keys.forEach((key) => {
    const option = document.createElement("option");
    option.value = key;
    option.textContent = INDICATOR_LABELS[key] || key;
    elements.macroIndicatorSelect.append(option);
  });
  elements.macroIndicatorSelect.value = keys.includes(previous)
    ? previous
    : keys[0] || "";
  renderMacroIndicatorChart(rows, elements.macroIndicatorSelect.value);
}

function renderMacroIndicatorChart(rows, key) {
  if (!key) return;
  renderLineChart(
    document.querySelector("#macro-indicator-chart"),
    rows.slice(-60),
    [{ key, color: "#303a48" }],
    { format: (value) => Number(value).toFixed(1) },
  );
}

function renderLineChart(container, rows, series, options = {}) {
  if (!rows.length) {
    container.textContent = "No historical observations available.";
    return;
  }
  const width = 720;
  const height = 260;
  const margin = { top: 18, right: 54, bottom: 32, left: 46 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const allValues = series.flatMap(({ key }) =>
    rows.map((row) => Number(row[key])).filter(Number.isFinite),
  );
  let min = options.min ?? Math.min(...allValues);
  let max = options.max ?? Math.max(...allValues);
  if (min === max) {
    min -= 1;
    max += 1;
  } else if (options.min == null || options.max == null) {
    const padding = (max - min) * 0.12;
    min = options.min ?? min - padding;
    max = options.max ?? max + padding;
  }
  const x = (index) =>
    margin.left + (index / Math.max(1, rows.length - 1)) * plotWidth;
  const y = (value) =>
    margin.top + (1 - (Number(value) - min) / (max - min)) * plotHeight;
  const format = options.format || ((value) => Number(value).toFixed(2));
  const grid = Array.from({ length: 5 }, (_, index) => {
    const value = min + ((max - min) * index) / 4;
    const py = y(value);
    return `<line x1="${margin.left}" y1="${py}" x2="${
      width - margin.right
    }" y2="${py}" class="chart-grid-line"/><text x="${
      margin.left - 8
    }" y="${py + 4}" text-anchor="end" class="chart-axis-label">${format(
      value,
    )}</text>`;
  }).join("");
  const lines = series
    .map(({ key, color }) => {
      const points = rows
        .map((row, index) => `${x(index)},${y(row[key])}`)
        .join(" ");
      const lastValue = Number(rows.at(-1)[key]);
      const lastY = y(lastValue);
      return `<polyline points="${points}" fill="none" stroke="${color}" class="chart-line"/><circle cx="${x(
        rows.length - 1,
      )}" cy="${lastY}" r="3.5" fill="${color}"/><text x="${
        width - margin.right + 8
      }" y="${lastY + 4}" class="chart-end-label" fill="${color}">${format(
        lastValue,
      )}</text>`;
    })
    .join("");
  const firstPeriod = formatPeriod(rows[0].period);
  const lastPeriod = formatPeriod(rows.at(-1).period);
  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Historical time-series chart from ${firstPeriod} to ${lastPeriod}">
      ${grid}
      <line x1="${margin.left}" y1="${height - margin.bottom}" x2="${
        width - margin.right
      }" y2="${height - margin.bottom}" class="chart-axis"/>
      ${lines}
      <text x="${margin.left}" y="${height - 8}" class="chart-axis-label">${firstPeriod}</text>
      <text x="${width - margin.right}" y="${
        height - 8
      }" text-anchor="end" class="chart-axis-label">${lastPeriod}</text>
    </svg>`;
}

function renderMacroScenarios(scenarios) {
  const container = document.querySelector("#macro-scenario-cards");
  container.replaceChildren();
  scenarios.forEach((scenario) => {
    const card = document.createElement("article");
    card.className = `scenario-card is-${scenario.scenario}`;
    const heading = document.createElement("div");
    const title = document.createElement("h3");
    title.textContent = capitalize(scenario.scenario);
    const sample = document.createElement("span");
    sample.textContent =
      scenario.scenario === "base"
        ? "Current snapshot"
        : `${Math.round(Number(scenario.sample_size))} historical months`;
    heading.append(title, sample);
    card.append(heading);

    Object.keys(INDICATOR_LABELS)
      .filter((indicator) => `${indicator}_level` in scenario)
      .forEach((indicator) => {
        const row = document.createElement("div");
        const label = document.createElement("span");
        label.textContent = INDICATOR_LABELS[indicator];
        const value = document.createElement("strong");
        const delta = Number(scenario[`${indicator}_delta`]);
        value.textContent = `${Number(
          scenario[`${indicator}_level`],
        ).toFixed(2)} · ${signed(delta)}`;
        row.append(label, value);
        card.append(row);
      });
    container.append(card);
  });
}

function signed(value) {
  const number = Number(value);
  return `${number > 0 ? "+" : ""}${number.toFixed(2)}`;
}

function formatPeriod(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

async function loadPortfolioScenarios(jobId) {
  const rows = document.querySelector("#scenario-rows");
  rows.replaceChildren();
  try {
    const response = await api(`/artifacts/${jobId}/portfolio_scenarios.csv`, {
      headers: { Accept: "text/csv" },
    });
    const csv = await response.text();
    parseCsv(csv).forEach((scenario) => {
      const [name, horizon] = scenario.case.split("|");
      const row = document.createElement("tr");
      const cells = [
        name[0].toUpperCase() + name.slice(1),
        horizon,
        percent(scenario.carrying_weighted_p_impairment),
        money(scenario.expected_impairment_loss),
        money(scenario.loss_p95),
      ];
      cells.forEach((value, index) => {
        const cell = document.createElement("td");
        cell.textContent = value;
        if (index === 2) {
          cell.className = "risk-value";
        }
        row.append(cell);
      });
      rows.append(row);
    });
  } catch (error) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 5;
    cell.textContent = `Unable to load scenarios: ${error.message}`;
    row.append(cell);
    rows.append(row);
  }
}

async function loadCompanyScores(jobId) {
  const rows = document.querySelector("#risk-rows");
  rows.replaceChildren();
  try {
    const response = await api(`/artifacts/${jobId}/impairment_scores.csv`, {
      headers: { Accept: "text/csv" },
    });
    const csv = await response.text();
    parseCsv(csv).forEach((score) => {
      const row = document.createElement("tr");
      const cells = [
        score.company,
        percent(score.p_impairment),
        money(score.recoverable_mean ?? score.ev_mean),
        `${money(score.recoverable_p05 ?? score.ev_p05)}–${money(
          score.recoverable_p95 ?? score.ev_p95,
        )}`,
      ];
      cells.forEach((value, index) => {
        const cell = document.createElement("td");
        cell.textContent = value;
        if (index === 1) {
          cell.className = "risk-value";
        }
        row.append(cell);
      });
      rows.append(row);
    });
  } catch (error) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 4;
    cell.textContent = `Unable to load company scores: ${error.message}`;
    row.append(cell);
    rows.append(row);
  }
}

function parseCsv(text) {
  const [headerLine, ...lines] = text.trim().split(/\r?\n/);
  const headers = headerLine.split(",");
  return lines.filter(Boolean).map((line) => {
    const values = line.split(",");
    return Object.fromEntries(headers.map((header, index) => [header, values[index]]));
  });
}

function renderArtifacts(artifacts, jobId) {
  const list = document.querySelector("#artifact-list");
  list.replaceChildren();
  artifacts.forEach((artifact) => {
    const item = document.createElement("article");
    item.className = "artifact";

    const info = document.createElement("div");
    const name = document.createElement("span");
    name.className = "artifact-name";
    name.textContent = artifact.name;
    const meta = document.createElement("span");
    meta.className = "artifact-meta";
    meta.textContent =
      `${formatBytes(artifact.size_bytes)} · SHA256 ${artifact.sha256.slice(0, 12)}…`;
    info.append(name, meta);

    const actions = document.createElement("div");
    actions.className = "artifact-actions";
    const open = document.createElement("button");
    open.type = "button";
    open.className = "text-button";
    open.textContent = "Open";
    open.addEventListener("click", () => openArtifact(jobId, artifact.name, false));
    const download = document.createElement("button");
    download.type = "button";
    download.className = "text-button";
    download.textContent = "Download";
    download.addEventListener("click", () => openArtifact(jobId, artifact.name, true));
    actions.append(open, download);
    item.append(info, actions);
    list.append(item);
  });
}

async function openArtifact(jobId, name, download) {
  try {
    const response = await api(`/artifacts/${jobId}/${encodeURIComponent(name)}`, {
      headers: { Accept: "*/*" },
    });
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    if (download) {
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = name;
      anchor.click();
    } else {
      window.open(url, "_blank", "noopener");
    }
    window.setTimeout(() => URL.revokeObjectURL(url), 30_000);
  } catch (error) {
    showNotice(error.message, "error");
  }
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function openKeyDialog() {
  elements.apiKeyInput.value = state.apiKey;
  elements.keyDialog.showModal();
  window.setTimeout(() => elements.apiKeyInput.focus(), 50);
}

elements.configureKey.addEventListener("click", openKeyDialog);
elements.cancelKey.addEventListener("click", () => elements.keyDialog.close());
elements.keyForm.addEventListener("submit", (event) => {
  event.preventDefault();
  state.apiKey = elements.apiKeyInput.value.trim();
  if (state.apiKey) {
    sessionStorage.setItem("atlas_api_key", state.apiKey);
    state.connectionMode = "api-key";
    sessionStorage.setItem("atlas_connection_mode", state.connectionMode);
  } else {
    sessionStorage.removeItem("atlas_api_key");
    sessionStorage.removeItem("atlas_connection_mode");
  }
  setConnectionState();
  elements.keyDialog.close();
  loadHistory();
});

elements.addCompany.addEventListener("click", () => {
  state.companies.push({
    name: "",
    sector: "general",
    ebitda: 100,
    multiple: 8,
    carrying_value: 800,
    ebitda_volatility: 0.3,
    multiple_floor: 4.4,
    multiple_ceiling: 10,
    macro_sensitivity: 1,
    sector_sensitivity: 1,
    multiple_volatility: 0.18,
    debt: 0,
    cash: 0,
    debt_due_1y: 0,
    interest_rate: 0.08,
  });
  renderCompanies();
});

elements.clearForm.addEventListener("click", () => {
  state.companies = [
    {
      name: "Alpha Industrials",
      sector: "industrials",
      ebitda: 120,
      multiple: 8,
      carrying_value: 900,
      ebitda_volatility: 0.3,
      multiple_floor: 4.4,
      multiple_ceiling: 10,
      macro_sensitivity: 1,
      sector_sensitivity: 1,
      multiple_volatility: 0.18,
      debt: 420,
      cash: 90,
      debt_due_1y: 80,
      interest_rate: 0.08,
    },
  ];
  elements.portfolioName.value = "Atlas Sample Portfolio";
  elements.nSims.value = "10000";
  elements.seed.value = "7";
  renderCompanies();
  hideNotice();
});

elements.form.addEventListener("submit", runAnalysis);
elements.runMacroMonitor.addEventListener("click", runMacroMonitor);
elements.refreshAnalysis.addEventListener("click", refreshAnalysis);
elements.refreshHistory.addEventListener("click", loadHistory);
elements.refreshMacroHistory.addEventListener("click", loadHistory);
elements.macroIndicatorSelect.addEventListener("change", () => {
  if (state.macroData) {
    renderMacroIndicatorChart(
      state.macroData.history,
      elements.macroIndicatorSelect.value,
    );
  }
});
elements.navItems.forEach((item) => {
  item.addEventListener("click", (event) => {
    const target = item.getAttribute("href");
    showPage(item.dataset.page);
    if (target === "#impairment" || target === "#macro-monitor") {
      event.preventDefault();
      history.pushState(null, "", target);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  });
});
window.addEventListener("hashchange", () => {
  showPage(location.hash === "#macro-monitor" ? "macro-monitor" : "impairment");
});
elements.copyCitation.addEventListener("click", async () => {
  const citation = document.querySelector("#portfolio-citation").textContent;
  try {
    await navigator.clipboard.writeText(citation);
    showNotice("Citation copied.", "success");
  } catch {
    showNotice("Clipboard access is unavailable. Select the citation manually.", "error");
  }
});

async function initialize() {
  renderCompanies();
  setConnectionState();
  const initialPage =
    location.hash === "#macro-monitor" ? "macro-monitor" : "impairment";
  showPage(initialPage);
  if (initialPage === "macro-monitor") {
    window.setTimeout(() => window.scrollTo({ top: 0 }), 0);
  }

  let historyLoaded = state.apiKey
    ? await loadHistory({ quiet: true })
    : false;

  if (!historyLoaded) {
    if (state.apiKey) {
      state.apiKey = "";
      state.connectionMode = "api-key";
      state.currentJobId = null;
      sessionStorage.removeItem("atlas_api_key");
      sessionStorage.removeItem("atlas_connection_mode");
      sessionStorage.removeItem("atlas_current_job");
      setConnectionState();
    }

    elements.systemMessage.textContent = "Preparing the local workspace…";
    try {
      const response = await fetch("/demo/bootstrap", { method: "POST" });
      if (response.ok) {
        const bootstrap = await response.json();
        state.apiKey = bootstrap.api_key;
        state.connectionMode = bootstrap.mode;
        sessionStorage.setItem("atlas_api_key", state.apiKey);
        sessionStorage.setItem("atlas_connection_mode", state.connectionMode);
        setConnectionState();
        showNotice(
          `Local workspace ready on snapshot ${bootstrap.snapshot_id}.`,
          "success",
        );
        historyLoaded = await loadHistory();
      } else if (response.status !== 404) {
        throw new Error(`${response.status} ${response.statusText}`);
      }
    } catch (error) {
      showNotice(`Local bootstrap failed: ${error.message}`, "error");
    }
  }

  if (!historyLoaded) {
    renderHistory([]);
    elements.systemMessage.textContent = "Waiting for API configuration.";
  }
  if (state.currentJobId) {
    await refreshAnalysis();
  }
}

initialize();
