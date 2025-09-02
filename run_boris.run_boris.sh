x#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# activate venv
if [ -f ".venv/bin/activate" ]; then
  source ".venv/bin/activate"
fi

# ensure PYTHONPATH so src/ works
export PYTHONPATH=.

# run the scanner
python -m src.boris_scanner

# build the HTML/MD report
python src/boris_report.py || true
