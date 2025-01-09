from chatgpt import get_definitions
from anki import add_notes
from word import Word

def add_word_to_anki(user_input: str) -> list[Word]:
    """
    Main logic:
    1. Send user input to ChatGPT for definitions.
    2. Add new words to Anki.
    3. Return the definitions as Word objects.
    """

    words = get_definitions(user_input).words

    if words:
        add_notes(words)

    return words

if __name__ == "__main__":
    test_input = input("Enter Dutch words or phrases: ")
    word_objects = add_word_to_anki(test_input)
    print(word_objects)
