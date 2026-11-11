"""启动本地模拟银行。不会打印演示口令。"""

from __future__ import annotations

import os

from app import create_app
from app.db import init_db
from app.paths import CREDENTIALS_FILE
from app.secrets import load_local_env


def main() -> None:
    load_local_env()
    application = create_app()
    with application.app_context():
        init_db(seed=True)
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "47653"))
    print(f"Linden Ledger is running at http://127.0.0.1:{port}")
    print("This is a coursework simulation. It is not a bank and it does not move real funds.")
    configured = (
        "BANK_SEED_PASSWORD_DEMO_ZHANG",
        "BANK_SEED_PASSWORD_DEMO_LI",
        "BANK_SEED_PASSWORD_DEMO_WANG",
    )
    if all(os.environ.get(name, "").strip() for name in configured):
        print("Passphrase source: one environment variable per demo account. This program does not print them.")
    elif CREDENTIALS_FILE.exists():
        print(f"Passphrase source: local file {CREDENTIALS_FILE.name}. This program does not print it. Do not commit that file.")
    application.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)


if __name__ == "__main__":
    main()
