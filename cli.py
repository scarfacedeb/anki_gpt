from chatgpt import get_definitions
from anki import add_notes, sync_anki
from word import Word, WordList

def add_word_to_anki(user_input: str) -> list[Word]:
    """
    Main logic:
    1. Send user input to ChatGPT for definitions.
    2. Add new words to Anki.
    3. Return the definitions as Word objects.
    """

    response = get_definitions(user_input)
    
    if response.words:
        add_notes(response.words)
        sync_anki()

    return response.words

if __name__ == "__main__":
    test_input = input("Enter Dutch words or phrases: ")
    word_objects = add_word_to_anki(test_input)
    for word in word_objects:
        print(f"\n{word.dutch} - {word.translation}")
        print(f"Definition: {word.definition_nl}")
        print(f"English: {word.definition_en}")
