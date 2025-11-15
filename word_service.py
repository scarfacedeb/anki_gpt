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
from word_sync import save_and_sync_word, save_and_sync_words

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
        db_row_id, anki_note_id = save_and_sync_word(word, self.deck_name, self.db)
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
        db_row_id, anki_note_id = save_and_sync_word(word, self.deck_name, self.db)
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

    def delete(self, dutch: str) -> bool:
        """
        Delete a word from the database.

        Args:
            dutch: The Dutch word to delete

        Returns:
            True if deleted, False if not found

        Note:
            This only deletes from the database, not from Anki.
            The word will remain in Anki for review.
        """
        success = self.db.delete_word(dutch)
        if success:
            logger.info(f"Deleted word: {dutch}")
        else:
            logger.warning(f"Word not found for deletion: {dutch}")
        return success

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
        total_saved, total_synced = save_and_sync_words(words, self.deck_name, self.db)
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
