"""Proxy‑VPIN liquidity stress signals using free official data.

This module avoids tick‑level aggressor imbalance by using:
- Auction imbalance (bid/cover, stop‑rate jumps)
- Secondary turnover regime shifts
- Yield volatility and shocks
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _zscore(series: pd.Series, window: int = 12) -> pd.Series:
    mean = series.rolling(window=window, min_periods=max(3, window // 3)).mean()
    std = series.rolling(window=window, min_periods=max(3, window // 3)).std()
    return (series - mean) / std.replace(0, np.nan)


def _parse_numeric(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    txt = str(value).strip()
    if not txt or txt in {"-", "—"}:
        return np.nan
    txt = txt.replace(",", "")
    txt = txt.replace("₦", "").replace("N", "")
    txt = txt.replace("billion", "").replace("bn", "")
    txt = txt.replace("%", "")
    try:
        return float(txt)
    except ValueError:
        return np.nan


def _coerce_dmo_wide(df: pd.DataFrame) -> pd.DataFrame:
    """Convert DMO wide-format extraction into tidy rows with date, bid_cover, stop_rate."""
    data = df.copy()
    if "auction_month" not in data.columns:
        return data

    label_col = "Unnamed: 0"
    if label_col not in data.columns:
        return data

    labels = ["Amount Offered:", "Subscription:", "Total Bids:", "Marginal Rates:"]
    subset = data[data[label_col].isin(labels)]
    if subset.empty:
        return data

    # melt by bond series
    bond_cols = [c for c in data.columns if c not in {label_col, "source_file", "auction_month"}]
    melted = subset.melt(
        id_vars=[label_col, "source_file", "auction_month"],
        value_vars=bond_cols,
        var_name="bond",
        value_name="value",
    )
    melted["value_num"] = melted["value"].apply(_parse_numeric)

    pivot = melted.pivot_table(
        index=["auction_month", "bond"],
        columns=label_col,
        values="value_num",
        aggfunc="first",
    ).reset_index()

    pivot["amount_offered"] = pivot.get("Amount Offered:")
    pivot["subscription_value"] = pivot.get("Subscription:")
    pivot["total_bids"] = pivot.get("Total Bids:")
    pivot["stop_rate"] = pivot.get("Marginal Rates:")
    pivot["bid_cover"] = pivot["subscription_value"] / pivot["amount_offered"]
    missing_bid_cover = pivot["bid_cover"].isna()
    pivot.loc[missing_bid_cover, "bid_cover"] = (
        pivot.loc[missing_bid_cover, "total_bids"] / pivot.loc[missing_bid_cover, "amount_offered"]
    )
    pivot = pivot.rename(columns={"auction_month": "date"})
    return pivot[["date", "bid_cover", "stop_rate"]]


def auction_imbalance_proxy(df: pd.DataFrame) -> pd.DataFrame:
    """Compute auction imbalance proxy from DMO auction results.

    Supports either tidy columns or DMO wide extraction.
    """
    data = df.copy()
    data.columns = [c.strip() for c in data.columns]

    if "date" not in [c.lower() for c in data.columns]:
        data = _coerce_dmo_wide(data)
    else:
        data.columns = [c.strip().lower() for c in data.columns]

    if "date" not in data.columns:
        raise ValueError("auction results must include a 'date' column")

    if data["date"].astype(str).str.contains(r"\d{4}/\d{2}").any():
        data["date"] = pd.to_datetime(data["date"], format="%Y/%m", errors="coerce")
    else:
        data["date"] = pd.to_datetime(data["date"], errors="coerce")
    bid_cover_col = "bid_cover" if "bid_cover" in data.columns else "bid_to_cover"
    stop_col = "stop_rate" if "stop_rate" in data.columns else "stop_yield"

    if bid_cover_col not in data.columns:
        raise ValueError("auction results must include bid_cover or bid_to_cover")
    if stop_col not in data.columns:
        raise ValueError("auction results must include stop_rate or stop_yield")

    data = data.sort_values("date")
    data["bid_cover_z"] = _zscore(data[bid_cover_col])
    data["stop_rate_change"] = data[stop_col].diff()
    data["stop_rate_jump_z"] = _zscore(data["stop_rate_change"].abs())

    data["auction_imbalance_proxy"] = (
        -0.6 * data["bid_cover_z"] + 0.4 * data["stop_rate_jump_z"]
    )
    data = data[["date", "auction_imbalance_proxy"]].dropna(subset=["date"])
    # Aggregate multiple bonds per auction month
    data = data.groupby("date", as_index=False)["auction_imbalance_proxy"].mean()
    return data


def turnover_proxy(df: pd.DataFrame) -> pd.DataFrame:
    """Compute turnover regime proxy from FMDQ turnover report.

    Expected columns:
    - date
    - turnover (for FGN bonds, or total debt)
    """
    data = df.copy()
    data.columns = [c.strip().lower() for c in data.columns]
    if "date" not in data.columns:
        raise ValueError("turnover data must include a 'date' column")
    if "turnover" not in data.columns:
        raise ValueError("turnover data must include a 'turnover' column")

    data["date"] = pd.to_datetime(data["date"])
    data = data.sort_values("date")
    data["turnover_z"] = _zscore(data["turnover"].pct_change().replace([np.inf, -np.inf], np.nan))
    data["turnover_proxy"] = -data["turnover_z"]
    return data[["date", "turnover_proxy"]]


def yield_stress_proxy(df: pd.DataFrame) -> pd.DataFrame:
    """Compute yield shock proxy from SARB yield series.

    Expected columns:
    - date
    - yield (R186 or 10Y benchmark)
    """
    data = df.copy()
    data.columns = [c.strip().lower() for c in data.columns]

    # Support SARB export schema (Date, Value)
    if "date" not in data.columns and "Date" in df.columns:
        data["date"] = df["Date"]
    if "yield" not in data.columns:
        if "value" in data.columns:
            data["yield"] = data["value"]

    if "date" not in data.columns:
        raise ValueError("yield data must include a 'date' column")
    if "yield" not in data.columns:
        raise ValueError("yield data must include a 'yield' column")

    if data["date"].astype(str).str.contains(r"\d{4}/\d{2}").any():
        data["date"] = pd.to_datetime(data["date"], format="%Y/%m", errors="coerce")
    else:
        data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["yield"] = pd.to_numeric(data["yield"], errors="coerce")
    data = data.sort_values("date")
    data["yield_change"] = data["yield"].diff()
    data["yield_vol_z"] = _zscore(data["yield_change"].rolling(5).std())
    data["yield_jump_z"] = _zscore(data["yield_change"].abs())
    data["yield_stress_proxy"] = 0.5 * data["yield_vol_z"] + 0.5 * data["yield_jump_z"]
    return data[["date", "yield_stress_proxy"]]


def combine_proxies(*frames: pd.DataFrame) -> pd.DataFrame:
    """Combine multiple proxy frames on date into a single stress score."""
    merged = None
    for frame in frames:
        if merged is None:
            merged = frame.copy()
        else:
            merged = pd.merge(merged, frame, on="date", how="outer")

    if merged is None:
        raise ValueError("No frames provided")

    merged = merged.sort_values("date")
    proxy_cols = [c for c in merged.columns if c.endswith("_proxy")]
    merged["liquidity_stress_proxy"] = merged[proxy_cols].mean(axis=1)
    return merged
