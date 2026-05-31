from pydantic import BaseModel, Field

# Centralized list of allowed tags used across the app (UI, prompts, validation)
TAGS_ALL: list[str] = [
    # Grammatical
    "noun", "verb", "adjective", "adverb", "pronoun", "preposition",
    "conjunction", "interjection", "article", "numeral",
    # Usage
    "inburgeringexam", "slang",
]

class Word(BaseModel):
    dutch: str = Field(
        validation_alias="Word or phrase to define in dutch",
        description="The normalized Dutch headword or phrase. Use Dutch only.",
    )
    translation: str = Field(
        description="English translation of the Dutch headword. Use English only; do not write Dutch prose here.",
    )
    definition_nl: str = Field(
        description="Concise definition written in Dutch. Define the meaning directly; do not start by repeating the headword or using '<word> betekent...'.",
    )
    definition_en: str = Field(
        description="Concise definition written in English for an English-speaking learner. Define the meaning directly; do not start by repeating the headword or using '<word> means...'.",
    )
    pronunciation: str = Field(
        description="IPA pronunciation in forward slashes, for example /ˈloː.pə(n)/.",
    )
    grammar: str = Field(
        description="Grammar and morphology explanation written in English. Dutch forms may appear, but all explanatory prose must be English.",
    )
    collocations: list[str] = Field(
        description="Common Dutch collocations, each followed by an English translation in parentheses. Format: 'Dutch phrase (English translation)'.",
    )
    synonyms: list[str] = Field(
        description="Interchangeable Dutch synonyms, each followed by an English gloss in parentheses. Format: 'Dutch synonym (English gloss)'.",
    )
    examples_nl: list[str] = Field(
        description="Example sentences written in Dutch only.",
    )
    examples_en: list[str] = Field(
        description="English translations of examples_nl. Use English only and keep the same order as examples_nl.",
    )
    etymology: str = Field(
        description="Word origin and history written in English. Dutch historical forms may appear, but all explanatory prose must be English.",
    )
    related: list[str] = Field(
        description="Etymologically related words from other languages, with English glosses in parentheses. Do not use Dutch explanatory prose.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Allowed lowercase tags only, for example 'noun' or 'verb'. Add 'inburgeringexam' if useful for the Dutch Inburgering A2 exam.",
    )
    level: str = Field(
        default="",
        description="CEFR difficulty level for Dutch learners. Use only one of A1, A2, B1, B2, C1, C2, or an empty string."
    )
    score: int = Field(
        default=1,
        ge=1,
        le=10,
        description="A score from 1 to 10 indicating how useful or important the word is to learn. 10 is most useful or important."
    )

    model_config = {
        "populate_by_name": True
    }

class WordList(BaseModel):
    words: list[Word]
    context: str | None = Field(
        default=None,
        validation_alias="Extra context to inform the user",
        description="Optional extra context for the user, written in English only.",
    )
    
    model_config = {
        "populate_by_name": True
    }

class WordTags(BaseModel):
    tags: list[str]


def word_to_anki(word: Word) -> dict:
    """Convert a Word object to Anki fields dictionary."""
    return {
        "Word": word.dutch,
        "Translation": word.translation,
        "Definition": word.definition_nl,
        "Definition (eng)": word.definition_en,
        "Pronunciation": word.pronunciation,
        "Grammar": word.grammar,
        "Collocations": "\n".join(word.collocations),
        "Synonyms": "\n".join(word.synonyms),
        "Examples": "\n".join(word.examples_nl),
        "Examples (eng)": "\n".join(word.examples_en),
        "Etymology": word.etymology,
        "Related": "\n".join(word.related)
    }

def word_to_html(word: Word) -> str:
    examples = list(zip(word.examples_nl, word.examples_en))
    examples_html = "".join(
        f"{nl} ({en})" for nl, en in examples
    )

    lines = [
        f"<b>{word.dutch}</b>\n",
        f"<b>Translation:</b> {word.translation}",
        f"<b>Etymology:</b> {word.etymology}",
        f"<b>Grammar:</b> {word.grammar}",
        f"<b>Pronunciation:</b> {word.pronunciation}",
        f"<b>Collocations:</b> {', '.join(word.collocations)}",
        f"<b>Synonyms:</b> {', '.join(word.synonyms)}",
        f"<b>Related:</b> {', '.join(word.related)}",
        f"<b>Tags:</b> {', '.join(word.tags)}",
        f"<b>Score:</b> {word.score}",
        f"<b>Definition:</b> {word.definition_nl} ",
        f"<b>Definition EN:</b> {word.definition_en} ",
        f"<b>Examples:</b><i>{examples_html}</i>"
    ]

    return "\n".join(lines)
