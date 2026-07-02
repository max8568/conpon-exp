import secrets
import sqlite3
from dataclasses import dataclass

_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
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
