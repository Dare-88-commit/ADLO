"""Ingestion utilities for free official data sources.

Expected inputs are CSV/Excel files placed in data/raw with the names below.
You can convert PDFs to CSV with tools like tabula or pandas+camelot.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

from .config import DATA_RAW

@dataclass
class IngestSpec:
    name: str
    filename: str
    description: str

SPECS = {
    "dmo_auction_results": IngestSpec(
        name="DMO Auction Results",
        filename="dmo_auction_results.csv",
        description="Monthly FGN bond auction results (stop rate, bid/cover, amount offered).",
    ),
    "dmo_benchmark_list": IngestSpec(
        name="DMO Benchmark Bond List",
        filename="dmo_benchmark_bonds.csv",
        description="Benchmark list with series, coupon, maturity for mapping 10Y benchmark.",
    ),
    "fmdq_turnover": IngestSpec(
        name="FMDQ Market Turnover",
        filename="fmdq_turnover.csv",
        description="Monthly turnover aggregates for secondary market activity.",
    ),
    "sarb_yields": IngestSpec(
        name="SARB Yield Series",
        filename="sarb_bond_yields.csv",
        description="Time series of SAGB yields (include R186 or 10Y benchmark).",
    ),
}


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing file: {path}. Place the CSV in data/raw as documented."
        )
    return pd.read_csv(path)


def load_dmo_auction_results(path: Optional[Path] = None) -> pd.DataFrame:
    path = path or (DATA_RAW / SPECS["dmo_auction_results"].filename)
    df = _load_csv(path)
    return df


def load_dmo_benchmark_list(path: Optional[Path] = None) -> pd.DataFrame:
    path = path or (DATA_RAW / SPECS["dmo_benchmark_list"].filename)
    df = _load_csv(path)
    return df


def load_fmdq_turnover(path: Optional[Path] = None) -> pd.DataFrame:
    path = path or (DATA_RAW / SPECS["fmdq_turnover"].filename)
    df = _load_csv(path)
    return df


def load_sarb_yields(path: Optional[Path] = None) -> pd.DataFrame:
    path = path or (DATA_RAW / SPECS["sarb_yields"].filename)
    df = _load_csv(path)
    return df
