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
