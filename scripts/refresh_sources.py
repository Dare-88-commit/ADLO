"""Refresh the automatically supported ADLO data sources.

This script updates:
- DMO auction PDFs and benchmark PDFs, then rebuilds CSV extracts
- SARB monthly yield series

FMDQ turnover remains manual on the free tier.
"""
from __future__ import annotations

import json

from adlo.fetchers import refresh_all_sources


def main() -> None:
    results = refresh_all_sources()
    print(json.dumps([result.__dict__ for result in results], indent=2))


if __name__ == "__main__":
    main()
