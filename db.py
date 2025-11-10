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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    synced_to_anki BOOLEAN DEFAULT FALSE,
                    anki_note_id INTEGER DEFAULT NULL,
                    UNIQUE(dutch)
                )
            """)

            # Create index for faster lookups
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dutch ON words(dutch)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_synced ON words(synced_to_anki)")
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
            'related': json.dumps(word.related)
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
            related=json.loads(row['related'])
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

            cursor.execute("SELECT * FROM words WHERE synced_to_anki = FALSE ORDER BY created_at DESC")
            rows = cursor.fetchall()

            return [self._dict_to_word(dict(row)) for row in rows]

    def mark_synced(self, dutch: str, anki_note_id: Optional[int] = None):
        """Mark a word as synced to Anki."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE words
                SET synced_to_anki = TRUE, anki_note_id = ?, updated_at = ?
                WHERE dutch = ?
            """, (anki_note_id, datetime.now().isoformat(), dutch))
            conn.commit()

    def mark_multiple_synced(self, words: List[str], anki_note_ids: Optional[List[int]] = None):
        """Mark multiple words as synced to Anki."""
        if anki_note_ids is None:
            anki_note_ids = [None] * len(words)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            timestamp = datetime.now().isoformat()

            for dutch, note_id in zip(words, anki_note_ids):
                cursor.execute("""
                    UPDATE words
                    SET synced_to_anki = TRUE, anki_note_id = ?, updated_at = ?
                    WHERE dutch = ?
                """, (note_id, timestamp, dutch))
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

            cursor.execute("SELECT COUNT(*) as synced FROM words WHERE synced_to_anki = TRUE")
            synced = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) as unsynced FROM words WHERE synced_to_anki = FALSE")
            unsynced = cursor.fetchone()[0]

            return {
                'total_words': total,
                'synced_to_anki': synced,
                'unsynced': unsynced
            }