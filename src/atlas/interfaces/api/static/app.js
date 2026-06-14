const state = {
  apiKey: sessionStorage.getItem("atlas_api_key") || "",
  connectionMode: sessionStorage.getItem("atlas_connection_mode") || "api-key",
  currentJobId: sessionStorage.getItem("atlas_current_job") || null,
  currentResult: null,
  companies: [
    { name: "Alpha Industrials", ebitda: 120, multiple: 8, carrying_value: 900 },
    { name: "Beta Logistics", ebitda: 60, multiple: 6.5, carrying_value: 450 },
    { name: "Gamma Health", ebitda: 200, multiple: 11, carrying_value: 2400 },
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
};

function escapeText(value) {
  return String(value ?? "");
}

function renderCompanies() {
  elements.companyRows.replaceChildren();
  state.companies.forEach((company, index) => {
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
    elements.companyRows.append(row);
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

function setLoading(loading, label = "Run analysis") {
  elements.body.classList.toggle("is-loading", loading);
  elements.runAnalysis.disabled = loading;
  elements.runAnalysis.lastChild.textContent = loading ? " Running…" : ` ${label}`;
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
      renderResult(analysis);
      elements.refreshAnalysis.classList.add("is-hidden");
      elements.systemMessage.textContent = "Analysis completed. Evidence is ready.";
      showNotice("Analysis completed successfully.", "success");
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
  elements.historyList.replaceChildren();
  if (!analyses.length) {
    const empty = document.createElement("p");
    empty.className = "history-empty";
    empty.textContent = state.apiKey
      ? "No persisted analyses yet."
      : "Connect to Atlas to load persisted analyses.";
    elements.historyList.append(empty);
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
      document.querySelector("#analysis").scrollIntoView({ behavior: "smooth" });
    });

    const main = document.createElement("span");
    main.className = "history-main";
    const name = document.createElement("strong");
    name.textContent = analysis.portfolio_name || analysis.job_id;
    const metadata = document.createElement("span");
    metadata.textContent = `${analysis.job_id} · ${analysis.status}`;
    main.append(name, metadata);

    const outcome = document.createElement("span");
    outcome.className =
      analysis.portfolio_mean_p_impairment == null
        ? "history-risk history-status"
        : "history-risk";
    outcome.textContent =
      analysis.portfolio_mean_p_impairment == null
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
    elements.historyList.append(item);
  });
}

function percent(value) {
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function money(value) {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 1,
  }).format(Number(value));
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

  renderRegimes(result.metrics);
  loadCompanyScores(analysis.job_id);
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
        money(score.ev_mean),
        `${money(score.ev_p05)}–${money(score.ev_p95)}`,
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
    ebitda: 100,
    multiple: 8,
    carrying_value: 800,
  });
  renderCompanies();
});

elements.clearForm.addEventListener("click", () => {
  state.companies = [
    { name: "Alpha Industrials", ebitda: 120, multiple: 8, carrying_value: 900 },
  ];
  elements.portfolioName.value = "Atlas Sample Portfolio";
  elements.nSims.value = "10000";
  elements.seed.value = "7";
  renderCompanies();
  hideNotice();
});

elements.form.addEventListener("submit", runAnalysis);
elements.refreshAnalysis.addEventListener("click", refreshAnalysis);
elements.refreshHistory.addEventListener("click", loadHistory);
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
