#!/usr/bin/env bash
set -euo pipefail
python -m pip install --disable-pip-version-check -r requirements.txt
exec python app.py --host 0.0.0.0 --port 3000
