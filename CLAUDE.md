# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A single-script Python tool that batch-analyzes photos using a local LM Studio vision model and stores structured results in SQLite. Uses the OpenAI-compatible API to send images to a vision LLM (default: Qwen3-VL-30B) which returns JSON with tags, composition scores, categories, descriptions, and locations.

## Running

Requires `uv` and a running LM Studio instance at `http://127.0.0.1:1234/v1`.

```
uv run analyze.py /path/to/photos
```

Key flags:
- `--db photo_analysis.db` — SQLite output path (default: `photo_analysis.db`)
- `--base-url http://127.0.0.1:1234/v1` — LM Studio endpoint
- `--model qwen/qwen3-vl-30b` — vision model name
- `--force` — re-analyze images already in the database
- `--max-images N` — limit batch size
- `--max-dimension 1024` — resize images before sending
- `--dry-run` — preview which images would be analyzed
- `-v` — verbose/debug logging

## Architecture

Everything lives in `analyze.py` with PEP 723 inline script metadata (dependencies: `openai`, `Pillow`, `pillow-heif`, `tqdm`).

**Pipeline per image:** find_images → extract_gps (EXIF) → resize_and_encode (base64 JPEG) → build_prompt (GPS-aware) → analyze_image (LM Studio API) → validate_analysis → insert_result (SQLite)

**Database schema** (`photo_analysis.db`):
- `photos` — one row per image with path, dimensions, file size, tags, category, composition score/elements/explanation, description, location, lat/lon, model name, and raw JSON response
- `photo_tags` — normalized tag junction table (photo_path, tag) for efficient tag queries

GPS coordinates from EXIF are passed to the prompt to improve location identification. Images without GPS get a fallback prompt that asks the model to infer location visually.

Skips already-analyzed images by default (keyed on resolved absolute path). Uses WAL mode and retries with exponential backoff on API failures.
