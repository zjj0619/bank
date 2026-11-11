#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p /opt/cursor/artifacts
destination="/opt/cursor/artifacts/chengbu-sim-bank-card-surfaces.zip"
rm -f "$destination"
zip -r "$destination" . \
  -x ".git/*" \
  -x ".venv/*" \
  -x "venv/*" \
  -x "*/__pycache__/*" \
  -x "__pycache__/*" \
  -x ".pytest_cache/*" \
  -x ".mypy_cache/*" \
  -x "htmlcov/*" \
  -x ".coverage" \
  -x ".demo_credentials" \
  -x ".session_secret" \
  -x ".env" \
  -x "*.sqlite3" \
  -x "*.db" \
  -x "*.sqlite3-wal" \
  -x "*.sqlite3-shm" \
  -x "data/*.sqlite3" \
  -x "data/*.sqlite3-wal" \
  -x "data/*.sqlite3-shm" \
  -x "*.pyc"
python3 - <<'PY'
import zipfile
from pathlib import Path
archive = zipfile.ZipFile("/opt/cursor/artifacts/chengbu-sim-bank-card-surfaces.zip")
names = archive.namelist()
banned = [name for name in names if name.endswith((".sqlite3", ".sqlite3-wal", ".sqlite3-shm", ".db")) or name.endswith(".demo_credentials") or name.endswith(".session_secret") or "/.venv/" in name or name.startswith(".venv/") or "account-light-" in name]
if banned:
    raise SystemExit("压缩包含有不该发布的文件: " + ", ".join(banned[:20]))
print(f"entries {len(names)}")
PY
echo "$destination"
