# ADLO

ADLO is a presentation-ready African debt market intelligence demo built for DCM, syndicate, and macro-risk conversations. It takes free official public data, turns it into a proxy liquidity-stress engine, and presents bankers with an issuance window score, liquidity-hole probability, premium guidance, and execution sizing advice.

The project is intentionally opinionated: it does not pretend that free data can deliver true tick-level VPIN, but it does turn the available public releases into a much stronger narrative than a simple charting prototype.

## What the system does

- Tracks Nigeria and South Africa sovereign debt conditions using free official data.
- Converts auction pressure, turnover drought, and yield shock into a composite liquidity-stress regime.
- Produces a banker-facing decision layer:
  - `Issuance window score`
  - `Liquidity-hole probability`
  - `Liquidity premium`
  - `Executable now`
  - `Phased days`
  - `Sovereign pulse`
- Compares the latest regime to any selected historical date.
- Surfaces source health so the demo is honest about what is automated and what is still manual.

## Current data stack

- `DMO auction results`
  - Automated refresh supported
  - Source: official DMO website
- `DMO benchmark bond updates`
  - Automated refresh supported
  - Source: official DMO website
- `SARB bond yields (KBP2002M)`
  - Automated refresh supported
  - Source: official Reserve Bank online download facility
- `FMDQ turnover`
  - Manual on the free tier
  - Still required for the strongest Nigeria secondary-liquidity read

## Project layout

- [src/adlo/app.py](/home/rator/Documents/ADLO/src/adlo/app.py)
  FastAPI app and API endpoints.
- [src/adlo/service.py](/home/rator/Documents/ADLO/src/adlo/service.py)
  Core market engine, scoring logic, execution advice, and dashboard packaging.
- [src/adlo/proxy_vpin.py](/home/rator/Documents/ADLO/src/adlo/proxy_vpin.py)
  Free-data proxy signal construction.
- [src/adlo/fetchers.py](/home/rator/Documents/ADLO/src/adlo/fetchers.py)
  Automatic DMO and SARB refreshers.
- [src/adlo/web/index.html](/home/rator/Documents/ADLO/src/adlo/web/index.html)
  Demo interface markup.
- [src/adlo/web/styles.css](/home/rator/Documents/ADLO/src/adlo/web/styles.css)
  Blue-and-white presentation styling.
- [src/adlo/web/app.js](/home/rator/Documents/ADLO/src/adlo/web/app.js)
  Frontend orchestration for the dashboard.
- [scripts/refresh_sources.py](/home/rator/Documents/ADLO/scripts/refresh_sources.py)
  One-command source refresh for DMO and SARB.
- [docs/DATA_SOURCES.md](/home/rator/Documents/ADLO/docs/DATA_SOURCES.md)
  Source documentation and refresh notes.
- [docs/DEMO_GUIDE.md](/home/rator/Documents/ADLO/docs/DEMO_GUIDE.md)
  Demo flow, product narrative, and limitations.

## Setup

Create or activate the local virtual environment, then install the requirements:

```bash
.venv/bin/pip install -r requirements.txt
```

## Run the app

```bash
PYTHONPATH=src .venv/bin/python scripts/run_server.py
```

Open:

```text
http://127.0.0.1:8050
```

## Refresh data

Automatic refresh for DMO and SARB:

```bash
PYTHONPATH=src .venv/bin/python scripts/refresh_sources.py
```

Manual FMDQ turnover remains:

- place the latest turnover CSV at `data/raw/fmdq_turnover.csv`, or
- place the PDF in `data/FMDQ turnover reports/` and run:

```bash
PYTHONPATH=src .venv/bin/python scripts/convert_fmdq_pdfs.py
```

## Terminal summary

If you want a quick CLI readout instead of the UI:

```bash
PYTHONPATH=src .venv/bin/python scripts/run_proxy.py
```

## API endpoints

- `GET /api/health`
- `GET /api/overview`
- `GET /api/dashboard?market=Nigeria%20(FGN)&desired_size=100&date=2025-07-01`
- `GET /api/series/{market}`
- `POST /api/refresh`

## What changed in this revamp

- Replaced the thin single-number prototype with a banker-facing market engine.
- Added automatic refreshers for the two sources we can reliably automate for free.
- Reframed the output around liquidity holes, issuance windows, and execution guidance.
- Rebuilt the interface in a blue-and-white visual system designed to feel presentation-ready.
- Added source-health visibility so the demo is explicit about automation and free-tier gaps.

## Important limitation

ADLO is still a free-data proxy system. It is stronger now, but it is not true real-time VPIN. The biggest remaining constraint is the absence of paid tick, quote, and order-book data, plus the fact that FMDQ turnover remains manual on the free tier.
