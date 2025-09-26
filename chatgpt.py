from openai import OpenAI
import os
import logging
from word import Word, WordList
from user_settings import get_user_config

logger = logging.getLogger(__name__)

# Get API key from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-nano")
OPENAI_MODEL_EFFORT = os.getenv("OPENAI_MODEL_EFFORT", "low")

GET_DEFINITIONS_PROMPT = """
You are an expert Dutch linguist and Anki flashcard generator. Always reply in English.

Instructions:
- Always reply in English.
- ALWAYS TREAT GIVEN WORDS AS DUTCH LANGUAGE (for example, given "sleep" is Dutch word to drag, aka slepen), except when specifically told not to with a prefix: "English: ".
- Always include all fields in your response, unless a field is truly invalid or empty for the word.
- Only show related words that are etymologically connected to the Dutch word (no false cognates or superficial similarities).
- Normalize word cases.
- Normalize words to their standard forms: use the infinitive for verbs, singular for nouns, masculine singular for adjectives, and keep past participles as is. Prefer the most common form.
- Keep past participles as is.
- Put normalized word in the "dutch" field.
- In the grammar section, always include verb forms (infinitive, present, past, past participle), past tenses, and any other important grammatical forms or notes (e.g., "het"/"de" for nouns, adjective forms, etc.). Also, if the word is composed of parts (root, suffix, prefix, etc.), clearly list and explain each part.
- For etymology, always fully unwrap the word’s history, especially for complex or long words. Trace the word’s origin step by step, mentioning all relevant languages and roots, but keep it concise and in English.
- For definitions, if a word has multiple meanings, list the top 2-3 most common ones.
- Include synonyms for the Dutch word when available, providing the most common and useful alternatives.
- If a phrase is provided, extract the most important words (ignore filler words and words very similar to English) and create a definition for each. Add the English translation of the whole phrase in the "context" field.
- If the phrase is a known idiom, treat it as a single entity and provide a definition, translation, examples, etymology, and related fields for the idiom as a whole.
- If the whole phrase is sent in quotes, treat it as a single entity and only include the following fields: dutch, translation, examples_nl, examples_en, collocations, etymology, related, and context. Omit grammar, pronunciation, and definitions fields for quoted phrases.
- Example sentences must be natural, relevant, and demonstrate the word’s usage in different contexts and forms (for verbs, show at least one example for a different tense or conjugation).

Examples:
Given input: "avonturen"
{
    dutch: "Avontuur",
    translation: "Adventure",
    definition_nl: "Een spannende of onverwachte gebeurtenis, vaak met een element van gevaar of ontdekking.",
    definition_en: "An exciting or unexpected event, often with an element of danger or discovery.",
    pronunciation: "/ˌaː.vɔnˈtyːr/",
    grammar: "Noun (het), root: avontuur. Parts: a- (prefix, intensifier) + avontuur (root).",
    examples_nl: ["Het was een groot avontuur om door de jungle te reizen.", "Ze gaan samen op avontuur in een nieuwe stad."],
    examples_en: ["It was a great adventure to travel through the jungle.", "They are going on an adventure together in a new city."],
    collocations: ["Op avontuur gaan (to go on an adventure)", "Een spannend avontuur (an exciting adventure)"],
    synonyms: ["Reis (journey)", "Expeditie (expedition)", "Onderneming (undertaking)"],
    etymology: "Borrowed from Old French aventure, from Latin adventura (things about to happen), from advenire ('to arrive, to come to'), composed of ad- (towards) + venire (to come). The term evolved in Dutch to refer to exciting or unpredictable events.",
    related: ["German: Abenteuer (adventure)", "Russian: авантюра (adventure)", "French: aventure (adventure)"]
}

Given input: "loopt"
{
    dutch: "Lopen",
    translation: "To walk / To run",
    definition_nl: "Zich te voet voortbewegen; wandelen.",
    definition_en: "To move on foot; to walk.",
    pronunciation: "/ˈloː.pə(n)/",
    grammar: "Verb (infinitive: lopen, present: loopt, past: liep, past participle: gelopen). Parts: lo- (root) + -pen (suffix, verb ending).",
    examples_nl: ["Ik loop elke ochtend naar mijn werk.", "We hebben gisteren in het park gelopen.", "Hij liep snel naar huis."],
    examples_en: ["I walk to work every morning.", "We walked in the park yesterday.", "He walked home quickly."],
    collocations: ["Een eind lopen (to walk a distance)", "Hard lopen (to run)"],
    synonyms: ["Wandelen (to stroll)", "Stappen (to step)", "Rennen (to run)"],
    etymology: "From Middle Dutch lopen, from Old Dutch *hlaupan, from Proto-Germanic *hlaupaną (to run, leap), from Proto-Indo-European *klewb- (to climb, run). Cognate with English 'leap'.",
    related: ["German: laufen (to run, to walk)", "English: leap (to jump)"]
}
"""

EXTRACT_WORDS_PROMPT = """
I want to learn dutch worlds using Anki flashcards.

I'll send a phrases in Dutch, you need to extract the words from it and return them in a list with items separated by "; ". Prefer frequent or important to know words first. Skip filler words. Ignore words that are very similar to English, like e-mail or computer. Try to extract more words if the phrase is longer, not just 2 or 4 words.

An example phrase: Een spannende of onverwachte gebeurtenis, vaak met een element van gevaar of ontdekking.
Should return: spannende; onverwachte; gebeurtenis; vaak; gevaar; ontdekking
"""

def build_prompt(prompt: str, input_text: str) -> list[dict]:
    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": input_text},
    ]

def get_definitions(input_text: str, user_id: int) -> WordList:
    logger.info(f"Input: {input_text}")

    config = get_user_config(user_id)

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.responses.parse(
        model=config.model,
        reasoning={ 'effort': config.effort },
        text_format=WordList,
        instructions=GET_DEFINITIONS_PROMPT,
        input=input_text,
    )

    result = response.output_parsed

    if hasattr(result, 'words') and result.words:
        for word in result.words:
            logger.info(f"Output: {word.dutch} - {word.translation}")

    return result


def extract_words(input_text: str) -> list[str]:
    messages = build_prompt(EXTRACT_WORDS_PROMPT, input_text)
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.responses.create(
        model=OPENAI_MODEL,
        input=messages,
        reasoning={ 'effort': OPENAI_MODEL_EFFORT }
    )

    return response.output_text.split('; ')


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    test_input = "hond kat of vis"
    definitions = get_definitions(test_input)
    print(definitions)
