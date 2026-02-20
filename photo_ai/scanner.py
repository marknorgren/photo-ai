"""Scan command: find, analyze, and store photo analysis results."""

import base64
import io
import json
import logging
import time
from pathlib import Path

from collections.abc import Callable
from typing import Any

from PIL import Image
from PIL.ExifTags import GPS, Base as ExifBase
from tqdm import tqdm

from .db import get_analyzed_paths
from .util import (
    ANALYSIS_PROMPT_BASE,
    IMAGE_EXTENSIONS,
    LOCATION_NO_GPS,
    LOCATION_WITH_GPS,
    SCORE_LABELS,
)

log = logging.getLogger(__name__)


def find_images(directory: Path) -> list[Path]:
    """Recursively find all image files in directory."""
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

    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")

    if max(original_width, original_height) > max_dimension:
        img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return b64, original_width, original_height


def build_prompt(gps: tuple[float, float] | None) -> str:
    """Build the analysis prompt, including GPS context if available."""
    if gps:
        location_instruction = LOCATION_WITH_GPS.format(lat=f"{gps[0]:.6f}", lon=f"{gps[1]:.6f}")
    else:
        location_instruction = LOCATION_NO_GPS
    return ANALYSIS_PROMPT_BASE.format(location_instruction=location_instruction)


def analyze_image(analyze_fn: Callable[[str, str], dict], b64_data: str, gps: tuple[float, float] | None = None) -> dict:
    """Send image to vision model via analyze_fn and return parsed analysis JSON."""
    prompt = build_prompt(gps)
    return analyze_fn(b64_data, prompt)


def validate_analysis(data: dict) -> dict:
    """Validate and normalize the analysis response."""
    raw_tags = data.get("tags", [])
    if isinstance(raw_tags, dict):
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
    if not isinstance(score, (int, float)):
        score = 0
    score = max(0, min(7, score))  # clamp to 0-7
    elements = comp.get("elements", [])
    if not isinstance(elements, list):
        elements = []
    explanation = str(comp.get("explanation", ""))
    issues = comp.get("issues", [])
    if not isinstance(issues, list):
        issues = []
    suggestions = comp.get("suggestions", [])
    if not isinstance(suggestions, list):
        suggestions = []
    suggestions = [str(s) for s in suggestions[:3]]

    category = str(data.get("category", "default"))
    description = str(data.get("description", ""))
    caption = str(data.get("caption", ""))
    title = str(data.get("title", ""))
    location = data.get("location")
    if location is not None:
        location = str(location)

    return {
        "tags": tags,
        "composition_score": float(score),
        "composition_elements": elements,
        "composition_issues": issues,
        "composition_explanation": explanation,
        "composition_suggestions": suggestions,
        "category": category,
        "description": description,
        "caption": caption,
        "title": title,
        "location": location,
    }


def insert_result(conn, image_path: Path, width: int, height: int, analysis: dict, model: str, raw_json: str, gps: tuple[float, float] | None) -> None:
    """Insert or replace a photo analysis result into the database."""
    file_size = image_path.stat().st_size
    analyzed_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    tags = analysis["tags"]
    lat, lon = gps if gps else (None, None)

    conn.execute(
        """INSERT OR REPLACE INTO photos
           (path, filename, analyzed_at, image_width, image_height, file_size_bytes,
            tags, category, composition_score, composition_elements,
            composition_explanation, composition_issues, composition_suggestions,
            description, caption, title,
            location, latitude, longitude, model, raw_response)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
            ", ".join(str(i) for i in analysis.get("composition_issues", [])),
            " | ".join(analysis.get("composition_suggestions", [])),
            analysis["description"],
            analysis["caption"],
            analysis["title"],
            analysis.get("location"),
            lat,
            lon,
            model,
            raw_json,
        ),
    )

    conn.execute("DELETE FROM photo_tags WHERE photo_path = ?", (str(image_path.resolve()),))
    for tag in tags:
        conn.execute(
            "INSERT OR IGNORE INTO photo_tags (photo_path, tag) VALUES (?, ?)",
            (str(image_path.resolve()), tag),
        )
    conn.commit()


def process_images(images: list[Path], *, analyze_fn: Callable[[str, str], dict], model: str, conn, max_dimension: int, max_retries: int = 3) -> tuple[int, int]:
    """Process a list of images. Returns (success_count, error_count)."""
    success = 0
    errors = 0

    for image_path in tqdm(images, desc="Analyzing", unit="img"):
        gps = extract_gps(image_path)
        for attempt in range(1, max_retries + 1):
            try:
                b64, width, height = resize_and_encode(image_path, max_dimension)
                result = analyze_image(analyze_fn, b64, gps=gps)
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


def print_scan_summary(conn) -> None:
    """Print a post-scan summary: score distribution, top 5, category/tag breakdown."""
    conn.row_factory = None

    total = conn.execute("SELECT COUNT(*) FROM photos").fetchone()[0]
    if total == 0:
        print("\nNo photos in database.")
        return

    print(f"\n{'=' * 50}")
    print(f"  Database: {total} photos analyzed")
    print(f"{'=' * 50}")

    # Score distribution
    print("\nScore distribution:")
    rows = conn.execute("SELECT CAST(composition_score AS INTEGER) AS s, COUNT(*) FROM photos GROUP BY s ORDER BY s DESC").fetchall()
    for score, count in rows:
        bar = "#" * count
        label = SCORE_LABELS.get(score, "?")
        print(f"  {score} {label:<10} {bar} ({count})")

    # Top 5
    print("\nTop 5:")
    top = conn.execute("SELECT filename, composition_score, category, title FROM photos ORDER BY composition_score DESC, filename LIMIT 5").fetchall()
    for fname, score, cat, title in top:
        title_str = f' "{title}"' if title else ""
        print(f"  {score:.0f}/7  {fname:<30} {cat}{title_str}")

    # Category breakdown
    print("\nCategories:")
    cats = conn.execute("SELECT category, COUNT(*) FROM photos GROUP BY category ORDER BY COUNT(*) DESC").fetchall()
    for cat, count in cats:
        print(f"  {cat:<20} {count}")

    # Top tags
    print("\nTop 10 tags:")
    tags = conn.execute("SELECT tag, COUNT(*) AS c FROM photo_tags GROUP BY tag ORDER BY c DESC LIMIT 10").fetchall()
    for tag, count in tags:
        print(f"  {tag:<20} {count}")

    print()
