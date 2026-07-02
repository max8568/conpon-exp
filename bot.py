import logging
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import load_config
from db import Database
from formatting import format_list
from parser import ParseError, parse_caption
from reminder import days_until, reminder_text, should_remind

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_FORMAT_HINT = "格式錯誤,請附文字說明,例:26.07.09 星巴克買一送一"

_TZ = ZoneInfo("Asia/Taipei")


def _today() -> date:
    return datetime.now(_TZ).date()


# ---- 純邏輯(可單元測試,不依賴 telegram 型別) ----

async def add_coupon_reply(
    database: Database, file_id: str, caption: str | None, now_iso: str
) -> str:
    try:
        expiry, description = parse_caption(caption)
    except ParseError:
        return _FORMAT_HINT
    code = database.add_coupon(file_id, description, expiry, now_iso)
    return f"✅ 已新增 {code},到期日 {expiry}"


async def list_reply(database: Database, today: date) -> str:
    return format_list(database.list_coupons(), today)


async def del_reply(database: Database, code: str) -> str:
    if database.delete_coupon(code):
        return f"🗑 已刪除 {code}"
    return f"查無此碼:{code}"


async def send_due_reminders(bot_api, database: Database, today: date) -> int:
    chat_id = database.get_meta("chat_id")
    if chat_id is None:
        return 0
    sent = 0
    for c in database.list_coupons():
        if should_remind(c.expiry_date, today):
            days = days_until(c.expiry_date, today)
            try:
                await bot_api.send_photo(
                    chat_id=int(chat_id),
                    photo=c.file_id,
                    caption=reminder_text(c.description, c.expiry_date, c.code, days),
                )
                sent += 1
            except Exception:
                logger.exception("發送提醒失敗:coupon %s", c.code)
    return sent


async def run_daily_check(bot_api, database: Database, today: date) -> int:
    today_iso = today.isoformat()
    if database.get_meta("last_check_date") == today_iso:
        return -1
    sent = await send_due_reminders(bot_api, database, today)
    database.set_meta("last_check_date", today_iso)
    return sent


# ---- Telegram handlers(薄殼,委派給上面的純邏輯) ----

def _remember_chat(database: Database, update: Update) -> None:
    if update.effective_chat is not None:
        database.set_meta("chat_id", str(update.effective_chat.id))


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    database: Database = context.application.bot_data["db"]
    _remember_chat(database, update)
    photo = update.message.photo[-1]
    reply = await add_coupon_reply(
        database, photo.file_id, update.message.caption, datetime.now().isoformat()
    )
    await update.message.reply_text(reply)


async def handle_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    database: Database = context.application.bot_data["db"]
    _remember_chat(database, update)
    await update.message.reply_text(await list_reply(database, _today()))


async def handle_del(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    database: Database = context.application.bot_data["db"]
    _remember_chat(database, update)
    if not context.args:
        await update.message.reply_text("用法:/del <唯一碼>")
        return
    await update.message.reply_text(await del_reply(database, context.args[0]))


async def _daily_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    database: Database = context.application.bot_data["db"]
    await run_daily_check(context.bot, database, _today())


async def _post_init(application: Application) -> None:
    database: Database = application.bot_data["db"]
    # 啟動時當天補發(去重),並發送啟動通知
    await run_daily_check(application.bot, database, _today())
    chat_id = database.get_meta("chat_id")
    if chat_id is not None:
        await application.bot.send_message(
            chat_id=int(chat_id), text="🤖 優惠券提醒機器人已啟動"
        )


def main() -> None:
    cfg = load_config()
    database = Database(cfg.db_path)

    owner_filter = filters.User(user_id=cfg.owner_id)
    app = Application.builder().token(cfg.bot_token).post_init(_post_init).build()
    app.bot_data["db"] = database

    async def _on_error(update, context):
        logger.exception("處理更新時發生例外", exc_info=context.error)

    app.add_error_handler(_on_error)

    app.add_handler(MessageHandler(filters.PHOTO & owner_filter, handle_photo))
    app.add_handler(CommandHandler("list", handle_list, filters=owner_filter))
    app.add_handler(CommandHandler("del", handle_del, filters=owner_filter))

    app.job_queue.run_daily(
        _daily_job, time=time(hour=0, minute=0, tzinfo=_TZ)
    )

    app.run_polling()


if __name__ == "__main__":
    main()
