import os
from dataclasses import dataclass

from dotenv import load_dotenv

# override=True 讓專案 .env 優先於既有的系統環境變數(避免外部殘留的
# BOT_TOKEN 等蓋過本專案設定)
load_dotenv(override=True)


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
