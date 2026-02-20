"""Vision model providers: LM Studio, OpenAI, Anthropic."""

import json
import logging
import os
import sys

log = logging.getLogger(__name__)

# Provider name -> (default model, description)
PROVIDERS = {
    "lmstudio": ("qwen/qwen3-vl-30b", "Local LM Studio server"),
    "openai": ("gpt-5", "OpenAI API"),
    "anthropic": ("claude-sonnet-4-20250514", "Anthropic API"),
}

DEFAULT_PROVIDER = "lmstudio"


def _strip_markdown_fences(raw: str) -> str:
    """Strip markdown code fences from model response."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)
    return raw


def _make_lmstudio(base_url: str, model: str):
    """Return an analyze function for LM Studio (OpenAI-compatible)."""
    from openai import OpenAI
    client = OpenAI(base_url=base_url, api_key="lm-studio")

    def analyze(b64_data: str, prompt: str) -> dict:
        response = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_data}"}},
                ],
            }],
            temperature=0.3,
        )
        raw = _strip_markdown_fences(response.choices[0].message.content)
        return json.loads(raw)

    return client, model, analyze


def _make_openai(model: str):
    """Return an analyze function for OpenAI API."""
    from openai import OpenAI
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)
    client = OpenAI(api_key=api_key)

    def analyze(b64_data: str, prompt: str) -> dict:
        response = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_data}"}},
                ],
            }],
            max_completion_tokens=8192,
        )
        raw = _strip_markdown_fences(response.choices[0].message.content)
        return json.loads(raw)

    return client, model, analyze


def _make_anthropic(model: str):
    """Return an analyze function for Anthropic API."""
    try:
        import anthropic
    except ImportError:
        print("Error: 'anthropic' package not installed. Run: uv pip install anthropic", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)
    client = anthropic.Anthropic(api_key=api_key)

    def analyze(b64_data: str, prompt: str) -> dict:
        response = client.messages.create(
            model=model,
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64_data}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        raw = _strip_markdown_fences(response.content[0].text)
        return json.loads(raw)

    return client, model, analyze


def create_provider(provider: str, model: str | None = None, base_url: str = "http://127.0.0.1:1234/v1"):
    """Create a provider and return (client, model_name, analyze_fn).

    The analyze_fn signature is: analyze(b64_data: str, prompt: str) -> dict
    """
    if model is None:
        model = PROVIDERS[provider][0]

    if provider == "lmstudio":
        return _make_lmstudio(base_url, model)
    elif provider == "openai":
        return _make_openai(model)
    elif provider == "anthropic":
        return _make_anthropic(model)
    else:
        print(f"Error: unknown provider '{provider}'. Choose from: {', '.join(PROVIDERS)}", file=sys.stderr)
        sys.exit(1)
