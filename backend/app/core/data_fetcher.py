from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import numpy as np
import pandas as pd

try:  # optional dependency during scaffolding
    import requests
except Exception:  # pragma: no cover - fallback path
    requests = None

try:
    import yfinance as yf
except Exception:  # pragma: no cover - fallback path
    yf = None

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - fallback path
    BeautifulSoup = None


WORLD_BANK_BASE = "https://api.worldbank.org/v2"
LIVE_DATA_ENABLED = os.getenv("ADLO_LIVE_DATA") == "1"


@dataclass(frozen=True)
class CountryFeed:
    country: str
    eurobond_tickers: tuple[str, ...]
    world_bank_code: str
    central_bank_urls: tuple[str, ...]


COUNTRY_FEEDS: dict[str, CountryFeed] = {
    "Nigeria": CountryFeed(
        country="Nigeria",
        eurobond_tickers=(),
        world_bank_code="NGA",
        central_bank_urls=("https://www.cbn.gov.ng/rates/mbs.asp",),
    ),
    "South Africa": CountryFeed(
        country="South Africa",
        eurobond_tickers=(),
        world_bank_code="ZAF",
        central_bank_urls=("https://www.resbank.co.za/en/home/what-we-do/statistics",),
    ),
    "Kenya": CountryFeed(
        country="Kenya",
        eurobond_tickers=(),
        world_bank_code="KEN",
        central_bank_urls=("https://www.centralbank.go.ke/",),
    ),
    "Ghana": CountryFeed(
        country="Ghana",
        eurobond_tickers=(),
        world_bank_code="GHA",
        central_bank_urls=("https://www.bog.gov.gh/",),
    ),
}


def _demo_curve(country: str) -> pd.DataFrame:
    maturities = np.array([1, 2, 3, 5, 7, 10, 15], dtype=float)
    slope = 0.42 if country == "Nigeria" else 0.28
    base = 9.25 if country == "Nigeria" else 7.5
    rates = base + slope * np.log1p(maturities)
    return pd.DataFrame(
        {
            "country": country,
            "maturity_years": maturities,
            "price": np.full_like(maturities, 100.0),
            "ytm": rates,
            "source": "demo",
            "date": pd.Timestamp.utcnow().normalize(),
        }
    )


def _demo_macro(country: str) -> pd.DataFrame:
    values = {
        "Nigeria": {
            "debt_to_gdp": 52.4,
            "inflation": 27.8,
            "fx_reserves_months": 4.1,
            "fx_volatility": 18.3,
        },
        "South Africa": {
            "debt_to_gdp": 73.1,
            "inflation": 5.6,
            "fx_reserves_months": 5.2,
            "fx_volatility": 10.4,
        },
    }.get(country, {
        "debt_to_gdp": 60.0,
        "inflation": 8.0,
        "fx_reserves_months": 4.0,
        "fx_volatility": 12.0,
    })
    return pd.DataFrame([{"country": country, **values, "date": pd.Timestamp.utcnow().normalize()}])


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return None
    try:
        return float(value)
    except Exception:
        return None


def fetch_eurobond_history(tickers: tuple[str, ...]) -> pd.DataFrame:
    """Fetch end-of-day history for a small bond universe.

    The live yfinance path is best-effort; the demo falls back to a stable
    synthetic panel when the market data source is missing or unavailable.
    """

    if not LIVE_DATA_ENABLED or yf is None or not tickers:
        return pd.DataFrame()

    frames: list[pd.DataFrame] = []
    for ticker in tickers:
        try:
            history = yf.Ticker(ticker).history(period="1y", auto_adjust=False)
        except Exception:
            continue
        if history.empty:
            continue
        frame = history.reset_index().rename(columns={"Date": "date", "Close": "price"})
        frame["ticker"] = ticker
        frames.append(frame[["date", "ticker", "price"]])

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


def fetch_world_bank_indicator(country_code: str, indicator: str) -> pd.DataFrame:
    if not LIVE_DATA_ENABLED or requests is None:
        return pd.DataFrame()

    url = f"{WORLD_BANK_BASE}/country/{country_code}/indicator/{indicator}?format=json&per_page=200"
    try:
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return pd.DataFrame()

    if not isinstance(payload, list) or len(payload) < 2:
        return pd.DataFrame()

    rows = []
    for row in payload[1]:
        rows.append(
            {
                "country": row.get("country", {}).get("value", country_code),
                "indicator": indicator,
                "date": row.get("date"),
                "value": _safe_float(row.get("value")),
            }
        )
    return pd.DataFrame(rows)


def scrape_yield_table(url: str) -> pd.DataFrame:
    if not LIVE_DATA_ENABLED or requests is None or BeautifulSoup is None:
        return pd.DataFrame()

    try:
        response = requests.get(url, timeout=8)
        response.raise_for_status()
    except Exception:
        return pd.DataFrame()

    soup = BeautifulSoup(response.text, "html.parser")
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        parsed_rows = []
        headers: list[str] = []
        for row_index, row in enumerate(rows):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
            if not cells:
                continue
            if row_index == 0:
                headers = cells
                continue
            if headers and len(cells) == len(headers):
                parsed_rows.append(dict(zip(headers, cells, strict=False)))
        if parsed_rows:
            return pd.DataFrame(parsed_rows)
    return pd.DataFrame()


@lru_cache(maxsize=8)
def load_country_bundle(country: str) -> dict[str, pd.DataFrame]:
    feed = COUNTRY_FEEDS.get(country)
    if feed is None or not LIVE_DATA_ENABLED:
        return {
            "eurobond": _demo_curve(country),
            "macro": _demo_macro(country),
            "yields": pd.DataFrame(),
        }

    eurobond_history = fetch_eurobond_history(feed.eurobond_tickers)
    if eurobond_history.empty:
        eurobond_history = _demo_curve(country)

    macro = _demo_macro(country)
    for indicator in ("NY.GDP.DEFL.KD.ZG", "FP.CPI.TOTL.ZG", "FI.RES.TOTL.CD"):
        indicator_frame = fetch_world_bank_indicator(feed.world_bank_code, indicator)
        if not indicator_frame.empty:
            latest = indicator_frame["value"].dropna()
            if not latest.empty:
                macro[indicator] = float(latest.iloc[-1])

    yields = pd.DataFrame()
    for url in feed.central_bank_urls:
        yields = scrape_yield_table(url)
        if not yields.empty:
            break

    return {
        "eurobond": eurobond_history,
        "macro": macro,
        "yields": yields,
    }


def available_countries() -> list[str]:
    return sorted(COUNTRY_FEEDS.keys())
