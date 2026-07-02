import pytest
from config import load_config


def test_load_config_reads_env(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "tok")
    monkeypatch.setenv("OWNER_ID", "42")
    cfg = load_config()
    assert cfg.bot_token == "tok"
    assert cfg.owner_id == 42
    assert cfg.db_path == "coupons.db"


def test_load_config_missing_token_raises(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.setenv("OWNER_ID", "42")
    with pytest.raises(RuntimeError):
        load_config()


def test_load_config_missing_owner_raises(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "tok")
    monkeypatch.delenv("OWNER_ID", raising=False)
    with pytest.raises(RuntimeError):
        load_config()
