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


def add_notes(words: list[Word], deck_name: str = DECK_NAME) -> list[tuple[Word, int | None]]:
    """
    Adds the given words to Anki via the AnkiConnect API.
    Each Word object will be added as a note in a given deck_name.
    Returns a list of tuples: (Word, note_id or None).
    """
    # Can't use addNotes because it fails the whole batch on duplicates
    return [(word, add_note(word, deck_name)) for word in words]

def find_note_id(word: Word, deck_name: str = DECK_NAME) -> int | None:
    """
    Finds the note id for a given word in the specified deck. Returns the note id or None.
    """
    try:
        # Escape special characters for Anki search
        # In Anki search: backslash escapes quotes, and we wrap in quotes
        dutch_escaped = word.dutch.replace('\\', '\\\\').replace('"', '\\"')

        # Use proper Anki search syntax: Field:"value"
        find_payload = {
            "action": "findNotes",
            "version": 6,
            "params": {
                "query": f'deck:"{deck_name}" Word:"{dutch_escaped}"'
            }
        }

        find_response = requests.post(ANKI_CONNECT_URL, json=find_payload, timeout=5).json()

        if find_response.get("error"):
            logger.error(f"Anki search error for '{word.dutch}': {find_response['error']}")
            return None

        note_ids = find_response.get("result", [])
        return note_ids[0] if note_ids else None

    except requests.exceptions.RequestException as e:
        logger.error(f"Connection error while finding note for {word.dutch}: {e}")
        return None

def update_note(word: Word, deck_name: str = DECK_NAME) -> int | None:
    """
    Updates an existing note in Anki with new fields for the given word.
    Returns the note_id if successful, None otherwise.
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
            return None
        else:
            logger.info(f"Note updated successfully: {word.dutch}")
            return note_id
    else:
        logger.error(f"Could not find note to update for: {word.dutch}")
        return None

def update_note_by_id(note_id: int, word: Word, deck_name: str = DECK_NAME) -> bool:
    """
    Updates an existing note in Anki by note ID.
    Returns True if successful, False otherwise.
    """
    if not note_id:
        logger.warning("Cannot update note: No note ID provided")
        return False

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

    try:
        update_response = requests.post(ANKI_CONNECT_URL, json=update_payload, timeout=5).json()
        if update_response.get("error"):
            logger.error(f"Error updating note {note_id}: {update_response['error']}")
            return False
        else:
            logger.info(f"Note updated successfully: {word.dutch} (note_id: {note_id})")
            return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Connection error to AnkiConnect while updating note: {e}")
        return False

def add_note(word: Word, deck_name: str = DECK_NAME) -> int | None:
    """
    Adds the given word to Anki via the AnkiConnect API.
    If the note already exists, updates it instead.
    Returns the note_id if successful, None otherwise.
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
                return update_note(word, deck_name)
            else:
                logger.error(f"Error adding note: {response['error']}")
                return None
        else:
            note_id = response.get("result")
            logger.info(f"Note added successfully: {word.dutch}")
            return note_id

    except requests.exceptions.RequestException as e:
        logger.error(f"Connection error to AnkiConnect: {e}")
        return None

def delete_note(anki_note_id: int) -> bool:
    """
    Delete a note from Anki by its note ID.
    Returns True if successful, False otherwise.
    """
    if not anki_note_id:
        logger.warning("Cannot delete note: No note ID provided")
        return False

    payload = {
        "action": "deleteNotes",
        "version": 6,
        "params": {
            "notes": [anki_note_id]
        }
    }

    try:
        response = requests.post(ANKI_CONNECT_URL, json=payload, timeout=5).json()

        if response.get("error"):
            logger.error(f"Error deleting note {anki_note_id}: {response['error']}")
            return False
        else:
            logger.info(f"Note deleted successfully: {anki_note_id}")
            return True

    except requests.exceptions.RequestException as e:
        logger.error(f"Connection error to AnkiConnect while deleting note: {e}")
        return False

def sync_anki() -> None:
    """
    Sync collections with AnkiWeb.
    """
    if not ENABLE_ANKI_SYNC:
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
