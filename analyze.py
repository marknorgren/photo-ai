# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "openai",
#     "Pillow",
#     "pillow-heif",
#     "tqdm",
# ]
# ///
"""Analyze photos using LM Studio vision API and store results in SQLite."""

import argparse
import base64
import io
import json
import logging
import os
import sqlite3
import sys
import time
from pathlib import Path

from openai import OpenAI
from PIL import Image
from PIL.ExifTags import GPS, Base as ExifBase
from tqdm import tqdm

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".tiff", ".tif"}

ANALYSIS_PROMPT_BASE = """\
Analyze this photograph and return a JSON object with exactly these keys:

1. "tags" — up to 8 tags from these categories. Be selective: only apply a tag if it is a defining characteristic of this specific image, not just vaguely present.
   Scene: landscape, portrait, street, architecture, macro, wildlife, aerial, concert, night, astro, food, sports, travel, fashion, urban
   Subject: person, animal, building, nature, water, sky, mountain, beach, forest, flower, vehicle
   Style: monochrome, silhouette, long_exposure, dramatic, minimalist, vintage, cinematic, abstract, bokeh
   Mood: dramatic, peaceful, energetic, intimate, moody
   Weather: fog, rain, snow, storm

2. "composition" — an object with:
   "score": integer 1-7 using this scale (be critical, most photos should score 3-5):
     7 = Perfect — museum-quality, exceptional in every way
     6 = Excellent — strong composition worth studying, minor imperfections
     5 = Good — solid composition, nothing distracting
     4 = Passable — acceptable but unremarkable, some compositional issues
     3 = Bad — noticeable problems (clutter, poor framing, no clear subject)
     2 = Atrocious — major compositional failures
     1 = Terrible — no compositional merit
   "elements": array of applicable elements from [rule_of_thirds, leading_lines, symmetry, depth, framing, negative_space]
   "explanation": one sentence explaining the score, referencing specific strengths or weaknesses

3. "category" — single best-fit from: landscape, portrait, street, architecture, macro, wildlife, aerial, concert, night, astro, food, sports, travel, fashion, urban, abstract, minimalist, dramatic, monochrome, weather, default

4. "description" — 1-2 sentence natural language description of the image

{location_instruction}

Return ONLY valid JSON, no markdown fences, no extra text.\
"""

LOCATION_WITH_GPS = """\
5. "location" — a human-readable place name that combines what you see in the photo with the GPS coordinates ({lat}, {lon}). \
Be specific: name the landmark, venue, park, neighborhood, or point of interest visible in the image, \
followed by city and state/country. Example: "Apple Store, Union Square, San Francisco, CA"\
"""

LOCATION_NO_GPS = """\
5. "location" — if you can identify the specific place, landmark, or venue in the photo, provide a human-readable location \
(e.g. "Golden Gate Bridge, San Francisco, CA"). If you cannot confidently identify the location, set to null.\
"""

SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS photos (
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
    location                TEXT,
    latitude                REAL,
    longitude               REAL,
    model                   TEXT,
    raw_response            TEXT
);

