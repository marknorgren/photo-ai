# Photo Analysis with Local Vision AI

_2026-02-18T23:40:43Z by Showboat dev_

<!-- showboat-id: e9e4af3a-10a9-40ab-8a13-27e90fa54978 -->

Analyze a directory of photos using a local LM Studio vision model
(qwen3-vl-30b). The script extracts GPS coordinates from EXIF data, sends each
image with context-aware prompts, and stores structured results — tags,
composition scores, categories, locations, and descriptions — in SQLite.

## Setup

The script uses PEP 723 inline metadata — no virtualenv needed. `uv run` handles
dependencies automatically.

## CLI Usage

```bash
uv run analyze.py --help 2>/dev/null
```

```output
usage: analyze.py [-h] [--db DB] [--base-url BASE_URL] [--model MODEL]
                  [--force] [--max-images MAX_IMAGES]
                  [--max-dimension MAX_DIMENSION] [--dry-run] [-v]
                  directory

Analyze photos using LM Studio vision API

positional arguments:
  directory             Directory of images to analyze

options:
  -h, --help            show this help message and exit
  --db DB               SQLite database path (default: photo_analysis.db)
  --base-url BASE_URL   LM Studio server URL (default:
                        http://127.0.0.1:1234/v1)
  --model MODEL         Model name (default: qwen/qwen3-vl-30b)
  --force               Re-analyze already processed images
  --max-images MAX_IMAGES
                        Limit number of images to process (0 = all)
  --max-dimension MAX_DIMENSION
                        Max image dimension for resizing (default: 1024)
  --dry-run             Preview which images would be analyzed
  -v, --verbose         Enable verbose logging
```

85 HEIC photos from a San Francisco trip were analyzed in ~8 minutes
(~6s/image). Results are stored in SQLite with WAL mode enabled for concurrent
reads.

## Results Overview

```bash
sqlite3 /Users/mark/working/photo-ai/photo_analysis.db "SELECT COUNT(*) || ' photos analyzed' FROM photos"
```

```output
85 photos analyzed
```

### Composition Scores (Steph Ango 1-7 Scale)

The prompt enforces a 7-point scale: 1=Terrible, 2=Atrocious, 3=Bad, 4=Passable,
5=Good, 6=Excellent, 7=Perfect. Validation clamps any out-of-range values as a
safety net.

```bash
sqlite3 /Users/mark/working/photo-ai/photo_analysis.db "SELECT CAST(composition_score AS INTEGER) AS score, COUNT(*) AS photos, CASE CAST(composition_score AS INTEGER) WHEN 7 THEN 'Perfect' WHEN 6 THEN 'Excellent' WHEN 5 THEN 'Good' WHEN 4 THEN 'Passable' WHEN 3 THEN 'Bad' ELSE 'Other' END AS label FROM photos GROUP BY score ORDER BY score DESC" -column -header
```

```output
score  photos  label
-----  ------  ---------
6      43      Excellent
5      41      Good
4      1       Passable
```

### GPS-Aware Locations

GPS coordinates from EXIF data are passed to the vision model alongside the
image, so it can identify specific landmarks and venues.

```bash
sqlite3 /Users/mark/working/photo-ai/photo_analysis.db "SELECT COUNT(DISTINCT location) || ' unique locations identified' FROM photos WHERE location IS NOT NULL"
```

```output
63 unique locations identified
```

```bash
sqlite3 /Users/mark/working/photo-ai/photo_analysis.db "SELECT location, CAST(composition_score AS INTEGER) AS score FROM photos WHERE location IS NOT NULL ORDER BY composition_score DESC LIMIT 10" -column -header
```

```output
location                                                 score
-------------------------------------------------------  -----
Fire escape, San Francisco, CA                           6
Apple Store, Union Square, San Francisco, CA             6
Phelan Building, San Francisco, CA                       6
Wells Fargo Building, Market Street, San Francisco, CA   6
Golden Gate National Recreation Area, San Francisco, CA  6
Golden Gate Bridge Viewpoint, San Francisco, CA          6
Golden Gate Bridge, San Francisco, CA                    6
Golden Gate Bridge, San Francisco, CA                    6
Golden Gate Bridge, San Francisco, CA                    6
Golden Gate Bridge, San Francisco, CA                    6
```

### Tags

```bash
sqlite3 /Users/mark/working/photo-ai/photo_analysis.db "SELECT tag, COUNT(*) AS count FROM photo_tags GROUP BY tag ORDER BY count DESC LIMIT 12" -column -header
```

```output
tag           count
------------  -----
building      53
street        49
urban         47
sky           47
dramatic      44
architecture  39
rain          26
vehicle       25
moody         23
nature        21
cinematic     20
person        18
```

```bash
sqlite3 /Users/mark/working/photo-ai/photo_analysis.db "SELECT COUNT(*) || ' total tags across ' || (SELECT COUNT(*) FROM photos) || ' photos (' || ROUND(CAST(COUNT(*) AS REAL) / (SELECT COUNT(*) FROM photos), 1) || ' avg per photo)' FROM photo_tags"
```

```output
583 total tags across 85 photos (6.9 avg per photo)
```

### Categories

