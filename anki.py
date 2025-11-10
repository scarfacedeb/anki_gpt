import requests
import sys
import logging
from word import Word, word_to_anki
from config import ENABLE_ANKI_SYNC, ANKI_CONNECT_URL

MODEL_NAME = "GPT"
DECK_NAME = "Default"
TAGS = ["gpt"]

logger = logging.getLogger(__name__)

def build_note(word: Word, deck_name: str = DECK_NAME) -> dict:
    return {
        "deckName": deck_name,
        "modelName": MODEL_NAME,
        "fields": word_to_anki(word),
        "options": {
            "allowDuplicate": False
        },
        "tags": TAGS
    }


def add_notes(words: list[Word], deck_name: str = DECK_NAME) -> None:
    """
    Adds the given words to Anki via the AnkiConnect API.
    Each Word object will be added as a note in a given deck_name.
    """
    # Can't use addNotes because it fails the whole batch on duplicates
    return [add_note(word, deck_name) for word in words]

def find_note_id(word: Word, deck_name: str = DECK_NAME) -> int | None:
    """
    Finds the note id for a given word in the specified deck. Returns the note id or None.
    """
    find_payload = {
        "action": "findNotes",
        "version": 6,
        "params": {
            "query": f"deck:'{deck_name}' Word:'{word.dutch}'"
        }
    }
    find_response = requests.post(ANKI_CONNECT_URL, json=find_payload, timeout=5).json()
    note_ids = find_response.get("result", [])
    return note_ids[0] if note_ids else None

def update_note(word: Word, deck_name: str = DECK_NAME) -> None:
    """
    Updates an existing note in Anki with new fields for the given word.
    """
    note_id = find_note_id(word, deck_name)
    if note_id:
        update_payload = {
            "action": "updateNoteFields",
            "version": 6,
            "params": {
                "note": {
                    "id": note_id,
                    "fields": build_note(word, deck_name)["fields"]
                }
            }
        }
        update_response = requests.post(ANKI_CONNECT_URL, json=update_payload, timeout=5).json()
        if update_response.get("error"):
            logger.error(f"Error updating note: {update_response['error']}")
        else:
            logger.info(f"Note updated successfully: {word.dutch}")
    else:
        logger.error(f"Could not find note to update for: {word.dutch}")

def add_note(word: Word, deck_name: str = DECK_NAME) -> None:
    """
    Adds the given word to Anki via the AnkiConnect API.
    If the note already exists, updates it instead.
    """
    payload = {
        "action": "addNote",
        "version": 6,
        "params": {
            "note": build_note(word)
        }
    }

    try:
        response = requests.post(ANKI_CONNECT_URL, json=payload, timeout=5).json()

        if response.get("error"):
            if "cannot create note because it is a duplicate" in response["error"]:
                logger.info(f"Note already exists: {word.dutch}, updating note...")
                update_note(word, deck_name)
            else:
                logger.error(f"Error adding note: {response['error']}")
        else:
            logger.info(f"Note added successfully: {word.dutch}")

        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"Connection error to AnkiConnect: {e}")
        return {"error": f"Connection error: {str(e)}"}

def sync_anki() -> None:
    """
    Sync collections with AnkiWeb.
    """
    if not ENABLE_ANKI_SYNC:
        logger.info("Anki sync is disabled via config (ENABLE_ANKI_SYNC=false)")
        return {"result": None, "sync_skipped": True}

    payload = {
        "action": "sync",
        "version": 6
    }

    try:
        response = requests.post(ANKI_CONNECT_URL, json=payload, timeout=5).json()

        if response.get("error"):
            logger.error(f"Error during sync: {response['error']}")
        else:
            logger.info("Sync successful.")

        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"Connection error to AnkiConnect: {e}")
        return {"error": f"Connection error: {str(e)}"}
