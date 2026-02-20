# photo-ai CLI Walkthrough

*2026-02-19T22:22:31Z by Showboat dev*
<!-- showboat-id: 298dc715-5974-4ba9-926a-80ae20150cee -->

The photo-ai CLI analyzes photos using a local vision LLM and stores results in SQLite. After scanning, you can query, filter, report, and publish your photo library — all from the command line. This walkthrough uses an existing database of 85 street photos from San Francisco.

## Discover available commands

```bash
uv run analyze.py --help
```

```output
usage: analyze.py [-h] [-v] [--db DB]
                  {scan,eval,top,bottom,tags,find,info,stats,report,export,publish} ...

Photo analysis CLI — analyze, query, and export photo data

positional arguments:
  {scan,eval,top,bottom,tags,find,info,stats,report,export,publish}
    scan                Analyze photos in a directory
    eval                Run model evaluation against golden dataset
    top                 Show top-scoring photos
    bottom              Show lowest-scoring photos
    tags                Show tag frequency
    find                Search photos with filters
    info                Show detail for one photo
    stats               Show database summary
    report              Generate markdown report to stdout
    export              Export data as JSON or CSV
    publish             Generate gallery markdown with thumbnails

options:
  -h, --help            show this help message and exit
  -v, --verbose         Enable verbose logging
  --db DB               SQLite database path (default: photo_analysis.db)
```

## Database overview

Start with `stats` to see what's in your database.

```bash
uv run analyze.py stats
```

```output
Photos:      85
Avg score:   5.49/7
Score range: 4-6
Categories:  9
Unique tags: 48
With GPS:    85
With location: 85
Total size:  272.4 MB
Models:      qwen/qwen3-vl-30b

Score distribution:
  6 Excellent  ########################################### (43)
  5 Good       ######################################### (41)
  4 Passable   # (1)
```

85 photos, all with GPS and location data. Scores cluster around 5-6 — this model tends to be generous.

## Best and worst photos

`top` and `bottom` show the score extremes.

```bash
uv run analyze.py top 5
```

```output
Score  Label      File           Category      Title  Location                           
-----  ---------  -------------  ------------  -----  -----------------------------------
  6/7  Excellent  IMG_8825.HEIC  street               Apple Store, Union Square, San F...
  6/7  Excellent  IMG_8837.HEIC  street               Chinatown Gate, San Francisco, CA  
  6/7  Excellent  IMG_8846.HEIC  street               Lombard Street, San Francisco, CA  
  6/7  Excellent  IMG_8852.HEIC  architecture         San Francisco City Hall Clock To...
  6/7  Excellent  IMG_8856.HEIC  street               Chinatown, San Francisco, CA       
```

```bash
uv run analyze.py bottom 3
```

```output
Score  Label     File           Category  Explanation                             
-----  --------  -------------  --------  ----------------------------------------
  4/7  Passable  IMG_8850.HEIC  urban     The image has a passable score due to...
  5/7  Good      IMG_8835.HEIC  street    The composition is strong, using the ...
  5/7  Good      IMG_8849.HEIC  travel    The image has a strong sense of depth...
```

Only one photo scored below 5. The `bottom` view includes the explanation so you can see why.

## Explore tags

`tags` shows which tags appear most often. Use `--min` to filter out rare tags.

```bash
uv run analyze.py tags --min 10
```

```output
  building             ############################## (53)
  street               ########################### (49)
  urban                ########################## (47)
  sky                  ########################## (47)
  dramatic             ######################## (44)
  architecture         ###################### (39)
  rain                 ############## (26)
  vehicle              ############## (25)
  moody                ############# (23)
  nature               ########### (21)
  cinematic            ########### (20)
  person               ########## (18)
  landscape            ####### (14)
  travel               ####### (13)
  mountain             ####### (13)
  water                ###### (12)
  peaceful             ###### (12)
  night                ##### (10)
```

Rainy day in SF — `rain` appears in 26 of 85 photos. The `dramatic` and `moody` tags reinforce the weather vibe.

## Filtered search

`find` combines filters: tag, category, location text, and score. Score supports exact (`6`), minimum (`5+`), and range (`3-5`) syntax.

```bash
uv run analyze.py find --tag rain --score 6
```

```output
13 photos found:

Score  File           Category      Title  Location                      
-----  -------------  ------------  -----  ------------------------------
  6/7  IMG_8825.HEIC  street               Apple Store, Union Square, ...
  6/7  IMG_8856.HEIC  street               Chinatown, San Francisco, CA  
  6/7  IMG_8860.HEIC  street               Chinatown, San Francisco, CA  
  6/7  IMG_8878.HEIC  urban                The Green Building, North B...
  6/7  IMG_8897.HEIC  street               Cafe Sicilia, North Beach, ...
  6/7  IMG_8902.HEIC  street               Pier 39, San Francisco, CA    
  6/7  IMG_8905.HEIC  street               Lombard Street, North Beach...
  6/7  IMG_8916.HEIC  architecture         Painted Ladies, Alamo Squar...
  6/7  IMG_8926.HEIC  urban                Lombard Street, San Francis...
  6/7  IMG_8927.HEIC  architecture         The Pink and Blue Buildings...
  6/7  IMG_9002.HEIC  food                 The Gourmet Burger Kitchen,...
  6/7  IMG_9043.HEIC  urban                Chinatown Gate, San Francis...
  6/7  IMG_9046.HEIC  street               Chinatown Tunnel, San Franc...
```

