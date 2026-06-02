#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

from src.pipeline import run_pipeline
from src.token_checker import run_checks

if __name__ == "__main__":
    if not run_checks():
        raise SystemExit("Token check failed — fix credentials before running pipeline.")
    run_pipeline()
