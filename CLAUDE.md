# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Python CLI tool that batch-analyzes photos using vision models (LM Studio, OpenAI, Anthropic) and stores structured results in SQLite. Sends images to a vision LLM which returns JSON with tags, composition scores, categories, descriptions, locations, and improvement suggestions. Includes subcommands for querying, reporting, and publishing results.

## Running

Requires `uv`. For `scan` and `eval`, needs one of:
- LM Studio running at `http://127.0.0.1:1234/v1` (default)
- `OPENAI_API_KEY` env var (for `--provider openai`)
- `ANTHROPIC_API_KEY` env var (for `--provider anthropic`)

```
uv run analyze.py scan /path/to/photos
uv run analyze.py /path/to/photos          # backward-compat (auto-detects path)
uv run analyze.py scan /path --provider openai
uv run analyze.py scan /path --provider anthropic
```

### Subcommands

**Analysis:**
- `scan /path/to/photos [--force] [--max-images N] [--dry-run]` — analyze photos
- `eval golden_eval.json [--model X]` — model evaluation against golden dataset

**Queries:**
- `top [N] [--category X] [--tag X]` — best photos by score
- `bottom [N]` — worst photos by score
- `tags [--min N]` — tag frequency with bar chart
- `find [--tag X] [--category X] [--location "text"] [--score "5+"]` — filtered search
- `info IMG_9187.HEIC` — detail view for one photo
- `stats` — database summary

**Output:**
- `report [--category X]` — markdown report to stdout
- `export [--format json|csv]` — data dump to stdout
- `publish [--top N] [--title "text"] [--gist] [--public]` — gallery markdown with thumbnails

### Global flags

- `--db photo_analysis.db` — SQLite database path (default: `photo_analysis.db`)
- `-v` — verbose/debug logging

### Scan/Eval flags

- `--provider lmstudio|openai|anthropic` — vision model provider (default: lmstudio)
- `--model NAME` — model name (default depends on provider: qwen/qwen3-vl-30b, gpt-5, claude-sonnet-4-20250514). For cheaper OpenAI usage, use `--model gpt-5-mini`
- `--base-url URL` — LM Studio endpoint (lmstudio provider only)
- `--force` — re-analyze images already in the database
- `--max-images N` — limit batch size
- `--max-dimension 1024` — resize images before sending
- `--dry-run` — preview which images would be analyzed

## Architecture

`analyze.py` is a thin entry point (PEP 723 inline metadata) that delegates to the `photo_ai/` package.

### Package structure

```
photo_ai/
├── __init__.py          # empty
├── __main__.py          # argparse, subcommand dispatch
├── providers.py         # multi-provider abstraction (lmstudio, openai, anthropic)
├── scanner.py           # scan: find_images, extract_gps, resize_and_encode,
│                        #   build_prompt, analyze_image, validate_analysis,
│                        #   insert_result, process_images, print_scan_summary
├── eval.py              # eval: run_eval
├── db.py                # schema, migrations, init_db, open_db_readonly
├── queries.py           # top, bottom, tags, find, info, stats commands
├── report.py            # report, export commands
├── publish.py           # publish: gallery markdown with base64 thumbnails
└── util.py              # SCORE_LABELS, score_label(), format_table(),
                         #   constants, prompt templates, COMPOSITION_ISSUES
```

**Pipeline per image:** find_images → extract_gps (EXIF) → resize_and_encode (base64 JPEG) → build_prompt (GPS-aware) → analyze_fn (provider-specific API call) → validate_analysis → insert_result (SQLite)

**Provider abstraction** (`providers.py`): `create_provider()` returns `(client, model_name, analyze_fn)` where `analyze_fn(b64_data, prompt) -> dict`. Each provider handles its own API format (OpenAI-compatible for lmstudio/openai, Anthropic Messages API for anthropic).

**Database schema** (`photo_analysis.db`):
- `photos` — one row per image with path, dimensions, file size, tags, category, composition score/elements/explanation/issues/suggestions, description, caption, title, location, lat/lon, model name, and raw JSON response
- `photo_tags` — normalized tag junction table (photo_path, tag) for efficient tag queries

GPS coordinates from EXIF are passed to the prompt to improve location identification. Images without GPS get a fallback prompt that asks the model to infer location visually.

Skips already-analyzed images by default (keyed on resolved absolute path). Uses WAL mode and retries with exponential backoff on API failures.

## Model Selection

**Default: LM Studio (qwen/qwen3-vl-30b)** — free, fast (~8s/img), uses full score range naturally. See `docs/model-comparison.md` for the full evaluation.

OpenAI models are available for cross-validation or GPU-less environments:
- Never use `gpt-4o` — deprecated and more expensive
- `gpt-5` (default for `--provider openai`) — reasoning model, slower (~66s/img), ~$2.50/85 photos
- `gpt-5-mini` — cheaper alternative for budget-conscious runs
- GPT-5 API requires `max_completion_tokens` (not `max_tokens`), no custom `temperature`, and higher token budgets due to reasoning overhead

All models agree within ±1 point on 98–100% of photos. OpenAI models score ~0.5 points more conservatively and use fewer category labels.

## Testing

```
uv run --with pytest --with Pillow --with tqdm --with openai pytest tests/ -v
```

## Dependencies

PEP 723 inline metadata in `analyze.py`: `openai`, `anthropic`, `Pillow`, `pillow-heif`, `tqdm`. Query subcommands use stdlib only (`argparse`, `sqlite3`, `csv`, `json`, `textwrap`, `subprocess`). The `publish --gist` flag requires the `gh` CLI.
