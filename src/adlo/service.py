"""ADLO market intelligence engine.

The goal of this layer is to turn free, lower-frequency public market data
into something a DCM or syndicate banker can talk through in a live demo:
window score, liquidity-hole probability, premium guidance, and execution
advice with an explicit narrative.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from . import ingest
from .config import DATA_RAW
from .proxy_vpin import (
    auction_imbalance_proxy,
    turnover_proxy,
    yield_stress_proxy,
)


@dataclass
class MarketSeries:
    slug: str
    name: str
    currency: str
    proxy: pd.DataFrame
    source_flags: dict[str, bool]


@dataclass
class MarketSnapshot:
    market: str
    latest_date: str
    liquidity_stress: float | None
    risk_label: str
    issuance_window_score: float | None
    liquidity_hole_probability: float | None
    premium_bps: float | None
    stance: str
    sovereign_signal: str
    headline: str
    data_completeness: float


@dataclass
class Advice:
    desired_size: float
    executable_now: float | None
    phased_days: int | None
    premium_bps: float | None
    max_single_day: float | None
    confidence: str
    rationale: str
    guidance: list[str]


RISK_BANDS = [
    (-np.inf, -0.6, "Calm"),
    (-0.6, 0.35, "Constructive"),
    (0.35, 0.95, "Watch"),
    (0.95, 1.55, "Stressed"),
    (1.55, np.inf, "Toxic"),
]


def _safe_load(loader):
    try:
        return loader()
    except Exception:
        return None


def _clean_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (float, np.floating)) and (np.isnan(value) or np.isinf(value)):
        return None
    return float(value)


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + np.exp(-value))


def _clip_score(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return float(np.clip(value, low, high))


def _pos(value: float | None) -> float:
    if value is None or np.isnan(value):
        return 0.0
    return max(float(value), 0.0)


def _label_risk(value: float | None) -> str:
    if value is None or np.isnan(value):
        return "Insufficient data"
    for low, high, label in RISK_BANDS:
        if low < value <= high:
            return label
    return "Unknown"


def _describe_stance(score: float | None) -> str:
    if score is None:
        return "Data limited"
    if score >= 78:
        return "Open window"
    if score >= 62:
        return "Usable window"
    if score >= 45:
        return "Selective window"
    if score >= 30:
        return "Fragile window"
    return "Delay / phase"


def _sovereign_signal(stress: float | None, momentum: float | None) -> str:
    if stress is None:
        return "Unavailable"
    if stress > 1.2 and _pos(momentum) > 0.25:
        return "Escalating sovereign stress"
    if stress > 0.6:
        return "Watch sovereign tone"
    if stress < -0.4:
        return "Contained sovereign tone"
    return "Neutral sovereign tone"


def _headline(row: pd.Series, name: str) -> str:
    score = _clean_float(row.get("issuance_window_score"))
    hole = _clean_float(row.get("liquidity_hole_probability"))
    stress = _clean_float(row.get("liquidity_stress_proxy"))
    if score is None or hole is None or stress is None:
        return f"{name}: still gathering enough signal density to give a clean issuance call."
    if score >= 75:
        return f"{name}: window open. The market can likely absorb risk with disciplined sizing."
    if score >= 55:
        return f"{name}: execution is feasible, but the tape is fragile enough to reward phased distribution."
    if score >= 35:
        return f"{name}: liquidity is thinning. Lean toward smaller clips and stronger new-issue concession."
    return f"{name}: liquidity hole risk is elevated. Delay a full-size print or split execution across sessions."


def _normalize_frame(frame: pd.DataFrame, component_map: dict[str, str]) -> pd.DataFrame:
    renamed = frame.rename(columns=component_map)
    return renamed


def _build_market_frame(
    slug: str,
    name: str,
    currency: str,
    auction: pd.DataFrame | None = None,
    turnover: pd.DataFrame | None = None,
    yields: pd.DataFrame | None = None,
) -> MarketSeries | None:
    frames: list[pd.DataFrame] = []
    source_flags = {
        "auction": auction is not None,
        "turnover": turnover is not None,
        "yield": yields is not None,
    }

    if auction is not None:
        frames.append(_normalize_frame(auction, {"auction_imbalance_proxy": "auction_pressure"}))
    if turnover is not None:
        frames.append(_normalize_frame(turnover, {"turnover_proxy": "turnover_drought"}))
    if yields is not None:
        frames.append(_normalize_frame(yields, {"yield_stress_proxy": "yield_shock"}))

    if not frames:
        return None

    merged = frames[0].copy()
    for frame in frames[1:]:
        merged = pd.merge(merged, frame, on="date", how="outer")

    component_cols = [c for c in merged.columns if c != "date"]
    merged = merged.sort_values("date")
    merged["liquidity_stress_proxy"] = merged[component_cols].mean(axis=1, skipna=True)
    merged["stress_momentum"] = merged["liquidity_stress_proxy"].diff().rolling(3, min_periods=1).mean()
    merged["stress_trend"] = merged["liquidity_stress_proxy"].rolling(3, min_periods=1).mean()
    merged["liquidity_hole_probability"] = merged.apply(
        lambda row: _clip_score(
            100
            * _sigmoid(
                1.1 * _pos(_clean_float(row.get("liquidity_stress_proxy")))
                + 0.7 * _pos(_clean_float(row.get("stress_momentum")))
                + 0.45 * _pos(_clean_float(row.get("yield_shock")))
                + 0.35 * _pos(_clean_float(row.get("turnover_drought")))
            )
        ),
        axis=1,
    )
    merged["issuance_window_score"] = merged.apply(
        lambda row: _clip_score(
            86
            - 18 * _pos(_clean_float(row.get("liquidity_stress_proxy")))
            - 11 * _pos(_clean_float(row.get("stress_momentum")))
            - 7 * _pos(_clean_float(row.get("turnover_drought")))
            - 9 * _pos(_clean_float(row.get("yield_shock"))),
            low=8,
            high=96,
        ),
        axis=1,
    )
    merged["premium_bps"] = merged.apply(
        lambda row: _clip_score(
            10
            + 6.5 * _pos(_clean_float(row.get("liquidity_stress_proxy")))
            + 4.5 * _pos(_clean_float(row.get("stress_momentum")))
            + 0.07 * float(row.get("liquidity_hole_probability", 0.0)),
            low=8,
            high=95,
        ),
        axis=1,
    )
    merged["sovereign_stress_score"] = merged.apply(
        lambda row: _clip_score(
            34
            + 16 * _pos(_clean_float(row.get("yield_shock")))
            + 12 * _pos(_clean_float(row.get("stress_momentum")))
            + 8 * _pos(_clean_float(row.get("liquidity_stress_proxy"))),
        ),
        axis=1,
    )
    merged["data_completeness"] = merged[component_cols].notna().mean(axis=1) * 100
    merged["stance"] = merged["issuance_window_score"].apply(_describe_stance)
    merged["risk_label"] = merged["liquidity_stress_proxy"].apply(_label_risk)
    merged["sovereign_signal"] = merged.apply(
        lambda row: _sovereign_signal(
            _clean_float(row.get("liquidity_stress_proxy")),
            _clean_float(row.get("stress_momentum")),
        ),
        axis=1,
    )
    merged["headline"] = merged.apply(lambda row: _headline(row, name), axis=1)
    merged["currency"] = currency
    merged["market_slug"] = slug

    return MarketSeries(
        slug=slug,
        name=name,
        currency=currency,
        proxy=merged,
        source_flags=source_flags,
    )


def load_market_series() -> dict[str, MarketSeries]:
    dmo = _safe_load(ingest.load_dmo_auction_results)
    fmdq = _safe_load(ingest.load_fmdq_turnover)
    sarb = _safe_load(ingest.load_sarb_yields)

    auction = auction_imbalance_proxy(dmo) if dmo is not None else None
    turnover = turnover_proxy(fmdq) if fmdq is not None else None
    yields = yield_stress_proxy(sarb) if sarb is not None else None

    markets: dict[str, MarketSeries] = {}
    nigeria = _build_market_frame(
        slug="nigeria-fgn",
        name="Nigeria (FGN)",
        currency="NGN bn",
        auction=auction,
        turnover=turnover,
    )
    south_africa = _build_market_frame(
        slug="south-africa-sagb",
        name="South Africa (SAGB)",
        currency="ZAR bn",
        yields=yields,
    )

    for series in [nigeria, south_africa]:
        if series is not None:
            markets[series.name] = series
    return markets


def _latest_row(series: MarketSeries) -> pd.Series | None:
    frame = series.proxy.dropna(subset=["liquidity_stress_proxy"]).sort_values("date")
    if frame.empty:
        return None
    return frame.iloc[-1]


def row_to_snapshot(series: MarketSeries, row: pd.Series) -> MarketSnapshot:
    return MarketSnapshot(
        market=series.name,
        latest_date=str(pd.to_datetime(row["date"]).date()),
        liquidity_stress=_clean_float(row.get("liquidity_stress_proxy")),
        risk_label=str(row.get("risk_label", "Insufficient data")),
        issuance_window_score=_clean_float(row.get("issuance_window_score")),
        liquidity_hole_probability=_clean_float(row.get("liquidity_hole_probability")),
        premium_bps=_clean_float(row.get("premium_bps")),
        stance=str(row.get("stance", "Data limited")),
        sovereign_signal=str(row.get("sovereign_signal", "Unavailable")),
        headline=str(row.get("headline", "")),
        data_completeness=float(row.get("data_completeness", 0.0)),
    )


def market_snapshot(series: MarketSeries) -> MarketSnapshot:
    row = _latest_row(series)
    if row is None:
        return MarketSnapshot(
            market=series.name,
            latest_date="n/a",
            liquidity_stress=None,
            risk_label="Insufficient data",
            issuance_window_score=None,
            liquidity_hole_probability=None,
            premium_bps=None,
            stance="Data limited",
            sovereign_signal="Unavailable",
            headline=f"{series.name}: insufficient data for a reliable call.",
            data_completeness=0.0,
        )
    return row_to_snapshot(series, row)


def get_market_row(series: MarketSeries, as_of: str | None = None) -> pd.Series:
    frame = series.proxy.sort_values("date")
    if as_of is None:
        row = _latest_row(series)
        if row is None:
            raise ValueError(f"No usable rows for {series.name}")
        return row

    target = pd.to_datetime(as_of).date()
    dates = pd.to_datetime(frame["date"]).dt.date
    row = frame[dates == target].tail(1)
    if row.empty:
        raise ValueError(f"No data for {series.name} on {as_of}")
    return row.iloc[0]


def executable_size(desired_size: float, row: pd.Series) -> Advice:
    window_score = _clean_float(row.get("issuance_window_score"))
    hole_probability = _clean_float(row.get("liquidity_hole_probability"))
    premium = _clean_float(row.get("premium_bps"))
    stress = _clean_float(row.get("liquidity_stress_proxy"))

    if window_score is None or hole_probability is None:
        return Advice(
            desired_size=desired_size,
            executable_now=None,
            phased_days=None,
            premium_bps=premium,
            max_single_day=None,
            confidence="Low",
            rationale="The free data stack is too sparse on this date to size execution confidently.",
            guidance=["Load more observations before using this scenario for a live mandate."],
        )

    base_ratio = (window_score / 100.0) * (1.0 - hole_probability / 180.0)
    base_ratio = float(np.clip(base_ratio, 0.12, 0.95))
    executable_now = round(desired_size * base_ratio, 2)
    max_single_day = round(desired_size * min(base_ratio + 0.08, 0.98), 2)
    phased_days = max(1, int(np.ceil(desired_size / max(executable_now, 1.0))))

    confidence = "High"
    if hole_probability > 70 or window_score < 35:
        confidence = "Low"
    elif hole_probability > 55 or window_score < 55:
        confidence = "Medium"

    rationale = (
        f"Window score is {window_score:.0f}/100 with a liquidity-hole probability of "
        f"{hole_probability:.0f}%. The model therefore caps same-session size at "
        f"{executable_now:.2f}."
    )

    guidance = [
        f"Target premium: {premium:.1f} bps" if premium is not None else "Premium unavailable on this date.",
        "Use syndicate cover or anchor accounts if you need to exceed the immediate executable clip.",
        "Prefer phased distribution if the hole probability is above 55%.",
    ]
    if stress is not None and stress > 1.0:
        guidance.append("Stress regime is hostile. Expect a weaker book and wider concession demands.")

    return Advice(
        desired_size=desired_size,
        executable_now=executable_now,
        phased_days=phased_days,
        premium_bps=premium,
        max_single_day=max_single_day,
        confidence=confidence,
        rationale=rationale,
        guidance=guidance,
    )


def liquidity_premium_bps(row: pd.Series) -> float | None:
    return _clean_float(row.get("premium_bps"))


def cross_market_signal(series_a: MarketSeries, series_b: MarketSeries) -> dict[str, float | str | None]:
    merged = pd.merge(
        series_a.proxy[["date", "liquidity_stress_proxy"]],
        series_b.proxy[["date", "liquidity_stress_proxy"]],
        on="date",
        how="inner",
        suffixes=("_a", "_b"),
    ).dropna()
    if merged.empty:
        return {
            "correlation": None,
            "latest_divergence": None,
            "warning": "Not enough overlapping history to judge contagion.",
        }

    correlation = merged["liquidity_stress_proxy_a"].corr(merged["liquidity_stress_proxy_b"])
    latest = merged.iloc[-1]
    divergence = abs(float(latest["liquidity_stress_proxy_a"]) - float(latest["liquidity_stress_proxy_b"]))
    warning = "Cross-market transmission looks contained."
    if divergence > 1.0:
        warning = "Major divergence: one market is pricing stress faster than the other."
    elif correlation is not None and correlation > 0.65:
        warning = "High co-movement: regional funding conditions are travelling together."

    return {
        "correlation": _clean_float(correlation),
        "latest_divergence": divergence,
        "warning": warning,
    }


def data_health() -> list[dict[str, Any]]:
    specs = [
        ("DMO auction", DATA_RAW / "dmo_auction_results.csv", True),
        ("DMO benchmark", DATA_RAW / "dmo_benchmark_bonds.csv", True),
        ("FMDQ turnover", DATA_RAW / "fmdq_turnover.csv", False),
        ("SARB yields", DATA_RAW / "sarb_bond_yields.csv", True),
    ]
    now = datetime.now(timezone.utc)
    rows: list[dict[str, Any]] = []
    for name, path, automated in specs:
        exists = path.exists()
        modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) if exists else None
        rows.append(
            {
                "source": name,
                "path": str(path),
                "status": "ready" if exists else "missing",
                "automated": automated,
                "last_modified": modified.isoformat() if modified else None,
                "age_hours": round((now - modified).total_seconds() / 3600, 1) if modified else None,
            }
        )
    return rows


def market_dashboard(series: MarketSeries, desired_size: float, as_of: str | None = None) -> dict[str, Any]:
    latest = row_to_snapshot(series, get_market_row(series))
    selected_row = get_market_row(series, as_of)
    selected = row_to_snapshot(series, selected_row)
    advice = executable_size(desired_size, selected_row)

    component_names = {
        "auction_pressure": "Auction pressure",
        "turnover_drought": "Turnover drought",
        "yield_shock": "Yield shock",
        "stress_momentum": "Stress momentum",
        "sovereign_stress_score": "Sovereign stress",
    }
    components = []
    for column, label in component_names.items():
        value = _clean_float(selected_row.get(column))
        scaled = None if value is None else _clip_score(50 + value * 18)
        if column == "sovereign_stress_score":
            scaled = value
        components.append({"key": column, "label": label, "value": value, "score": scaled})

    selected_stress = selected.liquidity_stress
    latest_stress = latest.liquidity_stress
    delta_stress = None
    if selected_stress is not None and latest_stress is not None:
        delta_stress = selected_stress - latest_stress

    dates = (
        series.proxy.sort_values("date")["date"].dropna().apply(lambda value: str(pd.to_datetime(value).date())).unique().tolist()
    )
    return {
        "market": series.name,
        "currency": series.currency,
        "latest": asdict(latest),
        "selected": asdict(selected),
        "selected_date": selected.latest_date,
        "latest_vs_selected": {
            "stress_delta": delta_stress,
            "premium_delta": (
                None
                if selected.premium_bps is None or latest.premium_bps is None
                else selected.premium_bps - latest.premium_bps
            ),
            "window_delta": (
                None
                if selected.issuance_window_score is None or latest.issuance_window_score is None
                else selected.issuance_window_score - latest.issuance_window_score
            ),
        },
        "advice": asdict(advice),
        "components": components,
        "watchpoints": _watchpoints(series, selected_row),
        "dates": dates,
    }


def _watchpoints(series: MarketSeries, row: pd.Series) -> list[str]:
    notes: list[str] = []
    stress = _clean_float(row.get("liquidity_stress_proxy"))
    hole = _clean_float(row.get("liquidity_hole_probability"))
    completeness = _clean_float(row.get("data_completeness")) or 0.0
    if stress is not None and stress > 1.0:
        notes.append("Stress is firmly in the red zone; expect more price sensitivity from investors.")
    if hole is not None and hole > 65:
        notes.append("Liquidity-hole probability is elevated, so larger clips should be split across sessions.")
    if completeness < 60:
        notes.append("This view is running on a partial free-data stack, so treat it as directional rather than executable truth.")
    if series.source_flags.get("turnover") is False:
        notes.append("Secondary market turnover is missing, which weakens the Nigeria micro-liquidity read.")
    if not notes:
        notes.append("No major structural red flags in the selected snapshot. Focus on price discipline and investor mix.")
    return notes