```bash
uv run analyze.py find --location 'Golden Gate'
```

```output
10 photos found:

Score  File           Category      Title  Location                      
-----  -------------  ------------  -----  ------------------------------
  6/7  IMG_9270.HEIC  landscape            Golden Gate National Recrea...
  6/7  IMG_9284.HEIC  landscape            Golden Gate Bridge Viewpoin...
  6/7  IMG_9292.HEIC  landscape            Golden Gate Bridge, San Fra...
  6/7  IMG_9304.HEIC  landscape            Golden Gate Bridge, San Fra...
  6/7  IMG_9309.HEIC  architecture         Golden Gate Bridge, San Fra...
  6/7  IMG_9334.HEIC  landscape            Golden Gate Bridge, San Fra...
  6/7  IMG_9343.HEIC  landscape            Golden Gate Bridge, San Fra...
  6/7  IMG_9353.HEIC  architecture         Golden Gate Bridge, San Fra...
  6/7  IMG_9365.HEIC  architecture         Golden Gate Bridge, San Fra...
  5/7  IMG_9259.HEIC  landscape            Golden Gate Bridge Viewpoin...
```

## Photo detail

`info` gives the full analysis for a single photo. Pass a filename — it matches by filename or path substring.

```bash
uv run analyze.py info IMG_9187.HEIC
```

```output
File:        IMG_9187.HEIC
Path:        /Users/mark/Downloads/SF Feb 2026/IMG_9187.HEIC
Title:       (none)
Caption:     (none)
Category:    architecture
Score:       6/7 (Excellent)
Elements:    leading_lines, symmetry, depth, framing
Explanation: The image excels in composition with strong leading lines created by the fire escape, a balanced symmetry, and effective framing by the adjacent buildings, all contributing to a dramatic and minimalist aesthetic.
Description: A high-contrast, monochrome photograph captures a metal fire escape descending through a narrow urban alleyway between two buildings. The scene is defined by strong vertical lines, a sense of depth, and graffiti on the walls, creating a dramatic and moody atmosphere.
Location:    Fire escape, San Francisco, CA
GPS:         37.788842, -122.404403
Tags:        architecture, building, dramatic, minimalist, monochrome, moody, street, urban
Dimensions:  4066x5422
File size:   3,149,099 bytes
Model:       qwen/qwen3-vl-30b
Analyzed:    2026-02-18T14:42:57
```

## Reports and exports

`report` generates a markdown report to stdout — pipe it to a file. `export` dumps JSON or CSV.

```bash
uv run analyze.py report | head -25
```

```output
# Photo Analysis Report

85 photos · avg score 5.5/7 · model: qwen/qwen3-vl-30b

## Score Distribution

| Score | Label | Count |
|------:|-------|------:|
| 6 | Excellent | 43 |
| 5 | Good | 41 |
| 4 | Passable | 1 |

## Categories

| Category | Count |
|----------|------:|
| street | 29 |
| architecture | 18 |
| urban | 13 |
| landscape | 13 |
| food | 4 |
| portrait | 3 |
| night | 2 |
| abstract | 2 |
| travel | 1 |
```

```bash
uv run analyze.py export --format csv | head -1 | tr ',' '\n'
```

```output
path
filename
analyzed_at
image_width
image_height
file_size_bytes
tags
category
composition_score
composition_elements
composition_explanation
description
model
raw_response
location
latitude
longitude
caption
title
```

19 columns in the CSV export — everything from file path and dimensions to composition analysis and GPS coordinates.

## Publish a gallery

`publish` generates a self-contained markdown file with embedded base64 thumbnail images. Add `--gist` to push directly to GitHub Gist.

```bash
uv run analyze.py publish --top 3 --title 'SF Feb 2026'
```

```output
Gallery written to gallery.md (3 photos, 149,613 bytes)
```

```bash
head -4 gallery.md && echo '...(base64 thumbnail data)...' && grep -c '<img' gallery.md | xargs -I{} echo '{} embedded thumbnails'
```

```output
# SF Feb 2026

3 photos · analyzed with qwen/qwen3-vl-30b

...(base64 thumbnail data)...
3 embedded thumbnails
```

Each photo gets a resized 400px thumbnail encoded as base64 directly in the markdown. GitHub Gist renders these inline — add `--gist` to publish directly.

## Backward compatibility

The original `uv run analyze.py /path/to/photos` syntax still works — the CLI auto-detects paths and prepends `scan`.

```bash
uv run analyze.py '/Users/mark/Downloads/SF Feb 2026' --dry-run --max-images 3
```

```output
Found 85 images, 0 to analyze
```

All 85 images already analyzed — nothing to do. The `--force` flag would re-analyze them.
