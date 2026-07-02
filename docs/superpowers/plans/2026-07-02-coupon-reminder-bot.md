# 優惠券到期提醒 Telegram 機器人 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立一個個人用 Telegram 機器人,接收「照片 + `yy.mm.dd 描述`」新增優惠券,每日 00:00 於到期前 7/3/1 天及當天發送提醒,並支援 `/list` 與 `/del`。

**Architecture:** 單一 Python 程序,`python-telegram-bot` v21 以 polling 接收訊息、內建 `JobQueue.run_daily` 排程每日檢查。資料存於 SQLite 單檔。程式碼切分為純函式模組(`parser`、`reminder`)、資料層(`db`)、設定(`config`)與 Telegram 接線層(`bot`),純函式與資料層以單元測試涵蓋。

**Tech Stack:** Python 3.10+、python-telegram-bot v21(含 `[job-queue]` extra)、SQLite(標準庫 `sqlite3`)、pytest、python-dotenv。

## Global Constraints

- 單一使用者:所有優惠券共用一份清單;操作限白名單 `OWNER_ID`,其他 user_id 訊息一律忽略。
- 日期儲存格式一律 `YYYY-MM-DD`(字串);輸入接受 `yy.mm.dd` 與 `yyyy.mm.dd`。
- 唯一碼:4 碼、字元集 `[a-z0-9]`,隨機且確保 DB 內唯一。
- 提醒門檻:剩餘天數 ∈ {7, 3, 1, 0};< 0 為已過期,不提醒但保留。
- 不做跨日補發;每日檢查以 `meta.last_check_date` 同日去重。
- 提醒與清單使用本機時區的「今天」(`datetime.date.today()`)。
- Bot Token 與 OWNER_ID 由環境變數 / `.env` 提供,絕不寫入原始碼或 commit。

---

### Task 1: 專案骨架與設定

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `config.py`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`

**Interfaces:**
- Consumes: 無(第一個任務)。
- Produces:
  - `config.load_config() -> Config`,其中 `Config` 為 dataclass:`bot_token: str`、`owner_id: int`、`db_path: str`(預設 `"coupons.db"`)。缺 `BOT_TOKEN` 或 `OWNER_ID` 時 raise `RuntimeError`。

- [ ] **Step 1: 建立依賴與忽略清單**

`requirements.txt`:
```
python-telegram-bot[job-queue]==21.6
python-dotenv==1.0.1
pytest==8.3.3
```

`.gitignore`:
```
__pycache__/
*.pyc
.env
coupons.db
.venv/
venv/
```

`.env.example`:
```
BOT_TOKEN=123456:your-telegram-bot-token
OWNER_ID=123456789
```

- [ ] **Step 2: 寫失敗測試**

`tests/__init__.py`:(空檔)

`tests/test_config.py`:
```python
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
```

- [ ] **Step 3: 執行測試確認失敗**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL(`ModuleNotFoundError: No module named 'config'`)

- [ ] **Step 4: 實作 config.py**

`config.py`:
```python
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    bot_token: str
    owner_id: int
    db_path: str = "coupons.db"


def load_config() -> Config:
    token = os.environ.get("BOT_TOKEN")
    owner = os.environ.get("OWNER_ID")
    if not token:
        raise RuntimeError("缺少環境變數 BOT_TOKEN")
    if not owner:
        raise RuntimeError("缺少環境變數 OWNER_ID")
    return Config(
        bot_token=token,
        owner_id=int(owner),
        db_path=os.environ.get("DB_PATH", "coupons.db"),
    )
```

- [ ] **Step 5: 執行測試確認通過**

Run: `python -m pytest tests/test_config.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .gitignore .env.example config.py tests/__init__.py tests/test_config.py
git commit -m "feat: project scaffold and config loader"
```

---

### Task 2: caption 解析(純函式)

**Files:**
- Create: `parser.py`
- Create: `tests/test_parser.py`

**Interfaces:**
- Consumes: 無。
- Produces:
  - `parser.ParseError(Exception)`。
  - `parser.parse_caption(caption: str | None) -> tuple[str, str]`:回傳 `(expiry_date, description)`,`expiry_date` 為 `YYYY-MM-DD`。輸入為 `None`/空白、無法解析日期、或日期後無描述時 raise `ParseError`。
  - 兩位數年份 `yy` 一律解讀為 `20yy`。

- [ ] **Step 1: 寫失敗測試**

`tests/test_parser.py`:
```python
import pytest
from parser import parse_caption, ParseError


