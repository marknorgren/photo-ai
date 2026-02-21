"""Tests for photo_ai.scanner."""

import tempfile
from pathlib import Path

from PIL import Image

from photo_ai.scanner import (
    build_prompt,
    find_images,
    resize_and_encode,
    validate_analysis,
)


def _make_test_image(path: Path, width=100, height=100):
    """Create a minimal test JPEG."""
    img = Image.new("RGB", (width, height), color="red")
    img.save(path, format="JPEG")


def test_find_images_filters_extensions():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "photo.jpg").touch()
        (p / "photo.png").touch()
        (p / "readme.txt").touch()
        (p / "data.csv").touch()
        images = find_images(p)
        names = {i.name for i in images}
        assert names == {"photo.jpg", "photo.png"}


def test_find_images_recursive():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        sub = p / "subdir"
        sub.mkdir()
        (p / "a.jpg").touch()
        (sub / "b.jpg").touch()
        images = find_images(p)
        assert len(images) == 2


def test_find_images_sorted():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "c.jpg").touch()
        (p / "a.jpg").touch()
        (p / "b.jpg").touch()
        images = find_images(p)
        names = [i.name for i in images]
        assert names == ["a.jpg", "b.jpg", "c.jpg"]


def test_resize_and_encode_returns_base64():
    with tempfile.NamedTemporaryFile(suffix=".jpg") as f:
        _make_test_image(Path(f.name), 200, 300)
        b64, w, h = resize_and_encode(Path(f.name), 1024)
        assert isinstance(b64, str)
        assert len(b64) > 0
        assert w == 200
        assert h == 300


def test_resize_and_encode_respects_max_dimension():
    with tempfile.NamedTemporaryFile(suffix=".jpg") as f:
        _make_test_image(Path(f.name), 2000, 1000)
        b64, w, h = resize_and_encode(Path(f.name), 500)
        assert w == 2000  # returns original dimensions
        assert h == 1000
        # The base64 should be smaller than full-size
        import base64
        data = base64.b64decode(b64)
        img = Image.open(__import__("io").BytesIO(data))
        assert max(img.size) <= 500


def test_build_prompt_with_gps():
    prompt = build_prompt((37.7749, -122.4194))
    assert "37.774900" in prompt
    assert "-122.419400" in prompt


def test_build_prompt_without_gps():
    prompt = build_prompt(None)
    assert "cannot confidently identify" in prompt


def test_validate_analysis_full():
    data = {
        "tags": ["urban", "street", "moody"],
        "composition": {
            "score": 5,
            "elements": ["leading_lines", "depth"],
            "issues": ["cluttered_background"],
            "explanation": "Nice leading lines but cluttered background.",
            "suggestions": ["Use wider aperture to blur background."],
        },
        "category": "street",
        "description": "A rainy city street.",
        "caption": "Rain in the city",
        "title": "Urban Rain",
        "location": "San Francisco, CA",
    }
    result = validate_analysis(data)
    assert result["tags"] == ["urban", "street", "moody"]
    assert result["composition_score"] == 5.0
    assert result["composition_elements"] == ["leading_lines", "depth"]
    assert result["composition_issues"] == ["cluttered_background"]
    assert result["composition_suggestions"] == ["Use wider aperture to blur background."]
    assert result["category"] == "street"
    assert result["title"] == "Urban Rain"
    assert result["location"] == "San Francisco, CA"


def test_validate_analysis_clamps_score():
    data = {"composition": {"score": 99}, "tags": []}
    result = validate_analysis(data)
    assert result["composition_score"] == 7.0

    data2 = {"composition": {"score": -5}, "tags": []}
    result2 = validate_analysis(data2)
    assert result2["composition_score"] == 0.0


def test_validate_analysis_truncates_tags():
    data = {"tags": [f"tag{i}" for i in range(20)], "composition": {}}
    result = validate_analysis(data)
    assert len(result["tags"]) == 8


def test_validate_analysis_handles_dict_tags():
    data = {
        "tags": {"scene": ["urban", "street"], "mood": "moody"},
        "composition": {},
    }
    result = validate_analysis(data)
    assert "urban" in result["tags"]
    assert "street" in result["tags"]
    assert "moody" in result["tags"]


def test_validate_analysis_truncates_suggestions():
    data = {
        "tags": [],
        "composition": {"suggestions": ["a", "b", "c", "d", "e"]},
    }
    result = validate_analysis(data)
    assert len(result["composition_suggestions"]) == 3


def test_validate_analysis_missing_fields():
    result = validate_analysis({})
    assert result["tags"] == []
    assert result["composition_score"] == 0.0
    assert result["category"] == "default"
    assert result["description"] == ""
    assert result["caption"] == ""
    assert result["title"] == ""
    assert result["location"] is None


def test_validate_analysis_null_location():
    data = {"tags": [], "composition": {}, "location": None}
    result = validate_analysis(data)
    assert result["location"] is None
