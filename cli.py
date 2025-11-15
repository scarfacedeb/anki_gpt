from dotenv import load_dotenv
from chatgpt import get_definitions
from anki import sync_anki
from word import Word, WordList
from word_sync import save_and_sync_words

# Load environment variables from .env file
load_dotenv()

def add_word_to_anki(user_input: str) -> list[Word]:
    """
    Main logic:
    1. Send user input to ChatGPT for definitions.
    2. Save words to database and sync to Anki.
    3. Sync with AnkiWeb.
    4. Return the definitions as Word objects.
    """

    response = get_definitions(user_input, user_id=0)  # Default user ID for CLI

    if response.words:
        # Save words to database and sync to Anki
        total_saved, total_synced = save_and_sync_words(response.words)
        print(f"Saved {total_saved}/{len(response.words)} words, synced {total_synced}/{len(response.words)} to Anki")

        # Sync with AnkiWeb
        sync_anki()

    return response.words

def main():
    """CLI entry point for anki-gpt-cli command."""
    test_input = input("Enter Dutch words or phrases: ")
    word_objects = add_word_to_anki(test_input)
    for word in word_objects:
        print(f"\n{word.dutch} - {word.translation}")
        print(f"Definition: {word.definition_nl}")
        print(f"English: {word.definition_en}")

if __name__ == "__main__":
    main()
