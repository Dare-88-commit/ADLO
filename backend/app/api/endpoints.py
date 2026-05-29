from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..core.data_fetcher import available_countries, load_country_bundle
from ..core.quant_engine import (
    bootstrap_zero_curve,
    compute_distress_score,
    distress_label,
    implied_currency_depreciation,
    stress_curve,
)


router = APIRouter()


class StressRequest(BaseModel):
    country: str = Field(default="Nigeria")
    inflation_bps: float = Field(default=0.0, ge=-2000.0, le=2000.0)
    fx_multiplier: float = Field(default=1.0, ge=0.1, le=3.0)
    curve_shift_bps: float = Field(default=0.0, ge=-1000.0, le=1000.0)


def _country_curve(country: str) -> pd.DataFrame:
    bundle = load_country_bundle(country)
    eurobond = bundle["eurobond"]
    if eurobond.empty:
        return pd.DataFrame()
    curve = eurobond.rename(columns={"price": "rate"}).copy()
    if "maturity_years" not in curve.columns:
        curve["maturity_years"] = pd.RangeIndex(start=1, stop=len(curve) + 1)
    if "ytm" in curve.columns:
        curve["rate"] = curve["ytm"].astype(float)
    bootstrapped = bootstrap_zero_curve(
        [
            {"maturity_years": float(row["maturity_years"]), "rate": float(row["rate"])}
            for _, row in curve[["maturity_years", "rate"]].dropna().iterrows()
        ]
    )
    return bootstrapped


def _local_curve_adjustment(country: str) -> float:
    return {
        "Nigeria": 1.8,
        "South Africa": 0.9,
        "Kenya": 1.3,
        "Ghana": 2.4,
    }.get(country, 1.2)


@router.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "ADLO Terminal",
        "countries": available_countries(),
    }


@router.get("/curves")
def curves(country: str = "Nigeria") -> dict[str, Any]:
    bundle = load_country_bundle(country)
    bootstrapped = _country_curve(country)
    if bootstrapped.empty:
        raise HTTPException(status_code=404, detail=f"No curve data available for {country}.")
    local_curve_frame = bootstrapped.copy()
    local_curve_frame["rate"] = local_curve_frame["rate"].astype(float) + _local_curve_adjustment(country)
    local_curve = local_curve_frame.to_dict(orient="records")
    usd_curve = bootstrapped.to_dict(orient="records")
    match_points = []
    for point in usd_curve:
        if bootstrapped.empty:
            continue
        nearest_index = (bootstrapped["maturity_years"] - point["maturity_years"]).abs().idxmin()
        local_row = bootstrapped.loc[[nearest_index]]
        if local_row.empty:
            continue
        local_rate = float(local_row.iloc[0]["rate"])
        depreciation = implied_currency_depreciation(local_rate / 100.0, point["rate"] / 100.0)
        match_points.append(
            {
                "maturity_years": float(point["maturity_years"]),
                "local_rate": local_rate,
                "usd_yield": float(point["rate"]),
                "implied_fx_depreciation": None if depreciation is None else float(depreciation),
            }
        )

    return {
        "country": country,
        "local_curve": local_curve,
        "usd_eurobond_curve": usd_curve,
        "implied_depreciation": match_points,
        "macro": bundle["macro"].to_dict(orient="records"),
    }


@router.get("/distress")
def distress(country: str = "Nigeria") -> dict[str, Any]:
    bundle = load_country_bundle(country)
    macro = bundle["macro"]
    if macro.empty:
        raise HTTPException(status_code=404, detail=f"No macro data available for {country}.")
    row = macro.iloc[-1]
    score_payload = compute_distress_score(
        {
            "yield_spread_history": pd.Series([1.2, 1.8, 1.9, 2.4, 2.9, 3.2]),
            "fx_reserve_import_cover": row.get("fx_reserves_months", 4.0),
            "debt_to_gdp_trend": 0.8,
            "fx_returns": pd.Series([0.01, -0.005, 0.006, 0.012, -0.009, 0.008]),
        }
    )
    score = float(score_payload["score"])
    return {
        "country": country,
        "score": score,
        "label": distress_label(score),
        "components": score_payload["components"],
        "macro": macro.to_dict(orient="records"),
    }


@router.post("/stress")
def stress(request: StressRequest) -> dict[str, Any]:
    bundle = load_country_bundle(request.country)
    curve = _country_curve(request.country)
    if curve.empty:
        raise HTTPException(status_code=404, detail=f"No curve data available for {request.country}.")
    stressed = stress_curve(
        curve.copy(),
        inflation_bps=request.inflation_bps,
        fx_multiplier=request.fx_multiplier,
        curve_shift_bps=request.curve_shift_bps,
    )
    distress_payload = compute_distress_score(
        {
            "yield_spread_history": pd.Series([1.2, 1.8, 2.0, 2.6, 3.1]),
            "fx_reserve_import_cover": bundle["macro"].iloc[-1].get("fx_reserves_months", 4.0),
            "debt_to_gdp_trend": 0.6 + (request.inflation_bps / 1000.0),
            "fx_returns": pd.Series([0.008, -0.011, 0.014, -0.004, 0.009]),
        }
    )
    return {
        "country": request.country,
        "inputs": request.model_dump(),
        "stressed_curve": stressed[["maturity_years", "rate"]].to_dict(orient="records"),
        "distress": {
            "score": float(distress_payload["score"]),
            "label": distress_label(float(distress_payload["score"])),
            "components": distress_payload["components"],
        },
    }


@router.get("/rv")
def relative_value() -> dict[str, Any]:
    curves_by_country = {
        country: _country_curve(country)
        for country in available_countries()
    }
    maturities = [2.0, 5.0, 10.0]
    rows: list[dict[str, Any]] = []
    for country, curve in curves_by_country.items():
        if curve.empty:
            continue
        for maturity in maturities:
            local_row = curve.iloc[(curve["maturity_years"] - maturity).abs().argsort()[:1]]
            if local_row.empty:
                continue
            peers = []
            for peer_country, peer_curve in curves_by_country.items():
                if peer_country == country or peer_curve.empty:
                    continue
                peer_row = peer_curve.iloc[(peer_curve["maturity_years"] - maturity).abs().argsort()[:1]]
                if not peer_row.empty:
                    peers.append(float(peer_row.iloc[0]["rate"]))
            peer_average = float(sum(peers) / len(peers)) if peers else None
            local_rate = float(local_row.iloc[0]["rate"])
            spread = None if peer_average is None else local_rate - peer_average
            tone = "amber"
            if spread is not None:
                if spread < -0.5:
                    tone = "green"
                elif spread > 0.5:
                    tone = "red"
            rows.append(
                {
                    "country": country,
                    "tenor": f"{maturity:.0f}Y",
                    "local_rate": local_rate,
                    "peer_average": peer_average,
                    "spread": spread,
                    "tone": tone,
                }
            )
    return {"rows": rows}
