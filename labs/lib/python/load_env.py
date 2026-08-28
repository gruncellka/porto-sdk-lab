"""Load lab credentials from repo root `.env` only."""

from __future__ import annotations

import importlib
import os
from pathlib import Path


def load_lab_env() -> None:
    """Load `porto-sdk-lab/.env` (shared by Python + TypeScript labs)."""
    repo_root = Path(__file__).resolve().parents[3]
    try:
        dotenv = importlib.import_module("dotenv")
    except ModuleNotFoundError:
        pass
    else:
        repo_env = repo_root / ".env"
        if repo_env.exists():
            dotenv.load_dotenv(repo_env, override=False)

    if not os.getenv("PORTO_DATA_PATH"):
        data_root = repo_root / "resources" / "porto-data" / "porto_data"
        if data_root.exists():
            os.environ["PORTO_DATA_PATH"] = str(data_root)

