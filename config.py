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