```bash
sqlite3 /Users/mark/working/photo-ai/photo_analysis.db "SELECT category, COUNT(*) AS photos FROM photos GROUP BY category ORDER BY photos DESC" -column -header
```

```output
category      photos
------------  ------
street        29
architecture  18
urban         13
landscape     13
food          4
portrait      3
night         2
abstract      2
travel        1
```

### Neighborhoods by Photo Count

```bash
sqlite3 /Users/mark/working/photo-ai/photo_analysis.db "SELECT CASE WHEN location LIKE '%Golden Gate%' THEN 'Golden Gate' WHEN location LIKE '%Fisherman%' OR location LIKE '%Wharf%' OR location LIKE '%Pier%' OR location LIKE '%Ghirardelli%' THEN 'Fishermans Wharf' WHEN location LIKE '%North Beach%' OR location LIKE '%Columbus%' THEN 'North Beach' WHEN location LIKE '%Chinatown%' THEN 'Chinatown' WHEN location LIKE '%Nob Hill%' OR location LIKE '%Grace Cathedral%' THEN 'Nob Hill' WHEN location LIKE '%Union Square%' OR location LIKE '%Market%' OR location LIKE '%Powell%' THEN 'Union Square' WHEN location LIKE '%Financial%' OR location LIKE '%Embarcadero%' OR location LIKE '%Transamerica%' THEN 'Financial District' WHEN location LIKE '%Sutro%' OR location LIKE '%Lands End%' OR location LIKE '%Cliff%' THEN 'Sutro / Lands End' ELSE 'Other' END AS neighborhood, COUNT(*) AS photos FROM photos GROUP BY neighborhood ORDER BY photos DESC" -column -header
```

```output
neighborhood       photos
-----------------  ------
Other              40
Golden Gate        10
Fishermans Wharf   10
Chinatown          10
Union Square       8
North Beach        4
Sutro / Lands End  2
Nob Hill           1
```

### Sample Descriptions

The model generates a 1-2 sentence description for each photo alongside its
analysis.

```bash
sqlite3 /Users/mark/working/photo-ai/photo_analysis.db "SELECT filename, description FROM photos ORDER BY filename LIMIT 5" -column -header
```

```output
filename       description
-------------  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
IMG_8825.HEIC  A low-angle view of the sleek, metallic facade of an Apple Store on a wet city street, with a tree on the left framing the shot and a city intersection visible in the background.
IMG_8835.HEIC  A wet, overcast day in a city where a traditional Chinese gate with green tiled roofs and stone lions marks the entrance to a neighborhood. The scene is framed by modern high-rise buildings and a busy street corner with traffic lights.
IMG_8837.HEIC  A low-angle shot captures a traditional Chinese gate with green tiled roofs and a stone lion statue in the foreground, set against a backdrop of a city street with modern buildings and a light snowfall. The scene is framed by the archway, creating a strong sense of depth and cultural contrast.
IMG_8846.HEIC  A vibrant mural of a man in a yellow and black suit adorns the wall next to a steep, concrete staircase. To the right, a shop window displays tote bags with San Francisco landmarks, creating a dynamic urban scene.
IMG_8849.HEIC  A wide-angle shot looking down a narrow, brightly lit souvenir shop filled with merchandise like t-shirts, keychains, and Route 66 memorabilia. The perspective creates a strong sense of depth, with red mats on the floor leading towards the back of the store.
```

## Pipeline Architecture

Each image goes through: HEIC decode → resize to 1024px max → base64 encode →
EXIF GPS extraction → single vision API call → JSON parse + validate → SQLite
insert.

```bash
sqlite3 /Users/mark/working/photo-ai/photo_analysis.db "SELECT COUNT(*) || ' photos with GPS' FROM photos WHERE latitude IS NOT NULL"
```

```output
85 photos with GPS
```

```bash
sqlite3 /Users/mark/working/photo-ai/photo_analysis.db "SELECT ROUND(SUM(file_size_bytes) / 1048576.0, 1) || ' MB total (' || ROUND(AVG(file_size_bytes) / 1048576.0, 1) || ' MB avg per photo)' FROM photos"
```

```output
272.4 MB total (3.2 MB avg per photo)
```

## Browsing with Datasette

The SQLite database uses WAL mode, so you can browse results in Datasette while
analysis is still running.

```bash
echo 'uvx datasette photo_analysis.db'
```

```output
uvx datasette photo_analysis.db
```

## Schema

```bash
sqlite3 /Users/mark/working/photo-ai/photo_analysis.db '.schema'
```

```output
CREATE TABLE photos (
    path                    TEXT PRIMARY KEY,
    filename                TEXT,
    analyzed_at             TEXT,
    image_width             INTEGER,
    image_height            INTEGER,
    file_size_bytes         INTEGER,
    tags                    TEXT,
    category                TEXT,
    composition_score       REAL,
    composition_elements    TEXT,
    composition_explanation TEXT,
    description             TEXT,
    model                   TEXT,
    raw_response            TEXT
, location TEXT, latitude REAL, longitude REAL);
CREATE TABLE photo_tags (
    photo_path TEXT NOT NULL REFERENCES photos(path) ON DELETE CASCADE,
    tag        TEXT NOT NULL,
    PRIMARY KEY (photo_path, tag)
);
```
