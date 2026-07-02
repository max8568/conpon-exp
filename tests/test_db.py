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
    assert len(c1) == 4 and c1.isalpha() and c1.islower()
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
