import asyncio
from datetime import date

from db import Database
import bot


class FakeBotApi:
    def __init__(self):
        self.photos = []
        self.messages = []

    async def send_photo(self, chat_id, photo, caption):
        self.photos.append((chat_id, photo, caption))

    async def send_message(self, chat_id, text):
        self.messages.append((chat_id, text))


def run(coro):
    return asyncio.run(coro)


def test_add_coupon_reply_success():
    d = Database(":memory:")
    reply = run(bot.add_coupon_reply(d, "file1", "26.07.09 星巴克", "2026-07-02T10:00:00"))
    assert "已新增" in reply
    assert "星巴克" in reply
    assert "2026-07-09" in reply
    assert len(d.list_coupons()) == 1


def test_add_coupon_reply_bad_format():
    d = Database(":memory:")
    reply = run(bot.add_coupon_reply(d, "file1", None, "2026-07-02T10:00:00"))
    assert "格式" in reply
    assert d.list_coupons() == []


def test_list_reply_empty():
    d = Database(":memory:")
    assert run(bot.list_reply(d, date(2026, 7, 2))) == "目前沒有優惠券"


def test_del_reply_found_and_missing():
    d = Database(":memory:")
    code = d.add_coupon("f", "a", "2026-07-10", "2026-07-02T10:00:00")
    assert "已刪除" in run(bot.del_reply(d, code))
    assert "查無此碼" in run(bot.del_reply(d, "zzzz"))


def test_send_due_reminders_sends_for_thresholds():
    d = Database(":memory:")
    d.set_meta("chat_id", "555")
    d.add_coupon("f7", "七天", "2026-07-09", "2026-07-02T10:00:00")   # 7 -> send
    d.add_coupon("f4", "四天", "2026-07-06", "2026-07-02T10:00:00")   # 4 -> skip
    d.add_coupon("f0", "當天", "2026-07-02", "2026-07-02T10:00:00")   # 0 -> send
    api = FakeBotApi()
    count = run(bot.send_due_reminders(api, d, date(2026, 7, 2)))
    assert count == 2
    captions = " ".join(c for _, _, c in api.photos)
    assert "還有 7 天" in captions
    assert "今天到期" in captions


def test_send_due_reminders_no_chat_id():
    d = Database(":memory:")
    d.add_coupon("f7", "七天", "2026-07-09", "2026-07-02T10:00:00")
    api = FakeBotApi()
    assert run(bot.send_due_reminders(api, d, date(2026, 7, 2))) == 0
    assert api.photos == []


def test_run_daily_check_dedups_same_day():
    d = Database(":memory:")
    d.set_meta("chat_id", "555")
    d.add_coupon("f0", "當天", "2026-07-02", "2026-07-02T10:00:00")
    api = FakeBotApi()
    first = run(bot.run_daily_check(api, d, date(2026, 7, 2)))
    second = run(bot.run_daily_check(api, d, date(2026, 7, 2)))
    assert first == 1
    assert second == -1
    assert len(api.photos) == 1


class PartialFailBotApi(FakeBotApi):
    def __init__(self, fail_code):
        super().__init__()
        self.fail_code = fail_code

    async def send_photo(self, chat_id, photo, caption):
        if self.fail_code in caption:
            raise RuntimeError("boom")
        await super().send_photo(chat_id, photo, caption)


def test_send_due_reminders_continues_past_failure():
    d = Database(":memory:")
    d.set_meta("chat_id", "555")
    d.add_coupon("fx", "壞的", "2026-07-02", "2026-07-02T10:00:00")   # 0 -> send fails
    d.add_coupon("fy", "好的", "2026-07-09", "2026-07-02T10:00:00")   # 7 -> send ok
    api = PartialFailBotApi("壞的")
    count = run(bot.send_due_reminders(api, d, date(2026, 7, 2)))
    assert count == 1
    assert len(api.photos) == 1


def test_run_daily_check_advances_despite_send_failure():
    d = Database(":memory:")
    d.set_meta("chat_id", "555")
    d.add_coupon("fx", "壞的", "2026-07-02", "2026-07-02T10:00:00")
    api = PartialFailBotApi("壞的")
    first = run(bot.run_daily_check(api, d, date(2026, 7, 2)))
    second = run(bot.run_daily_check(api, d, date(2026, 7, 2)))
    assert first == 0            # nothing sent successfully
    assert second == -1          # but last_check_date advanced, so deduped


def _owner_ids(flt):
    # CommandHandler stores the User filter directly; the photo MessageHandler
    # wraps it in a _MergedFilter (base=PHOTO, and_filter=User). Walk to the
    # component exposing .user_ids.
    if getattr(flt, "user_ids", None) is not None:
        return flt.user_ids
    for part in (getattr(flt, "and_filter", None), getattr(flt, "base_filter", None)):
        if part is not None and getattr(part, "user_ids", None) is not None:
            return part.user_ids
    raise AssertionError("no User filter found")


def test_all_handlers_restricted_to_owner():
    handlers = bot.build_handlers(42)
    assert len(handlers) == 3
    for h in handlers:
        ids = _owner_ids(h.filters)
        assert 42 in ids
        assert 99 not in ids
