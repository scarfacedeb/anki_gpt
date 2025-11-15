"""
Word Service - High-level abstraction for word operations.

This service encapsulates all word-related operations including:
- Creating, reading, updating, and deleting words
- Automatic synchronization with Anki
- Database management
- Statistics and search

Usage:
    service = WordService()
    word = service.create(dutch="hond", translation="dog", ...)
    word = service.get("hond")
    service.delete("hond")
"""
import logging
from typing import Optional, List
from word import Word
from db import WordDatabase
from anki import delete_note, add_note
from config import ENABLE_ANKI_SYNC

logger = logging.getLogger(__name__)


class WordService:
    """
    High-level service for managing words with automatic Anki synchronization.

    This class provides a clean interface for all word operations while
    encapsulating the complexity of database and Anki synchronization.
    """

    def __init__(self, db: Optional[WordDatabase] = None, deck_name: str = "Default"):
        """
        Initialize the word service.

        Args:
            db: Optional WordDatabase instance (creates new one if not provided)
            deck_name: Anki deck name for synchronization
        """
        self.db = db or WordDatabase()
        self.deck_name = deck_name
        logger.debug(f"WordService initialized with deck: {deck_name}")

    # ==================== Private Sync Methods ====================

    def _sync_word_to_anki(self, word: Word) -> Optional[int]:
        """
        Sync a single word to Anki.

        Args:
            word: The Word object to sync

        Returns:
            The Anki note ID if successful, None otherwise
        """
        if not ENABLE_ANKI_SYNC:
            return None

        try:
            note_id = add_note(word, self.deck_name)
            if note_id:
                logger.info(f"Successfully synced word to Anki: {word.dutch} (note_id: {note_id})")
            else:
                logger.warning(f"Failed to sync word to Anki: {word.dutch}")
            return note_id
        except Exception as e:
            logger.error(f"Error syncing word to Anki: {word.dutch} - {e}")
            return None

    def _save_and_sync_word(self, word: Word) -> tuple[int, Optional[int]]:
        """
        Save a word to the database and sync it to Anki.

        Args:
            word: The Word object to save and sync

        Returns:
            Tuple of (db_row_id, anki_note_id)
        """
        # Step 1: Save to database
        try:
            db_row_id = self.db.save_word(word)
            logger.info(f"Saved word to database: {word.dutch} (row_id: {db_row_id})")
        except Exception as e:
            logger.error(f"Failed to save word to database: {word.dutch} - {e}")
            raise

        # Step 2: Sync to Anki
        anki_note_id = self._sync_word_to_anki(word)

        # Step 3: Mark as synced if Anki sync was successful
        if anki_note_id:
            try:
                self.db.mark_synced(word.dutch, anki_note_id, self.deck_name)
                logger.info(f"Marked word as synced: {word.dutch}")
            except Exception as e:
                logger.error(f"Failed to mark word as synced: {word.dutch} - {e}")

        return (db_row_id, anki_note_id)

    # ==================== CRUD Operations ====================

    def create(self, word: Word) -> tuple[Word, bool]:
        """
        Create a new word and sync to Anki.

        Args:
            word: Word object to create

        Returns:
            Tuple of (word, synced_to_anki)
            - word: The created Word object
            - synced_to_anki: True if successfully synced to Anki

        Raises:
            Exception: If database save fails
        """
        db_row_id, anki_note_id = self._save_and_sync_word(word)
        synced = anki_note_id is not None

        logger.info(f"Created word: {word.dutch} (synced: {synced})")
        return word, synced

    def create_from_dict(self, **kwargs) -> tuple[Word, bool]:
        """
        Create a new word from dictionary/kwargs and sync to Anki.

        Args:
            **kwargs: Word fields (dutch, translation, etc.)

        Returns:
            Tuple of (word, synced_to_anki)

        Example:
            word, synced = service.create_from_dict(
                dutch="hond",
                translation="dog",
                grammar="de (noun)"
            )
        """
        word = Word(**kwargs)
        return self.create(word)

    def update(self, word: Word) -> tuple[Word, bool]:
        """
        Update an existing word and sync changes to Anki.

        Args:
            word: Word object with updated fields

        Returns:
            Tuple of (word, synced_to_anki)

        Note:
            This will create the word if it doesn't exist.
        """
        db_row_id, anki_note_id = self._save_and_sync_word(word)
        synced = anki_note_id is not None

        logger.info(f"Updated word: {word.dutch} (synced: {synced})")
        return word, synced

    def get(self, dutch: str) -> Optional[Word]:
        """
        Get a word by its Dutch text.

        Args:
            dutch: The Dutch word to retrieve

        Returns:
            Word object if found, None otherwise
        """
        word = self.db.get_word(dutch)
        if word:
            logger.debug(f"Retrieved word: {dutch}")
        else:
            logger.debug(f"Word not found: {dutch}")
        return word

    def delete(self, dutch: str, delete_from_anki: bool = True) -> tuple[bool, bool]:
        """
        Delete a word from the database and optionally from Anki.

        Args:
            dutch: The Dutch word to delete
            delete_from_anki: If True, also delete from Anki (default: True)

        Returns:
            Tuple of (deleted_from_db, deleted_from_anki)
            - deleted_from_db: True if deleted from database
            - deleted_from_anki: True if deleted from Anki (or N/A if not synced)

        Note:
            If the word was synced to Anki and delete_from_anki is True,
            it will be removed from both the database and Anki.
        """
        # Get sync info before deleting from DB
        sync_info = self.db.get_sync_info(dutch)
        anki_note_id = sync_info.get('anki_note_id') if sync_info else None

        # Delete from database (this also deletes from anki_words via CASCADE)
        db_deleted = self.db.delete_word(dutch)

        if not db_deleted:
            logger.warning(f"Word not found for deletion: {dutch}")
            return False, False

        logger.info(f"Deleted word from database: {dutch}")

        # Delete from Anki if it was synced and deletion is enabled
        anki_deleted = None  # Default: N/A (not synced or sync disabled)
        if delete_from_anki and anki_note_id and ENABLE_ANKI_SYNC:
            anki_deleted = delete_note(anki_note_id)
            if anki_deleted:
                logger.info(f"Deleted word from Anki: {dutch} (note_id: {anki_note_id})")
            else:
                logger.warning(f"Failed to delete word from Anki: {dutch}")

        return db_deleted, anki_deleted

    def exists(self, dutch: str) -> bool:
        """
        Check if a word exists in the database.

        Args:
            dutch: The Dutch word to check

        Returns:
            True if word exists, False otherwise
        """
        return self.get(dutch) is not None

    # ==================== Batch Operations ====================

    def create_many(self, words: List[Word]) -> tuple[int, int]:
        """
        Create multiple words and sync to Anki.

        Args:
            words: List of Word objects to create

        Returns:
            Tuple of (total_saved, total_synced)
        """
        total_saved = 0
        total_synced = 0

        for word in words:
            try:
                db_row_id, anki_note_id = self._save_and_sync_word(word)
                total_saved += 1
                if anki_note_id:
                    total_synced += 1
            except Exception as e:
                logger.error(f"Failed to save and sync word: {word.dutch} - {e}")

        logger.info(f"Batch create: {total_saved}/{len(words)} saved, {total_synced}/{len(words)} synced")
        return total_saved, total_synced

    # ==================== Query Operations ====================

    def get_all(self) -> List[Word]:
        """
        Get all words from the database.

        Returns:
            List of all Word objects
        """
        words = self.db.get_all_words()
        logger.debug(f"Retrieved {len(words)} words")
        return words

    def search(self, query: str) -> List[Word]:
        """
        Search for words matching the query.

        Args:
            query: Search term (matches Dutch, translation, or definitions)

        Returns:
            List of matching Word objects
        """
        words = self.db.search_words(query)
        logger.debug(f"Search '{query}' returned {len(words)} results")
        return words

    def get_unsynced(self) -> List[Word]:
        """
        Get all words that haven't been synced to Anki.

        Returns:
            List of unsynced Word objects
        """
        words = self.db.get_unsynced_words()
        logger.debug(f"Found {len(words)} unsynced words")
        return words

    # ==================== Statistics ====================

    def get_stats(self) -> dict:
        """
        Get statistics about words in the database.

        Returns:
            Dictionary with stats:
            - total_words: Total number of words
            - synced_to_anki: Number of words synced to Anki
            - unsynced: Number of words not yet synced
        """
        return self.db.get_stats()

    def count(self) -> int:
        """
        Get total count of words.

        Returns:
            Total number of words in database
        """
        return self.get_stats()['total_words']

    # ==================== Sync Management ====================

    def mark_synced(self, dutch: str, anki_note_id: Optional[int] = None) -> None:
        """
        Manually mark a word as synced to Anki.

        Args:
            dutch: The Dutch word to mark
            anki_note_id: Optional Anki note ID

        Note:
            Generally not needed as create/update handle this automatically.
        """
        self.db.mark_synced(dutch, anki_note_id)
        logger.info(f"Marked word as synced: {dutch}")

    # ==================== Context Manager ====================

    def __enter__(self):
        """Enable using WordService as a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup when exiting context."""
        # Database connections are managed per-operation, no cleanup needed
        pass

    # ==================== Representation ====================

    def __repr__(self) -> str:
        stats = self.get_stats()
        return f"WordService(deck='{self.deck_name}', words={stats['total_words']}, synced={stats['synced_to_anki']})"
