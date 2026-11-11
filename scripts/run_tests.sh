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
"$PY" -m pytest \
  --junitxml=reports/junit.xml \
  --cov=app \
  --cov-branch \
  --cov-report=term-missing \
  --cov-report=xml:reports/coverage.xml \
  --html=reports/pytest-report.html \
  --self-contained-html \
  --alluredir=reports/allure-results \
  | tee reports/pytest-output.txt
code=${PIPESTATUS[0]}
printf '%s\n' "$code" > reports/pytest-exit-code.txt
"$PY" scripts/build_report.py
build_code=$?
"$PY" scripts/scrub_reports.py
scrub_code=$?
set -e
if [[ "$scrub_code" -ne 0 ]]; then
  exit "$scrub_code"
fi
if [[ "$build_code" -ne 0 ]]; then
  exit "$build_code"
fi
exit "$code"
