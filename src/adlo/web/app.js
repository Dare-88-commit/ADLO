const elements = {
  marketSelect: document.getElementById("marketSelect"),
  dateFilter: document.getElementById("dateFilter"),
  desiredSize: document.getElementById("desiredSize"),
  refreshBtn: document.getElementById("refreshBtn"),
  runAdviceBtn: document.getElementById("runAdviceBtn"),
  headline: document.getElementById("headline"),
  subHeadline: document.getElementById("subHeadline"),
  lastUpdated: document.getElementById("lastUpdated"),
  dateInfo: document.getElementById("dateInfo"),
  stanceValue: document.getElementById("stanceValue"),
  riskLabel: document.getElementById("riskLabel"),
  windowScore: document.getElementById("windowScore"),
  holeProbability: document.getElementById("holeProbability"),
  premiumBps: document.getElementById("premiumBps"),
  sovereignSignal: document.getElementById("sovereignSignal"),
  execNow: document.getElementById("execNow"),
  maxSingleDay: document.getElementById("maxSingleDay"),
  phasedDays: document.getElementById("phasedDays"),
  confidence: document.getElementById("confidence"),
  execRationale: document.getElementById("execRationale"),
  guidanceList: document.getElementById("guidanceList"),
  components: document.getElementById("components"),
  latestStressComp: document.getElementById("latestStressComp"),
  selectedStressComp: document.getElementById("selectedStressComp"),
  deltaStressComp: document.getElementById("deltaStressComp"),
  premiumDeltaComp: document.getElementById("premiumDeltaComp"),
  windowDeltaComp: document.getElementById("windowDeltaComp"),
  activeMarkets: document.getElementById("activeMarkets"),
  crossCorr: document.getElementById("crossCorr"),
  crossDivergence: document.getElementById("crossDivergence"),
  crossWarning: document.getElementById("crossWarning"),
  watchpoints: document.getElementById("watchpoints"),
  dataHealth: document.getElementById("dataHealth"),
  chart: document.getElementById("stressChart"),
};

let state = {
  overview: null,
  series: null,
};

async function fetchJSON(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function formatNumber(value, digits = 2, suffix = "") {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "--";
  }
  return `${Number(value).toFixed(digits)}${suffix}`;
}

function formatSigned(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "--";
  }
  const numeric = Number(value);
  return `${numeric > 0 ? "+" : ""}${numeric.toFixed(digits)}`;
}

function setList(target, items) {
  target.innerHTML = "";
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    target.appendChild(li);
  });
}

function setStatus(message) {
  elements.lastUpdated.textContent = message;
}

