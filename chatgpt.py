from openai import OpenAI
from word import Word, WordList

PROMPT = """
I want to learn dutch worlds using Anki flashcards.

I'm going to send you a word OR a phrase in Dutch, and you'll create a word definition for the flashcard for me.

Extra comments for the json schema:
- Etymology (match the etymology format of wiktionary, but make it shorter)
- Related (only add related words that are etymologically related, prefer english, german, russian, french languages if possible)
- Grammar (het/de word, part of speech, parts of the word, like suffix, root, etc, some forms, like past tense.)
- For definitions, if a word has multiple meanings, list top 2-3 most common ones.

If I send a phrases in Dutch, extract the words and create a definition for each word. Prefer frequent or important to know words first. Skip filler words. Ignore words that are very similar to English, like e-mail or computer. Try to extract more words if the phrase is longer, not just 2 or 4 words.

An example:
{
    dutch: "Avontuur",
    "translation": "Adventure",
    "definition_nl": "Een spannende of onverwachte gebeurtenis, vaak met een element van gevaar of ontdekking.",
    "definition_en": "An exciting or unexpected event, often with an element of danger or discovery.",
    "pronunciation": "/ˌaː.vɔnˈtyːr/",
    "grammar": "Noun (het), root: avontuur",
    "examples_nl": ["Het was een groot avontuur om door de jungle te reizen.", "Ze gaan samen op avontuur in een nieuwe stad."],
    "examples_en": ["It was a great adventure to travel through the jungle.", "They are going on an adventure together in a new city."],
    "collocations": ["Op avontuur gaan (to go on an adventure)", "Een spannend avontuur (an exciting adventure)"],
    "etymology": "Borrowed from Old French aventure, derived from Latin adventura (things about to happen), from advenire ("to arrive, to come to"), composed of ad- (towards) + venire (to come). The term evolved in Dutch to refer to exciting or unpredictable events.",
    "related": ["German: Abenteuer (adventure).", "Russian: авантюра (adventure).", "French: aventure (adventure)."]
}

"""

def build_prompt(input_text: str) -> list[dict]:
    return [
        {"role": "developer", "content": PROMPT},
        {"role": "user", "content": input_text},
    ]

def get_definitions(input_text: str) -> list[Word]:
    messages = build_prompt(input_text)

    client = OpenAI()
    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=messages,
        response_format=WordList
    )

    return response.choices[0].message.parsed


if __name__ == "__main__":
    test_input = "hond kat"
    definitions = get_definitions(test_input)
    print(definitions)
