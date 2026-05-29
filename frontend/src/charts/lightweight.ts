export type CurveDatum = {
  maturity_years: number;
  rate: number;
};

export async function renderCurveChart(
  container: HTMLDivElement,
  localCurve: CurveDatum[],
  usdCurve: CurveDatum[],
) {
  const toChartTime = (maturityYears: number) =>
    `${2020 + Math.max(0, Math.round(maturityYears))}-01-01`;
  const chartModule = await import("lightweight-charts");
  const chart = chartModule.createChart(container, {
    width: container.clientWidth,
    height: 320,
    layout: {
      background: { type: chartModule.ColorType.Solid, color: "rgba(7, 17, 31, 0)" },
      textColor: "#cbd5e1",
    },
    grid: {
      vertLines: { color: "rgba(148, 163, 184, 0.12)" },
      horzLines: { color: "rgba(148, 163, 184, 0.12)" },
    },
    rightPriceScale: { visible: true },
    timeScale: { borderVisible: false },
  });

  const localSeries = chart.addLineSeries({
    color: "#60a5fa",
    lineWidth: 2,
  });
  const usdSeries = chart.addLineSeries({
    color: "#22d3ee",
    lineWidth: 2,
  });

  localSeries.setData(
    localCurve.map((point) => ({
      time: toChartTime(point.maturity_years),
      value: point.rate,
    })) as any,
  );
  usdSeries.setData(
    usdCurve.map((point) => ({
      time: toChartTime(point.maturity_years),
      value: point.rate,
    })) as any,
  );

  chart.timeScale().fitContent();

  return () => chart.remove();
}
