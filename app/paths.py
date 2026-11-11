"""项目路径。数据库和密钥文件都留在本机，不随源码提交。"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DEFAULT_DATABASE = DATA_DIR / "bank.sqlite3"
CREDENTIALS_FILE = ROOT / ".demo_credentials"
SECRET_FILE = ROOT / ".session_secret"
ENV_FILE = ROOT / ".env"


def resolve_database_path() -> Path:
    raw = os.environ.get("BANK_DATABASE", "").strip()
    path = Path(raw) if raw else DEFAULT_DATABASE
    if not path.is_absolute():
        path = ROOT / path
    return path
