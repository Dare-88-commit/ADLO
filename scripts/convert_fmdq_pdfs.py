"""Batch convert FMDQ Monthly Market Reports to fmdq_turnover.csv.

Usage:
  .venv/bin/python scripts/convert_fmdq_pdfs.py \
    --reports-dir "data/FMDQ turnover reports"

Output:
  data/raw/fmdq_turnover.csv
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import List, Optional

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
            "pdfplumber is required. Install with: .venv/bin/pip install pdfplumber"
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
                df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
                if len(df.columns) >= 2:
                    tables.append(df)
    return tables


def _parse_month_year_from_filename(name: str) -> Optional[pd.Timestamp]:
    lower = name.lower()
    match = re.search(r"(january|february|march|april|may|june|july|august|september|october|november|december)[- ](\d{4})", lower)
    if not match:
        match = re.search(r"(january|february|march|april|may|june|july|august|september|october|november|december)[, ]+(\d{4})", lower)
    if not match:
        return None
    month = MONTHS[match.group(1)]
    year = int(match.group(2))
    return pd.Timestamp(year=year, month=month, day=1)


def _clean_number(value: str) -> Optional[float]:
    if value is None:
        return None
    txt = str(value).strip()
    if txt in {"-", "—", ""}:
        return None
    txt = txt.replace(",", "")
    try:
        return float(txt)
    except ValueError:
        return None


def _find_fgn_row(tables: List[pd.DataFrame]) -> Optional[pd.Series]:
    for df in tables:
        cols = [str(c).lower() for c in df.columns]
        if any("product" in c for c in cols):
            # look for row containing FGN Bonds
            for _, row in df.iterrows():
                first = str(row.iloc[0]).lower() if len(row) > 0 else ""
                if "fgn" in first and "bond" in first:
                    return row
    # fallback: search any table
    for df in tables:
        for _, row in df.iterrows():
            first = str(row.iloc[0]).lower() if len(row) > 0 else ""
            if "fgn" in first and "bond" in first:
                return row
    return None


def extract_turnover_from_pdf(pdf_path: Path) -> Optional[float]:
    tables = _extract_tables(pdf_path)
    row = _find_fgn_row(tables)
    if row is None:
        return None

    # Heuristic: second column is ₦'mm, third is $'mm
    if len(row) < 2:
        return None
    value = _clean_number(row.iloc[1])
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="data/FMDQ turnover reports")
    parser.add_argument("--out", default="data/raw/fmdq_turnover.csv")
    args = parser.parse_args()

    reports_dir = Path(args.reports_dir)
    rows = []
    for pdf in sorted(reports_dir.glob("*.pdf")):
        date = _parse_month_year_from_filename(pdf.name)
        turnover = extract_turnover_from_pdf(pdf)
        rows.append({"date": date, "turnover": turnover, "source_file": pdf.name})

    if not rows:
        raise SystemExit("No PDFs found in reports dir.")

    df = pd.DataFrame(rows)
    df = df.dropna(subset=["date"]).sort_values("date")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df[["date", "turnover"]].to_csv(args.out, index=False)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
