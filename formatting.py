from datetime import date

from db import Coupon
from reminder import is_expired


def format_list(coupons: list[Coupon], today: date) -> str:
    if not coupons:
        return "目前沒有優惠券"
    lines = []
    for c in coupons:
        if is_expired(c.expiry_date, today):
            lines.append(f"❌ {c.expiry_date} (已過期) {c.description}  {c.code}")
        else:
            lines.append(f"📅 {c.expiry_date}  {c.description}  {c.code}")
    return "\n".join(lines)
