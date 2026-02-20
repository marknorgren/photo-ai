# photo-ai

![ALPHA](https://img.shields.io/badge/status-ALPHA-ff6b35?style=for-the-badge) ![vibe coded](https://img.shields.io/badge/vibe-coded-blueviolet?style=for-the-badge) ![AI paired](https://img.shields.io/badge/AI%20%2B%20human-paired-22c55e?style=for-the-badge)

> **Alpha.** Mostly AI-generated, human-paired, and evolving fast. Expect rough edges.

Batch-analyze photos with a local vision LLM. One script, one API call per
image, structured results in SQLite.

## Quick Start

Prerequisites:

1. [LM Studio](https://lmstudio.ai/) running with a vision model loaded
   (default: `qwen/qwen3-vl-30b`)
2. [uv](https://docs.astral.sh/uv/)

```
uv run analyze.py /path/to/photos
```

Browse results immediately:

```
uvx datasette photo_analysis.db
```

## What It Does

```
find images → extract GPS (EXIF) → resize + base64 → vision API call → validate JSON → SQLite
```

Each image gets a single API call to a local vision model. The prompt is
GPS-aware — if EXIF coordinates exist, the model gets them alongside the image
for better location identification. The response is structured JSON with five
fields:

- **tags** — up to 8 from a fixed vocabulary (scene, subject, style, mood,
  weather)
- **composition score** — 1-7 scale (1=Terrible, 4=Passable, 7=Perfect)
- **category** — single best-fit from 20 categories
- **description** — 1-2 sentence natural language
- **location** — human-readable place name, or null

## Output

Results from 85 HEIC photos (SF trip, ~6s/image on Qwen3-VL-30B):

**Score distribution:**

| Score | Label     | Photos |
| ----- | --------- | ------ |
| 6     | Excellent | 43     |
| 5     | Good      | 41     |
| 4     | Passable  | 1      |

**Top locations:**

```
Fire escape, San Francisco, CA
Apple Store, Union Square, San Francisco, CA
Phelan Building, San Francisco, CA
Golden Gate Bridge Viewpoint, San Francisco, CA
Golden Gate Bridge, San Francisco, CA
```

**Top tags:**

| Tag          | Count | Tag       | Count |
| ------------ | ----- | --------- | ----- |
| building     | 53    | rain      | 26    |
| street       | 49    | vehicle   | 25    |
| urban        | 47    | moody     | 23    |
| sky          | 47    | nature    | 21    |
| dramatic     | 44    | cinematic | 20    |
| architecture | 39    | person    | 18    |

**Sample description:**

> A low-angle view of the sleek, metallic facade of an Apple Store on a wet city
> street, with a tree on the left framing the shot and a city intersection
> visible in the background.

## CLI Reference

| Flag              | Default                    | Description                               |
| ----------------- | -------------------------- | ----------------------------------------- |
| `directory`       | (required)                 | Directory of images to analyze            |
| `--db`            | `photo_analysis.db`        | SQLite database path                      |
| `--base-url`      | `http://127.0.0.1:1234/v1` | LM Studio server URL                      |
| `--model`         | `qwen/qwen3-vl-30b`        | Model name                                |
| `--force`         | off                        | Re-analyze images already in the database |
| `--max-images N`  | 0 (all)                    | Limit batch size                          |
| `--max-dimension` | 1024                       | Max image dimension before resizing       |
| `--dry-run`       | off                        | Preview which images would be analyzed    |
| `-v`              | off                        | Verbose/debug logging                     |

## Schema

**photos** — one row per image:

```sql
CREATE TABLE photos (
    path                    TEXT PRIMARY KEY,
    filename                TEXT,
    analyzed_at             TEXT,
    image_width             INTEGER,
    image_height            INTEGER,
    file_size_bytes         INTEGER,
    tags                    TEXT,       -- comma-separated
    category                TEXT,
    composition_score       REAL,
    composition_elements    TEXT,       -- comma-separated
    composition_explanation TEXT,
    description             TEXT,
    location                TEXT,
    latitude                REAL,
    longitude               REAL,
    model                   TEXT,
    raw_response            TEXT        -- full JSON from model
);
```

**photo_tags** — normalized for efficient tag queries:

```sql
CREATE TABLE photo_tags (
    photo_path TEXT NOT NULL REFERENCES photos(path) ON DELETE CASCADE,
    tag        TEXT NOT NULL,
    PRIMARY KEY (photo_path, tag)
);
```

Useful queries:

```sql
-- Top compositions
SELECT filename, category, composition_score, location
FROM photos ORDER BY composition_score DESC LIMIT 10;

-- Photos by tag
SELECT p.filename, p.description
FROM photos p JOIN photo_tags t ON p.path = t.photo_path
WHERE t.tag = 'rain';

-- Tag co-occurrence
SELECT a.tag, b.tag, COUNT(*) as co
FROM photo_tags a
JOIN photo_tags b ON a.photo_path = b.photo_path AND a.tag < b.tag
GROUP BY a.tag, b.tag ORDER BY co DESC LIMIT 10;
```

## Configuration

**Different model:** Any vision model in LM Studio works. Load it and pass the
name:

```
uv run analyze.py /path/to/photos --model google/gemma-3-27b-it
```

**Remote server:** Point to any OpenAI-compatible endpoint:

```
uv run analyze.py /path/to/photos --base-url http://192.168.1.100:1234/v1
```

**Smaller images for faster inference:**

```
uv run analyze.py /path/to/photos --max-dimension 512
```

## Development

- [demo.md](demo.md) — executable walkthrough with real query output
- [REVIEW.md](REVIEW.md) — analysis of results, known issues, and next steps
- [diagrams/](diagrams/) — Excalidraw architecture diagrams (pipeline, scores,
  journey)

Supported image formats: JPEG, PNG, WebP, HEIC/HEIF, TIFF. HEIC support requires
`pillow-heif` (installed automatically by `uv run`).
