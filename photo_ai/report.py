"""Report and export commands."""

import csv
import io
import json
import sqlite3
import sys

from .util import score_label


def cmd_report(conn: sqlite3.Connection, category: str | None = None) -> None:
    """Generate a markdown report to stdout."""
    query = "SELECT * FROM photos"
    params: list = []
    if category:
        query += " WHERE category = ?"
        params.append(category)
    query += " ORDER BY composition_score DESC, filename"

    rows = conn.execute(query, params).fetchall()
    if not rows:
        print("No photos found.", file=sys.stderr)
        sys.exit(1)

    total = len(rows)
    avg = sum(r["composition_score"] for r in rows) / total
    models = sorted(set(r["model"] for r in rows))

    print(f"# Photo Analysis Report")
    print()
    print(f"{total} photos · avg score {avg:.1f}/7 · model{'s' if len(models) > 1 else ''}: {', '.join(models)}")
    print()

    # Score summary
    print("## Score Distribution")
    print()
    dist: dict[int, int] = {}
    for r in rows:
        k = int(r["composition_score"])
        dist[k] = dist.get(k, 0) + 1
    print("| Score | Label | Count |")
    print("|------:|-------|------:|")
    for s in sorted(dist, reverse=True):
        print(f"| {s} | {score_label(s)} | {dist[s]} |")
    print()

    # Category summary
    print("## Categories")
    print()
    cats: dict[str, int] = {}
    for r in rows:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
    print("| Category | Count |")
    print("|----------|------:|")
    for cat in sorted(cats, key=cats.get, reverse=True):
        print(f"| {cat} | {cats[cat]} |")
    print()

    # All photos
    print("## Photos")
    print()
    print("| Score | File | Category | Title | Location |")
    print("|------:|------|----------|-------|----------|")
    for r in rows:
        score = f"{r['composition_score']:.0f}/7"
        title = r["title"] or ""
        loc = r["location"] or ""
        print(f"| {score} | {r['filename']} | {r['category']} | {title} | {loc} |")


def cmd_export(conn: sqlite3.Connection, fmt: str) -> None:
    """Export database as JSON or CSV to stdout."""
    rows = conn.execute("SELECT * FROM photos ORDER BY composition_score DESC, filename").fetchall()
    if not rows:
        print("No photos found.", file=sys.stderr)
        sys.exit(1)

    columns = rows[0].keys()

    if fmt == "json":
        data = [dict(r) for r in rows]
        json.dump(data, sys.stdout, indent=2)
        print()
    elif fmt == "csv":
        writer = csv.DictWriter(sys.stdout, fieldnames=columns)
        writer.writeheader()
        for r in rows:
            writer.writerow(dict(r))
