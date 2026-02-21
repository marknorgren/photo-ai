"""Tests for photo_ai.queries."""

from photo_ai.queries import _parse_score_filter


def test_parse_score_exact():
    assert _parse_score_filter("5") == (5.0, 5.0)


def test_parse_score_plus():
    assert _parse_score_filter("5+") == (5.0, 7.0)


def test_parse_score_range():
    assert _parse_score_filter("3-5") == (3.0, 5.0)
