"""
Word synchronization module - orchestrates saving words to database and syncing to Anki.

This module provides high-level functions that combine database and Anki operations
while maintaining separation of concerns.
"""
import logging
from typing import Optional
from word import Word
from db import WordDatabase
from anki import add_note
from config import ENABLE_ANKI_SYNC

logger = logging.getLogger(__name__)

DECK_NAME = "Default"


def sync_word_to_anki(word: Word, deck_name: str = DECK_NAME) -> Optional[int]:
    """
    Sync a single word to Anki.

    Args:
        word: The Word object to sync
        deck_name: The Anki deck name (default: "Default")

    Returns:
        The Anki note ID if successful, None otherwise

    Note:
        This function only syncs to Anki and does not save to the database.
        Use save_and_sync_word() for combined save + sync operation.
    """
    if not ENABLE_ANKI_SYNC:
        logger.info(f"Anki sync is disabled via config for word: {word.dutch}")
        return None

    try:
        note_id = add_note(word, deck_name)
        if note_id:
            logger.info(f"Successfully synced word to Anki: {word.dutch} (note_id: {note_id})")
        else:
            logger.warning(f"Failed to sync word to Anki: {word.dutch}")
        return note_id
    except Exception as e:
        logger.error(f"Error syncing word to Anki: {word.dutch} - {e}")
        return None


def save_and_sync_word(word: Word, deck_name: str = DECK_NAME, db: Optional[WordDatabase] = None) -> tuple[int, Optional[int]]:
    """
    Save a word to the database and sync it to Anki.

    Args:
        word: The Word object to save and sync
        deck_name: The Anki deck name (default: "Default")
        db: Optional WordDatabase instance (creates new one if not provided)

    Returns:
        Tuple of (db_row_id, anki_note_id)
        - db_row_id: The database row ID (always returned)
        - anki_note_id: The Anki note ID if sync was successful, None otherwise

    This function maintains separation of concerns:
    1. Saves word to database (always happens)
    2. Syncs to Anki (only if ENABLE_ANKI_SYNC is True)
    3. Marks as synced in database (only if Anki sync succeeded)
    """
    # Create database instance if not provided
    if db is None:
        db = WordDatabase()

    # Step 1: Save to database
    try:
        db_row_id = db.save_word(word)
        logger.info(f"Saved word to database: {word.dutch} (row_id: {db_row_id})")
    except Exception as e:
        logger.error(f"Failed to save word to database: {word.dutch} - {e}")
        raise

    # Step 2: Sync to Anki
    anki_note_id = sync_word_to_anki(word, deck_name)

    # Step 3: Mark as synced if Anki sync was successful
    if anki_note_id:
        try:
            db.mark_synced(word.dutch, anki_note_id)
            logger.info(f"Marked word as synced: {word.dutch}")
        except Exception as e:
            logger.error(f"Failed to mark word as synced: {word.dutch} - {e}")

    return (db_row_id, anki_note_id)


def save_and_sync_words(words: list[Word], deck_name: str = DECK_NAME, db: Optional[WordDatabase] = None) -> tuple[int, int]:
    """
    Save multiple words to the database and sync them to Anki.

    Args:
        words: List of Word objects to save and sync
        deck_name: The Anki deck name (default: "Default")
        db: Optional WordDatabase instance (creates new one if not provided)

    Returns:
        Tuple of (total_saved, total_synced)
        - total_saved: Number of words successfully saved to database
        - total_synced: Number of words successfully synced to Anki
    """
    if db is None:
        db = WordDatabase()

    total_saved = 0
    total_synced = 0

    for word in words:
        try:
            db_row_id, anki_note_id = save_and_sync_word(word, deck_name, db)
            total_saved += 1
            if anki_note_id:
                total_synced += 1
        except Exception as e:
            logger.error(f"Failed to save and sync word: {word.dutch} - {e}")

    logger.info(f"Batch complete: {total_saved}/{len(words)} saved, {total_synced}/{len(words)} synced")
    return (total_saved, total_synced)
