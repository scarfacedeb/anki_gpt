from chatgpt import get_definitions
from anki import add_notes, sync_anki
from word import Word, WordList
from db import WordDatabase

def add_word_to_anki(user_input: str) -> list[Word]:
    """
    Main logic:
    1. Send user input to ChatGPT for definitions.
    2. Save words to database.
    3. Add new words to Anki.
    4. Mark words as synced in database.
    5. Return the definitions as Word objects.
    """

    response = get_definitions(user_input, user_id=0)  # Default user ID for CLI

    if response.words:
        # Save words to database first
        db = WordDatabase()
        db.save_words(response.words)

        # Then add to Anki
        results = add_notes(response.words)

        # Mark words as synced in database
        for word, note_id in results:
            if note_id:
                db.mark_synced(word.dutch, note_id)

        sync_anki()

    return response.words

if __name__ == "__main__":
    test_input = input("Enter Dutch words or phrases: ")
    word_objects = add_word_to_anki(test_input)
    for word in word_objects:
        print(f"\n{word.dutch} - {word.translation}")
        print(f"Definition: {word.definition_nl}")
        print(f"English: {word.definition_en}")
