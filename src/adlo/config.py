from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"

@dataclass(frozen=True)
class BondSpec:
    market: str
    name: str
    currency: str
    benchmark_tenor: str
    id_hint: str

BONDS = {
    "NG_10Y_FGN": BondSpec(
        market="Nigeria",
        name="FGN 10Y Benchmark",
        currency="NGN",
        benchmark_tenor="10Y",
        id_hint="Use DMO benchmark list to map series",
    ),
    "ZA_R186": BondSpec(
        market="South Africa",
        name="SAGB R186",
        currency="ZAR",
        benchmark_tenor="10Y",
        id_hint="Use SARB/JSE series code for R186",
    ),
}
