"""Vercel serverless entrypoint for /api/health."""

import sys
from pathlib import Path


API_DIR = Path(__file__).resolve().parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from _app import app  # noqa: E402
