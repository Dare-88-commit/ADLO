"""Batch convert DMO PDFs to CSV using pdfplumber.

Usage:
  python scripts/convert_dmo_pdfs.py \
    --auction-dir "data/DMO auction results" \
    --benchmark-dir "data/DMO benchmark bond updates"

Outputs:
  data/raw/dmo_auction_results.csv
  data/raw/dmo_benchmark_bonds.csv
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd


MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def _require_pdfplumber():
    try:
        import pdfplumber  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise SystemExit(
            "pdfplumber is required. Install with: pip install pdfplumber"
        ) from exc
    return pdfplumber


def _extract_tables(pdf_path: Path) -> List[pd.DataFrame]:
    pdfplumber = _require_pdfplumber()
    tables: List[pd.DataFrame] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            raw_tables = page.extract_tables()
            for table in raw_tables:
                if not table or len(table) < 2:
                    continue
                df = pd.DataFrame(table[1:], columns=table[0])
                df = df.dropna(axis=1, how="all")
                df = df.dropna(axis=0, how="all")
                if len(df.columns) >= 2:
                    tables.append(df)
    return tables


def _pick_table(tables: List[pd.DataFrame], keywords: Iterable[str]) -> Optional[pd.DataFrame]:
    kw = [k.lower() for k in keywords]
    for df in tables:
        cols = " ".join([str(c).lower() for c in df.columns])
        if any(k in cols for k in kw):
            return df
    return tables[0] if tables else None


def _parse_month_year_from_filename(name: str) -> Optional[pd.Timestamp]:
    lower = name.lower()
    # Examples:
    # "Summary of Auction Results for April 2025.pdf"
    # "Summary of FGN Bond Auction Results for April, 2024.pdf"
    match = re.search(r"(january|february|march|april|may|june|july|august|september|october|november|december)[, ]+(\d{4})", lower)
    if not match:
        return None
    month = MONTHS[match.group(1)]
    year = int(match.group(2))
    return pd.Timestamp(year=year, month=month, day=1)


def convert_auction_pdfs(auction_dir: Path) -> pd.DataFrame:
    rows = []
    for pdf in sorted(auction_dir.glob("*.pdf")):
        date = _parse_month_year_from_filename(pdf.name)
        tables = _extract_tables(pdf)
        table = _pick_table(tables, ["bid", "cover", "stop", "yield", "rate"])
        if table is None:
            continue
        table = table.copy()
        table["source_file"] = pdf.name
        if date is not None:
            table["auction_month"] = date
        rows.append(table)

    if not rows:
        raise SystemExit("No auction tables extracted. Check PDF structure or install pdfplumber.")

    combined = pd.concat(rows, ignore_index=True)
    return combined


def convert_benchmark_pdfs(benchmark_dir: Path) -> pd.DataFrame:
    rows = []
    for pdf in sorted(benchmark_dir.glob("*.pdf")):
        tables = _extract_tables(pdf)
        table = _pick_table(tables, ["bond", "maturity", "coupon", "isin"])
        if table is None:
            continue
        table = table.copy()
        table["source_file"] = pdf.name
        rows.append(table)

    if not rows:
        raise SystemExit("No benchmark tables extracted. Check PDF structure or install pdfplumber.")

    combined = pd.concat(rows, ignore_index=True)
    return combined


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--auction-dir", default="data/DMO auction results")
    parser.add_argument("--benchmark-dir", default="data/DMO benchmark bond updates")
    parser.add_argument("--out-auction", default="data/raw/dmo_auction_results.csv")
    parser.add_argument("--out-benchmark", default="data/raw/dmo_benchmark_bonds.csv")
    args = parser.parse_args()

    auction_dir = Path(args.auction_dir)
    benchmark_dir = Path(args.benchmark_dir)

    auction_df = convert_auction_pdfs(auction_dir)
    benchmark_df = convert_benchmark_pdfs(benchmark_dir)

    Path(args.out_auction).parent.mkdir(parents=True, exist_ok=True)
    auction_df.to_csv(args.out_auction, index=False)
    benchmark_df.to_csv(args.out_benchmark, index=False)

    print(f"Wrote {args.out_auction}")
    print(f"Wrote {args.out_benchmark}")


if __name__ == "__main__":
    main()
