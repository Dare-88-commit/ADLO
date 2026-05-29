"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { MacroSlider } from "./MacroSlider";
import { RelativeValueHeatmap } from "./RelativeValueHeatmap";
import { renderCurveChart, type CurveDatum } from "../charts/lightweight";

type CurveResponse = {
  country: string;
  local_curve: CurveDatum[];
  usd_eurobond_curve: CurveDatum[];
  implied_depreciation: Array<{
    maturity_years: number;
    local_rate: number;
    usd_yield: number;
    implied_fx_depreciation: number | null;
  }>;
};

type DistressResponse = {
  score: number;
  label: string;
  components: Record<string, number>;
};

type StressResponse = {
  country: string;
  inputs: {
    country: string;
    inflation_bps: number;
    fx_multiplier: number;
    curve_shift_bps: number;
  };
  stressed_curve: CurveDatum[];
  distress: DistressResponse;
};

const countries = ["Nigeria", "South Africa", "Kenya", "Ghana"];
const apiBase = process.env.NEXT_PUBLIC_ADLO_API_URL ?? "http://127.0.0.1:8000";

export function TerminalDashboard() {
  const [country, setCountry] = useState("Nigeria");
  const [curve, setCurve] = useState<CurveResponse | null>(null);
  const [distress, setDistress] = useState<DistressResponse | null>(null);
  const [stress, setStress] = useState<StressResponse | null>(null);
  const [rvRows, setRvRows] = useState<
    Array<{
      country: string;
      tenor: string;
      local_rate: number;
      peer_average: number | null;
      spread: number | null;
      tone: "green" | "amber" | "red";
    }>
  >([]);
  const [inflationShock, setInflationShock] = useState(0);
  const [fxMultiplier, setFxMultiplier] = useState(1);
  const [curveShift, setCurveShift] = useState(0);
  const [loading, setLoading] = useState(false);

  const chartRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      const [curveResponse, distressResponse] = await Promise.all([
        fetch(`${apiBase}/curves?country=${encodeURIComponent(country)}`).then((response) =>
          response.json(),
        ),
        fetch(`${apiBase}/distress?country=${encodeURIComponent(country)}`).then((response) =>
          response.json(),
        ),
      ]);
      const rvResponse = await fetch(`${apiBase}/rv`).then((response) => response.json());
      if (!active) return;
      setCurve(curveResponse);
      setDistress(distressResponse);
      setRvRows(rvResponse.rows || []);
      setLoading(false);
    }
    load().catch(() => setLoading(false));
    return () => {
      active = false;
    };
  }, [country]);

  useEffect(() => {
    if (!chartRef.current || !curve) return;
    let cleanup: (() => void) | undefined;
    renderCurveChart(chartRef.current, curve.local_curve, curve.usd_eurobond_curve)
      .then((dispose) => {
        cleanup = dispose;
      })
      .catch(() => {
        cleanup = undefined;
      });
    return () => {
      cleanup?.();
    };
  }, [curve]);

  const heatmapRows = useMemo(
    () =>
      rvRows.map((row) => ({
        country: row.country,
        tenor: row.tenor,
        spread: Math.abs(Number(row.spread ?? 0)) * 100,
        tone: row.tone,
      })),
    [rvRows],
  );

  async function runStressScenario() {
    const response = await fetch(`${apiBase}/stress`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        country,
        inflation_bps: inflationShock,
        fx_multiplier: fxMultiplier,
        curve_shift_bps: curveShift,
      }),
    });
    const payload = await response.json();
    setStress(payload);
  }

  return (
    <main className="min-h-screen px-6 py-8 text-slate-100">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.5em] text-sky-300">
              ADLO Terminal
            </p>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight">
              African Debt Liquidity Oracle
            </h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-400">
              Open-data sovereign curve analysis, distress scoring, and scenario stress tests for
              frontier fixed-income desks.
            </p>
          </div>

          <label className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
            <span className="block font-mono text-xs uppercase tracking-[0.32em] text-slate-400">
              Country
            </span>
            <select
              className="mt-2 w-48 rounded-xl border border-white/10 bg-slate-950 px-3 py-2 font-mono text-sm text-slate-100"
              value={country}
              onChange={(event) => setCountry(event.target.value)}
            >
              {countries.map((entry) => (
                <option key={entry}>{entry}</option>
              ))}
            </select>
          </label>
        </header>

        <section className="grid gap-6 lg:grid-cols-[1.3fr_0.9fr]">
          <article className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-2xl shadow-sky-950/20 terminal-grid">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="font-mono text-xs uppercase tracking-[0.35em] text-slate-400">
                  Curve view
                </p>
                <h2 className="mt-1 text-xl font-semibold">Local vs USD Eurobond</h2>
              </div>
              <span className="font-mono text-xs text-slate-400">
                {loading ? "Refreshing..." : "Live"}
              </span>
            </div>
            <div ref={chartRef} className="min-h-[320px] rounded-2xl bg-slate-950/50 p-3" />
          </article>

          <article className="rounded-3xl border border-white/10 bg-white/5 p-5">
            <p className="font-mono text-xs uppercase tracking-[0.35em] text-slate-400">
              Distress engine
            </p>
            <div className="mt-4 space-y-4">
              <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Score</span>
                  <strong className="font-mono text-2xl text-sky-300">
                    {distress ? distress.score.toFixed(1) : "--"}
                  </strong>
                </div>
                <p className="mt-2 text-sm text-slate-300">
                  {distress ? distress.label : "Waiting for signal density"}
                </p>
              </div>
              <div className="grid gap-3">
                {distress
                  ? Object.entries(distress.components).map(([label, value]) => (
                      <div key={label} className="rounded-2xl border border-white/10 bg-slate-950/40 p-3">
                        <div className="flex items-center justify-between text-sm">
                          <span className="capitalize text-slate-300">{label.replaceAll("_", " ")}</span>
                          <span className="font-mono text-sky-300">{value.toFixed(1)}</span>
                        </div>
                        <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/5">
                          <div className="h-full rounded-full bg-gradient-to-r from-sky-400 to-cyan-300" style={{ width: `${value}%` }} />
                        </div>
                      </div>
                    ))
                  : null}
              </div>
            </div>
          </article>
        </section>

        <section className="mt-6 grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
          <article className="rounded-3xl border border-white/10 bg-white/5 p-5">
            <p className="font-mono text-xs uppercase tracking-[0.35em] text-slate-400">
              Macro shocks
            </p>
            <div className="mt-4 grid gap-4">
              <MacroSlider
                label="Inflation shock"
                min={-500}
                max={500}
                step={5}
                value={inflationShock}
                suffix=" bps"
                hint="Macro stress input that feeds the scenario endpoint."
                onChange={setInflationShock}
              />
              <MacroSlider
                label="FX multiplier"
                min={0.5}
                max={2}
                step={0.01}
                value={fxMultiplier}
                hint="Multiplier applied to the stress curve in the scenario response."
                onChange={setFxMultiplier}
              />
              <MacroSlider
                label="Curve shift"
                min={-300}
                max={300}
                step={5}
                value={curveShift}
                suffix=" bps"
                onChange={setCurveShift}
              />
            </div>
            <button
              className="mt-4 rounded-2xl bg-sky-500 px-4 py-3 font-mono text-xs uppercase tracking-[0.35em] text-slate-950"
              onClick={() => runStressScenario().catch(() => undefined)}
            >
              Run stress test
            </button>
            {stress ? (
              <div className="mt-4 rounded-2xl border border-white/10 bg-slate-950/50 p-4 text-sm text-slate-300">
                <p className="font-mono text-xs uppercase tracking-[0.35em] text-slate-400">
                  Stress result
                </p>
                <p className="mt-2">
                  {stress.distress.label} — score {stress.distress.score.toFixed(1)}
                </p>
              </div>
            ) : null}
          </article>

          <article className="rounded-3xl border border-white/10 bg-white/5 p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-mono text-xs uppercase tracking-[0.35em] text-slate-400">
                  Relative value grid
                </p>
                <h2 className="mt-1 text-xl font-semibold">Cross-tenor spread table</h2>
              </div>
              <span className="font-mono text-xs text-slate-400">Monospaced execution view</span>
            </div>
            <div className="mt-4">
              <RelativeValueHeatmap rows={heatmapRows} />
            </div>
          </article>
        </section>
      </div>
    </main>
  );
}
