from datetime import date
from db import Coupon
from formatting import format_list


def _c(code, desc, expiry):
    return Coupon(code=code, file_id="f", description=desc,
                  expiry_date=expiry, created_at="2026-07-01T00:00:00")


def test_empty():
    assert format_list([], date(2026, 7, 2)) == "目前沒有優惠券"


def test_future_and_expired_lines():
    coupons = [
        _c("c1x8", "麥當勞", "2026-06-30"),
        _c("a3f9", "星巴克", "2026-07-09"),
    ]
    out = format_list(coupons, date(2026, 7, 2))
    lines = out.splitlines()
    assert lines[0] == "❌ 2026-06-30 (已過期) 麥當勞  c1x8"
    assert lines[1] == "📅 2026-07-09  星巴克  a3f9"
