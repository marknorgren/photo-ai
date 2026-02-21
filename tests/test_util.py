"""Tests for photo_ai.util."""

from photo_ai.util import (
    ALL_CATEGORIES,
    ALL_TAGS,
    COMPOSITION_ELEMENTS,
    COMPOSITION_ISSUES,
    SCORE_LABELS,
    format_table,
    score_label,
)


def test_score_labels_cover_full_range():
    for i in range(1, 8):
        assert i in SCORE_LABELS


def test_score_label_returns_label():
    assert score_label(5) == "Good"
    assert score_label(7) == "Perfect"
    assert score_label(1) == "Terrible"


def test_score_label_with_float():
    assert score_label(5.4) == "Good"


def test_score_label_unknown():
    assert score_label(0) == "Unknown"
    assert score_label(99) == "Unknown"


def test_format_table_basic():
    result = format_table(["Name", "Score"], [["Alice", "5"], ["Bob", "3"]])
    lines = result.split("\n")
    assert len(lines) == 4  # header, separator, 2 rows
    assert "Alice" in lines[2]
    assert "Bob" in lines[3]


def test_format_table_empty():
    assert format_table(["Name"], []) == "(no results)"


def test_format_table_alignment():
    result = format_table(["Name", "Score"], [["A", "5"]], align=["<", ">"])
    assert "A" in result
    assert "5" in result


def test_no_duplicate_tags():
    assert len(ALL_TAGS) == len(set(ALL_TAGS))


def test_no_duplicate_categories():
    assert len(ALL_CATEGORIES) == len(set(ALL_CATEGORIES))


def test_no_duplicate_elements():
    assert len(COMPOSITION_ELEMENTS) == len(set(COMPOSITION_ELEMENTS))


def test_no_duplicate_issues():
    assert len(COMPOSITION_ISSUES) == len(set(COMPOSITION_ISSUES))
