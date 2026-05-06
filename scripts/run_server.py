"""Run the ADLO API + frontend.

Usage:
  PYTHONPATH=src python scripts/run_server.py
"""
from __future__ import annotations

import os
import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("ADLO_PORT", "8050"))
    uvicorn.run("adlo.app:app", host="127.0.0.1", port=port, reload=False)
