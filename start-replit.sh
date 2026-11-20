#!/usr/bin/env bash
set -euo pipefail
runtime=.replit-venv
if command -v uv >/dev/null 2>&1; then
  if [[ ! -x "$runtime/bin/python" ]]; then uv venv --python python "$runtime"; fi
  uv pip install --python "$runtime/bin/python" -r requirements.txt
else
  if [[ ! -x "$runtime/bin/python" ]]; then python -m venv "$runtime"; fi
  "$runtime/bin/python" -m pip install --disable-pip-version-check -r requirements.txt
fi
exec "$runtime/bin/python" app.py --host 0.0.0.0 --port "${PORT:-3000}"