function drawChart(points, selectedDate) {
  const ctx = elements.chart.getContext("2d");
  const width = elements.chart.width;
  const height = elements.chart.height;
  const padding = 28;
  ctx.clearRect(0, 0, width, height);

  if (!points || points.length < 2) {
    ctx.fillStyle = "#587197";
    ctx.font = "14px Space Grotesk";
    ctx.fillText("Not enough history to draw the tape yet.", 30, 50);
    return;
  }

  const stressValues = points.map((point) => point.stress).filter((value) => value !== null);
  const windowValues = points.map((point) => point.window).filter((value) => value !== null);
  const allValues = stressValues.concat(windowValues.map((value) => (value - 50) / 20));
  const minValue = Math.min(...allValues, -1.5);
  const maxValue = Math.max(...allValues, 1.5);
  const plotWidth = width - padding * 2;
  const plotHeight = height - padding * 2;

  const toX = (index) => padding + (index / (points.length - 1)) * plotWidth;
  const toY = (value) => padding + plotHeight - ((value - minValue) / (maxValue - minValue || 1)) * plotHeight;

  ctx.strokeStyle = "rgba(18, 58, 159, 0.12)";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i += 1) {
    const y = padding + (plotHeight / 4) * i;
    ctx.beginPath();
    ctx.moveTo(padding, y);
    ctx.lineTo(width - padding, y);
    ctx.stroke();
  }

  ctx.lineWidth = 3;
  ctx.strokeStyle = "#1f5eff";
  ctx.beginPath();
  points.forEach((point, index) => {
    if (point.stress === null) {
      return;
    }
    const x = toX(index);
    const y = toY(point.stress);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();

  ctx.strokeStyle = "#59b2ff";
  ctx.beginPath();
  points.forEach((point, index) => {
    if (point.window === null) {
      return;
    }
    const scaledWindow = (point.window - 50) / 20;
    const x = toX(index);
    const y = toY(scaledWindow);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();

  const selectedIndex = points.findIndex((point) => point.date === selectedDate);
  if (selectedIndex >= 0) {
    const point = points[selectedIndex];
    const x = toX(selectedIndex);
    if (point.stress !== null) {
      const y = toY(point.stress);
      ctx.fillStyle = "#ffffff";
      ctx.beginPath();
      ctx.arc(x, y, 6, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = "#1f5eff";
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  }
}

function renderComponents(components) {
  elements.components.innerHTML = "";
  components.forEach((component) => {
    const wrapper = document.createElement("div");
    wrapper.className = "component";
    const score = component.score === null || component.score === undefined ? 0 : component.score;
    wrapper.innerHTML = `
      <div class="component-head">
        <span>${component.label}</span>
        <strong>${formatNumber(score, 0)}</strong>
      </div>
      <div class="component-track">
        <div class="component-fill" style="width: ${Math.max(0, Math.min(100, score))}%"></div>
      </div>
    `;
    elements.components.appendChild(wrapper);
  });
}

function renderHealth(items) {
  elements.dataHealth.innerHTML = "";
  items.forEach((item) => {
    const card = document.createElement("div");
    const statusClass = `status-${item.status}`;
    card.className = "health-item";
    card.innerHTML = `
      <h3>${item.source}</h3>
      <div class="health-meta">
        <span class="${statusClass}">Status: ${item.status}</span>
        <span>Refresh: ${item.automated ? "Automatic" : "Manual"}</span>
        <span>Updated: ${item.last_modified ? item.last_modified.slice(0, 19).replace("T", " ") : "Not available"}</span>
      </div>
    `;
    elements.dataHealth.appendChild(card);
  });
}

function renderOverview(overview) {
  state.overview = overview;
  const markets = overview.markets || [];
  const current = elements.marketSelect.value;
  elements.marketSelect.innerHTML = "";
  markets.forEach((market) => {
    const option = document.createElement("option");
    option.value = market.market;
    option.textContent = market.market;
    elements.marketSelect.appendChild(option);
  });
  if (current && markets.some((market) => market.market === current)) {
    elements.marketSelect.value = current;
  }

  elements.activeMarkets.textContent = markets.map((market) => market.market).join(" / ") || "--";
  elements.crossCorr.textContent = formatNumber(overview.cross_market?.correlation, 2);
  elements.crossDivergence.textContent = formatNumber(overview.cross_market?.latest_divergence, 2);
  elements.crossWarning.textContent = overview.cross_market?.warning || "Regional read unavailable.";
  renderHealth(overview.data_health || []);
}

async function loadSeries(market) {
  state.series = await fetchJSON(`/api/series/${encodeURIComponent(market)}`);
  const dates = Array.from(new Set((state.series.points || []).map((point) => point.date).filter(Boolean)));
  const current = elements.dateFilter.value;
  elements.dateFilter.innerHTML = "";
  dates.forEach((entry) => {
    const option = document.createElement("option");
    option.value = entry;
    option.textContent = entry;
    elements.dateFilter.appendChild(option);
  });
  if (current && dates.includes(current)) {
    elements.dateFilter.value = current;
  } else if (dates.length) {
    elements.dateFilter.value = dates[dates.length - 1];
  }
  elements.dateInfo.textContent = elements.dateFilter.value
    ? `Scenario date: ${elements.dateFilter.value}`
    : "Scenario date unavailable";
}

async function loadDashboard() {
  const market = elements.marketSelect.value;
  if (!market) {
    return;
  }
  const desiredSize = Number(elements.desiredSize.value || 100);
  const date = elements.dateFilter.value;
  const query = date ? `&date=${encodeURIComponent(date)}` : "";
  const data = await fetchJSON(
    `/api/dashboard?market=${encodeURIComponent(market)}&desired_size=${desiredSize}${query}`
  );

  elements.headline.textContent = data.selected.headline;
  elements.subHeadline.textContent =
    `${data.selected.market} is currently rated "${data.selected.stance}" with ` +
    `${formatNumber(data.selected.data_completeness, 0, "%")} source completeness in the free data stack.`;

  elements.stanceValue.textContent = data.selected.stance;
  elements.riskLabel.textContent = data.selected.risk_label;
  elements.windowScore.textContent = formatNumber(data.selected.issuance_window_score, 0);
  elements.holeProbability.textContent = formatNumber(data.selected.liquidity_hole_probability, 0, "%");
  elements.premiumBps.textContent = formatNumber(data.selected.premium_bps, 1, " bps");
  elements.sovereignSignal.textContent = data.selected.sovereign_signal;

  elements.execNow.textContent = `${formatNumber(data.advice.executable_now, 2)} ${data.currency}`;
  elements.maxSingleDay.textContent = `${formatNumber(data.advice.max_single_day, 2)} ${data.currency}`;
  elements.phasedDays.textContent = data.advice.phased_days ?? "--";
  elements.confidence.textContent = data.advice.confidence;
  elements.execRationale.textContent = data.advice.rationale;

  setList(elements.guidanceList, data.advice.guidance || []);
  setList(elements.watchpoints, data.watchpoints || []);
  renderComponents(data.components || []);

  elements.latestStressComp.textContent = formatNumber(data.latest.liquidity_stress, 2);
  elements.selectedStressComp.textContent = formatNumber(data.selected.liquidity_stress, 2);
  elements.deltaStressComp.textContent = formatSigned(data.latest_vs_selected.stress_delta, 2);
  elements.premiumDeltaComp.textContent = formatSigned(data.latest_vs_selected.premium_delta, 1);
  elements.windowDeltaComp.textContent = formatSigned(data.latest_vs_selected.window_delta, 0);

  drawChart(state.series?.points || [], data.selected_date);
  setStatus(`Latest point: ${data.latest.latest_date}`);
}

async function refreshData() {
  try {
    setStatus("Refreshing official sources...");
    await fetchJSON("/api/refresh", { method: "POST" });
  } catch (error) {
    console.error(error);
    setStatus("Refresh failed; reloading local data.");
  }
  await boot();
}

async function boot() {
  try {
    setStatus("Loading market intelligence...");
    const overview = await fetchJSON("/api/overview");
    renderOverview(overview);
    const market = elements.marketSelect.value || overview.markets?.[0]?.market;
    if (!market) {
      setStatus("No markets available");
      return;
    }
    elements.marketSelect.value = market;
    await loadSeries(market);
    await loadDashboard();
  } catch (error) {
    console.error(error);
    setStatus("Unable to load dashboard");
    elements.headline.textContent = "The dashboard could not load the current market package.";
    elements.subHeadline.textContent = "Check the data files or the refresh pipeline and try again.";
  }
}

elements.refreshBtn.addEventListener("click", refreshData);
elements.runAdviceBtn.addEventListener("click", loadDashboard);
elements.marketSelect.addEventListener("change", async () => {
  await loadSeries(elements.marketSelect.value);
  await loadDashboard();
});
elements.dateFilter.addEventListener("change", loadDashboard);

boot();
