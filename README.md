# ADLO Terminal

ADLO Terminal is being refactored into the SRS-defined architecture for an African sovereign debt analytics desk:

- `backend/` FastAPI engine for public data ingestion, curve bootstrapping, and distress scoring
- `frontend/` Next.js client shell for curves, macro shocks, and relative-value visualization

The repo keeps the implementation lightweight and free-tier friendly. The backend is designed to work with public EOD data and graceful fallbacks when live sources are unavailable.

Supported demo countries:

- Nigeria
- South Africa
- Kenya
- Ghana

## Layout

- `backend/app/main.py` — FastAPI entrypoint and CORS/static wiring
- `backend/app/core/data_fetcher.py` — yfinance, World Bank, and scraper helpers
- `backend/app/core/quant_engine.py` — curve bootstrapping and distress math
- `backend/app/api/endpoints.py` — `/curves`, `/distress`, and `/stress` routes
- `frontend/src/app/` — Next.js app router pages and layout
- `frontend/src/components/` — dashboard blocks and controls
- `frontend/src/charts/` — Lightweight Charts setup helpers

## Backend setup

Install the backend dependencies:

```bash
pip install -r backend/requirements.txt
```

Run the API:

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

## Frontend setup

Install the frontend dependencies:

```bash
cd frontend
npm install
```

Run the client:

```bash
npm run dev
```

If you need the fastest presentation path, you can skip the Next.js client and use the bundled static dashboard served by the FastAPI app at `http://127.0.0.1:8000/`.

## API surface

- `GET /health`
- `GET /curves?country=Nigeria`
- `GET /distress?country=Nigeria`
- `POST /stress`
- `GET /rv`

## Notes

- The new structure is intentionally modular so the backend can be deployed independently from the client.
- The static fallback under `backend/app/static/` is the safest demo path if frontend package installation is delayed.
- Set `ADLO_LIVE_DATA=1` only if you want to try live public-source fetches; the default mode uses deterministic demo data for a stable presentation.
