import Link from "next/link";

const sections = [
  {
    title: "What the Terminal Shows",
    body:
      "The home screen is a sovereign debt workstation for African frontier markets. It compares local-currency yield curves with USD Eurobond curves, summarizes sovereign stress, and highlights relative-value spreads across Nigeria, South Africa, Kenya, and Ghana.",
  },
  {
    title: "Curve View",
    body:
      "The curve chart overlays a local-rate path and a USD sovereign curve. The goal is to make interest-rate divergence visible at a glance, especially where local yields imply pressure against hard-currency funding conditions.",
  },
  {
    title: "Distress Engine",
    body:
      "The distress score compresses market and macro signals into a 0 to 100 risk read. It combines yield momentum, foreign-reserve cover, debt trend pressure, and realized currency volatility into one readable signal.",
  },
  {
    title: "Macro Shocks",
    body:
      "The sliders send inflation, FX, and curve-shift assumptions to the FastAPI backend. The backend recalculates the stressed curve and returns a refreshed distress read without a page reload.",
  },
  {
    title: "Relative Value Grid",
    body:
      "The grid compares country tenors against peer averages. Green rows suggest relatively rich or attractive levels, amber rows are watch zones, and red rows flag wider stress or potential mispricing.",
  },
  {
    title: "Data Mode",
    body:
      "For presentation stability, ADLO runs on deterministic demo data by default. Live public-data hooks exist for yfinance, World Bank indicators, and central-bank pages when ADLO_LIVE_DATA is enabled on the backend.",
  },
];

export default function ExplainPage() {
  return (
    <main className="min-h-screen px-6 py-8 text-slate-100">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8 flex flex-wrap items-end justify-between gap-4 border-b border-white/10 pb-6">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.4em] text-sky-300">
              ADLO Terminal
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight">
              How the Dashboard Works
            </h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
              A plain-English guide to the analytics shown on the home terminal, the data pipeline
              behind it, and how to frame the current accuracy of the platform.
            </p>
          </div>
          <Link
            className="rounded-lg border border-white/10 bg-white/5 px-4 py-3 font-mono text-xs uppercase tracking-[0.24em] text-slate-200 transition hover:border-sky-300/60 hover:text-sky-200"
            href="/"
          >
            Back To Terminal
          </Link>
        </header>

        <section className="grid gap-4 md:grid-cols-2">
          {sections.map((section) => (
            <article
              className="rounded-lg border border-white/10 bg-white/5 p-5"
              key={section.title}
            >
              <h2 className="text-lg font-semibold text-slate-100">{section.title}</h2>
              <p className="mt-3 text-sm leading-6 text-slate-400">{section.body}</p>
            </article>
          ))}
        </section>

        <section className="mt-6 rounded-lg border border-white/10 bg-slate-950/50 p-5">
          <h2 className="text-lg font-semibold text-slate-100">Best Presentation Framing</h2>
          <p className="mt-3 text-sm leading-6 text-slate-400">
            ADLO is a working open-data sovereign analytics prototype. TradingView Lightweight
            Charts is used only for visualization; the data is produced by the FastAPI backend.
            The current deployment is best described as directionally useful and presentation
            reliable, with live public-data ingestion available as an opt-in backend mode.
          </p>
        </section>
      </div>
    </main>
  );
}
