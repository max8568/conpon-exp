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
