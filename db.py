import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from word import Word

class WordDatabase:
    def __init__(self, db_path: str = "words.db"):
        self.db_path = Path(db_path)
        self.init_database()

    def init_database(self):
        """Initialize the database and create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            # Create words table (core word data)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dutch TEXT NOT NULL,
                    translation TEXT NOT NULL,
                    definition_nl TEXT NOT NULL,
                    definition_en TEXT NOT NULL,
                    pronunciation TEXT NOT NULL,
                    grammar TEXT NOT NULL,
                    collocations TEXT NOT NULL,  -- JSON array
                    synonyms TEXT NOT NULL,      -- JSON array
                    examples_nl TEXT NOT NULL,   -- JSON array
                    examples_en TEXT NOT NULL,   -- JSON array
                    etymology TEXT NOT NULL,
                    related TEXT NOT NULL,       -- JSON array
                    level TEXT DEFAULT '',       -- Difficulty level
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(dutch)
                )
            """)

            # Create anki_words table (Anki synchronization data)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS anki_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word_id INTEGER NOT NULL,
                    anki_note_id INTEGER,
                    deck_name TEXT DEFAULT 'Default',
                    synced_at TIMESTAMP,
                    last_updated_at TIMESTAMP,
                    sync_count INTEGER DEFAULT 0,
                    reviews INTEGER,
                    lapses INTEGER,
                    ease_factor INTEGER,
                    interval INTEGER,
                    due INTEGER,
                    FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE,
                    UNIQUE(word_id)
                )
            """)

            # Create indexes for faster lookups
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dutch ON words(dutch)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_word_id ON anki_words(word_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_anki_note_id ON anki_words(anki_note_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_synced_at ON anki_words(synced_at)")

            conn.commit()

            # Migrate legacy data if old columns exist
            self._migrate_legacy_anki_data(conn)
            self._migrate_add_anki_stats_columns(conn)
            self._migrate_add_level_column(conn)

    def _migrate_legacy_anki_data(self, conn):
        """Migrate data from legacy synced_to_anki and anki_note_id columns to anki_words table."""
        cursor = conn.cursor()

        # Check if legacy columns exist
        cursor.execute("PRAGMA table_info(words)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'synced_to_anki' in columns and 'anki_note_id' in columns:
            # Migrate data from words table to anki_words table
            cursor.execute("""
                INSERT OR IGNORE INTO anki_words (word_id, anki_note_id, synced_at, sync_count)
                SELECT
                    id,
                    anki_note_id,
                    CASE WHEN synced_to_anki = 1 THEN updated_at ELSE NULL END,
                    CASE WHEN synced_to_anki = 1 THEN 1 ELSE 0 END
                FROM words
                WHERE synced_to_anki = 1 AND anki_note_id IS NOT NULL
            """)
            conn.commit()

            # Note: We don't drop the old columns to maintain backward compatibility
            # They can be manually dropped later if needed

    def _migrate_add_anki_stats_columns(self, conn):
        """Add Anki statistics columns to anki_words table if they don't exist."""
        cursor = conn.cursor()

        # Check which columns exist in anki_words table
        cursor.execute("PRAGMA table_info(anki_words)")
        existing_columns = {col[1] for col in cursor.fetchall()}

        # Add missing columns
        columns_to_add = {
            'reviews': 'INTEGER',
            'lapses': 'INTEGER',
            'ease_factor': 'INTEGER',
            'interval': 'INTEGER',
            'due': 'INTEGER'
        }

        for column_name, column_type in columns_to_add.items():
            if column_name not in existing_columns:
                cursor.execute(f"ALTER TABLE anki_words ADD COLUMN {column_name} {column_type}")

        conn.commit()

    def _migrate_add_level_column(self, conn):
        """Add level column to words table if it doesn't exist."""
        cursor = conn.cursor()

        # Check if level column exists
        cursor.execute("PRAGMA table_info(words)")
        existing_columns = {col[1] for col in cursor.fetchall()}

        if 'level' not in existing_columns:
            cursor.execute("ALTER TABLE words ADD COLUMN level TEXT DEFAULT ''")
            conn.commit()

    def _word_to_dict(self, word: Word) -> dict:
        """Convert Word object to dictionary for database storage."""
        return {
            'dutch': word.dutch,
            'translation': word.translation,
            'definition_nl': word.definition_nl,
            'definition_en': word.definition_en,
            'pronunciation': word.pronunciation,
            'grammar': word.grammar,
            'collocations': json.dumps(word.collocations),
            'synonyms': json.dumps(word.synonyms),
            'examples_nl': json.dumps(word.examples_nl),
            'examples_en': json.dumps(word.examples_en),
            'etymology': word.etymology,
            'related': json.dumps(word.related),
            'level': word.level
        }

    def _dict_to_word(self, row: dict) -> Word:
        """Convert database row to Word object."""
        return Word(
            dutch=row['dutch'],
            translation=row['translation'],
            definition_nl=row['definition_nl'],
            definition_en=row['definition_en'],
            pronunciation=row['pronunciation'],
            grammar=row['grammar'],
            collocations=json.loads(row['collocations']),
            synonyms=json.loads(row['synonyms']),
            examples_nl=json.loads(row['examples_nl']),
            examples_en=json.loads(row['examples_en']),
            etymology=row['etymology'],
            related=json.loads(row['related']),
            level=row.get('level', '')  # Use get() for backwards compatibility
        )

    def save_word(self, word: Word) -> int:
        """Save a word to the database. Returns the row ID."""
        word_dict = self._word_to_dict(word)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Check if word already exists
            cursor.execute("SELECT id FROM words WHERE dutch = ?", (word.dutch,))
            existing = cursor.fetchone()

            if existing:
                # Update existing word
                word_dict['updated_at'] = datetime.now().isoformat()
                placeholders = ', '.join([f"{key} = ?" for key in word_dict.keys()])
                values = list(word_dict.values()) + [word.dutch]

                cursor.execute(f"""
                    UPDATE words SET {placeholders} WHERE dutch = ?
                """, values)
                return existing['id']
            else:
                # Insert new word
                placeholders = ', '.join(['?' for _ in word_dict])
                columns = ', '.join(word_dict.keys())

                cursor.execute(f"""
                    INSERT INTO words ({columns}) VALUES ({placeholders})
                """, list(word_dict.values()))
                return cursor.lastrowid

    def save_words(self, words: List[Word]) -> List[int]:
        """Save multiple words to the database. Returns list of row IDs."""
        return [self.save_word(word) for word in words]

    def get_word(self, dutch: str) -> Optional[Word]:
        """Get a word by its Dutch text."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM words WHERE dutch = ?", (dutch,))
            row = cursor.fetchone()

            if row:
                return self._dict_to_word(dict(row))
            return None

    def get_all_words(self) -> List[Word]:
        """Get all words from the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM words ORDER BY created_at DESC")
            rows = cursor.fetchall()

            return [self._dict_to_word(dict(row)) for row in rows]

    def get_unsynced_words(self) -> List[Word]:
        """Get all words that haven't been synced to Anki yet."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get words that don't have an entry in anki_words or have NULL synced_at
            cursor.execute("""
                SELECT w.* FROM words w
                LEFT JOIN anki_words a ON w.id = a.word_id
                WHERE a.synced_at IS NULL OR a.word_id IS NULL
                ORDER BY w.created_at DESC
            """)
            rows = cursor.fetchall()

            return [self._dict_to_word(dict(row)) for row in rows]

    def mark_synced(self, dutch: str, anki_note_id: Optional[int] = None, deck_name: str = "Default"):
        """Mark a word as synced to Anki."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            timestamp = datetime.now().isoformat()

            # Get word_id
            cursor.execute("SELECT id FROM words WHERE dutch = ?", (dutch,))
            row = cursor.fetchone()
            if not row:
                return

            word_id = row[0]

            # Insert or update anki_words record
            cursor.execute("""
                INSERT INTO anki_words (word_id, anki_note_id, deck_name, synced_at, last_updated_at, sync_count)
                VALUES (?, ?, ?, ?, ?, 1)
                ON CONFLICT(word_id) DO UPDATE SET
                    anki_note_id = ?,
                    deck_name = ?,
                    last_updated_at = ?,
                    sync_count = sync_count + 1
            """, (word_id, anki_note_id, deck_name, timestamp, timestamp,
                  anki_note_id, deck_name, timestamp))

            conn.commit()

    def mark_multiple_synced(self, words: List[str], anki_note_ids: Optional[List[int]] = None, deck_name: str = "Default"):
        """Mark multiple words as synced to Anki."""
        if anki_note_ids is None:
            anki_note_ids = [None] * len(words)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            timestamp = datetime.now().isoformat()

            for dutch, note_id in zip(words, anki_note_ids):
                # Get word_id
                cursor.execute("SELECT id FROM words WHERE dutch = ?", (dutch,))
                row = cursor.fetchone()
                if not row:
                    continue

                word_id = row[0]

                # Insert or update anki_words record
                cursor.execute("""
                    INSERT INTO anki_words (word_id, anki_note_id, deck_name, synced_at, last_updated_at, sync_count)
                    VALUES (?, ?, ?, ?, ?, 1)
                    ON CONFLICT(word_id) DO UPDATE SET
                        anki_note_id = ?,
                        deck_name = ?,
                        last_updated_at = ?,
                        sync_count = sync_count + 1
                """, (word_id, note_id, deck_name, timestamp, timestamp,
                      note_id, deck_name, timestamp))

            conn.commit()

    def delete_word(self, dutch: str) -> bool:
        """Delete a word from the database. Returns True if deleted, False if not found."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM words WHERE dutch = ?", (dutch,))
            conn.commit()
            return cursor.rowcount > 0

    def search_words(self, query: str) -> List[Word]:
        """Search words by Dutch text, translation, or definition."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            search_pattern = f"%{query}%"
            cursor.execute("""
                SELECT * FROM words
                WHERE dutch LIKE ?
                   OR translation LIKE ?
                   OR definition_nl LIKE ?
                   OR definition_en LIKE ?
                ORDER BY created_at DESC
            """, (search_pattern, search_pattern, search_pattern, search_pattern))

            rows = cursor.fetchall()
            return [self._dict_to_word(dict(row)) for row in rows]

    def get_stats(self) -> dict:
        """Get database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) as total FROM words")
            total = cursor.fetchone()[0]

            # Count words that have a sync record with synced_at
            cursor.execute("""
                SELECT COUNT(*) as synced
                FROM words w
                INNER JOIN anki_words a ON w.id = a.word_id
                WHERE a.synced_at IS NOT NULL
            """)
            synced = cursor.fetchone()[0]

            # Count words that don't have a sync record or have NULL synced_at
            cursor.execute("""
                SELECT COUNT(*) as unsynced
                FROM words w
                LEFT JOIN anki_words a ON w.id = a.word_id
                WHERE a.synced_at IS NULL OR a.word_id IS NULL
            """)
            unsynced = cursor.fetchone()[0]

            return {
                'total_words': total,
                'synced_to_anki': synced,
                'unsynced': unsynced
            }

    def get_sync_info(self, dutch: str) -> Optional[dict]:
        """Get Anki sync information for a word."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT a.*
                FROM anki_words a
                INNER JOIN words w ON a.word_id = w.id
                WHERE w.dutch = ?
            """, (dutch,))

            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_sync_info(self) -> List[dict]:
        """Get Anki sync information for all synced words."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT w.dutch, a.*
                FROM anki_words a
                INNER JOIN words w ON a.word_id = w.id
                WHERE a.synced_at IS NOT NULL
                ORDER BY a.synced_at DESC
            """)

            rows = cursor.fetchall()
            return [dict(row) for row in rows]