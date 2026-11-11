#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p reports docs/screenshots
PY="${PYTHON:-}"
if [[ -z "$PY" ]]; then
  if [[ -x .venv/bin/python ]]; then
    PY=".venv/bin/python"
  else
    PY="python3"
  fi
fi
set +e
"$PY" -m pytest --junitxml=reports/junit.xml --cov=app --cov-report=term-missing --cov-report=xml:reports/coverage.xml | tee reports/pytest-output.txt
code=${PIPESTATUS[0]}
set -e
printf '%s\n' "$code" > reports/pytest-exit-code.txt
"$PY" scripts/build_report.py
exit "$code"