CREATE TABLE IF NOT EXISTS photo_tags (
    photo_path TEXT NOT NULL REFERENCES photos(path) ON DELETE CASCADE,
    tag        TEXT NOT NULL,
    PRIMARY KEY (photo_path, tag)
);
"""

MIGRATIONS = [
    "ALTER TABLE photos ADD COLUMN location TEXT",
    "ALTER TABLE photos ADD COLUMN latitude REAL",
    "ALTER TABLE photos ADD COLUMN longitude REAL",
]


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA_SQL)
    # Run migrations for existing databases
    for sql in MIGRATIONS:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass  # Column already exists
    conn.commit()
    return conn


def get_analyzed_paths(conn: sqlite3.Connection) -> set[str]:
    cursor = conn.execute("SELECT path FROM photos")
    return {row[0] for row in cursor.fetchall()}


def find_images(directory: Path) -> list[Path]:
    images = []
    for entry in sorted(directory.rglob("*")):
        if entry.is_file() and entry.suffix.lower() in IMAGE_EXTENSIONS:
            images.append(entry)
    return images


def extract_gps(image_path: Path) -> tuple[float, float] | None:
    """Extract GPS lat/lon from EXIF data. Returns (lat, lon) or None."""
    try:
        img = Image.open(image_path)
        exif = img.getexif()
        if not exif:
            return None
        gps_info = exif.get_ifd(ExifBase.GPSInfo)
        if not gps_info:
            return None

        def to_degrees(dms_tuple, ref):
            d, m, s = [float(x) for x in dms_tuple]
            degrees = d + m / 60.0 + s / 3600.0
            if ref in ("S", "W"):
                degrees = -degrees
            return degrees

        lat_dms = gps_info.get(GPS.GPSLatitude)
        lat_ref = gps_info.get(GPS.GPSLatitudeRef)
        lon_dms = gps_info.get(GPS.GPSLongitude)
        lon_ref = gps_info.get(GPS.GPSLongitudeRef)

        if lat_dms and lat_ref and lon_dms and lon_ref:
            return to_degrees(lat_dms, lat_ref), to_degrees(lon_dms, lon_ref)
    except Exception as e:
        log.debug("Could not extract GPS from %s: %s", image_path.name, e)
    return None


def resize_and_encode(image_path: Path, max_dimension: int) -> tuple[str, int, int]:
    """Load image, resize to fit max_dimension, return base64 JPEG + original dimensions."""
    img = Image.open(image_path)
    original_width, original_height = img.size

    # Convert palette/RGBA to RGB for JPEG encoding
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Resize if needed
    if max(original_width, original_height) > max_dimension:
        img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return b64, original_width, original_height


def build_prompt(gps: tuple[float, float] | None) -> str:
    if gps:
        location_instruction = LOCATION_WITH_GPS.format(lat=f"{gps[0]:.6f}", lon=f"{gps[1]:.6f}")
    else:
        location_instruction = LOCATION_NO_GPS
    return ANALYSIS_PROMPT_BASE.format(location_instruction=location_instruction)


def analyze_image(client: OpenAI, model: str, b64_data: str, gps: tuple[float, float] | None = None) -> dict:
    """Send image to LM Studio and return parsed analysis JSON."""
    prompt = build_prompt(gps)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64_data}"},
                    },
                ],
            }
        ],
        temperature=0.3,
    )
    raw = response.choices[0].message.content.strip()

    # Strip markdown fences if the model wraps its response
    if raw.startswith("```"):
        lines = raw.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)

    return json.loads(raw)


def validate_analysis(data: dict) -> dict:
    """Validate and normalize the analysis response."""
    raw_tags = data.get("tags", [])
    if isinstance(raw_tags, dict):
        # Model returned {"Scene": "street", "Subject": "building", ...}
        # Flatten values — handle both single strings and lists
        tags = []
        for v in raw_tags.values():
            if isinstance(v, list):
                tags.extend(str(t) for t in v)
            else:
                tags.append(str(v))
    elif isinstance(raw_tags, list):
        tags = [str(t) for t in raw_tags]
    else:
        tags = []
    tags = tags[:8]

    comp = data.get("composition", {})
    if not isinstance(comp, dict):
        comp = {}
    score = comp.get("score", 0)
    if not isinstance(score, (int, float)) or not (1 <= score <= 7):
        score = 0
    elements = comp.get("elements", [])
    if not isinstance(elements, list):
        elements = []
    explanation = str(comp.get("explanation", ""))

    category = str(data.get("category", "default"))
    description = str(data.get("description", ""))
    location = data.get("location")
    if location is not None:
        location = str(location)

    return {
        "tags": tags,
        "composition_score": float(score),
        "composition_elements": elements,
        "composition_explanation": explanation,
        "category": category,
        "description": description,
        "location": location,
    }


def insert_result(
    conn: sqlite3.Connection,
    image_path: Path,
    width: int,
    height: int,
    analysis: dict,
    model: str,
    raw_json: str,
    gps: tuple[float, float] | None,
) -> None:
    file_size = image_path.stat().st_size
    analyzed_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    tags = analysis["tags"]
    lat, lon = gps if gps else (None, None)

    conn.execute(
        """INSERT OR REPLACE INTO photos
           (path, filename, analyzed_at, image_width, image_height, file_size_bytes,
            tags, category, composition_score, composition_elements,
            composition_explanation, description, location, latitude, longitude,
            model, raw_response)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            str(image_path.resolve()),
            image_path.name,
            analyzed_at,
            width,
            height,
            file_size,
            ", ".join(tags),
            analysis["category"],
            analysis["composition_score"],
            ", ".join(str(e) for e in analysis["composition_elements"]),
            analysis["composition_explanation"],
            analysis["description"],
            analysis.get("location"),
            lat,
            lon,
            model,
            raw_json,
        ),
    )

    # Clear old tags then insert fresh
    conn.execute("DELETE FROM photo_tags WHERE photo_path = ?", (str(image_path.resolve()),))
    for tag in tags:
        conn.execute(
            "INSERT OR IGNORE INTO photo_tags (photo_path, tag) VALUES (?, ?)",
            (str(image_path.resolve()), tag),
        )
    conn.commit()


