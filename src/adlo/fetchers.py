"""Automatic source refreshers for the free ADLO data stack.

DMO and SARB are automated here because they expose public web endpoints
that can be queried without authentication. FMDQ remains manual because
the free turnover reports are still distributed as PDFs with less stable
public access patterns.
"""
from __future__ import annotations

import json
import re
import ssl
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from html import unescape
from pathlib import Path
from typing import Iterable
from urllib.parse import quote, urljoin
from urllib.request import urlopen

import pandas as pd

from .config import DATA_RAW, ROOT

DMO_AUCTION_LIST_URL = "https://www.dmo.gov.ng/fgn-bonds/bonds-auction-results"
DMO_BENCHMARK_LIST_URL = "https://www.dmo.gov.ng/fgn-bonds/fgn-bond-updates"
SARB_DOWNLOAD_URL = "https://www.resbank.co.za/bin/sarb/custom/downloadfacility"

DEFAULT_SSL_CONTEXT = ssl.create_default_context()
DEFAULT_SSL_CONTEXT.check_hostname = False
DEFAULT_SSL_CONTEXT.verify_mode = ssl.CERT_NONE


@dataclass
class RefreshResult:
    source: str
    status: str
    message: str
    artifacts: list[str]


def _http_get_text(url: str) -> str:
    response = urlopen(url, context=DEFAULT_SSL_CONTEXT, timeout=45)
    return response.read().decode("utf-8", "ignore")


def _http_get_bytes(url: str) -> bytes:
    response = urlopen(url, context=DEFAULT_SSL_CONTEXT, timeout=60)
    return response.read()


def _safe_filename(name: str) -> str:
    name = unescape(name).strip()
    name = re.sub(r"[\\/:*?\"<>|]+", "", name)
    return name


def _extract_doc_links(html: str, section_prefix: str) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    pattern = re.compile(
        rf'href="(?P<href>/{section_prefix}/[^"]+)"[^>]*title="(?P<title>[^"]+?\.pdf)"',
        re.IGNORECASE,
    )
    seen: set[str] = set()
    for match in pattern.finditer(html):
        href = urljoin("https://www.dmo.gov.ng", match.group("href"))
        title = _safe_filename(match.group("title"))
        key = f"{href}|{title}"
        if key in seen:
            continue
        seen.add(key)
        links.append((href, title))
    return links


def _extract_download_link(detail_html: str, detail_url: str) -> str | None:
    match = re.search(
        r'href="(?P<href>[^"]+/file)"[^>]*docman_download__button',
        detail_html,
        re.IGNORECASE,
    )
    if not match:
        return None
    return urljoin(detail_url, match.group("href"))


def _download_dmo_documents(
    list_url: str,
    destination: Path,
    section_prefix: str,
    limit: int,
) -> list[str]:
    destination.mkdir(parents=True, exist_ok=True)
    html = _http_get_text(list_url)
    detail_links = _extract_doc_links(html, section_prefix)[:limit]
    downloaded: list[str] = []

    for detail_url, title in detail_links:
        detail_html = _http_get_text(detail_url)
        download_url = _extract_download_link(detail_html, detail_url)
        if not download_url:
            continue
        output_path = destination / title
        output_path.write_bytes(_http_get_bytes(download_url))
        downloaded.append(str(output_path))

    return downloaded


def refresh_dmo(limit: int = 12) -> list[RefreshResult]:
    auction_dir = ROOT / "data" / "DMO auction results"
    benchmark_dir = ROOT / "data" / "DMO benchmark bond updates"

    auction_files = _download_dmo_documents(
        DMO_AUCTION_LIST_URL,
        auction_dir,
        "fgn-bonds/bonds-auction-results",
        limit,
    )
    benchmark_files = _download_dmo_documents(
        DMO_BENCHMARK_LIST_URL,
        benchmark_dir,
        "fgn-bonds/fgn-bond-updates",
        min(limit, 10),
    )

    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "convert_dmo_pdfs.py")],
        check=True,
        cwd=str(ROOT),
    )

    return [
        RefreshResult(
            source="DMO Auction Results",
            status="ok" if auction_files else "warning",
            message=f"Downloaded {len(auction_files)} auction PDFs and rebuilt CSV extracts.",
            artifacts=auction_files[:5],
        ),
        RefreshResult(
            source="DMO Benchmark Updates",
            status="ok" if benchmark_files else "warning",
            message=f"Downloaded {len(benchmark_files)} benchmark PDFs and rebuilt CSV extracts.",
            artifacts=benchmark_files[:5],
        ),
    ]


def refresh_sarb(
    version_code: str = "KBP2002M",
    start: str = "1986/05",
    end: str | None = None,
) -> RefreshResult:
    if end is None:
        today = date.today()
        end = f"{today.year}/{today.month:02d}"

    params = (
        f"onlineDownload=sSRSData"
        f"&sSRSDataTsCodes={quote(version_code)}"
        f"&sSRSDataFrequencyDescription=Monthly"
        f"&sSRSDataStartDate={quote(start)}"
        f"&sSRSDataEndDate={quote(end)}"
    )
    payload = _http_get_text(f"{SARB_DOWNLOAD_URL}?{params}")
    parsed = json.loads(payload)
    tables = parsed["xs:ssrsDataResult"]["diffgr:diffgram"]["TsObservations"]["Table"]
    if isinstance(tables, dict):
        tables = [tables]

    rows: list[dict[str, object]] = []
    for row in tables:
        period = str(row["Period"])
        rows.append(
            {
                "Date": f"{period[:4]}/{period[4:6]}",
                "Code": row["TimeSeriesCode"],
                "Description": row["LongDesc"],
                "Unit of Measure": row["UnitOfMeasure"],
                "Value": row["Value"],
            }
        )

    output = DATA_RAW / "sarb_bond_yields.csv"
    pd.DataFrame(rows).to_csv(output, index=False)
    return RefreshResult(
        source="SARB Yield Query",
        status="ok",
        message=f"Downloaded {len(rows)} monthly observations for {version_code}.",
        artifacts=[str(output)],
    )


def refresh_all_sources() -> list[RefreshResult]:
    results: list[RefreshResult] = []
    results.extend(refresh_dmo())
    results.append(refresh_sarb())
    results.append(
        RefreshResult(
            source="FMDQ Turnover",
            status="manual",
            message="Still manual on the free tier. Drop the latest turnover PDF or CSV into the project when available.",
            artifacts=[str(DATA_RAW / "fmdq_turnover.csv")],
        )
    )
    return results