def test_parse_two_digit_year():
    assert parse_caption("26.07.09 星巴克買一送一") == ("2026-07-09", "星巴克買一送一")


def test_parse_four_digit_year():
    assert parse_caption("2026.07.09 全家咖啡") == ("2026-07-09", "全家咖啡")


def test_parse_strips_extra_whitespace():
    assert parse_caption("26.7.9   麥當勞  ") == ("2026-07-09", "麥當勞")


def test_none_raises():
    with pytest.raises(ParseError):
        parse_caption(None)


def test_empty_raises():
    with pytest.raises(ParseError):
        parse_caption("   ")


def test_no_description_raises():
    with pytest.raises(ParseError):
        parse_caption("26.07.09")


def test_bad_date_raises():
    with pytest.raises(ParseError):
        parse_caption("hello 星巴克")


def test_invalid_calendar_date_raises():
    with pytest.raises(ParseError):
        parse_caption("26.13.40 描述")
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python -m pytest tests/test_parser.py -v`
Expected: FAIL(`ModuleNotFoundError: No module named 'parser'` 或 import 錯誤)

- [ ] **Step 3: 實作 parser.py**

`parser.py`:
```python
import re
from datetime import date

_DATE_RE = re.compile(r"^\s*(\d{2,4})\.(\d{1,2})\.(\d{1,2})\s*(.*)$", re.DOTALL)


class ParseError(Exception):
    pass


def parse_caption(caption: str | None) -> tuple[str, str]:
    if not caption or not caption.strip():
        raise ParseError("沒有文字說明")
    m = _DATE_RE.match(caption)
    if not m:
        raise ParseError("無法解析日期")
    y, mo, d, desc = m.groups()
    year = int(y)
    if year < 100:
        year += 2000
    try:
        parsed = date(year, int(mo), int(d))
    except ValueError as exc:
        raise ParseError("日期不合法") from exc
    description = desc.strip()
    if not description:
        raise ParseError("沒有描述")
    return parsed.isoformat(), description
```

- [ ] **Step 4: 執行測試確認通過**

Run: `python -m pytest tests/test_parser.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add parser.py tests/test_parser.py
git commit -m "feat: caption parser for date and description"
```

---

### Task 3: 資料層 db.py(SQLite)

**Files:**
- Create: `db.py`
- Create: `tests/test_db.py`

**Interfaces:**
- Consumes: 無(不依賴 config;呼叫端傳入路徑)。
- Produces:
  - `db.Coupon` dataclass:`code: str`、`file_id: str`、`description: str`、`expiry_date: str`、`created_at: str`。
  - `db.Database(path: str)`:建構時建立資料表(若不存在)。
    - `add_coupon(file_id: str, description: str, expiry_date: str, now_iso: str) -> str`:產生唯一 4 碼短碼,寫入,回傳該碼。
    - `list_coupons() -> list[Coupon]`:依 `expiry_date` 由近到遠排序。
    - `delete_coupon(code: str) -> bool`:刪除成功回 `True`,查無回 `False`。
    - `get_meta(key: str) -> str | None`、`set_meta(key: str, value: str) -> None`。
  - 短碼字元集 `abcdefghijklmnopqrstuvwxyz0123456789`,長度 4。

- [ ] **Step 1: 寫失敗測試**

`tests/test_db.py`:
```python
from db import Database


def make_db():
    return Database(":memory:")


def test_add_and_list_sorted_by_expiry():
    d = make_db()
    d.add_coupon("f1", "晚到期", "2026-08-01", "2026-07-02T10:00:00")
    d.add_coupon("f2", "早到期", "2026-07-10", "2026-07-02T10:00:00")
    coupons = d.list_coupons()
    assert [c.description for c in coupons] == ["早到期", "晚到期"]


def test_add_returns_unique_code():
    d = make_db()
    c1 = d.add_coupon("f1", "a", "2026-07-10", "2026-07-02T10:00:00")
    c2 = d.add_coupon("f2", "b", "2026-07-11", "2026-07-02T10:00:00")
    assert len(c1) == 4 and c1.isalnum()
    assert c1 != c2


def test_delete_existing_returns_true():
    d = make_db()
    code = d.add_coupon("f1", "a", "2026-07-10", "2026-07-02T10:00:00")
    assert d.delete_coupon(code) is True
    assert d.list_coupons() == []


def test_delete_missing_returns_false():
    d = make_db()
    assert d.delete_coupon("zzzz") is False


