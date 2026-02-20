"""Configuration globale et chargement des variables d'environnement."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "results"

OPENROUTER_API_KEY: str = os.environ.get("OPENROUTER_API_KEY", "")
JUDGE_MODEL: str = os.environ.get("JUDGE_MODEL", "anthropic/claude-sonnet-4-20250514")
MAX_CONCURRENT: int = int(os.environ.get("MAX_CONCURRENT", "5"))
