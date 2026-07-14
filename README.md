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

## 背景服務(Windows,開機自動執行 + 自動復活)

要讓 bot 常駐、開機自動啟動、被砍或當掉也會自己回來,用 `run_service.py`
(pythonw 無主控台,日誌輪替寫到 `logs/bot.log`)搭配 Windows 工作排程器。
一次性註冊(冪等,可重複執行以更新設定):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\register_task.ps1
```

註冊的工作 `CouponReminderBot` 有兩個觸發器:登入時立即啟動,以及一個每 5 分鐘的
時間觸發 watchdog。搭配「不啟動多個執行個體(IgnoreNew)」,watchdog 在 bot 存活時
什麼都不做、死掉時會在 5 分鐘內重新拉起,且不會開出第二個。

```powershell
Start-ScheduledTask -TaskName CouponReminderBot                    # 立即啟動
Get-ScheduledTask   -TaskName CouponReminderBot | Get-ScheduledTaskInfo   # 查看狀態
```

> 因為有 watchdog,`Stop-ScheduledTask` 停掉後 5 分鐘內會被再次拉起。要真正停用請先
> `Disable-ScheduledTask -TaskName CouponReminderBot`。

## 使用

- **新增**:傳一張優惠券照片,說明欄填 `26.07.09 星巴克買一送一`(日期也接受 `2026.07.09`)。
- **列出**:`/list` — 依到期日由近到遠,顯示日期、描述與唯一碼。
- **刪除**:`/del a3f9` — 依唯一碼刪除。

## 提醒規則

- 每日 00:00(Asia/Taipei)檢查;程式啟動時亦補發當天該發的提醒(不跨日補發)。
- 到期前 7、3、1 天及當天各提醒一次,附上原照片。
- 已過期的券不再提醒,但保留在 `/list`(標示「已過期」)。
- 由於每日只在 00:00 檢查一次,今天才新增、且到期門檻剛好落在今天(或已過的 7/3/1 天前)的券,要到隔天 00:00 才會收到提醒。

## 測試

```bash
python -m pytest -v
```
