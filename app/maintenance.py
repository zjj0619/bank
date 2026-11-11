"""显式重建本地演示库。调用方必须传入已确认的参数。"""

from __future__ import annotations

from pathlib import Path

from app.db import init_db
from app.paths import resolve_database_path


def remove_sqlite_files(path: Path) -> None:
    for candidate in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")):
        if candidate.exists():
            candidate.unlink()


def reset_database() -> Path:
    path = resolve_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    remove_sqlite_files(path)
    from app import create_app

    application = create_app({"DATABASE": str(path)})
    with application.app_context():
        init_db(seed=True)
    return path
