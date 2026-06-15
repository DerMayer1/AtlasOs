const state = {
  apiKey: sessionStorage.getItem("atlas_api_key") || "",
  connectionMode: sessionStorage.getItem("atlas_connection_mode") || "api-key",
  currentJobId: sessionStorage.getItem("atlas_current_job") || null,
  currentResult: null,
  macroJobId: sessionStorage.getItem("atlas_macro_job") || null,
  macroData: null,
  portfolios: [],
  selectedPortfolioId: sessionStorage.getItem("atlas_portfolio_id") || null,
  selectedPortfolio: null,
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
  savePortfolio: document.querySelector("#save-portfolio"),
  portfolioVersionContext: document.querySelector("#portfolio-version-context"),
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
  buildReport: document.querySelector("#build-report"),
  reportEmpty: document.querySelector("#report-empty"),
  reportBody: document.querySelector("#report-body"),
  reportHeadline: document.querySelector("#report-headline"),
  reportFigures: document.querySelector("#report-figures"),
  reportDrivers: document.querySelector("#report-drivers"),
  reportActions: document.querySelector("#report-actions"),
  refreshHistory: document.querySelector("#refresh-history"),
  historyList: document.querySelector("#history-list"),
  navItems: document.querySelectorAll("[data-page]"),
  pageTitle: document.querySelector("#page-title"),
  pageSubtitle: document.querySelector("#page-subtitle"),
  overviewPage: document.querySelector("#overview"),
  overviewMacroRegime: document.querySelector("#overview-macro-regime"),
  overviewMacroMeta: document.querySelector("#overview-macro-meta"),
  overviewMacroCard: document.querySelector("#overview-macro-card"),
  overviewPortfolioCount: document.querySelector("#overview-portfolio-count"),
  overviewPortfolioRisk: document.querySelector("#overview-portfolio-risk"),
  overviewDecisionCount: document.querySelector("#overview-decision-count"),
  overviewDecisionMeta: document.querySelector("#overview-decision-meta"),
  overviewDecisionsCard: document.querySelector("#overview-decisions-card"),
  overviewActivityValue: document.querySelector("#overview-activity-value"),
  overviewActivityMeta: document.querySelector("#overview-activity-meta"),
  overviewDecisionList: document.querySelector("#overview-decision-list"),
  overviewRefresh: document.querySelector("#overview-refresh"),
  overviewShortcuts: document.querySelectorAll(".overview-shortcut"),
  impairmentPage: document.querySelector("#impairment"),
  portfoliosPage: document.querySelector("#portfolios"),
  macroPage: document.querySelector("#macro-monitor"),
  askPage: document.querySelector("#ask"),
  askForm: document.querySelector("#ask-form"),
  askQuestion: document.querySelector("#ask-question"),
  askPortfolio: document.querySelector("#ask-portfolio"),
  askSubmit: document.querySelector("#ask-submit"),
  askExamples: document.querySelector("#ask-examples"),
  askEmptyState: document.querySelector("#ask-empty-state"),
  askAnswer: document.querySelector("#ask-answer"),
  askBanner: document.querySelector("#ask-banner"),
  askNarrative: document.querySelector("#ask-narrative"),
  askMeta: document.querySelector("#ask-meta"),
  askPlan: document.querySelector("#ask-plan"),
  askCitations: document.querySelector("#ask-citations"),
  portfolioList: document.querySelector("#portfolio-list"),
  portfolioDetailEmpty: document.querySelector("#portfolio-detail-empty"),
  portfolioDetailContent: document.querySelector("#portfolio-detail-content"),
  portfolioDetailName: document.querySelector("#portfolio-detail-name"),
  portfolioDetailVersion: document.querySelector("#portfolio-detail-version"),
  portfolioDetailMeta: document.querySelector("#portfolio-detail-meta"),
  portfolioCompanyList: document.querySelector("#portfolio-company-list"),
  portfolioVersionList: document.querySelector("#portfolio-version-list"),
  refreshPortfolios: document.querySelector("#refresh-portfolios"),
  newPortfolio: document.querySelector("#new-portfolio"),
  usePortfolio: document.querySelector("#use-portfolio"),
  runMacroMonitor: document.querySelector("#run-macro-monitor"),
  macroEmptyState: document.querySelector("#macro-empty-state"),
  macroResults: document.querySelector("#macro-results"),
  macroHistoryList: document.querySelector("#macro-history-list"),
  refreshMacroHistory: document.querySelector("#refresh-macro-history"),
  macroIndicatorSelect: document.querySelector("#macro-indicator-select"),
};

