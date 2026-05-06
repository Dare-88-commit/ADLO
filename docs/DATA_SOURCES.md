# ADLO Data Sources

ADLO uses free official public sources wherever possible. The project now automates the sources that are stable enough to refresh programmatically and keeps the remaining free-tier constraint explicit.

## Automated sources

### DMO auction results

- Purpose: Nigeria auction pressure and primary market imbalance
- Listing page: `https://www.dmo.gov.ng/fgn-bonds/bonds-auction-results`
- Refresh mode: automatic
- Local outputs:
  - `data/DMO auction results/`
  - `data/raw/dmo_auction_results.csv`

### DMO benchmark bond updates

- Purpose: benchmark bond reference context
- Listing page: `https://www.dmo.gov.ng/fgn-bonds/fgn-bond-updates`
- Refresh mode: automatic
- Local outputs:
  - `data/DMO benchmark bond updates/`
  - `data/raw/dmo_benchmark_bonds.csv`

### SARB yield series

- Purpose: South Africa 5y-10y nominal bond yield stress
- Series used: `KBP2002M`
- Refresh mode: automatic
- Endpoint flow:
  - official online statistical query page
  - official download facility endpoint
- Local output:
  - `data/raw/sarb_bond_yields.csv`

## Manual source

### FMDQ turnover

- Purpose: Nigeria secondary-market turnover drought
- Source page: `https://fmdqgroup.com/exchange/market-turnover/`
- Refresh mode: manual on the free tier
- Local output:
  - `data/raw/fmdq_turnover.csv`

If you have the turnover PDFs, place them in:

- `data/FMDQ turnover reports/`

Then run:

```bash
PYTHONPATH=src .venv/bin/python scripts/convert_fmdq_pdfs.py
```

## Refresh commands

Refresh the automated stack:

```bash
PYTHONPATH=src .venv/bin/python scripts/refresh_sources.py
```

Rebuild the DMO CSVs from downloaded PDFs:

```bash
PYTHONPATH=src .venv/bin/python scripts/convert_dmo_pdfs.py
```

## Why FMDQ is still manual

The free FMDQ turnover materials are still distributed in a way that is less stable for unattended public scraping than the DMO and SARB flows. The paid path would solve this with proper market data access, but the free public demo keeps FMDQ as a manual attachment.
