"""Database schema, migrations, and connection helpers."""

import sqlite3

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
    composition_issues      TEXT,
    composition_suggestions TEXT,
    description             TEXT,
    caption                 TEXT,
    title                   TEXT,
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
    "ALTER TABLE photos ADD COLUMN caption TEXT",
    "ALTER TABLE photos ADD COLUMN title TEXT",
    "ALTER TABLE photos ADD COLUMN composition_issues TEXT",
    "ALTER TABLE photos ADD COLUMN composition_suggestions TEXT",
]


def init_db(db_path: str) -> sqlite3.Connection:
    """Create/migrate the database and return a read-write connection."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA_SQL)
    for sql in MIGRATIONS:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass  # Column already exists
    conn.commit()
    return conn


def open_db_readonly(db_path: str) -> sqlite3.Connection:
    """Run migrations if needed, then return a read-only connection with Row factory."""
    # Run migrations first (needs write access)
    rw = sqlite3.connect(db_path)
    for sql in MIGRATIONS:
        try:
            rw.execute(sql)
        except sqlite3.OperationalError:
            pass
    rw.commit()
    rw.close()

    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def get_analyzed_paths(conn: sqlite3.Connection) -> set[str]:
    """Return set of all analyzed absolute paths."""
    cursor = conn.execute("SELECT path FROM photos")
    return {row[0] for row in cursor.fetchall()}