const PAGE_COPY = {
  overview: {
    title: "Overview",
    subtitle: "Macro state, portfolio risk and decisions that need attention.",
  },
  impairment: {
    title: "Impairment analysis",
    subtitle: "Deterministic macro-financial portfolio stress analysis.",
  },
  portfolios: {
    title: "Portfolios",
    subtitle: "Versioned financial inputs and reproducible analysis context.",
  },
  "macro-monitor": {
    title: "Macro Monitor",
    subtitle: "Current regimes, stress signals and transparent reference scenarios.",
  },
  ask: {
    title: "Ask Atlas",
    subtitle: "Institutional questions answered from cited numbers, never from the LLM.",
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
  const target = PAGE_COPY[page] ? page : "overview";
  elements.overviewPage.classList.toggle("is-hidden", target !== "overview");
  elements.impairmentPage.classList.toggle("is-hidden", target !== "impairment");
  elements.portfoliosPage.classList.toggle("is-hidden", target !== "portfolios");
  elements.macroPage.classList.toggle("is-hidden", target !== "macro-monitor");
  elements.askPage.classList.toggle("is-hidden", target !== "ask");
  if (target === "ask") {
    populateAskPortfolios();
  }
  if (target === "overview") {
    loadOverview();
  }
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

function portfolioPayload() {
  return {
    name: elements.portfolioName.value.trim(),
    companies: state.companies,
  };
}

function setPortfolioContext(portfolio = null) {
  state.selectedPortfolio = portfolio;
  state.selectedPortfolioId = portfolio?.portfolio_id || null;
  if (state.selectedPortfolioId) {
    sessionStorage.setItem("atlas_portfolio_id", state.selectedPortfolioId);
  } else {
    sessionStorage.removeItem("atlas_portfolio_id");
  }
  elements.portfolioVersionContext.textContent = portfolio
    ? `${portfolio.portfolio_id} · version ${portfolio.version_number || "legacy"}`
    : "New unsaved portfolio";
}

async function persistPortfolio({ quiet = false } = {}) {
  validatePortfolio();
  const payload = portfolioPayload();
  if (!payload.name) {
    throw new Error("Portfolio name is required.");
  }
  const path = state.selectedPortfolioId
    ? `/portfolios/${state.selectedPortfolioId}`
    : "/portfolios";
  const response = await api(path, {
    method: state.selectedPortfolioId ? "PUT" : "POST",
    body: JSON.stringify(payload),
  });
  const portfolio = await response.json();
  setPortfolioContext(portfolio);
  if (!quiet) {
    showNotice(
      portfolio.changed
        ? `Portfolio saved as version ${portfolio.version_number}.`
        : `Portfolio version ${portfolio.version_number} is already current.`,
      "success",
    );
  }
  await loadPortfolios({ quiet: true, selectId: portfolio.portfolio_id });
  return portfolio;
}

async function loadPortfolios({ quiet = false, selectId = null } = {}) {
  if (!state.apiKey) {
    renderPortfolioList([]);
    return false;
  }
  try {
    const response = await api("/portfolios?limit=100");
    const body = await response.json();
    state.portfolios = body.portfolios;
    renderPortfolioList(state.portfolios);
    const targetId =
      selectId ||
      (state.selectedPortfolioId &&
      state.portfolios.some((item) => item.portfolio_id === state.selectedPortfolioId)
        ? state.selectedPortfolioId
        : null);
    if (targetId) {
      await inspectPortfolio(targetId);
    } else if (!state.portfolios.length) {
      clearPortfolioDetail();
    }
    return true;
  } catch (error) {
    renderPortfolioList([]);
    if (!quiet) {
      showNotice(`Unable to load portfolios: ${error.message}`, "error");
    }
    return false;
  }
}

function renderPortfolioList(portfolios) {
  elements.portfolioList.replaceChildren();
  if (!portfolios.length) {
    const empty = document.createElement("p");
    empty.className = "history-empty";
    empty.textContent = state.apiKey
      ? "No saved portfolios yet."
      : "Connect to Atlas to load portfolios.";
    elements.portfolioList.append(empty);
    return;
  }
  portfolios.forEach((portfolio) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "portfolio-list-item";
    item.classList.toggle(
      "is-selected",
      portfolio.portfolio_id === state.selectedPortfolioId,
    );
    item.addEventListener("click", () => inspectPortfolio(portfolio.portfolio_id));

    const heading = document.createElement("span");
    const name = document.createElement("strong");
    name.textContent = portfolio.name;
    const id = document.createElement("small");
    id.textContent = portfolio.portfolio_id;
    heading.append(name, id);

    const metadata = document.createElement("span");
    metadata.className = "portfolio-list-meta";
    metadata.textContent = `${portfolio.company_count} companies · v${
      portfolio.version_number || "legacy"
    }`;
    item.append(heading, metadata);
    elements.portfolioList.append(item);
  });
}

async function inspectPortfolio(portfolioId) {
  try {
    const [portfolioResponse, versionsResponse] = await Promise.all([
      api(`/portfolios/${portfolioId}`),
      api(`/portfolios/${portfolioId}/versions`),
    ]);
    const portfolio = await portfolioResponse.json();
    const versions = (await versionsResponse.json()).versions;
    state.selectedPortfolio = portfolio;
    renderPortfolioDetail(portfolio, versions);
    renderPortfolioList(state.portfolios);
  } catch (error) {
    showNotice(`Unable to inspect portfolio: ${error.message}`, "error");
  }
}

function renderPortfolioDetail(portfolio, versions) {
  elements.portfolioDetailEmpty.classList.add("is-hidden");
  elements.portfolioDetailContent.classList.remove("is-hidden");
  elements.portfolioDetailName.textContent = portfolio.name;
  elements.portfolioDetailVersion.textContent = `Current version ${
    portfolio.version_number || "legacy"
  }`;
  elements.portfolioDetailMeta.textContent =
    `${portfolio.company_count} companies · updated ${formatDateTime(
      portfolio.updated_at,
    )}`;

  elements.portfolioCompanyList.replaceChildren();
  portfolio.companies.forEach((company) => {
    const row = document.createElement("tr");
    [
      company.name,
      company.sector,
      money(company.ebitda),
      Number(company.multiple).toFixed(2),
      money(company.carrying_value),
    ].forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    });
    elements.portfolioCompanyList.append(row);
  });

  elements.portfolioVersionList.replaceChildren();
  if (!versions.length) {
    const legacy = document.createElement("p");
    legacy.className = "history-empty";
    legacy.textContent = "Legacy portfolio. Its first version will be created when saved.";
    elements.portfolioVersionList.append(legacy);
  }
  versions.forEach((version) => {
    const item = document.createElement("article");
    item.className = "version-item";
    const label = document.createElement("strong");
    label.textContent = `Version ${version.version_number}`;
    const metadata = document.createElement("span");
    metadata.textContent = `${version.company_count} companies · ${formatDateTime(
      version.created_at,
    )}`;
    const hash = document.createElement("code");
    hash.textContent = version.input_hash.slice(0, 12);
    if (version.is_current) {
      item.classList.add("is-current");
      hash.textContent = `current · ${hash.textContent}`;
    }
    item.append(label, metadata, hash);
    elements.portfolioVersionList.append(item);
  });
}

