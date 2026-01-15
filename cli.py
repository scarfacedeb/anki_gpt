import sys
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from chatgpt import get_definitions, generate_tags
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

def cmd_regenerate():
    """Regenerate all words in the database, skipping words that already have a level."""
    word_service = WordService()
    all_words = word_service.get_all()

    # Filter words that don't have a level yet
    words_to_regenerate = [word for word in all_words if not word.level or word.level.strip() == '']

    total = len(all_words)
    to_regenerate_count = len(words_to_regenerate)
    skipped_count = total - to_regenerate_count

    print(f"Found {total} total words:")
    print(f"  - {to_regenerate_count} words to regenerate (no level)")
    print(f"  - {skipped_count} words to skip (already have level)")

    if to_regenerate_count == 0:
        print("✅ No words to regenerate!")
        return

    # Ask for confirmation
    response = input(f"\nProceed with regenerating {to_regenerate_count} words in batches of 10? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return

    print("\nStarting regeneration (batches of 10)...")
    success_count = 0
    failed_words = []
    completed_count = 0

    def regenerate_word(word):
        """Regenerate a single word and return result."""
        try:
            result = get_definitions(word.dutch, user_id=0)
            if result.words and len(result.words) > 0:
                new_word = result.words[0]
                # If GPT returns a different Dutch word, delete the original
                # before adding the new one to avoid duplicates.
                try:
                    old_norm = (word.dutch or "").strip().lower()
                    new_norm = (new_word.dutch or "").strip().lower()
                    if new_norm and new_norm != old_norm:
                        # Delete original entry (and its Anki note if synced)
                        word_service.delete(word.dutch)
                        # Create the regenerated word as a new entry
                        _, _ = word_service.create(new_word)
                        return (True, new_word.dutch, new_word.level)
                    else:
                        # Same Dutch term: update in place
                        _, _ = word_service.update(new_word)
                        return (True, new_word.dutch, new_word.level)
                except Exception as inner_e:
                    return (False, word.dutch, f"Post-process error: {inner_e}")
            else:
                return (False, word.dutch, "No data returned")
        except Exception as e:
            return (False, word.dutch, str(e))

    # Process in batches of 10
    batch_size = 10
    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        # Submit all tasks
        future_to_word = {executor.submit(regenerate_word, word): word for word in words_to_regenerate}

        # Process results as they complete
        for future in as_completed(future_to_word):
            word = future_to_word[future]
            completed_count += 1

            try:
                success, dutch, info = future.result()
                if success:
                    success_count += 1
                    print(f"[{completed_count}/{to_regenerate_count}] ✓ {dutch} (level: {info or 'none'})")
                else:
                    failed_words.append(dutch)
                    print(f"[{completed_count}/{to_regenerate_count}] ✗ {dutch} - {info}")
            except Exception as e:
                failed_words.append(word.dutch)
                print(f"[{completed_count}/{to_regenerate_count}] ✗ {word.dutch} - Error: {e}")

    print(f"\n{'='*60}")
    print(f"Regeneration complete!")
    print(f"  ✓ Success: {success_count}/{to_regenerate_count}")
    print(f"  ○ Skipped: {skipped_count} (already have level)")
    if failed_words:
        print(f"  ✗ Failed: {len(failed_words)}")
        print(f"\nFailed words: {', '.join(failed_words)}")


def cmd_generate_tags():
    """Generate tags for words in the database."""
    word_service = WordService()
    all_words = word_service.get_all()
    
    force_all = '--force' in sys.argv
    
    if force_all:
        words_to_tag = all_words
        skipped_count = 0
    else:
        words_to_tag = [word for word in all_words if not word.tags]
        skipped_count = len(all_words) - len(words_to_tag)

    total_to_tag = len(words_to_tag)

    print(f"Found {len(all_words)} total words:")
    print(f"  - {total_to_tag} words to tag")
    if not force_all:
        print(f"  - {skipped_count} words to skip (already have tags)")

    if total_to_tag == 0:
        print("✅ No words to tag!")
        return

    response = input(f"\nProceed with generating tags for {total_to_tag} words in batches of 10? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
        
    print("\nStarting tag generation (batches of 10)...")
    success_count = 0
    failed_words = []
    completed_count = 0

    def process_word_tags(word):
        """Generate and update tags for a single word."""
        try:
            tags = generate_tags(word, user_id=0)
            if tags:
                word.tags = tags
                _, _ = word_service.update(word)
                return (True, word.dutch, ", ".join(tags))
            else:
                return (False, word.dutch, "No tags generated")
        except Exception as e:
            return (False, word.dutch, str(e))

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_word = {executor.submit(process_word_tags, word): word for word in words_to_tag}

        for future in as_completed(future_to_word):
            word = future_to_word[future]
            completed_count += 1
            
            try:
                success, dutch, info = future.result()
                if success:
                    success_count += 1
                    print(f"[{completed_count}/{total_to_tag}] ✓ {dutch} (tags: {info})")
                else:
                    failed_words.append(dutch)
                    print(f"[{completed_count}/{total_to_tag}] ✗ {dutch} - {info}")
            except Exception as e:
                failed_words.append(word.dutch)
                print(f"[{completed_count}/{total_to_tag}] ✗ {word.dutch} - Error: {e}")

    print(f"\n{'='*60}")
    print(f"Tag generation complete!")
    print(f"  ✓ Success: {success_count}/{total_to_tag}")
    if not force_all:
        print(f"  ○ Skipped: {skipped_count}")
    if failed_words:
        print(f"  ✗ Failed: {len(failed_words)}")
        print(f"\nFailed words: {', '.join(failed_words)}")


def cmd_help():
    """Show help message."""
    print("Usage: anki-gpt-cli [command]")
    print("\nCommands:")
    print("  add              Add words via ChatGPT (interactive)")
    print("  import           Import words from Anki to database")
    print("  export           Export words from database to Anki")
    print("  sync             Sync all database words to Anki")
    print("  regenerate       Regenerate all words without a level")
    print("  generate-tags    Generate tags for words without them")
    print("  help             Show this help message")

def main():
    """CLI entry point for anki-gpt-cli command."""
    if len(sys.argv) < 2:
        cmd_help()
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
    elif command == "regenerate":
        cmd_regenerate()
    elif command == "generate-tags":
        cmd_generate_tags()
    elif command == "help":
        cmd_help()
    else:
        print(f"Unknown command: {command}")
        print("Run 'anki-gpt-cli help' for usage information")
        sys.exit(1)

if __name__ == "__main__":
    main()
