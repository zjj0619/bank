"""English copy and locally bundled images. Amounts and account ids stay unchanged."""

from __future__ import annotations

import pytest

from app.paths import ROOT

pytestmark = pytest.mark.acceptance

CHINESE_UI = ("模拟银行", "登录", "存入", "支取", "转账", "明细", "余额")


def test_english_login_and_local_assets(client):
    page = client.get("/login")
    html = page.get_data(as_text=True)
    assert page.status_code == 200
    assert 'lang="en"' in html
    assert "Linden Ledger" in html
    assert "Mingyuan Zhang" in html
    assert "Wanqing Li" in html
    assert "Qinian Wang" in html
    assert "SIM-1001" in html
    assert "10,000.00" in html
    assert "5,000.00" in html
    assert "2,580.25" in html
    assert "/static/images/login-arch-864.jpg" in html
    assert "/static/images/login-arch-864.webp" in html
    assert "/static/images/mark.svg" in html
    for word in CHINESE_UI:
        assert word not in html
    assert "BANK_SEED_PASSWORD" not in html
    assert "share one" not in html.lower()
    assert "/static/images/atrium-tall-800.jpg" in html
    assert "/static/images/chip-plate-480.jpg" in html
    photo = ROOT / "app/static/images/login-arch-864.jpg"
    source = ROOT / "app/static/images/source/bank-editorial-architecture.jpg"
    atrium = ROOT / "app/static/images/atrium-tall-800.jpg"
    font = ROOT / "app/static/fonts/newsreader-latin-400.woff2"
    webp = ROOT / "app/static/images/login-arch-864.webp"
    assert photo.stat().st_size > 20_000
    assert source.stat().st_size > 20_000
    assert atrium.stat().st_size > 20_000
    assert font.stat().st_size > 1_000
    assert photo.read_bytes().startswith(b"\xff\xd8")
    assert atrium.read_bytes().startswith(b"\xff\xd8")
    assert webp.read_bytes().startswith(b"RIFF")


def test_signed_in_pages_are_english(client):
    from tests.helpers import FIXTURE_PASSWORD

    login_page = client.get("/login")
    token = login_page.get_data(as_text=True).split('name="csrf_token" value="', 1)[1].split('"', 1)[0]
    client.post(
        "/login",
        data={"username": "demo_zhang", "password": FIXTURE_PASSWORD, "csrf_token": token},
    )
    for path in ("/", "/deposit", "/withdraw", "/transfer", "/history", "/password"):
        page = client.get(path)
        html = page.get_data(as_text=True)
        assert page.status_code == 200, path
        assert "Not a bank" in html
        assert "Linden Ledger" in html
        for word in CHINESE_UI:
            assert word not in html, (path, word)
    overview = client.get("/")
    overview_html = overview.get_data(as_text=True)
    assert "/static/images/dashboard-sculpture-1152.jpg" in overview_html
    assert "/static/images/dashboard-sculpture-1152.webp" in overview_html
    assert "/static/images/card-face-1400.jpg" in overview_html
    assert "/static/images/chip-plate-480.jpg" in overview_html
    assert "account-light-" not in overview_html
    sculpture = ROOT / "app/static/images/dashboard-sculpture-1152.jpg"
    source = ROOT / "app/static/images/source/bank-dashboard-sculpture-yellow.jpg"
    assert sculpture.read_bytes().startswith(b"\xff\xd8")
    assert source.read_bytes().startswith(b"\xff\xd8")
    assert not (ROOT / "app/static/images/account-light-1100.jpg").exists()
    deposit = client.get("/deposit")
    assert "/static/images/deposit-still-960.jpg" in deposit.get_data(as_text=True)
    assert "/static/images/withdraw-hall-960.jpg" in client.get("/withdraw").get_data(as_text=True)
    assert "/static/images/transfer-arcs-960.jpg" in client.get("/transfer").get_data(as_text=True)
    assert "/static/images/activity-stairs-1400.jpg" in client.get("/history").get_data(as_text=True)
    history = client.get("/history")
    assert "Opening balance for the simulation" in history.get_data(as_text=True)
    assert "10,000.00" in client.get("/").get_data(as_text=True)