function clearPortfolioDetail() {
  elements.portfolioDetailEmpty.classList.remove("is-hidden");
  elements.portfolioDetailContent.classList.add("is-hidden");
}

function loadPortfolioIntoAnalysis(portfolio) {
  elements.portfolioName.value = portfolio.name;
  state.companies = portfolio.companies.map((company) => ({ ...company }));
  setPortfolioContext(portfolio);
  renderCompanies();
  showPage("impairment");
  history.pushState(null, "", "#impairment");
  window.scrollTo({ top: 0, behavior: "smooth" });
  showNotice(
    `${portfolio.name} version ${portfolio.version_number || "legacy"} loaded.`,
    "success",
  );
}

function formatDateTime(value) {
  if (!value) return "unknown date";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

async function runAnalysis(event) {
  event.preventDefault();
  hideNotice();
  try {
    validatePortfolio();
    setLoading(true);
    elements.systemMessage.textContent = state.selectedPortfolioId
      ? "Confirming portfolio version…"
      : "Creating portfolio…";
    const portfolio = await persistPortfolio({ quiet: true });

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
  document.querySelector("#analysis-portfolio-version").textContent =
    analysis.portfolio_version_id || "legacy / inline";
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

  resetReport();
  loadReport(analysis.job_id);
}

function resetReport() {
  elements.reportBody.classList.add("is-hidden");
  elements.reportEmpty.classList.remove("is-hidden");
  elements.reportFigures.replaceChildren();
  elements.reportDrivers.replaceChildren();
  elements.reportActions.replaceChildren();
}

function formatFigure(value, format) {
  if (format === "ratio") return percent(value);
  if (format === "currency") return money(value);
  if (format === "count") return String(Math.round(Number(value)));
  return Number(value).toFixed(2);
}

function citationChip(runId, citation) {
  const chip = document.createElement("button");
  chip.type = "button";
  chip.className = "citation-chip";
  chip.textContent = `${citation.artifact}:${citation.locator}`;
  chip.title = "Open the artifact behind this number";
  chip.addEventListener("click", () => openArtifact(runId, citation.artifact, false));
  return chip;
}

function renderReportFigures(target, runId, figures) {
  target.replaceChildren();
  figures.forEach((figure) => {
    const item = document.createElement("li");
    item.className = `report-figure is-${figure.severity}`;
    const label = document.createElement("span");
    label.className = "report-figure-label";
    label.textContent = figure.label;
    const value = document.createElement("strong");
    value.className = "report-figure-value";
    value.textContent = formatFigure(figure.value, figure.format);
    item.append(label, value, citationChip(runId, figure.citation));
    target.append(item);
  });
}

function renderReport(report) {
  elements.reportEmpty.classList.add("is-hidden");
  elements.reportBody.classList.remove("is-hidden");
  elements.reportHeadline.textContent = report.headline;

  renderReportFigures(elements.reportFigures, report.run_id, report.key_figures);
  renderReportFigures(elements.reportDrivers, report.run_id, report.risk_drivers);

  elements.reportActions.replaceChildren();
  if (!report.actions.length) {
    const empty = document.createElement("li");
    empty.className = "report-action-empty";
    empty.textContent = "No actions flagged for this run.";
    elements.reportActions.append(empty);
    return;
  }
  report.actions.forEach((action) => {
    const item = document.createElement("li");
    item.className = `report-action is-${action.severity}`;

    const head = document.createElement("div");
    head.className = "report-action-head";
    const badge = document.createElement("span");
    badge.className = "report-action-severity";
    badge.textContent = capitalize(action.severity);
    const title = document.createElement("span");
    title.className = "report-action-title";
    title.textContent = action.title;
    head.append(badge, title);

    const rationale = document.createElement("p");
    rationale.className = "report-action-rationale";
    rationale.textContent = action.rationale;

    const cites = document.createElement("div");
    cites.className = "report-action-citations";
    action.citations.forEach((citation) =>
      cites.append(citationChip(report.run_id, citation)),
    );

    item.append(head, rationale, cites);
    elements.reportActions.append(item);
  });
}

async function loadReport(jobId) {
  try {
    const response = await api(`/analyses/${jobId}/report`);
    renderReport(await response.json());
  } catch {
    resetReport();
  }
}

async function buildReport() {
  if (!state.currentJobId) {
    return;
  }
  elements.buildReport.disabled = true;
  try {
    const response = await api(`/analyses/${state.currentJobId}/report`, {
      method: "POST",
    });
    renderReport(await response.json());
    showNotice("Decision report ready.", "success");
  } catch (error) {
    showNotice(error.message, "error");
  } finally {
    elements.buildReport.disabled = false;
  }
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

// --- Ask Atlas ---------------------------------------------------------------

async function populateAskPortfolios() {
  if (!state.portfolios.length) {
    await loadPortfolios({ quiet: true }).catch(() => {});
  }
  const select = elements.askPortfolio;
  const previous = select.value;
  select.replaceChildren();
  const none = document.createElement("option");
  none.value = "";
  none.textContent = "No portfolio (macro questions)";
  select.append(none);
  state.portfolios.forEach((portfolio) => {
    const option = document.createElement("option");
    option.value = portfolio.portfolio_id;
    option.textContent = portfolio.name;
    select.append(option);
  });
  select.value = previous || state.selectedPortfolioId || "";
}

const CITATION_PATTERN = /\[([^\][:]+):([^\][]+)\]/g;

function appendNarrativeWithCitations(target, narrative) {
  target.replaceChildren();
  let lastIndex = 0;
  let match;
  CITATION_PATTERN.lastIndex = 0;
  while ((match = CITATION_PATTERN.exec(narrative)) !== null) {
    if (match.index > lastIndex) {
      target.append(narrative.slice(lastIndex, match.index));
    }
    const artifactId = match[1];
    const locator = match[2];
    const slash = artifactId.indexOf("/");
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "citation-chip";
    chip.textContent = `${artifactId}:${locator}`;
    chip.title = "Open the artifact behind this number";
    if (slash > -1) {
      const runId = artifactId.slice(0, slash);
      const name = artifactId.slice(slash + 1);
      chip.addEventListener("click", () => openArtifact(runId, name, false));
    } else {
      chip.disabled = true;
    }
    target.append(chip);
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < narrative.length) {
    target.append(narrative.slice(lastIndex));
  }
}

function isRefusal(answer) {
  // Plan.is_refusal is a server-side @property and is not serialized: an empty
  // calls list is the refusal signal.
  return answer.plan.calls.length === 0;
}

function renderAskBanner(answer) {
  const banner = elements.askBanner;
  if (isRefusal(answer)) {
    banner.className = "ask-banner is-refusal";
    banner.textContent =
      answer.plan.refusal_reason ||
      "Atlas declined: the question is outside the engines' capabilities.";
    banner.classList.remove("is-hidden");
    return;
  }
  if (answer.degraded) {
    banner.className = "ask-banner is-degraded";
    banner.textContent =
      "Numbers-only answer: " +
      (answer.degraded_reason || "narration failed citation validation.");
    banner.classList.remove("is-hidden");
    return;
  }
  banner.classList.add("is-hidden");
  banner.textContent = "";
}

function renderAskMeta(answer) {
  const valid = answer.citations.orphan_claims.length === 0 &&
    answer.citations.citations.every((c) => c.ok);
  const parts = [
    {
      label: answer.citations.citations.length
        ? valid
          ? "Citations valid"
          : "Citation issues"
        : "No citations",
      cls: answer.citations.citations.length
        ? valid
          ? "is-ok"
          : "is-bad"
        : "",
    },
    { label: answer.llm_model || "deterministic planner" },
    {
      label: `${answer.usage.input_tokens + answer.usage.output_tokens} tokens · $${answer.usage.cost_usd.toFixed(4)}`,
    },
    { label: `${answer.latency_ms} ms` },
    { label: answer.trace_id },
  ];
  elements.askMeta.replaceChildren();
  parts.forEach((part) => {
    const chip = document.createElement("span");
    chip.className = `ask-meta-chip ${part.cls || ""}`.trim();
    chip.textContent = part.label;
    elements.askMeta.append(chip);
  });
}

function renderAskPlan(answer) {
  const container = elements.askPlan;
  container.replaceChildren();
  if (isRefusal(answer)) {
    const p = document.createElement("p");
    p.className = "ask-plan-empty";
    p.textContent = "No engine was called.";
    container.append(p);
    return;
  }
  const executedByEngine = new Map(
    answer.executed.map((call) => [call.engine, call]),
  );
  answer.plan.calls.forEach((call) => {
    const executed = executedByEngine.get(call.engine);
    const item = document.createElement("div");
    item.className = "ask-plan-item";
    const head = document.createElement("div");
    head.className = "ask-plan-head";
    const engine = document.createElement("strong");
    engine.textContent = call.engine;
    const status = document.createElement("span");
    status.className = `ask-plan-status is-${executed ? executed.status : "planned"}`;
    status.textContent = executed
      ? `${executed.status} · ${executed.latency_ms} ms`
      : "planned";
    head.append(engine, status);
    item.append(head);
    if (call.reason) {
      const reason = document.createElement("p");
      reason.className = "ask-plan-reason";
      reason.textContent = call.reason;
      item.append(reason);
    }
    if (executed && executed.run_id) {
      const run = document.createElement("button");
      run.type = "button";
      run.className = "citation-chip";
      run.textContent = `${executed.run_id}/metrics.json`;
      run.addEventListener("click", () =>
        openArtifact(executed.run_id, "metrics.json", false),
      );
      item.append(run);
    }
    container.append(item);
  });
}

function renderAskCitations(answer) {
  const container = elements.askCitations;
  container.replaceChildren();
  const citations = answer.citations.citations;
  if (!citations.length) {
    const p = document.createElement("p");
    p.className = "ask-plan-empty";
    p.textContent = "This answer makes no numeric claims to cite.";
    container.append(p);
  }
  citations.forEach((citation) => {
    const item = document.createElement("div");
    item.className = `ask-citation-item is-${citation.ok ? "ok" : "bad"}`;
    const loc = document.createElement("button");
    loc.type = "button";
    loc.className = "citation-chip";
    loc.textContent = `${citation.artifact_id}:${citation.locator}`;
    const slash = citation.artifact_id.indexOf("/");
    if (slash > -1) {
      const runId = citation.artifact_id.slice(0, slash);
      const name = citation.artifact_id.slice(slash + 1);
      loc.addEventListener("click", () => openArtifact(runId, name, false));
    } else {
      loc.disabled = true;
    }
    const detail = document.createElement("span");
    detail.className = "ask-citation-detail";
    const resolved =
      citation.resolved_value == null ? "—" : citation.resolved_value;
    detail.textContent = citation.ok
      ? `✓ ${resolved}`
      : `✗ ${citation.detail || "mismatch"}`;
    item.append(loc, detail);
    container.append(item);
  });
  answer.citations.orphan_claims.forEach((claim) => {
    const item = document.createElement("div");
    item.className = "ask-citation-item is-bad";
    const span = document.createElement("span");
    span.className = "ask-citation-detail";
    span.textContent = `Uncited figure: ${claim}`;
    item.append(span);
    container.append(item);
  });
}

function renderAnswer(answer) {
  elements.askEmptyState.classList.add("is-hidden");
  elements.askAnswer.classList.remove("is-hidden");
  appendNarrativeWithCitations(
    elements.askNarrative,
    answer.narrative || "Atlas returned no narrative for this question.",
  );
  renderAskBanner(answer);
  renderAskMeta(answer);
  renderAskPlan(answer);
  renderAskCitations(answer);
}

function setAskLoading(loading) {
  elements.askSubmit.disabled = loading;
  elements.askSubmit.textContent = loading ? "Asking…" : "Ask";
}

async function askAtlas(event) {
  if (event) {
    event.preventDefault();
  }
  const question = elements.askQuestion.value.trim();
  if (!question) {
    showNotice("Enter a question first.", "error");
    return;
  }
  hideNotice();
  setAskLoading(true);
  try {
    const body = { question };
    if (elements.askPortfolio.value) {
      body.portfolio_id = elements.askPortfolio.value;
    }
    const response = await api("/agent/ask", {
      method: "POST",
      body: JSON.stringify(body),
    });
    renderAnswer(await response.json());
  } catch (error) {
    showNotice(error.message, "error");
  } finally {
    setAskLoading(false);
  }
}

// --- Overview ----------------------------------------------------------------

const SEVERITY_RANK = { info: 0, watch: 1, elevated: 2, critical: 3 };

async function openAnalysis(jobId) {
  state.currentJobId = jobId;
  sessionStorage.setItem("atlas_current_job", jobId);
  await refreshAnalysis();
}

function relativeTime(value) {
  const then = new Date(value).getTime();
  if (Number.isNaN(then)) {
    return "—";
  }
  const seconds = Math.round((Date.now() - then) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  return `${Math.round(hours / 24)} d ago`;
}

async function loadOverview() {
  if (!state.apiKey) {
    return;
  }
  try {
    const [analysesRes, portfoliosRes, reportsRes] = await Promise.all([
      api("/analyses?limit=50"),
      api("/portfolios?limit=200"),
      api("/reports?limit=10"),
    ]);
    renderOverview(
      (await analysesRes.json()).analyses,
      (await portfoliosRes.json()).portfolios,
      (await reportsRes.json()).reports,
    );
  } catch (error) {
    elements.overviewDecisionList.replaceChildren();
    const message = document.createElement("p");
    message.className = "history-empty";
    message.textContent = `Unable to load overview: ${error.message}`;
    elements.overviewDecisionList.append(message);
  }
}

function renderOverview(analyses, portfolios, reports) {
  // Macro card: latest succeeded macro_monitor run.
  const macro = analyses.find(
    (a) => a.engine === "macro_monitor" && a.status === "succeeded",
  );
  if (macro && macro.macro_regime) {
    elements.overviewMacroRegime.textContent = capitalize(macro.macro_regime);
    elements.overviewMacroMeta.textContent =
      macro.stress_index == null
        ? "Stress —"
        : `Stress ${Number(macro.stress_index).toFixed(2)} · ${relativeTime(macro.created_at)}`;
    elements.overviewMacroCard.dataset.regime = macro.macro_regime;
  } else {
    elements.overviewMacroRegime.textContent = "—";
    elements.overviewMacroMeta.textContent = "No macro run yet";
    delete elements.overviewMacroCard.dataset.regime;
  }

  // Portfolio card: count + mean of the latest impairment risk per portfolio.
  elements.overviewPortfolioCount.textContent = String(portfolios.length);
  const latestRiskByPortfolio = new Map();
  analyses
    .filter(
      (a) =>
        a.engine === "impairment" &&
        a.status === "succeeded" &&
        a.portfolio_id &&
        a.portfolio_mean_p_impairment != null,
    )
    .forEach((a) => {
      if (!latestRiskByPortfolio.has(a.portfolio_id)) {
        latestRiskByPortfolio.set(a.portfolio_id, a.portfolio_mean_p_impairment);
      }
    });
  const risks = [...latestRiskByPortfolio.values()];
  elements.overviewPortfolioRisk.textContent = risks.length
    ? `Mean impairment risk ${percent(risks.reduce((s, v) => s + v, 0) / risks.length)}`
    : "No impairment analysis yet";

  // Decisions card: total actions + worst severity across recent reports.
  const totalActions = reports.reduce((sum, r) => sum + (r.action_count || 0), 0);
  const worst = reports.reduce(
    (acc, r) => (SEVERITY_RANK[r.max_severity] > SEVERITY_RANK[acc] ? r.max_severity : acc),
    "info",
  );
  elements.overviewDecisionCount.textContent = String(totalActions);
  elements.overviewDecisionMeta.textContent = reports.length
    ? `Worst severity: ${capitalize(worst)} · ${reports.length} report(s)`
    : "No reports built yet";
  elements.overviewDecisionsCard.dataset.severity = reports.length ? worst : "info";

  // Activity card.
  elements.overviewActivityValue.textContent = String(analyses.length);
  elements.overviewActivityMeta.textContent = analyses.length
    ? `Last run ${relativeTime(analyses[0].created_at)}`
    : "No analyses yet";

  renderOverviewDecisions(reports);
}

function renderOverviewDecisions(reports) {
  const list = elements.overviewDecisionList;
  list.replaceChildren();
  if (!reports.length) {
    const empty = document.createElement("p");
    empty.className = "history-empty";
    empty.textContent =
      "No decisions yet. Run an analysis and build a report to populate this list.";
    list.append(empty);
    return;
  }
  reports.forEach((report) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = `overview-decision is-${report.max_severity}`;
    item.addEventListener("click", () => openAnalysis(report.analysis_id));

    const main = document.createElement("span");
    main.className = "overview-decision-main";
    const headline = document.createElement("strong");
    headline.textContent = report.headline;
    const meta = document.createElement("span");
    const scope = report.portfolio_name || report.engine;
    meta.textContent = `${scope} · ${relativeTime(report.created_at)}`;
    main.append(headline, meta);

    const badge = document.createElement("span");
    badge.className = `overview-decision-badge is-${report.max_severity}`;
    badge.textContent = report.action_count
      ? `${report.action_count} · ${capitalize(report.max_severity)}`
      : "No actions";

    item.append(main, badge);
    list.append(item);
  });
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
  loadPortfolios();
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
  setPortfolioContext(null);
  renderCompanies();
  hideNotice();
});

elements.form.addEventListener("submit", runAnalysis);
elements.savePortfolio.addEventListener("click", async () => {
  hideNotice();
  try {
    elements.savePortfolio.disabled = true;
    elements.systemMessage.textContent = "Saving versioned portfolio inputs…";
    await persistPortfolio();
    elements.systemMessage.textContent = "Portfolio inputs are saved and versioned.";
  } catch (error) {
    showNotice(error.message, "error");
    elements.systemMessage.textContent = "Portfolio was not saved.";
  } finally {
    elements.savePortfolio.disabled = false;
  }
});
elements.refreshPortfolios.addEventListener("click", () => loadPortfolios());
elements.newPortfolio.addEventListener("click", () => {
  elements.clearForm.click();
  showPage("impairment");
  history.pushState(null, "", "#impairment");
  window.scrollTo({ top: 0, behavior: "smooth" });
});
elements.usePortfolio.addEventListener("click", () => {
  if (state.selectedPortfolio) {
    loadPortfolioIntoAnalysis(state.selectedPortfolio);
  }
});
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
    if (
      target === "#impairment" ||
      target === "#portfolios" ||
      target === "#macro-monitor"
    ) {
      event.preventDefault();
      history.pushState(null, "", target);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  });
});
window.addEventListener("hashchange", () => {
  const page = location.hash.replace("#", "");
  showPage(PAGE_COPY[page] ? page : "overview");
});
elements.overviewRefresh.addEventListener("click", loadOverview);
elements.overviewShortcuts.forEach((shortcut) => {
  shortcut.addEventListener("click", () => {
    const page = shortcut.dataset.go;
    history.pushState(null, "", `#${page}`);
    showPage(page);
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
});

elements.buildReport.addEventListener("click", buildReport);

elements.askForm.addEventListener("submit", askAtlas);
elements.askExamples.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-q]");
  if (!button) {
    return;
  }
  elements.askQuestion.value = button.dataset.q;
  askAtlas();
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
  const hashPage = location.hash.replace("#", "");
  const initialPage = PAGE_COPY[hashPage] ? hashPage : "overview";
  showPage(initialPage);
  if (initialPage !== "impairment") {
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
    renderPortfolioList([]);
    elements.systemMessage.textContent = "Waiting for API configuration.";
  } else {
    await loadPortfolios({ quiet: true });
  }
  if (state.currentJobId) {
    await refreshAnalysis();
  }
}

initialize();
