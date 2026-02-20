# Subcommand Architecture Plan

Refactored the single-file `analyze.py` (650 lines) into a modular `photo_ai/` package with subcommand-based CLI, while preserving `uv run analyze.py` backward compatibility.

## Motivation

The tool grew from a single-purpose batch analyzer into something with analysis, evaluation, query, report, and publish needs. Adding all commands to one file would push it past 1000 lines. Splitting into a package keeps each module focused and testable.

## Package Structure

```
analyze.py               # thin wrapper (PEP 723 metadata + import)
photo_ai/
├── __init__.py          # empty
├── __main__.py          # argparse, subcommand dispatch (~100 lines)
├── scanner.py           # scan command (~200 lines, from analyze.py)
├── eval.py              # eval command (~130 lines, from analyze.py)
├── db.py                # schema, migrations, connections (~80 lines)
├── queries.py           # top, bottom, tags, find, info, stats (~200 lines, new)
├── report.py            # report, export (~90 lines, new)
├── publish.py           # gallery markdown + gist push (~90 lines, new)
└── util.py              # constants, labels, formatting (~160 lines)
```

## Subcommands

| Command | Description | DB Mode |
|---------|-------------|---------|
| `scan` | Analyze photos (default when path given) | read-write |
| `eval` | Model evaluation against golden dataset | none (file I/O) |
| `top` | Best photos by score | read-only |
| `bottom` | Worst photos by score | read-only |
| `tags` | Tag frequency with bar chart | read-only |
| `find` | Search with filters (tag, category, location, score) | read-only |
| `info` | Detail view for one photo | read-only |
| `stats` | Database summary | read-only |
| `report` | Markdown report to stdout | read-only |
| `export` | JSON or CSV dump to stdout | read-only |
| `publish` | Gallery markdown with embedded thumbnails | read-only |

## Backward Compatibility

`__main__.py` auto-detects when the first argument is a path (starts with `/`, `.`, `~`, or exists as a directory) and prepends `scan`. Both invocations work:

```
uv run analyze.py /path/to/photos          # legacy
uv run analyze.py scan /path/to/photos     # new explicit
```

## Key Design Decisions

**PEP 723 stays in `analyze.py`**: The `# /// script` metadata block must be in the entry point that `uv run` sees. The `photo_ai/` package imports happen at runtime.

**Lazy imports**: Heavy dependencies (`openai`, `Pillow`, `tqdm`) are imported only in the subcommands that need them (`scan`, `eval`, `publish`). Query commands start instantly with just `sqlite3`.

**Migrations on read-only open**: `open_db_readonly()` first opens a write connection to run pending migrations (e.g. adding `caption`/`title` columns), then reopens as read-only. This ensures query commands work against older databases.

**SIGPIPE handling**: The entry point installs `signal.signal(signal.SIGPIPE, signal.SIG_DFL)` so piping to `head` doesn't produce Python tracebacks.

**Score filter syntax**: The `find --score` flag supports three formats: `6` (exact), `5+` (>= 5), `3-5` (range).

**Publish thumbnails**: Gallery markdown uses base64-encoded `<img>` tags at 400px max width (~30-50KB each). GitHub Gist renders these inline. Total size stays manageable with `--top N` (default 20).

## No New Dependencies

All query/report/publish commands use stdlib only. Existing deps (`openai`, `Pillow`, `pillow-heif`, `tqdm`) remain in `analyze.py`'s PEP 723 block and are only imported for `scan`/`eval`/`publish`.
