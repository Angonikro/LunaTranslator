import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_DIR = Path.home() / ".local" / "share" / "LunaTranslator"
DB_PATH = DB_DIR / "history.sqlite3"

class History:
    def __init__(self):
        DB_DIR.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        return sqlite3.connect(DB_PATH)

    def _init_db(self):
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS translations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                source_lang TEXT NOT NULL,
                target_lang TEXT NOT NULL,
                source_text TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                provider TEXT NOT NULL
            )""")

    def add(self, source_lang, target_lang, source, translated, provider):
        with self._connect() as db:
            db.execute(
                "INSERT INTO translations VALUES (NULL, ?, ?, ?, ?, ?, ?)",
                (datetime.now(timezone.utc).isoformat(), source_lang, target_lang,
                 source, translated, provider)
            )

    def recent(self, limit=300):
        with self._connect() as db:
            return db.execute(
                "SELECT created_at, source_lang, target_lang, source_text, translated_text, provider "
                "FROM translations ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()

    def search(self, term):
        pattern = f"%{term}%"
        with self._connect() as db:
            return db.execute(
                "SELECT created_at, source_lang, target_lang, source_text, translated_text, provider "
                "FROM translations WHERE source_text LIKE ? OR translated_text LIKE ? "
                "ORDER BY id DESC LIMIT 300", (pattern, pattern)
            ).fetchall()

    def clear(self):
        with self._connect() as db:
            db.execute("DELETE FROM translations")
