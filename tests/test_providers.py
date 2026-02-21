"""Tests for photo_ai.providers."""

from photo_ai.providers import (
    DEFAULT_PROVIDER,
    PROVIDERS,
    _REASONING_MODELS,
    _strip_markdown_fences,
)


def test_strip_markdown_fences_json():
    raw = '```json\n{"score": 5}\n```'
    assert _strip_markdown_fences(raw) == '{"score": 5}'


def test_strip_markdown_fences_plain():
    raw = '```\n{"score": 5}\n```'
    assert _strip_markdown_fences(raw) == '{"score": 5}'


def test_strip_markdown_fences_noop():
    raw = '{"score": 5}'
    assert _strip_markdown_fences(raw) == '{"score": 5}'


def test_strip_markdown_fences_whitespace():
    raw = '  ```json\n{"score": 5}\n```  '
    assert _strip_markdown_fences(raw) == '{"score": 5}'


def test_default_provider():
    assert DEFAULT_PROVIDER == "lmstudio"
    assert DEFAULT_PROVIDER in PROVIDERS


def test_all_providers_have_defaults():
    for name, (model, desc) in PROVIDERS.items():
        assert isinstance(model, str) and len(model) > 0
        assert isinstance(desc, str) and len(desc) > 0


def test_reasoning_models_include_gpt5():
    assert "gpt-5" in _REASONING_MODELS


def test_gpt4o_not_in_providers():
    for _, (default_model, _) in PROVIDERS.items():
        assert default_model != "gpt-4o", "gpt-4o is deprecated and should not be a default"
