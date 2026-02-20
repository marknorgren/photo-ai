"""Publish command: generate gallery markdown with embedded thumbnails."""

import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from .scanner import resize_and_encode
from .util import score_label


def cmd_publish(conn: sqlite3.Connection, top_n: int = 20, title: str = "Photo Gallery", gist: bool = False, public: bool = False, all_photos: bool = False) -> None:
    """Generate a markdown gallery with embedded base64 thumbnails."""
    if all_photos:
        rows = conn.execute(
            "SELECT * FROM photos ORDER BY composition_score DESC, filename"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM photos ORDER BY composition_score DESC, filename LIMIT ?",
            (top_n,),
        ).fetchall()

    if not rows:
        print("No photos found.", file=sys.stderr)
        sys.exit(1)

    models = sorted(set(r["model"] for r in rows))
    md_lines = [
        f"# {title}",
        "",
        f"{len(rows)} photos · analyzed with {', '.join(models)}",
        "",
        "## Gallery",
        "",
    ]

    for row in rows:
        photo_path = Path(row["path"])
        photo_title = row["title"] or row["filename"]
        score = row["composition_score"]
        category = row["category"]
        location = row["location"] or ""
        caption = row["caption"] or ""
        tags = row["tags"] or ""

        md_lines.append(f"### {photo_title}")
        score_str = f"**Score: {score:.0f}/7** ({score_label(score)})"
        loc_str = f" · {location}" if location else ""
        md_lines.append(f"{score_str} · {category}{loc_str}")
        md_lines.append("")

        # Embed thumbnail if the file exists
        if photo_path.exists():
            try:
                b64, _, _ = resize_and_encode(photo_path, 400)
                md_lines.append(f'<img src="data:image/jpeg;base64,{b64}" width="400">')
                md_lines.append("")
            except Exception:
                md_lines.append("*(thumbnail unavailable)*")
                md_lines.append("")
        else:
            md_lines.append("*(file not found)*")
            md_lines.append("")

        if caption:
            md_lines.append(f"*{caption}*")
            md_lines.append("")
        if tags:
            md_lines.append(f"Tags: {tags}")
            md_lines.append("")
        suggestions = row["composition_suggestions"] if "composition_suggestions" in row.keys() else None
        if suggestions:
            tips = [s.strip() for s in suggestions.split(" | ") if s.strip()]
            if tips:
                md_lines.append("**Tips:**")
                for tip in tips:
                    md_lines.append(f"- {tip}")
                md_lines.append("")

        md_lines.append("---")
        md_lines.append("")

    markdown = "\n".join(md_lines)

    if gist:
        _push_gist(markdown, title, public)
    else:
        output_path = Path("gallery.md")
        output_path.write_text(markdown)
        print(f"Gallery written to {output_path} ({len(rows)} photos, {len(markdown):,} bytes)")


def _push_gist(markdown: str, title: str, public: bool) -> None:
    """Create a GitHub Gist via gh CLI."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", prefix="gallery_", delete=False) as f:
        f.write(markdown)
        tmp_path = f.name

    cmd = ["gh", "gist", "create", tmp_path, "--desc", title]
    if public:
        cmd.append("--public")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        url = result.stdout.strip()
        print(f"Gist created: {url}")
    except FileNotFoundError:
        print("Error: 'gh' CLI not found. Install it: https://cli.github.com/", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error creating gist: {e.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
