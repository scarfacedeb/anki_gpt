import requests
import sys
import logging
from word import Word

ANKI_CONNECT_URL = "http://localhost:8765"
MODEL_NAME = "GPT"
DECK_NAME = "Default"
TAGS = ["gpt"]

logger = logging.getLogger(__name__)

def build_note(word: Word, deck_name: str = DECK_NAME) -> dict:
    return {
        "deckName": deck_name,
        "modelName": MODEL_NAME,
        "fields": {
            "Word": word.dutch,
            "Translation": word.translation,
            "Definition": word.definition_nl,
            "Definition (eng)": word.definition_en,
            "Pronunciation": word.pronunciation,
            "Grammar": word.grammar,
            "Collocations": "\n".join(word.collocations),
            "Examples": "\n".join(word.examples_nl),
            "Examples (eng)": "\n".join(word.examples_en),
            "Etymology": word.etymology,
            "Related": "\n".join(word.related)
        },
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

def add_note(word: Word, deck_name: str = DECK_NAME) -> None:
    """
    Adds the given word to Anki via the AnkiConnect API.
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
                logger.info(f"Note already exists: {word.dutch}")
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
