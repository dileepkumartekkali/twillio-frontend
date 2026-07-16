"""Vercel's Python runtime looks for an ASGI `app` under api/. Reuses the
same FastAPI app as local dev (server.py) instead of duplicating it."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import app  # noqa: E402
