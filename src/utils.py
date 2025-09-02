from __future__ import annotations
import os, yaml, logging
from datetime import datetime
from dateutil import tz

def load_cfg(path: str) -> dict:
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)
    return cfg

def setup_logger(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

def now_str(tz_name: str) -> str:
    tzinfo = tz.gettz(tz_name)
    return datetime.now(tzinfo).strftime("%Y-%m-%d %H:%M:%S %Z")

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)
