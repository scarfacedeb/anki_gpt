"""
Backfill operations between Anki and the local database.
"""
import requests
import logging
from dotenv import load_dotenv
from word import Word
from db import WordDatabase
from anki import add_note
from config import ANKI_CONNECT_URL

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

DECK_NAME = "Default"
MODEL_NAME = "GPT"


def anki_to_word(note: dict) -> Word | None:
    """
    Convert an Anki note (from notesInfo response) to a Word object.
    Returns None if the note cannot be converted.
    """
    try:
        fields = note.get("fields", {})

        # Extract field values (handle both direct string and {"value": ""} format)
        def get_field_value(field_name: str) -> str:
            field = fields.get(field_name, "")
            if isinstance(field, dict):
                return field.get("value", "")
            return field

        return Word(
            dutch=get_field_value("Word"),
            translation=get_field_value("Translation"),
            definition_nl=get_field_value("Definition"),
            definition_en=get_field_value("Definition (eng)"),
            pronunciation=get_field_value("Pronunciation"),
            grammar=get_field_value("Grammar"),
            collocations=[line.strip() for line in get_field_value("Collocations").split("\n") if line.strip()],
            synonyms=[line.strip() for line in get_field_value("Synonyms").split("\n") if line.strip()],
            examples_nl=[line.strip() for line in get_field_value("Examples").split("\n") if line.strip()],
            examples_en=[line.strip() for line in get_field_value("Examples (eng)").split("\n") if line.strip()],
            etymology=get_field_value("Etymology"),
            related=[line.strip() for line in get_field_value("Related").split("\n") if line.strip()]
        )
    except Exception as e:
        logger.error(f"Error converting Anki note to Word: {e}")
        return None


def export_anki_to_db(deck_name: str = DECK_NAME) -> tuple[int, int]:
    """
    Export all words from Anki to the database.
    Returns tuple of (successful_count, total_count).
    """
    db = WordDatabase()

    # Step 1: Find all notes in the deck with the GPT model
    find_payload = {
        "action": "findNotes",
        "version": 6,
        "params": {
            "query": f"deck:{deck_name} note:{MODEL_NAME}"
        }
    }

    try:
        find_response = requests.post(ANKI_CONNECT_URL, json=find_payload, timeout=10).json()
        note_ids = find_response.get("result", [])

        if not note_ids:
            logger.info(f"No notes found in deck '{deck_name}' with model '{MODEL_NAME}'")
            return (0, 0)

        logger.info(f"Found {len(note_ids)} notes in Anki")

        # Step 2: Get note details
        notes_info_payload = {
            "action": "notesInfo",
            "version": 6,
            "params": {
                "notes": note_ids
            }
        }

        notes_response = requests.post(ANKI_CONNECT_URL, json=notes_info_payload, timeout=10).json()
        notes = notes_response.get("result", [])

        # Step 3: Convert to Word objects and save to database
        success_count = 0
        for note in notes:
            word = anki_to_word(note)
            if word:
                try:
                    note_id = note.get("noteId")
                    db.save_word(word)
                    db.mark_synced(word.dutch, note_id)
                    success_count += 1
                    logger.info(f"Saved: {word.dutch}")
                except Exception as e:
                    logger.error(f"Error saving word to database: {e}")

        logger.info(f"Successfully imported {success_count}/{len(notes)} notes from Anki to database")
        return (success_count, len(notes))

    except requests.exceptions.RequestException as e:
        logger.error(f"Connection error to AnkiConnect: {e}")
        return (0, 0)


def export_db_to_anki(deck_name: str = DECK_NAME) -> tuple[int, int]:
    """
    Export all words from database to Anki.
    Returns tuple of (successful_count, total_count).
    """
    db = WordDatabase()
    all_words = db.get_all_words()

    if not all_words:
        logger.info("No words found in database")
        return (0, 0)

    logger.info(f"Found {len(all_words)} words in database")

    success_count = 0
    for word in all_words:
        note_id = add_note(word, deck_name)
        if note_id:
            db.mark_synced(word.dutch, note_id)
            success_count += 1
            logger.info(f"Added to Anki: {word.dutch}")

    logger.info(f"Successfully exported {success_count}/{len(all_words)} words from database to Anki")
    return (success_count, len(all_words))
