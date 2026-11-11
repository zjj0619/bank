from __future__ import annotations

import pytest

from tests.helpers import make_app


@pytest.fixture
def app(tmp_path, monkeypatch):
    for name in (
        "BANK_SEED_PASSWORD",
        "BANK_SEED_PASSWORD_DEMO_ZHANG",
        "BANK_SEED_PASSWORD_DEMO_LI",
        "BANK_SEED_PASSWORD_DEMO_WANG",
        "BANK_DATABASE",
    ):
        monkeypatch.delenv(name, raising=False)
    return make_app(tmp_path)


@pytest.fixture
def client(app):
    return app.test_client()
