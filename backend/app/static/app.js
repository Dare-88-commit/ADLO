const apiBase = "";

const el = {
  country: document.getElementById("country"),
  refresh: document.getElementById("refresh"),
  stress: document.getElementById("stress"),
  curve: document.getElementById("curve"),
  score: document.getElementById("score"),
  label: document.getElementById("label"),
  components: document.getElementById("components"),
  rvBody: document.getElementById("rvBody"),
  status: document.getElementById("status"),
  inflation: document.getElementById("inflation"),
  fx: document.getElementById("fx"),
  shift: document.getElementById("shift"),
  inflationValue: document.getElementById("inflationValue"),
  fxValue: document.getElementById("fxValue"),
  shiftValue: document.getElementById("shiftValue"),
  stressOut: document.getElementById("stressOut"),
};

let currentCurve = null;

const format = (value, digits = 1, suffix = "") =>
  value === null || value === undefined || Number.isNaN(Number(value))
    ? "--"
    : `${Number(value).toFixed(digits)}${suffix}`;

async function fetchJSON(path, options = {}) {
  const response = await fetch(`${apiBase}${path}`, options);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function drawChart(payload) {
  const pointsLocal = payload.local_curve || [];
  const pointsUsd = payload.usd_eurobond_curve || [];
  const ctx = el.curve.getContext("2d");
  const width = el.curve.width;
  const height = el.curve.height;
  const padding = 32;
  ctx.clearRect(0, 0, width, height);

  const allValues = pointsLocal.concat(pointsUsd).map((point) => Number(point.rate));
  const min = Math.min(...allValues) - 0.5;
  const max = Math.max(...allValues) + 0.5;
  const xStep = (width - padding * 2) / Math.max(pointsLocal.length - 1, 1);
  const yFor = (value) => height - padding - ((value - min) / (max - min || 1)) * (height - padding * 2);

  ctx.strokeStyle = "rgba(148, 163, 184, 0.12)";
  for (let i = 0; i < 5; i += 1) {
    const y = padding + ((height - padding * 2) / 4) * i;
    ctx.beginPath();
    ctx.moveTo(padding, y);
    ctx.lineTo(width - padding, y);
    ctx.stroke();
  }

  const drawLine = (points, color) => {
    ctx.beginPath();
    points.forEach((point, index) => {
      const x = padding + index * xStep;
      const y = yFor(Number(point.rate));
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    ctx.stroke();
  };

  drawLine(pointsLocal, "#5bb4ff");
  drawLine(pointsUsd, "#22d3ee");
}

function renderComponents(components) {
  el.components.innerHTML = "";
  Object.entries(components || {}).forEach(([key, value]) => {
    const card = document.createElement("div");
    card.className = "component";
    card.innerHTML = `
      <div style="display:flex;justify-content:space-between;gap:12px">
        <strong>${key.replaceAll("_", " ")}</strong>
        <span>${format(value, 1)}</span>
      </div>
      <div class="bar"><div style="width:${Math.max(0, Math.min(100, Number(value)))}%"></div></div>
    `;
    el.components.appendChild(card);
  });
}

function renderRV(points) {
  el.rvBody.innerHTML = "";
  points.forEach((point) => {
    const tr = document.createElement("tr");
    const spread = Math.abs(Number(point.spread ?? 0)) * 100;
    const tone = point.tone === "green" ? "color:#86efac" : point.tone === "red" ? "color:#fda4af" : "color:#fcd34d";
    tr.innerHTML = `
      <td>${point.country} ${point.tenor}</td>
      <td>${format(point.local_rate, 2)}</td>
      <td>${point.peer_average === null || point.peer_average === undefined ? "--" : format(point.peer_average, 2)}</td>
      <td style="${tone}">${spread.toFixed(1)} bps</td>
    `;
    el.rvBody.appendChild(tr);
  });
}

async function loadData() {
  el.status.textContent = "Refreshing…";
  const country = el.country.value;
  const [curve, distress] = await Promise.all([
    fetchJSON(`/curves?country=${encodeURIComponent(country)}`),
    fetchJSON(`/distress?country=${encodeURIComponent(country)}`),
  ]);
  const rv = await fetchJSON("/rv");
  currentCurve = curve;
  el.score.textContent = format(distress.score, 1);
  el.label.textContent = distress.label;
  el.status.textContent = country;
  drawChart(curve);
  renderComponents(distress.components);
  renderRV(rv.rows || []);
}

async function runStress() {
  const country = el.country.value;
  const payload = {
    country,
    inflation_bps: Number(el.inflation.value),
    fx_multiplier: Number(el.fx.value),
    curve_shift_bps: Number(el.shift.value),
  };
  const response = await fetchJSON("/stress", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  el.stressOut.textContent = `${response.distress.label} — score ${format(response.distress.score, 1)}`;
}

async function init() {
  const health = await fetchJSON("/health");
  el.country.innerHTML = "";
  health.countries.forEach((country) => {
    const option = document.createElement("option");
    option.value = country;
    option.textContent = country;
    el.country.appendChild(option);
  });
  el.country.value = health.countries[0] || "Nigeria";
  await loadData();
}

el.refresh.addEventListener("click", () => loadData().catch((error) => {
  el.status.textContent = "error";
  el.label.textContent = error.message;
}));
el.stress.addEventListener("click", () => runStress().catch((error) => {
  el.stressOut.textContent = error.message;
}));

[el.inflation, el.fx, el.shift].forEach((input) => {
  input.addEventListener("input", () => {
    el.inflationValue.textContent = `${el.inflation.value} bps`;
    el.fxValue.textContent = `${Number(el.fx.value).toFixed(2)}x`;
    el.shiftValue.textContent = `${el.shift.value} bps`;
  });
});

el.country.addEventListener("change", () => loadData().catch((error) => {
  el.status.textContent = "error";
  el.label.textContent = error.message;
}));

init().catch((error) => {
  el.status.textContent = "error";
  el.label.textContent = error.message;
});
