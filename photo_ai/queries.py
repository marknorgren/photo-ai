"""Query commands: top, bottom, tags, find, info, stats."""

import sqlite3
import sys

from .util import format_table, score_label


def cmd_top(conn: sqlite3.Connection, n: int, category: str | None = None, tag: str | None = None) -> None:
    """Show top N photos by composition score."""
    query = "SELECT filename, composition_score, category, title, location FROM photos"
    conditions = []
    params: list = []

    if category:
        conditions.append("category = ?")
        params.append(category)
    if tag:
        conditions.append("path IN (SELECT photo_path FROM photo_tags WHERE tag = ?)")
        params.append(tag)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY composition_score DESC, filename LIMIT ?"
    params.append(n)

    rows = conn.execute(query, params).fetchall()
    if not rows:
        print("No photos found.")
        return

    table_rows = []
    for row in rows:
        score = row["composition_score"]
        label = score_label(score)
        title = row["title"] or ""
        loc = row["location"] or ""
        if len(loc) > 35:
            loc = loc[:32] + "..."
        table_rows.append([f"{score:.0f}/7", label, row["filename"], row["category"], title, loc])

    print(format_table(
        ["Score", "Label", "File", "Category", "Title", "Location"],
        table_rows,
        [">", "<", "<", "<", "<", "<"],
    ))


def cmd_bottom(conn: sqlite3.Connection, n: int) -> None:
    """Show bottom N photos by composition score."""
    rows = conn.execute(
        "SELECT filename, composition_score, category, title, composition_explanation FROM photos ORDER BY composition_score ASC, filename LIMIT ?",
        (n,),
    ).fetchall()
    if not rows:
        print("No photos found.")
        return

    table_rows = []
    for row in rows:
        score = row["composition_score"]
        label = score_label(score)
        expl = row["composition_explanation"] or ""
        if len(expl) > 40:
            expl = expl[:37] + "..."
        table_rows.append([f"{score:.0f}/7", label, row["filename"], row["category"], expl])

    print(format_table(
        ["Score", "Label", "File", "Category", "Explanation"],
        table_rows,
        [">", "<", "<", "<", "<"],
    ))


def cmd_tags(conn: sqlite3.Connection, min_count: int = 1) -> None:
    """Show tag frequency with bar chart."""
    rows = conn.execute(
        "SELECT tag, COUNT(*) AS c FROM photo_tags GROUP BY tag HAVING c >= ? ORDER BY c DESC",
        (min_count,),
    ).fetchall()
    if not rows:
        print("No tags found.")
        return

    max_count = max(row["c"] for row in rows)
    bar_width = 30

    for row in rows:
        tag = row["tag"]
        count = row["c"]
        bar_len = int(count / max_count * bar_width) if max_count > 0 else 0
        bar = "#" * bar_len
        print(f"  {tag:<20} {bar} ({count})")


def _parse_score_filter(score_str: str) -> tuple[float, float]:
    """Parse score filter string. Returns (min, max) inclusive.

    Supports: "6" (exact), "5+" (>=5), "3-5" (range).
    """
    if "+" in score_str:
        val = float(score_str.replace("+", ""))
        return val, 7.0
    if "-" in score_str:
        parts = score_str.split("-")
        return float(parts[0]), float(parts[1])
    val = float(score_str)
    return val, val


def cmd_find(conn: sqlite3.Connection, tag: str | None = None, category: str | None = None, location: str | None = None, score_filter: str | None = None) -> None:
    """Search photos with filters."""
    query = "SELECT filename, composition_score, category, title, location, tags FROM photos"
    conditions = []
    params: list = []

    if tag:
        conditions.append("path IN (SELECT photo_path FROM photo_tags WHERE tag = ?)")
        params.append(tag)
    if category:
        conditions.append("category = ?")
        params.append(category)
    if location:
        conditions.append("location LIKE ?")
        params.append(f"%{location}%")
    if score_filter:
        min_s, max_s = _parse_score_filter(score_filter)
        conditions.append("composition_score >= ? AND composition_score <= ?")
        params.extend([min_s, max_s])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY composition_score DESC, filename"

    rows = conn.execute(query, params).fetchall()
    if not rows:
        print("No photos match the filters.")
        return

    print(f"{len(rows)} photos found:\n")
    table_rows = []
    for row in rows:
        score = row["composition_score"]
        loc = row["location"] or ""
        if len(loc) > 30:
            loc = loc[:27] + "..."
        table_rows.append([f"{score:.0f}/7", row["filename"], row["category"], row["title"] or "", loc])

    print(format_table(
        ["Score", "File", "Category", "Title", "Location"],
        table_rows,
        [">", "<", "<", "<", "<"],
    ))


