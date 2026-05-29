"use client";

type HeatmapRow = {
  country: string;
  tenor: string;
  spread: number;
  tone: "green" | "amber" | "red";
};

type Props = {
  rows: HeatmapRow[];
};

const toneClasses: Record<HeatmapRow["tone"], string> = {
  green: "text-emerald-300",
  amber: "text-amber-300",
  red: "text-rose-300",
};

export function RelativeValueHeatmap({ rows }: Props) {
  return (
    <div className="overflow-hidden rounded-2xl border border-white/10 bg-slate-950/60">
      <table className="w-full border-collapse font-mono text-xs">
        <thead className="bg-white/5 text-slate-400">
          <tr>
            <th className="px-3 py-2 text-left">Country</th>
            <th className="px-3 py-2 text-left">Tenor</th>
            <th className="px-3 py-2 text-right">Spread</th>
            <th className="px-3 py-2 text-left">Read</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.country}-${row.tenor}`} className="border-t border-white/5">
              <td className="px-3 py-2 text-slate-100">{row.country}</td>
              <td className="px-3 py-2 text-slate-300">{row.tenor}</td>
              <td className={`px-3 py-2 text-right ${toneClasses[row.tone]}`}>
                {row.spread.toFixed(1)} bps
              </td>
              <td className={`px-3 py-2 ${toneClasses[row.tone]}`}>
                {row.tone === "green" ? "Rich" : row.tone === "amber" ? "Watch" : "Stretched"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
