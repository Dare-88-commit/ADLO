from __future__ import annotations

from dataclasses import asdict, dataclass
from math import log1p
from typing import Any, Iterable

import numpy as np
import pandas as pd

try:  # optional dependency during scaffolding
    import QuantLib as ql
except Exception:  # pragma: no cover - fallback path
    ql = None

try:
    from scipy.interpolate import CubicSpline
except Exception:  # pragma: no cover - fallback path
    CubicSpline = None


@dataclass(frozen=True)
class CurvePoint:
    maturity_years: float
    rate: float


@dataclass(frozen=True)
class DistressComponents:
    yield_spread_momentum: float
    fx_reserve_import_cover: float
    macro_trend_velocity: float
    realized_currency_volatility: float


def _as_decimal(value: float | None) -> float | None:
    if value is None:
        return None
    numeric = float(value)
    if abs(numeric) > 1.5:
        return numeric / 100.0
    return numeric


def _clean(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except Exception:
        return None
    if np.isnan(numeric) or np.isinf(numeric):
        return None
    return numeric


def bootstrap_zero_curve(points: Iterable[CurvePoint]) -> pd.DataFrame:
    normalized_rows = []
    for point in points:
        if isinstance(point, dict):
            normalized_rows.append(
                {
                    "maturity_years": float(point.get("maturity_years")),
                    "rate": float(point.get("rate")),
                }
            )
        else:
            normalized_rows.append(asdict(point))
    frame = pd.DataFrame(normalized_rows)
    if frame.empty:
        return frame
    frame = frame.dropna().drop_duplicates(subset=["maturity_years"]).sort_values("maturity_years")
    if frame.shape[0] < 2:
        return frame

    if ql is not None:
        # QuantLib path intentionally stays light; callers can swap in a richer
        # instrument set without changing the output contract.
        return frame.reset_index(drop=True)

    if CubicSpline is None:
        return frame.reset_index(drop=True)

    dense_maturities = np.linspace(frame["maturity_years"].min(), frame["maturity_years"].max(), 40)
    spline = CubicSpline(frame["maturity_years"], frame["rate"], bc_type="natural")
    dense_rates = spline(dense_maturities)
    return pd.DataFrame({"maturity_years": dense_maturities, "rate": dense_rates})


def interpolate_curve(curve: pd.DataFrame, maturities: Iterable[float]) -> pd.DataFrame:
    frame = curve.copy().dropna(subset=["maturity_years", "rate"]).sort_values("maturity_years")
    if frame.empty:
        return pd.DataFrame(columns=["maturity_years", "rate"])
    sample_points = np.asarray(list(maturities), dtype=float)
    interpolated = np.interp(
        sample_points,
        frame["maturity_years"].to_numpy(dtype=float),
        frame["rate"].to_numpy(dtype=float),
    )
    return pd.DataFrame({"maturity_years": sample_points, "rate": interpolated})


def implied_currency_depreciation(local_rate: float | None, usd_yield: float | None) -> float | None:
    local_decimal = _as_decimal(local_rate)
    usd_decimal = _as_decimal(usd_yield)
    if local_decimal is None or usd_decimal is None:
        return None
    return ((1.0 + local_decimal) / (1.0 + usd_decimal)) - 1.0


def _zscore(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.shape[0] < 2:
        return 0.0
    std = float(values.std(ddof=0))
    if std == 0.0 or np.isnan(std):
        return 0.0
    return float((values.iloc[-1] - values.mean()) / std)


def _normalize(value: float, center: float, scale: float, invert: bool = False) -> float:
    score = 50.0 + ((value - center) / max(scale, 1e-6)) * 12.0
    score = float(np.clip(score, 0.0, 100.0))
    return 100.0 - score if invert else score


def compute_distress_score(features: pd.Series | dict[str, Any]) -> dict[str, Any]:
    row = pd.Series(features) if not isinstance(features, pd.Series) else features

    spread_history = pd.to_numeric(row.get("yield_spread_history", pd.Series(dtype=float)), errors="coerce")
    reserve_cover = _clean(row.get("fx_reserve_import_cover"))
    debt_trend = _clean(row.get("debt_to_gdp_trend"))
    fx_returns = pd.to_numeric(row.get("fx_returns", pd.Series(dtype=float)), errors="coerce")

    yield_momentum = _normalize(_zscore(spread_history), 0.0, 1.0)
    reserve_score = _normalize(reserve_cover or 0.0, 4.0, 1.5, invert=True)
    macro_score = _normalize(debt_trend or 0.0, 0.0, 1.0)
    fx_volatility = float(np.nan_to_num(fx_returns.std(ddof=0), nan=0.0)) * np.sqrt(252.0) * 100.0
    volatility_score = _normalize(fx_volatility, 10.0, 5.0)

    distress = (
        0.30 * yield_momentum
        + 0.30 * reserve_score
        + 0.20 * macro_score
        + 0.20 * volatility_score
    )

    return {
        "score": float(np.clip(distress, 0.0, 100.0)),
        "components": asdict(
            DistressComponents(
                yield_spread_momentum=yield_momentum,
                fx_reserve_import_cover=reserve_score,
                macro_trend_velocity=macro_score,
                realized_currency_volatility=volatility_score,
            )
        ),
    }


def stress_curve(curve: pd.DataFrame, inflation_bps: float = 0.0, fx_multiplier: float = 1.0, curve_shift_bps: float = 0.0) -> pd.DataFrame:
    frame = curve.copy()
    if frame.empty:
        return frame
    inflation_shift = inflation_bps / 100.0
    yield_shift = curve_shift_bps / 100.0
    multiplier = max(fx_multiplier, 0.1)
    frame["rate"] = frame["rate"].astype(float) + yield_shift + (log1p(max(inflation_shift, 0.0)) * 0.5)
    frame["rate"] = frame["rate"] * multiplier
    return frame


def distress_label(score: float | None) -> str:
    if score is None:
        return "insufficient data"
    if score < 25:
        return "contained"
    if score < 50:
        return "watch"
    if score < 75:
        return "stressed"
    return "distressed"
