import re
from datetime import date

_DATE_RE = re.compile(r"^\s*(\d{2}|\d{4})\.(\d{1,2})\.(\d{1,2})\s*(.*)$", re.DOTALL)


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
