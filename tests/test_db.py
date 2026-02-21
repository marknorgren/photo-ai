"""Tests for photo_ai.db."""

import sqlite3
import tempfile
from pathlib import Path

from photo_ai.db import get_analyzed_paths, init_db, open_db_readonly


def test_init_db_creates_tables():
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        conn = init_db(f.name)
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = {row[0] for row in tables}
        assert "photos" in table_names
        assert "photo_tags" in table_names
        conn.close()


def test_init_db_wal_mode():
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        conn = init_db(f.name)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"
        conn.close()


def test_init_db_idempotent():
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        conn1 = init_db(f.name)
        conn1.close()
        conn2 = init_db(f.name)
        tables = conn2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        assert len(tables) >= 2
        conn2.close()


def test_open_db_readonly():
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        init_db(f.name).close()
        conn = open_db_readonly(f.name)
        assert conn.row_factory == sqlite3.Row
        conn.close()


def test_open_db_readonly_runs_migrations():
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        # Create a minimal DB without migrations
        conn = sqlite3.connect(f.name)
        conn.execute("""CREATE TABLE IF NOT EXISTS photos (
            path TEXT PRIMARY KEY, filename TEXT, analyzed_at TEXT,
            image_width INTEGER, image_height INTEGER, file_size_bytes INTEGER,
            tags TEXT, category TEXT, composition_score REAL,
            composition_elements TEXT, composition_explanation TEXT,
            description TEXT, model TEXT, raw_response TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS photo_tags (
            photo_path TEXT NOT NULL, tag TEXT NOT NULL,
            PRIMARY KEY (photo_path, tag)
        )""")
        conn.commit()
        conn.close()

        # open_db_readonly should add missing columns via migrations
        ro = open_db_readonly(f.name)
        cols = [desc[0] for desc in ro.execute("PRAGMA table_info(photos)").fetchall()]
        assert "title" in [c[1] for c in ro.execute("PRAGMA table_info(photos)").fetchall()]
        ro.close()


def test_get_analyzed_paths_empty():
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        conn = init_db(f.name)
        assert get_analyzed_paths(conn) == set()
        conn.close()


def test_get_analyzed_paths_returns_paths():
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        conn = init_db(f.name)
        conn.execute(
            "INSERT INTO photos (path, filename) VALUES (?, ?)",
            ("/test/photo.jpg", "photo.jpg"),
        )
        conn.commit()
        paths = get_analyzed_paths(conn)
        assert paths == {"/test/photo.jpg"}
        conn.close()
