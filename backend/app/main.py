from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.endpoints import router as api_router


APP_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = APP_DIR.parents[2] / "frontend"
FRONTEND_PUBLIC = FRONTEND_DIR / "public"
FRONTEND_OUT = FRONTEND_DIR / "out"
STATIC_DIR = APP_DIR / "static"

app = FastAPI(title="ADLO Terminal", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

if FRONTEND_OUT.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_OUT), name="assets")
elif FRONTEND_PUBLIC.exists():
    app.mount("/public", StaticFiles(directory=FRONTEND_PUBLIC), name="public")
elif STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")


@app.get("/", response_model=None)
def index() -> object:
    index_file = FRONTEND_OUT / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    static_index = STATIC_DIR / "index.html"
    if static_index.exists():
        return FileResponse(static_index)
    return {
        "message": "ADLO Terminal backend is running.",
        "hint": "Build the Next.js client under frontend/ or use the bundled static fallback.",
    }
