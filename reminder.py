from datetime import date

REMIND_DAYS = {7, 3, 1, 0}


def days_until(expiry_date: str, today: date) -> int:
    expiry = date.fromisoformat(expiry_date)
    return (expiry - today).days


def should_remind(expiry_date: str, today: date) -> bool:
    return days_until(expiry_date, today) in REMIND_DAYS


def is_expired(expiry_date: str, today: date) -> bool:
    return days_until(expiry_date, today) < 0


def reminder_text(description: str, expiry_date: str, code: str, days: int) -> str:
    if days == 0:
        header = "⚠️ 今天到期!"
    else:
        header = f"⏰ 還有 {days} 天到期!"
    return f"{header}\n{description}\n到期日 {expiry_date}\n唯一碼 {code}"