def cmd_info(conn: sqlite3.Connection, photo_name: str) -> None:
    """Show detailed info for a single photo (matches filename)."""
    row = conn.execute(
        "SELECT * FROM photos WHERE filename = ? OR path LIKE ?",
        (photo_name, f"%{photo_name}"),
    ).fetchone()
    if not row:
        print(f"No photo found matching '{photo_name}'", file=sys.stderr)
        sys.exit(1)

    tags = conn.execute("SELECT tag FROM photo_tags WHERE photo_path = ?", (row["path"],)).fetchall()
    tag_list = [t["tag"] for t in tags]

    print(f"File:        {row['filename']}")
    print(f"Path:        {row['path']}")
    print(f"Title:       {row['title'] or '(none)'}")
    print(f"Caption:     {row['caption'] or '(none)'}")
    print(f"Category:    {row['category']}")
    print(f"Score:       {row['composition_score']:.0f}/7 ({score_label(row['composition_score'])})")
    print(f"Elements:    {row['composition_elements'] or '(none)'}")
    issues = row["composition_issues"] if "composition_issues" in row.keys() else None
    print(f"Issues:      {issues or '(none)'}")
    print(f"Explanation: {row['composition_explanation']}")
    suggestions = row["composition_suggestions"] if "composition_suggestions" in row.keys() else None
    if suggestions:
        print(f"Suggestions:")
        for s in suggestions.split(" | "):
            if s.strip():
                print(f"  - {s.strip()}")
    else:
        print(f"Suggestions: (none)")
    print(f"Description: {row['description']}")
    print(f"Location:    {row['location'] or '(none)'}")
    if row["latitude"] is not None:
        print(f"GPS:         {row['latitude']:.6f}, {row['longitude']:.6f}")
    print(f"Tags:        {', '.join(tag_list) if tag_list else '(none)'}")
    print(f"Dimensions:  {row['image_width']}x{row['image_height']}")
    print(f"File size:   {row['file_size_bytes']:,} bytes")
    print(f"Model:       {row['model']}")
    print(f"Analyzed:    {row['analyzed_at']}")


def cmd_stats(conn: sqlite3.Connection) -> None:
    """Show database summary statistics."""
    total = conn.execute("SELECT COUNT(*) AS c FROM photos").fetchone()["c"]
    if total == 0:
        print("Database is empty.")
        return

    avg = conn.execute("SELECT AVG(composition_score) AS a FROM photos").fetchone()["a"]
    min_s = conn.execute("SELECT MIN(composition_score) AS m FROM photos").fetchone()["m"]
    max_s = conn.execute("SELECT MAX(composition_score) AS m FROM photos").fetchone()["m"]
    total_size = conn.execute("SELECT SUM(file_size_bytes) AS s FROM photos").fetchone()["s"]
    n_tags = conn.execute("SELECT COUNT(DISTINCT tag) AS c FROM photo_tags").fetchone()["c"]
    n_cats = conn.execute("SELECT COUNT(DISTINCT category) AS c FROM photos").fetchone()["c"]
    n_located = conn.execute("SELECT COUNT(*) AS c FROM photos WHERE location IS NOT NULL").fetchone()["c"]
    n_gps = conn.execute("SELECT COUNT(*) AS c FROM photos WHERE latitude IS NOT NULL").fetchone()["c"]
    models = conn.execute("SELECT DISTINCT model FROM photos").fetchall()

    print(f"Photos:      {total}")
    print(f"Avg score:   {avg:.2f}/7")
    print(f"Score range: {min_s:.0f}-{max_s:.0f}")
    print(f"Categories:  {n_cats}")
    print(f"Unique tags: {n_tags}")
    print(f"With GPS:    {n_gps}")
    print(f"With location: {n_located}")
    print(f"Total size:  {total_size / 1024 / 1024:.1f} MB")
    print(f"Models:      {', '.join(r['model'] for r in models)}")

    # Score distribution
    print("\nScore distribution:")
    rows = conn.execute("SELECT CAST(composition_score AS INTEGER) AS s, COUNT(*) AS c FROM photos GROUP BY s ORDER BY s DESC").fetchall()
    for row in rows:
        bar = "#" * row["c"]
        print(f"  {row['s']} {score_label(row['s']):<10} {bar} ({row['c']})")
