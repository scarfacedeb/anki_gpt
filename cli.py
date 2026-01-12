import sys
import logging
from dotenv import load_dotenv
from chatgpt import get_definitions
from anki import sync_anki
from word import Word, WordList
from word_service import WordService
from backfill import export_anki_to_db, export_db_to_anki

# Load environment variables from .env file
load_dotenv()

def add_word_to_anki(user_input: str) -> list[Word]:
    """
    Main logic:
    1. Send user input to ChatGPT for definitions.
    2. Save words to database and sync to Anki via WordService.
    3. Sync with AnkiWeb.
    4. Return the definitions as Word objects.
    """
    word_service = WordService()
    response = get_definitions(user_input, user_id=0)  # Default user ID for CLI

    if response.words:
        # Save words to database and sync to Anki
        total_saved, total_synced = word_service.create_many(response.words)
        print(f"Saved {total_saved}/{len(response.words)} words, synced {total_synced}/{len(response.words)} to Anki")

        # Sync with AnkiWeb
        sync_anki()

    return response.words

def cmd_add():
    """Interactive mode - add words via ChatGPT."""
    user_input = input("Enter Dutch words or phrases: ")
    word_objects = add_word_to_anki(user_input)
    for word in word_objects:
        print(f"\n{word.dutch} - {word.translation}")
        print(f"Definition: {word.definition_nl}")
        print(f"English: {word.definition_en}")

def cmd_import():
    """Import words from Anki to database."""
    print("Importing words from Anki to database...")
    success, total = export_anki_to_db()
    print(f"✅ Imported {success}/{total} words from Anki to database")

def cmd_export():
    """Export words from database to Anki."""
    print("Exporting words from database to Anki...")
    success, total = export_db_to_anki()
    print(f"✅ Exported {success}/{total} words from database to Anki")

def cmd_sync():
    """Sync all words in database to Anki."""
    word_service = WordService()
    print("Syncing all words to Anki...")
    result = word_service.sync_all_to_anki()

    if result.get('success'):
        print(f"✅ Synced {result['synced']}/{result['total']} words (failed: {result['failed']})")
    else:
        print(f"❌ Sync failed: {result.get('error')}")

def main():
    """CLI entry point for anki-gpt-cli command."""
    if len(sys.argv) < 2:
        # Default: interactive add mode
        cmd_add()
        return

    command = sys.argv[1]

    # Configure logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    if command == "add":
        cmd_add()
    elif command == "import":
        cmd_import()
    elif command == "export":
        cmd_export()
    elif command == "sync":
        cmd_sync()
    elif command == "help":
        print("Usage: anki-gpt [command]")
        print("\nCommands:")
        print("  add      Add words via ChatGPT (default, interactive)")
        print("  import   Import words from Anki to database")
        print("  export   Export words from database to Anki")
        print("  sync     Sync all database words to Anki")
        print("  help     Show this help message")
    else:
        print(f"Unknown command: {command}")
        print("Run 'anki-gpt help' for usage information")
        sys.exit(1)

if __name__ == "__main__":
    main()
