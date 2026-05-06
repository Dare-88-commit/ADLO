from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .fetchers import refresh_all_sources
from .service import cross_market_signal, data_health, load_market_series, market_dashboard, market_snapshot

APP_ROOT = Path(__file__).resolve().parent
WEB_ROOT = APP_ROOT / "web"

app = FastAPI(title="ADLO", version="2.0.0")


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


@app.post("/api/refresh")
def refresh():
    results = refresh_all_sources()
    return {"status": "ok", "results": [result.__dict__ for result in results]}


@app.get("/api/overview")
def overview():
    markets = load_market_series()
    snapshots = [market_snapshot(series).__dict__ for series in markets.values()]
    names = list(markets.keys())
    cross = (
        cross_market_signal(markets[names[0]], markets[names[1]])
        if len(names) >= 2
        else {"correlation": None, "latest_divergence": None, "warning": "Need more than one market."}
    )
    return {
        "markets": snapshots,
        "cross_market": cross,
        "data_health": data_health(),
    }


@app.get("/api/dashboard")
def dashboard(market: str, desired_size: float = 100.0, date: str | None = None):
    markets = load_market_series()
    if market not in markets:
        raise HTTPException(404, f"Unknown or unavailable market: {market}")
    return market_dashboard(markets[market], desired_size=desired_size, as_of=date)


@app.get("/api/series/{market}")
def market_series(market: str):
    markets = load_market_series()
    if market not in markets:
        raise HTTPException(404, f"Unknown or unavailable market: {market}")
    frame = markets[market].proxy.sort_values("date")
    return {
        "market": market,
        "points": [
            {
                "date": str(point.date()),
                "stress": None if value != value else float(value),
                "window": None if window != window else float(window),
                "hole_probability": None if hole != hole else float(hole),
            }
            for point, value, window, hole in zip(
                frame["date"].apply(lambda value: value.to_pydatetime() if hasattr(value, "to_pydatetime") else value),
                frame["liquidity_stress_proxy"],
                frame["issuance_window_score"],
                frame["liquidity_hole_probability"],
            )
        ],
    }


app.mount("/", StaticFiles(directory=WEB_ROOT, html=True), name="web")


@app.get("/")
def index():
    return FileResponse(WEB_ROOT / "index.html")

