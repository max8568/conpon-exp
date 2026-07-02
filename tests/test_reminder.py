from datetime import date
from reminder import days_until, should_remind, reminder_text, is_expired


def test_days_until():
    assert days_until("2026-07-09", date(2026, 7, 2)) == 7
    assert days_until("2026-07-02", date(2026, 7, 2)) == 0
    assert days_until("2026-06-30", date(2026, 7, 2)) == -2


def test_should_remind_thresholds():
    today = date(2026, 7, 2)
    assert should_remind("2026-07-09", today) is True   # 7
    assert should_remind("2026-07-05", today) is True   # 3
    assert should_remind("2026-07-03", today) is True   # 1
    assert should_remind("2026-07-02", today) is True   # 0
    assert should_remind("2026-07-06", today) is False  # 4
    assert should_remind("2026-06-30", today) is False  # expired


def test_reminder_text_future():
    txt = reminder_text("星巴克", "2026-07-09", "a3f9", 7)
    assert "還有 7 天到期" in txt
    assert "星巴克" in txt
    assert "2026-07-09" in txt
    assert "a3f9" in txt


def test_reminder_text_today():
    txt = reminder_text("星巴克", "2026-07-02", "a3f9", 0)
    assert "今天到期" in txt


def test_is_expired():
    today = date(2026, 7, 2)
    assert is_expired("2026-06-30", today) is True
    assert is_expired("2026-07-02", today) is False