def process_images(
    images: list[Path],
    *,
    client: OpenAI,
    model: str,
    conn: sqlite3.Connection,
    max_dimension: int,
    max_retries: int = 3,
) -> tuple[int, int]:
    """Process a list of images. Returns (success_count, error_count)."""
    success = 0
    errors = 0

    for image_path in tqdm(images, desc="Analyzing", unit="img"):
        gps = extract_gps(image_path)
        for attempt in range(1, max_retries + 1):
            try:
                b64, width, height = resize_and_encode(image_path, max_dimension)
                result = analyze_image(client, model, b64, gps=gps)
                raw_json = json.dumps(result)
                analysis = validate_analysis(result)
                insert_result(conn, image_path, width, height, analysis, model, raw_json, gps=gps)
                success += 1
                break
            except json.JSONDecodeError as e:
                log.warning("Invalid JSON from model for %s (attempt %d/%d): %s", image_path.name, attempt, max_retries, e)
                if attempt == max_retries:
                    log.error("Skipping %s after %d failed attempts", image_path.name, max_retries)
                    errors += 1
            except Exception as e:
                log.warning("Error analyzing %s (attempt %d/%d): %s", image_path.name, attempt, max_retries, e)
                if attempt == max_retries:
                    log.error("Skipping %s after %d failed attempts", image_path.name, max_retries)
                    errors += 1
                else:
                    time.sleep(2 ** attempt)

    return success, errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze photos using LM Studio vision API")
    parser.add_argument("directory", type=Path, help="Directory of images to analyze")
    parser.add_argument("--db", default="photo_analysis.db", help="SQLite database path (default: photo_analysis.db)")
    parser.add_argument("--base-url", default="http://127.0.0.1:1234/v1", help="LM Studio server URL (default: http://127.0.0.1:1234/v1)")
    parser.add_argument("--model", default="qwen/qwen3-vl-30b", help="Model name (default: qwen/qwen3-vl-30b)")
    parser.add_argument("--force", action="store_true", help="Re-analyze already processed images")
    parser.add_argument("--max-images", type=int, default=0, help="Limit number of images to process (0 = all)")
    parser.add_argument("--max-dimension", type=int, default=1024, help="Max image dimension for resizing (default: 1024)")
    parser.add_argument("--dry-run", action="store_true", help="Preview which images would be analyzed")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.directory.is_dir():
        print(f"Error: {args.directory} is not a directory", file=sys.stderr)
        sys.exit(1)

    # Register HEIF/HEIC support
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
    except ImportError:
        log.warning("pillow-heif not available — HEIC/HEIF files will be skipped")

    all_images = find_images(args.directory)
    if not all_images:
        print("No images found in", args.directory)
        sys.exit(0)

    conn = init_db(args.db)
    analyzed = get_analyzed_paths(conn) if not args.force else set()

    to_process = [img for img in all_images if str(img.resolve()) not in analyzed]

    if args.max_images > 0:
        to_process = to_process[: args.max_images]

    print(f"Found {len(all_images)} images, {len(to_process)} to analyze")

    if args.dry_run:
        for img in to_process:
            print(f"  {img}")
        conn.close()
        return

    if not to_process:
        print("Nothing to do — all images already analyzed. Use --force to re-analyze.")
        conn.close()
        return

    client = OpenAI(base_url=args.base_url, api_key="lm-studio")

    success, errors = process_images(
        to_process,
        client=client,
        model=args.model,
        conn=conn,
        max_dimension=args.max_dimension,
    )

    conn.close()

    print(f"\nDone: {success} analyzed, {errors} errors, {len(all_images) - len(to_process)} skipped (already in db)")


if __name__ == "__main__":
    main()
