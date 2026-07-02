"""背景服務啟動器:設定檔案 log(pythonw 無主控台),再啟動 bot。

由 Windows 工作排程器於登入時以 pythonw.exe 執行。日誌輪替寫到 logs/bot.log。
"""
import logging
import os
from logging.handlers import RotatingFileHandler

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)
os.makedirs(os.path.join(BASE, "logs"), exist_ok=True)

# import bot 會觸發其模組層級的 logging.basicConfig(加上一個寫 stderr 的 handler,
# 在 pythonw 下 stderr 無效);import 後改成只保留檔案 handler。
import bot  # noqa: E402

root = logging.getLogger()
for h in list(root.handlers):
    root.removeHandler(h)

file_handler = RotatingFileHandler(
    os.path.join(BASE, "logs", "bot.log"),
    maxBytes=1_000_000,
    backupCount=3,
    encoding="utf-8",
)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
)
root.addHandler(file_handler)
root.setLevel(logging.INFO)

bot.main()