def test_meta_roundtrip():
    d = make_db()
    assert d.get_meta("chat_id") is None
    d.set_meta("chat_id", "999")
    assert d.get_meta("chat_id") == "999"
    d.set_meta("chat_id", "1000")
    assert d.get_meta("chat_id") == "1000"


def test_coupon_fields_persisted():
    d = make_db()
    code = d.add_coupon("file123", "星巴克", "2026-07-10", "2026-07-02T10:00:00")
    c = d.list_coupons()[0]
    assert c.code == code
    assert c.file_id == "file123"
    assert c.description == "星巴克"
    assert c.expiry_date == "2026-07-10"
    assert c.created_at == "2026-07-02T10:00:00"
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python -m pytest tests/test_db.py -v`
Expected: FAIL(`ModuleNotFoundError: No module named 'db'`)

- [ ] **Step 3: 實作 db.py**

`db.py`:
```python
import secrets
import sqlite3
from dataclasses import dataclass

_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"
_CODE_LEN = 4


@dataclass
class Coupon:
    code: str
    file_id: str
    description: str
    expiry_date: str
    created_at: str


class Database:
    def __init__(self, path: str):
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS coupons (
                code TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                description TEXT NOT NULL,
                expiry_date TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def _new_code(self) -> str:
        while True:
            code = "".join(secrets.choice(_ALPHABET) for _ in range(_CODE_LEN))
            row = self._conn.execute(
                "SELECT 1 FROM coupons WHERE code = ?", (code,)
            ).fetchone()
            if row is None:
                return code

    def add_coupon(
        self, file_id: str, description: str, expiry_date: str, now_iso: str
    ) -> str:
        code = self._new_code()
        self._conn.execute(
            "INSERT INTO coupons (code, file_id, description, expiry_date, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (code, file_id, description, expiry_date, now_iso),
        )
        self._conn.commit()
        return code

    def list_coupons(self) -> list[Coupon]:
        rows = self._conn.execute(
            "SELECT code, file_id, description, expiry_date, created_at"
            " FROM coupons ORDER BY expiry_date ASC, created_at ASC"
        ).fetchall()
        return [Coupon(**dict(r)) for r in rows]

    def delete_coupon(self, code: str) -> bool:
        cur = self._conn.execute("DELETE FROM coupons WHERE code = ?", (code,))
        self._conn.commit()
        return cur.rowcount > 0

    def get_meta(self, key: str) -> str | None:
        row = self._conn.execute(
            "SELECT value FROM meta WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def set_meta(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self._conn.commit()
```

- [ ] **Step 4: 執行測試確認通過**

Run: `python -m pytest tests/test_db.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add db.py tests/test_db.py
git commit -m "feat: SQLite data layer with coupons and meta"
```

---

### Task 4: 提醒判斷與訊息(純函式)

**Files:**
- Create: `reminder.py`
- Create: `tests/test_reminder.py`

**Interfaces:**
- Consumes: 無(接收字串日期與 `datetime.date`,不依賴 db)。
- Produces:
  - `reminder.REMIND_DAYS = {7, 3, 1, 0}`。
  - `reminder.days_until(expiry_date: str, today: date) -> int`:回傳到期日減今天的天數。
  - `reminder.should_remind(expiry_date: str, today: date) -> bool`:`days_until ∈ REMIND_DAYS`。
  - `reminder.reminder_text(description: str, expiry_date: str, code: str, days: int) -> str`:組提醒文字。`days == 0` 用「⚠️ 今天到期!」,否則「⏰ 還有 N 天到期!」。
  - `reminder.is_expired(expiry_date: str, today: date) -> bool`:`days_until < 0`。

- [ ] **Step 1: 寫失敗測試**

`tests/test_reminder.py`:
```python
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
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python -m pytest tests/test_reminder.py -v`
Expected: FAIL(`ModuleNotFoundError: No module named 'reminder'`)

- [ ] **Step 3: 實作 reminder.py**

`reminder.py`:
```python
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
```

- [ ] **Step 4: 執行測試確認通過**

Run: `python -m pytest tests/test_reminder.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add reminder.py tests/test_reminder.py
git commit -m "feat: reminder threshold logic and message formatting"
```

---

### Task 5: `/list` 格式化(純函式)

**Files:**
- Create: `formatting.py`
- Create: `tests/test_formatting.py`

**Interfaces:**
- Consumes: `db.Coupon`、`reminder.is_expired`。
- Produces:
  - `formatting.format_list(coupons: list[Coupon], today: date) -> str`:空清單回「目前沒有優惠券」;否則逐行,未過期 `📅 YYYY-MM-DD  <描述>  <code>`,已過期 `❌ YYYY-MM-DD (已過期) <描述>  <code>`。假設傳入的 coupons 已排序(由 `db.list_coupons` 負責)。

- [ ] **Step 1: 寫失敗測試**

`tests/test_formatting.py`:
```python
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
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python -m pytest tests/test_formatting.py -v`
Expected: FAIL(`ModuleNotFoundError: No module named 'formatting'`)

- [ ] **Step 3: 實作 formatting.py**

`formatting.py`:
```python
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
```

- [ ] **Step 4: 執行測試確認通過**

Run: `python -m pytest tests/test_formatting.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add formatting.py tests/test_formatting.py
git commit -m "feat: /list formatting"
```

---

### Task 6: Telegram 接線層 bot.py

此任務把前面模組接到 python-telegram-bot。以整合測試驗證訊息處理與提醒的核心邏輯,不對 Telegram API 發真實請求(以 fake 物件替代)。

**Files:**
- Create: `bot.py`
- Create: `tests/test_bot.py`

**Interfaces:**
- Consumes: `config.load_config`、`db.Database`、`parser.parse_caption`/`ParseError`、`reminder.should_remind`/`days_until`/`reminder_text`、`formatting.format_list`。
- Produces(供測試與 `main` 呼叫,均為 `async`,第一參數 `bot` 具 `send_message`/`send_photo`/`copy_message` 介面,第二參數 `database: Database`,`owner_id: int`):
  - `bot.handle_photo(update, context)` — 收照片訊息的 handler。
  - `bot.handle_list(update, context)` — `/list`。
  - `bot.handle_del(update, context)` — `/del`。
  - 為了可測,將純邏輯抽為不依賴 telegram 型別的 async 函式:
    - `bot.add_coupon_reply(database, file_id, caption, now_iso) -> str`:解析並存檔,回傳要回覆使用者的字串(成功或錯誤提示)。
    - `bot.list_reply(database, today) -> str`。
    - `bot.del_reply(database, code) -> str`。
    - `bot.send_due_reminders(bot_api, database, today) -> int`:對每張 `should_remind` 的券呼叫 `bot_api.send_photo(chat_id, photo=file_id, caption=...)`,回傳發送則數;chat_id 取自 `meta.chat_id`,若無則不發並回 0。
    - `bot.run_daily_check(bot_api, database, today) -> int`:若 `meta.last_check_date` != today,呼叫 `send_due_reminders` 後將 `last_check_date` 設為 today 並回發送數;否則回 -1(已檢查)。

- [ ] **Step 1: 寫失敗測試**

`tests/test_bot.py`:
```python
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
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python -m pytest tests/test_bot.py -v`
Expected: FAIL(`ModuleNotFoundError: No module named 'bot'`)

- [ ] **Step 3: 實作 bot.py**

`bot.py`:
```python
import logging
from datetime import date, datetime

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
            await bot_api.send_photo(
                chat_id=int(chat_id),
                photo=c.file_id,
                caption=reminder_text(c.description, c.expiry_date, c.code, days),
            )
            sent += 1
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
    await update.message.reply_text(await list_reply(database, date.today()))


async def handle_del(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    database: Database = context.application.bot_data["db"]
    _remember_chat(database, update)
    if not context.args:
        await update.message.reply_text("用法:/del <唯一碼>")
        return
    await update.message.reply_text(await del_reply(database, context.args[0]))


async def _daily_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    database: Database = context.application.bot_data["db"]
    await run_daily_check(context.bot, database, date.today())


async def _post_init(application: Application) -> None:
    database: Database = application.bot_data["db"]
    # 啟動時當天補發(去重),並發送啟動通知
    await run_daily_check(application.bot, database, date.today())
    chat_id = database.get_meta("chat_id")
    if chat_id is not None:
        await application.bot.send_message(
            chat_id=int(chat_id), text="🤖 優惠券提醒機器人已啟動"
        )


def main() -> None:
    from datetime import time
    from zoneinfo import ZoneInfo

    cfg = load_config()
    database = Database(cfg.db_path)

    owner_filter = filters.User(user_id=cfg.owner_id)
    app = Application.builder().token(cfg.bot_token).post_init(_post_init).build()
    app.bot_data["db"] = database

    app.add_handler(MessageHandler(filters.PHOTO & owner_filter, handle_photo))
    app.add_handler(CommandHandler("list", handle_list, filters=owner_filter))
    app.add_handler(CommandHandler("del", handle_del, filters=owner_filter))

    app.job_queue.run_daily(
        _daily_job, time=time(hour=0, minute=0, tzinfo=ZoneInfo("Asia/Taipei"))
    )

    app.run_polling()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 執行測試確認通過**

Run: `python -m pytest tests/test_bot.py -v`
Expected: 7 passed

- [ ] **Step 5: 全套測試**

Run: `python -m pytest -v`
Expected: 全部 passed(config 3 + parser 8 + db 6 + reminder 5 + formatting 2 + bot 7)

- [ ] **Step 6: Commit**

```bash
git add bot.py tests/test_bot.py
git commit -m "feat: telegram wiring, handlers, daily reminder job, startup notice"
```

---

### Task 7: README 使用說明

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: 前面所有成果。
- Produces: 無程式介面,純文件。

- [ ] **Step 1: 撰寫 README.md**

`README.md`:
````markdown
# 優惠券到期提醒 Telegram 機器人

個人用 Telegram 機器人:傳「照片 + `yy.mm.dd 描述`」新增優惠券,到期前 7/3/1 天及當天自動提醒。

## 準備

1. 在 Telegram 找 [@BotFather](https://t.me/BotFather),`/newbot` 建立機器人,取得 **BOT_TOKEN**。
2. 找 [@userinfobot](https://t.me/userinfobot) 取得你自己的 **user id**(數字)。
3. 複製設定檔:
   ```bash
   cp .env.example .env
   ```
   編輯 `.env` 填入 `BOT_TOKEN` 與 `OWNER_ID`。

## 安裝與啟動

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python bot.py
```

啟動後 bot 會在你的對話送出「🤖 優惠券提醒機器人已啟動」(若你曾與它互動過)。
電腦需保持開機,00:00 才會執行每日提醒檢查。

## 使用

- **新增**:傳一張優惠券照片,說明欄填 `26.07.09 星巴克買一送一`(日期也接受 `2026.07.09`)。
- **列出**:`/list` — 依到期日由近到遠,顯示日期、描述與唯一碼。
- **刪除**:`/del a3f9` — 依唯一碼刪除。

## 提醒規則

- 每日 00:00(Asia/Taipei)檢查;程式啟動時亦補發當天該發的提醒(不跨日補發)。
- 到期前 7、3、1 天及當天各提醒一次,附上原照片。
- 已過期的券不再提醒,但保留在 `/list`(標示「已過期」)。

## 測試

```bash
python -m pytest -v
```
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: usage README"
```

---

## Self-Review

**1. Spec coverage:**
- 新增優惠券(照片+caption、解析、成功/失敗) → Task 2(parser)+ Task 6(`add_coupon_reply`、`handle_photo`)。✅
- 每日 00:00 檢查、7/3/1/當天提醒、啟動當天補發、去重、不跨日補發 → Task 4(reminder)+ Task 6(`send_due_reminders`/`run_daily_check`/`_daily_job`/`_post_init`)。✅
- `/list` 排序與過期標示 → Task 3(排序)+ Task 5(格式)+ Task 6(`handle_list`)。✅
- `/del <碼>` → Task 3(delete)+ Task 6(`del_reply`/`handle_del`)。✅
- file_id 存取、照片重發 → Task 3 + Task 6(`send_photo` with `photo=file_id`)。✅
- meta:chat_id、last_check_date → Task 3 + Task 6。✅
- 白名單 OWNER_ID → Task 6(`filters.User`)。✅
- 啟動通知 + 首次無 chat_id 略過 → Task 6(`_post_init`)。✅
- 設定 BOT_TOKEN/OWNER_ID、取得說明 → Task 1 + Task 7。✅

**2. Placeholder scan:** 無 TODO/TBD;所有 code step 均含完整程式碼。✅

**3. Type consistency:**
- `Database` 方法簽名在 Task 3 定義,Task 5/6 使用一致(`list_coupons`、`add_coupon(file_id, description, expiry_date, now_iso)`、`delete_coupon`、`get_meta`/`set_meta`)。✅
- `parse_caption -> (expiry_date, description)` 在 Task 2 定義,Task 6 依此順序解包。✅
- `reminder_text(description, expiry_date, code, days)` 在 Task 4 定義,Task 6 依此順序呼叫。✅
- `format_list(coupons, today)` 在 Task 5 定義,Task 6 經 `list_reply` 使用。✅
