import requests
import sys
from word import Word

ANKI_CONNECT_URL = "http://localhost:8765"
MODEL_NAME = "GPT"
DECK_NAME = "Default"
TAGS = ["gpt"]

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

    response = requests.post(ANKI_CONNECT_URL, json=payload).json()

    if response.get("error"):
        if "cannot create note because it is a duplicate" in response["error"]:
            pass
        else:
            print(f"Error adding note: {response['error']}")
    else:
        print(f"Note added successfully: {word.dutch}")

    return response

def sync_anki() -> None:
    """
    Sync collections with AnkiWeb.
    """

    payload = {
        "action": "sync",
        "version": 6
    }

    response = requests.post(ANKI_CONNECT_URL, json=payload).json()

    if response.get("error"):
        print(f"Error during sync: {response['error']}")
    else:
        print("Sync successful.")

    return response
