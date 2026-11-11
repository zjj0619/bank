"""删除并重建本地模拟数据库。必须带 --yes 才会执行。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.maintenance import reset_database
from app.secrets import load_local_env


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--yes" not in args:
        print("This deletes the local simulated database and every entry. It cannot be undone.")
        print("To proceed: python scripts/reset_db.py --yes")
        return 2
    load_local_env()
    path = reset_database()
    print(f"Rebuilt the simulated database: {path}")
    print("Fictional users: demo_zhang, demo_li, demo_wang")
    print("Opening balances: 10000.00, 5000.00, and 2580.25 CNY")
    print("The passphrases were not printed. Use BANK_SEED_PASSWORD_DEMO_ZHANG, BANK_SEED_PASSWORD_DEMO_LI, and BANK_SEED_PASSWORD_DEMO_WANG, or the local .demo_credentials file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
